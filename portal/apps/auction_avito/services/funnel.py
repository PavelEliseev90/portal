"""
Воронка аукциона Авито:

1. всего лотов
2. участвовали (были ставки)
3. выиграли
4. дошли до оценки (ИО по win RLK)
5. дошли до КД
6. принято (АМ принят / активный ЛО)

+ причины архива с DocRLK.reasonArchive, этап отвала, клик → список.
Разбивка по ЦГ + детализация лотов/РЛ по этапу (?stage=).
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, Subquery
from django.urls import reverse

from auction_avito.models import AvitoLot, AvitoLotCalculation, AvitoLotOffer
from auction_avito.services.analytics import _day_bounds, _pct, resolve_period
from auction_avito.services.outcome import OUTCOME_NAMES, OUTCOME_NOT_TAKEN, OUTCOME_WON
from refs.price_groups import ZG_ORDER, normalize_price_group_display

FUNNEL_COLORS = {
    'total': '#94a3b8',
    'with_bids': '#2563eb',
    'won': '#16a34a',
    'estimation': '#7c3aed',
    'kd': '#ea580c',
    'accepted': '#0f766e',
    'not_taken': '#f59e0b',
}

ZG_UNDEFINED = 'Неопределена'

# Этапы воронки (ключ → подпись / описание)
FUNNEL_STAGES = (
    {
        'key': 'total',
        'title': 'Всего лотов',
        'short': 'Лоты',
        'desc': 'Все лоты за период (по дате окончания или синхронизации).',
        'color_key': 'total',
    },
    {
        'key': 'with_bids',
        'title': 'Участвовали',
        'short': 'Ставки',
        'desc': 'Лоты, где была хотя бы одна наша ставка (bid > 0).',
        'color_key': 'with_bids',
    },
    {
        'key': 'won',
        'title': 'Выиграли',
        'short': 'Выигрыш',
        'desc': 'Итог «выбрали нас» (outcome_code = won).',
        'color_key': 'won',
    },
    {
        'key': 'estimation',
        'title': 'Дошли до оценки',
        'short': 'Оценка',
        'desc': 'По рабочему листу выигрыша создана интерактивная оценка.',
        'color_key': 'estimation',
    },
    {
        'key': 'kd',
        'title': 'Дошли до КД',
        'short': 'КД',
        'desc': (
            'Есть согласованная цена до КД или статус диагностики / '
            'согласования после КД / согласовано / принято.'
        ),
        'color_key': 'kd',
    },
    {
        'key': 'accepted',
        'title': 'Приняты',
        'short': 'Приём',
        'desc': 'Статус «АМ принят» (8) или активный лист оценки (DocLO).',
        'color_key': 'accepted',
    },
)

STAGE_KEYS = {s['key'] for s in FUNNEL_STAGES}

# Статусы ИО: 5 диагностика, 6 после КД, 4 согласовано, 8 принят
_KD_STATUS_IDS = (4, 5, 6, 8)
_ACCEPTED_STATUS_ID = 8


def _parse_zg_filter(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        values = list(raw)
    else:
        values = str(raw).split(',')
    selected = []
    seen = set()
    for item in values:
        name = normalize_price_group_display(str(item or '').strip())
        if not name or name in seen:
            continue
        if name not in ZG_ORDER and name != ZG_UNDEFINED:
            continue
        seen.add(name)
        selected.append(name)
    return selected


def _latest_calc_subqueries():
    latest = (
        AvitoLotCalculation.objects
        .filter(lot=OuterRef('pk'), is_success=True)
        .order_by('-calculated_at', '-pk')
    )
    return (
        Subquery(latest.values('price_group')[:1]),
        Subquery(latest.values('zna')[:1]),
        Subquery(latest.values('estimation_price')[:1]),
    )


def _resolve_lot_zg(price_group_raw, zna, estimation_price) -> str:
    price = zna if zna not in (None, 0, '0', '') else estimation_price
    return normalize_price_group_display(price_group_raw, price=price) or ZG_UNDEFINED


def _empty_bucket(zg: str) -> dict:
    return {
        'zg': zg,
        'total': 0,
        'with_bids': 0,
        'won': 0,
        'estimation': 0,
        'kd': 0,
        'accepted': 0,
        'not_taken': 0,
        'lost': 0,
        'waiting': 0,
        'other_outcome': 0,
    }


def _period_lots_qs(start, end):
    pg_sq, zna_sq, est_sq = _latest_calc_subqueries()
    return (
        AvitoLot.objects
        .filter(
            Q(finish_at__gte=start, finish_at__lte=end)
            | Q(finish_at__isnull=True, synced_at__gte=start, synced_at__lte=end)
        )
        .annotate(
            calc_price_group=pg_sq,
            calc_zna=zna_sq,
            calc_estimation_price=est_sq,
        )
    )


def _parse_reason_archive(value: str | None) -> tuple[str, str]:
    """DocRLK.reasonArchive: «Причина: комментарий»."""
    if not value:
        return '', ''
    parts = str(value).split(':', 1)
    name = parts[0].strip()
    comment = parts[1].strip() if len(parts) > 1 else ''
    return name, comment


def _normalize_archive_reason(type_archive_name: str | None, reason_raw: str | None) -> tuple[str, str]:
    """
    Причина архива именно с РЛ: поле reasonArchive (до «:» + комментарий).
    Справочник type_archive — только запасной вариант, если текст пустой.
    """
    parsed_name, comment = _parse_reason_archive(reason_raw)
    if parsed_name:
        return parsed_name, comment
    raw = (reason_raw or '').strip()
    if raw:
        return raw[:120], ''
    type_name = (type_archive_name or '').strip()
    if type_name:
        return type_name, ''
    return 'Без указания причины', ''


def _load_rlk_archive_info(rlk_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Причина архива с DocRLK (reasonArchive), не из сторонних сущностей."""
    out: dict[int, dict[str, Any]] = {}
    if not rlk_ids:
        return out
    from documents.models import DocRLK

    for row in (
        DocRLK.objects
        .filter(pk__in=rlk_ids)
        .values(
            'id', 'nomer', 'archive', 'dateArchive', 'reasonArchive',
            'type_archive_id', 'type_archive__name',
        )
    ):
        reason_raw = (row.get('reasonArchive') or '').strip()
        reason_name, reason_comment = _normalize_archive_reason(
            row.get('type_archive__name'),
            reason_raw,
        )
        archived = bool(row.get('archive'))
        has_reason_text = bool(reason_raw) or bool(row.get('type_archive_id'))
        if not archived and not has_reason_text:
            reason_name = ''
            reason_comment = ''
        out[row['id']] = {
            'rlk_nomer': row.get('nomer') or '',
            'archive': archived,
            'date_archive': row.get('dateArchive'),
            'reason_raw': reason_raw,
            'type_archive_id': row.get('type_archive_id'),
            'type_archive_name': (row.get('type_archive__name') or '').strip(),
            'archive_reason': reason_name if (archived or has_reason_text) else '',
            'archive_comment': reason_comment if (archived or has_reason_text) else '',
        }
    return out


def _drop_stage_key(info: dict) -> str:
    """Последний достигнутый этап для выигранного, но не принятого лота."""
    if info.get('accepted'):
        return 'accepted'
    if info.get('kd'):
        return 'kd_no_accepted'
    if info.get('estimation'):
        return 'estimation_no_kd'
    if info.get('won'):
        return 'won_no_estimation'
    return 'other'


DROP_STAGE_LABELS = {
    'won_no_estimation': 'Выигрыш → без оценки',
    'estimation_no_kd': 'Оценка → без КД',
    'kd_no_accepted': 'КД → без приёма',
    'accepted': 'Приняты',
    'other': 'Прочее',
}


def _load_estimation_flags(rlk_ids: list[int]) -> dict[int, dict[str, Any]]:
    """
    По DocRLK id → флаги ИО / КД / принят.
    """
    flags: dict[int, dict[str, Any]] = {}
    if not rlk_ids:
        return flags

    from documents.models import DocLO
    from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK

    for rid in rlk_ids:
        flags[rid] = {
            'has_estimation': False,
            'reached_kd': False,
            'accepted': False,
            'status_id': None,
            'status_name': '',
            'interactiv_rlk_id': None,
            'estimation_id': None,
            'price_before_kd': 0,
            'price_after_kd': 0,
            'rlk_nomer': '',
        }

    # ИО по РЛ (основной путь)
    for row in (
        RegInteractivOcenkaRLK.objects
        .filter(rlk_id__in=rlk_ids)
        .select_related('status', 'page_soglasovanie', 'rlk', 'estimation')
        .values(
            'id',
            'rlk_id',
            'estimation_id',
            'status_id',
            'status__name',
            'page_soglasovanie__price_before_kd',
            'page_soglasovanie__price_after_kd',
            'rlk__nomer',
        )
    ):
        rid = row['rlk_id']
        if rid not in flags:
            continue
        f = flags[rid]
        f['has_estimation'] = True
        f['interactiv_rlk_id'] = row['id']
        f['estimation_id'] = row['estimation_id']
        f['status_id'] = row['status_id']
        f['status_name'] = row['status__name'] or ''
        f['price_before_kd'] = int(row['page_soglasovanie__price_before_kd'] or 0)
        f['price_after_kd'] = int(row['page_soglasovanie__price_after_kd'] or 0)
        f['rlk_nomer'] = row['rlk__nomer'] or ''

    # Fallback: оценка напрямую на DocRLK
    missing = [rid for rid, f in flags.items() if not f['has_estimation']]
    if missing:
        for row in (
            RegInteractivOcenka.objects
            .filter(rlk_id__in=missing)
            .select_related('status', 'page_soglasovanie', 'rlk')
            .values(
                'id',
                'rlk_id',
                'status_id',
                'status__name',
                'page_soglasovanie__price_before_kd',
                'page_soglasovanie__price_after_kd',
                'rlk__nomer',
            )
        ):
            rid = row['rlk_id']
            f = flags[rid]
            f['has_estimation'] = True
            f['estimation_id'] = row['id']
            f['status_id'] = row['status_id']
            f['status_name'] = row['status__name'] or ''
            f['price_before_kd'] = int(row['page_soglasovanie__price_before_kd'] or 0)
            f['price_after_kd'] = int(row['page_soglasovanie__price_after_kd'] or 0)
            f['rlk_nomer'] = row['rlk__nomer'] or f['rlk_nomer']

    accepted_rlk = set(
        DocLO.objects.filter(rlk_id__in=rlk_ids, active=True)
        .values_list('rlk_id', flat=True)
        .distinct()
    )

    for rid, f in flags.items():
        status_id = f['status_id']
        if (
            status_id in _KD_STATUS_IDS
            or f['price_before_kd'] > 0
            or f['price_after_kd'] > 0
        ):
            f['reached_kd'] = True
        if status_id == _ACCEPTED_STATUS_ID or rid in accepted_rlk:
            f['accepted'] = True
            f['reached_kd'] = True
            f['has_estimation'] = True

    return flags


def _attach_missing_win_rlk_ids(offers_by_lot: dict[int, list]) -> None:
    """Проставляет win_rlk_id по UIN/номеру 1С, если FK пустой."""
    from documents.models import DocRLK

    need_uin = []
    need_num = []
    for offers in offers_by_lot.values():
        for o in offers:
            if o.get('win_rlk_id'):
                continue
            uin = (o.get('win_rlk_uin') or '').strip()
            number = (o.get('win_rlk_number') or '').strip()
            if uin:
                need_uin.append(uin)
            elif number:
                need_num.append(number)
    by_uin = {}
    by_num = {}
    if need_uin:
        for pk, uin in DocRLK.objects.filter(uin__in=list(set(need_uin))).values_list('pk', 'uin'):
            if uin and uin not in by_uin:
                by_uin[uin] = pk
    if need_num:
        for pk, nomer in DocRLK.objects.filter(nomer__in=list(set(need_num))).values_list('pk', 'nomer'):
            if nomer and nomer not in by_num:
                by_num[nomer] = pk
    if not by_uin and not by_num:
        return
    for offers in offers_by_lot.values():
        for o in offers:
            if o.get('win_rlk_id'):
                continue
            uin = (o.get('win_rlk_uin') or '').strip()
            number = (o.get('win_rlk_number') or '').strip()
            rid = by_uin.get(uin) if uin else None
            if rid is None and number:
                rid = by_num.get(number)
            if rid:
                o['win_rlk_id'] = rid


def _classify_lot_offers(offers: list[dict]) -> dict[str, Any]:
    has_bid = any(int(o.get('bid') or 0) > 0 for o in offers)
    outcomes = {(o.get('outcome_code') or '').strip() for o in offers}
    is_won = OUTCOME_WON in outcomes
    is_lost = 'lost' in outcomes and not is_won
    is_waiting = 'waiting_seller' in outcomes and not is_won and not is_lost
    win_offer = None
    if is_won:
        won_offers = [o for o in offers if (o.get('outcome_code') or '').strip() == OUTCOME_WON]
        for o in won_offers:
            if o.get('win_rlk_id') or (o.get('win_rlk_number') or '').strip() or (o.get('win_rlk_uin') or '').strip():
                win_offer = o
                break
        if win_offer is None and won_offers:
            win_offer = won_offers[0]
    if win_offer is None and offers:
        for o in offers:
            if o.get('win_rlk_id'):
                win_offer = o
                break

    return {
        'has_bid': has_bid,
        'is_won': is_won,
        'is_not_taken': OUTCOME_NOT_TAKEN in outcomes and not is_won,
        'is_lost': is_lost,
        'is_waiting': is_waiting,
        'outcomes': outcomes,
        'win_offer': win_offer,
        'best_bid': max((int(o.get('bid') or 0) for o in offers), default=0),
    }


def _build_lot_pipeline(request) -> tuple[list[dict], dict, list[str], Any, Any]:
    """
    Собирает по каждому лоту флаги воронки.
    Возвращает (lot_infos, by_zg, selected_zg, date_from, date_to).
    """
    date_from, date_to = resolve_period(request, default_days=30)
    start, end = _day_bounds(date_from, date_to)
    selected_zg = _parse_zg_filter(request.GET.getlist('zg') or request.GET.get('zg'))

    lots_qs = _period_lots_qs(start, end)
    lot_rows = list(lots_qs.values(
        'id', 'lot_id', 'finish_at', 'synced_at', 'seller_place_name',
        'calc_price_group', 'calc_zna', 'calc_estimation_price',
    ))
    lot_ids = [row['id'] for row in lot_rows]

    offers_by_lot: dict[int, list] = defaultdict(list)
    if lot_ids:
        for offer in (
            AvitoLotOffer.objects
            .filter(lot_id__in=lot_ids)
            .values(
                'id', 'lot_id', 'lot_offer_id', 'bid', 'outcome_code',
                'outcome_title', 'win_rlk_id', 'win_rlk_number', 'win_rlk_uin',
            )
        ):
            offers_by_lot[offer['lot_id']].append(offer)

    # Дорезолв DocRLK по UIN/номеру, если FK ещё не проставлен
    _attach_missing_win_rlk_ids(offers_by_lot)

    win_rlk_ids = []
    for offers in offers_by_lot.values():
        for o in offers:
            if o.get('win_rlk_id'):
                win_rlk_ids.append(o['win_rlk_id'])
    win_rlk_ids = list(dict.fromkeys(win_rlk_ids))
    est_flags = _load_estimation_flags(win_rlk_ids)
    archive_info = _load_rlk_archive_info(win_rlk_ids)

    by_zg = {zg: _empty_bucket(zg) for zg in ZG_ORDER}
    lot_infos = []

    for row in lot_rows:
        zg = _resolve_lot_zg(
            row.get('calc_price_group'),
            row.get('calc_zna'),
            row.get('calc_estimation_price'),
        )
        if zg not in by_zg:
            by_zg[zg] = _empty_bucket(zg)
        if selected_zg and zg not in selected_zg:
            continue

        offers = offers_by_lot.get(row['id'], [])
        cls = _classify_lot_offers(offers)
        win_offer = cls['win_offer'] if cls['is_won'] else None
        rlk_id = win_offer.get('win_rlk_id') if win_offer else None
        ef = est_flags.get(rlk_id) if rlk_id else None
        ar = archive_info.get(rlk_id) if rlk_id else None

        has_estimation = bool(ef and ef['has_estimation'])
        reached_kd = bool(ef and ef['reached_kd'])
        accepted = bool(ef and ef['accepted'])
        # Воронка: каждый следующий этап ⊆ предыдущего
        if not cls['is_won']:
            has_estimation = reached_kd = accepted = False
        if not has_estimation:
            reached_kd = accepted = False
        if not reached_kd:
            accepted = False

        archive = bool(ar and ar['archive'])
        archive_reason = (ar.get('archive_reason') or '') if ar else ''
        if archive and not archive_reason:
            archive_reason = 'Без указания причины'

        info = {
            'id': row['id'],
            'lot_id': row['lot_id'],
            'zg': zg,
            'finish_at': row.get('finish_at'),
            'seller_place_name': row.get('seller_place_name') or '',
            'has_bid': cls['has_bid'],
            'won': cls['is_won'],
            'estimation': has_estimation,
            'kd': reached_kd,
            'accepted': accepted,
            'not_taken': cls['is_not_taken'],
            'lost': cls['is_lost'],
            'waiting': cls['is_waiting'],
            'best_bid': cls['best_bid'],
            'outcome_code': (
                (win_offer or {}).get('outcome_code')
                or (next(iter(cls['outcomes'] - {''}), '') if cls['outcomes'] else '')
            ),
            'outcome_title': (win_offer or {}).get('outcome_title') or '',
            'win_rlk_id': rlk_id,
            'win_rlk_number': (win_offer or {}).get('win_rlk_number') or (
                (ar.get('rlk_nomer') if ar else '') or (ef.get('rlk_nomer') if ef else '')
            ),
            'win_rlk_uin': (win_offer or {}).get('win_rlk_uin') or '',
            'lot_offer_id': (win_offer or {}).get('lot_offer_id'),
            'status_id': ef.get('status_id') if ef else None,
            'status_name': ef.get('status_name') if ef else '',
            'price_before_kd': ef.get('price_before_kd') if ef else 0,
            'price_after_kd': ef.get('price_after_kd') if ef else 0,
            'estimation_price': row.get('calc_estimation_price'),
            'zna': row.get('calc_zna'),
            'rlk_archive': archive,
            'archive_reason': archive_reason if archive else '',
            'archive_comment': (ar.get('archive_comment') or '') if (ar and archive) else '',
            'date_archive': ar.get('date_archive') if ar else None,
            'drop_stage': '',
        }
        if info['won']:
            info['drop_stage'] = _drop_stage_key(info)
        lot_infos.append(info)

        bucket = by_zg[zg]
        bucket['total'] += 1
        if info['has_bid']:
            bucket['with_bids'] += 1
        if info['won']:
            bucket['won'] += 1
        elif info['not_taken']:
            bucket['not_taken'] += 1
        elif info['lost']:
            bucket['lost'] += 1
        elif info['waiting']:
            bucket['waiting'] += 1
        elif info['has_bid'] and cls['outcomes'] - {''}:
            bucket['other_outcome'] += 1
        if info['estimation']:
            bucket['estimation'] += 1
        if info['kd']:
            bucket['kd'] += 1
        if info['accepted']:
            bucket['accepted'] += 1

    return lot_infos, by_zg, selected_zg, date_from, date_to


def _summary_from_lots(lot_infos: list[dict]) -> dict:
    s = {
        'total': len(lot_infos),
        'with_bids': sum(1 for x in lot_infos if x['has_bid']),
        'won': sum(1 for x in lot_infos if x['won']),
        'estimation': sum(1 for x in lot_infos if x['estimation']),
        'kd': sum(1 for x in lot_infos if x['kd']),
        'accepted': sum(1 for x in lot_infos if x['accepted']),
        'not_taken': sum(1 for x in lot_infos if x['not_taken']),
        'lost': sum(1 for x in lot_infos if x['lost']),
        'waiting': sum(1 for x in lot_infos if x['waiting']),
    }
    s.update({
        'bid_share': _pct(s['with_bids'], s['total']),
        'win_share_of_total': _pct(s['won'], s['total']),
        'win_share_of_bids': _pct(s['won'], s['with_bids']),
        'estimation_share_of_won': _pct(s['estimation'], s['won']),
        'kd_share_of_estimation': _pct(s['kd'], s['estimation']),
        'accepted_share_of_kd': _pct(s['accepted'], s['kd']),
        'accepted_share_of_won': _pct(s['accepted'], s['won']),
        'not_taken_share_of_bids': _pct(s['not_taken'], s['with_bids']),
    })
    return s


def _stage_query_string(
    request,
    stage: str,
    *,
    archive_reason: str | None = None,
    drop_stage: str | None = None,
) -> str:
    params = []
    date_from = (request.GET.get('date_from') or '').strip()
    date_to = (request.GET.get('date_to') or '').strip()
    if date_from:
        params.append(('date_from', date_from))
    if date_to:
        params.append(('date_to', date_to))
    for zg in request.GET.getlist('zg'):
        if zg:
            params.append(('zg', zg))
    if stage:
        params.append(('stage', stage))
    reason = (request.GET.get('archive_reason') or '').strip() if archive_reason is None else archive_reason
    if reason:
        params.append(('archive_reason', reason))
    drop = (request.GET.get('drop_stage') or '').strip() if drop_stage is None else drop_stage
    if drop:
        params.append(('drop_stage', drop))
    return urlencode(params)


def _filter_archive_rows(rows: list[dict], archive_reason: str, drop_stage: str = '') -> list[dict]:
    out = rows
    if archive_reason == '__archived__':
        out = [x for x in out if x.get('rlk_archive')]
    elif archive_reason == '__not_archived__':
        out = [x for x in out if x.get('win_rlk_id') and not x.get('rlk_archive')]
    elif archive_reason == '__no_rlk__':
        out = [x for x in out if x.get('won') and not x.get('win_rlk_id')]
    elif archive_reason:
        out = [x for x in out if x.get('rlk_archive') and x.get('archive_reason') == archive_reason]
    if drop_stage:
        out = [x for x in out if x.get('drop_stage') == drop_stage]
    return out


def build_archive_reason_stats(lot_infos: list[dict], request) -> dict:
    """
    Систематизация причин архива РЛ среди выигранных лотов.
    """
    won = [x for x in lot_infos if x.get('won')]
    won_count = len(won)
    with_rlk = [x for x in won if x.get('win_rlk_id')]
    archived = [x for x in with_rlk if x.get('rlk_archive')]
    not_archived = [x for x in with_rlk if not x.get('rlk_archive')]
    no_rlk = [x for x in won if not x.get('win_rlk_id')]
    not_accepted = [x for x in won if not x.get('accepted')]
    archived_not_accepted = [x for x in archived if not x.get('accepted')]

    # причины среди всех архивных РЛ выигрышей
    by_reason: dict[str, dict] = {}
    for item in archived:
        name = item.get('archive_reason') or 'Без указания причины'
        bucket = by_reason.get(name)
        if bucket is None:
            bucket = {
                'name': name,
                'count': 0,
                'not_accepted': 0,
                'by_drop': defaultdict(int),
                'comments': defaultdict(int),
            }
            by_reason[name] = bucket
        bucket['count'] += 1
        if not item.get('accepted'):
            bucket['not_accepted'] += 1
        bucket['by_drop'][item.get('drop_stage') or 'other'] += 1
        comment = (item.get('archive_comment') or '').strip()
        if comment:
            # короткие частые комментарии
            key = comment if len(comment) <= 80 else comment[:77] + '…'
            bucket['comments'][key] += 1

    reasons = []
    for name, bucket in sorted(by_reason.items(), key=lambda kv: (-kv[1]['count'], kv[0].lower())):
        drop_rows = [
            {
                'key': dk,
                'label': DROP_STAGE_LABELS.get(dk, dk),
                'count': cnt,
            }
            for dk, cnt in sorted(bucket['by_drop'].items(), key=lambda kv: -kv[1])
            if cnt
        ]
        top_comments = [
            {'text': text, 'count': cnt}
            for text, cnt in sorted(bucket['comments'].items(), key=lambda kv: -kv[1])[:5]
        ]
        reasons.append({
            'name': name,
            'count': bucket['count'],
            'share_of_archived': _pct(bucket['count'], len(archived)),
            'share_of_won': _pct(bucket['count'], won_count),
            'not_accepted': bucket['not_accepted'],
            'drop_rows': drop_rows,
            'top_comments': top_comments,
            'detail_url': '?' + _stage_query_string(
                request, 'won', archive_reason=name, drop_stage='',
            ),
        })

    # матрица: причина × этап отвала
    drop_order = [
        'won_no_estimation',
        'estimation_no_kd',
        'kd_no_accepted',
        'accepted',
    ]
    matrix_rows = []
    for reason in reasons:
        name = reason['name']
        src = by_reason[name]['by_drop']
        cells = [int(src.get(dk) or 0) for dk in drop_order]
        matrix_rows.append({'name': name, 'cells': cells})
    matrix = {
        'drop_labels': [DROP_STAGE_LABELS[k] for k in drop_order],
        'rows': matrix_rows,
    }

    structural = [
        {
            'key': '__no_rlk__',
            'name': 'Нет рабочего листа',
            'count': len(no_rlk),
            'desc': 'Выигрыш без связанного DocRLK (РЛ ещё не создан или не подтянулся).',
            'detail_url': '?' + _stage_query_string(
                request, 'won', archive_reason='__no_rlk__', drop_stage='',
            ),
        },
        {
            'key': '__not_archived__',
            'name': 'РЛ не в архиве',
            'count': len(not_archived),
            'desc': 'Рабочий лист есть, но ещё не отправлен в архив.',
            'detail_url': '?' + _stage_query_string(
                request, 'won', archive_reason='__not_archived__', drop_stage='',
            ),
        },
        {
            'key': '__archived__',
            'name': 'РЛ в архиве',
            'count': len(archived),
            'desc': 'Все выигрыши с архивным РЛ (любая причина).',
            'detail_url': '?' + _stage_query_string(
                request, 'won', archive_reason='__archived__', drop_stage='',
            ),
        },
    ]

    drop_counts = defaultdict(int)
    for item in won:
        drop_counts[item.get('drop_stage') or 'other'] += 1
    drop_summary = []
    for key in drop_order:
        cnt = int(drop_counts.get(key) or 0)
        drop_summary.append({
            'key': key,
            'label': DROP_STAGE_LABELS.get(key, key),
            'count': cnt,
            'share_of_won': _pct(cnt, won_count),
            'detail_url': '?' + _stage_query_string(
                request, 'won', archive_reason='', drop_stage=key,
            ),
        })

    return {
        'won': won_count,
        'with_rlk': len(with_rlk),
        'archived': len(archived),
        'not_archived': len(not_archived),
        'no_rlk': len(no_rlk),
        'not_accepted': len(not_accepted),
        'archived_not_accepted': len(archived_not_accepted),
        'archived_share_of_won': _pct(len(archived), won_count),
        'structural': structural,
        'reasons': reasons,
        'matrix': matrix,
        'matrix_json': json.dumps(matrix, ensure_ascii=False),
        'drop_summary': drop_summary,
        'hint': (
            'Причина архива берётся с рабочего листа (поле reasonArchive: «причина: комментарий»). '
            'Справочник type_archive — только если текст на РЛ пустой. '
            'Клик по причине или этапу отвала открывает список лотов.'
        ),
    }


def _vehicle_labels(lot_ids: list[int]) -> dict[int, str]:
    if not lot_ids:
        return {}
    labels = {}
    lots = (
        AvitoLot.objects.filter(pk__in=lot_ids)
        .select_related('vehicle_avito', 'vehicle_autohub')
    )
    for lot in lots:
        v = getattr(lot, 'vehicle_avito', None)
        parts = []
        if v is not None:
            for p in (v.brand_name, v.model_name, v.generation_name, v.year):
                if p not in (None, ''):
                    parts.append(str(p))
        if not parts:
            ah = getattr(lot, 'vehicle_autohub', None)
            if ah is not None and ah.year:
                parts.append(str(ah.year))
        labels[lot.pk] = ' '.join(parts).strip() or f'Лот {lot.lot_id}'
    return labels


def build_funnel_stage_rows(lot_infos: list[dict], stage: str) -> list[dict]:
    """Фильтр лотов по этапу воронки."""
    key_map = {
        'total': None,
        'with_bids': 'has_bid',
        'won': 'won',
        'estimation': 'estimation',
        'kd': 'kd',
        'accepted': 'accepted',
    }
    field = key_map.get(stage)
    if field is None:
        rows = list(lot_infos)
    else:
        rows = [x for x in lot_infos if x.get(field)]
    return rows


def enrich_detail_rows(rows: list[dict]) -> list[dict]:
    labels = _vehicle_labels([r['id'] for r in rows])
    out = []
    for r in rows:
        item = dict(r)
        item['vehicle_label'] = labels.get(r['id'], f"Лот {r.get('lot_id')}")
        item['lot_url'] = reverse('auction_avito:lot_detail', kwargs={'pk': r['id']})
        item['rlk_url'] = f"/docs_rlk/{r['win_rlk_id']}/" if r.get('win_rlk_id') else ''
        item['eco_url'] = f"/eco/{r['win_rlk_id']}/" if r.get('win_rlk_id') else ''
        item['estimation_url'] = (
            f"/estimations/{r['win_rlk_id']}/" if r.get('win_rlk_id') else ''
        )
        item['drop_stage_label'] = DROP_STAGE_LABELS.get(item.get('drop_stage') or '', '')
        out.append(item)
    return out


def build_funnel_context(request) -> dict:
    lot_infos, by_zg, selected_zg, date_from, date_to = _build_lot_pipeline(request)
    summary = _summary_from_lots(lot_infos)
    archive_stats = build_archive_reason_stats(lot_infos, request)

    zg_list = [zg for zg in ZG_ORDER if by_zg.get(zg, {}).get('total', 0) > 0]
    for zg, bucket in by_zg.items():
        if zg not in zg_list and bucket['total'] > 0:
            zg_list.append(zg)
    if not zg_list and selected_zg:
        zg_list = [zg for zg in ZG_ORDER if zg in selected_zg] or list(selected_zg)
    if not zg_list:
        zg_list = list(ZG_ORDER)

    rows = []
    for zg in zg_list:
        b = by_zg.get(zg) or _empty_bucket(zg)
        rows.append({
            **b,
            'bid_share': _pct(b['with_bids'], b['total']),
            'win_share_of_total': _pct(b['won'], b['total']),
            'win_share_of_bids': _pct(b['won'], b['with_bids']),
            'estimation_share_of_won': _pct(b['estimation'], b['won']),
            'kd_share_of_estimation': _pct(b['kd'], b['estimation']),
            'accepted_share_of_kd': _pct(b['accepted'], b['kd']),
            'color': FUNNEL_COLORS['total'],
        })

    chart = {
        'labels': zg_list,
        'datasets': [
            {
                'label': 'Всего лотов',
                'data': [(by_zg.get(zg) or {}).get('total', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['total'],
                'borderRadius': 6,
            },
            {
                'label': 'Участвовали',
                'data': [(by_zg.get(zg) or {}).get('with_bids', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['with_bids'],
                'borderRadius': 6,
            },
            {
                'label': 'Выиграли',
                'data': [(by_zg.get(zg) or {}).get('won', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['won'],
                'borderRadius': 6,
            },
            {
                'label': 'Оценка',
                'data': [(by_zg.get(zg) or {}).get('estimation', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['estimation'],
                'borderRadius': 6,
            },
            {
                'label': 'КД',
                'data': [(by_zg.get(zg) or {}).get('kd', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['kd'],
                'borderRadius': 6,
            },
            {
                'label': 'Приняты',
                'data': [(by_zg.get(zg) or {}).get('accepted', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['accepted'],
                'borderRadius': 6,
            },
        ],
    }

    # Этапы с конверсиями и ссылками на детализацию
    stage_counts = {
        'total': summary['total'],
        'with_bids': summary['with_bids'],
        'won': summary['won'],
        'estimation': summary['estimation'],
        'kd': summary['kd'],
        'accepted': summary['accepted'],
    }
    prev_count = None
    stages = []
    for meta in FUNNEL_STAGES:
        key = meta['key']
        count = stage_counts[key]
        of_prev = _pct(count, prev_count) if prev_count is not None else 100
        of_total = _pct(count, summary['total'])
        stages.append({
            **meta,
            'count': count,
            'of_prev': of_prev,
            'of_total': of_total,
            'color': FUNNEL_COLORS[meta['color_key']],
            'detail_url': '?' + _stage_query_string(request, key, archive_reason='', drop_stage=''),
        })
        prev_count = count

    active_stage = (request.GET.get('stage') or '').strip()
    if active_stage not in STAGE_KEYS:
        active_stage = ''

    archive_reason = (request.GET.get('archive_reason') or '').strip()
    drop_stage = (request.GET.get('drop_stage') or '').strip()
    if drop_stage and drop_stage not in DROP_STAGE_LABELS:
        drop_stage = ''

    # если фильтр архива/отвала без stage — показываем выигрыши
    if (archive_reason or drop_stage) and not active_stage:
        active_stage = 'won'

    detail = None
    if active_stage:
        stage_meta = next(s for s in FUNNEL_STAGES if s['key'] == active_stage)
        filtered = build_funnel_stage_rows(lot_infos, active_stage)
        filtered = _filter_archive_rows(filtered, archive_reason, drop_stage)

        detail_title = stage_meta['title']
        detail_desc = stage_meta['desc']
        if archive_reason == '__archived__':
            detail_title = f'{detail_title} · РЛ в архиве'
            detail_desc = 'Выигрыши с архивным рабочим листом.'
        elif archive_reason == '__not_archived__':
            detail_title = f'{detail_title} · РЛ не в архиве'
            detail_desc = 'Есть DocRLK, архив ещё не проставлен.'
        elif archive_reason == '__no_rlk__':
            detail_title = f'{detail_title} · нет РЛ'
            detail_desc = 'Выигрыш без связанного рабочего листа.'
        elif archive_reason:
            detail_title = f'{detail_title} · архив: {archive_reason}'
            detail_desc = f'Причина архива РЛ: «{archive_reason}».'
        if drop_stage:
            detail_title = f'{detail_title} · {DROP_STAGE_LABELS.get(drop_stage, drop_stage)}'
            detail_desc = (detail_desc + ' ' if detail_desc else '') + (
                f'Этап отвала: {DROP_STAGE_LABELS.get(drop_stage, drop_stage)}.'
            )

        paginator = Paginator(filtered, 50)
        page_num = 1
        try:
            page_num = max(1, int(request.GET.get('page') or 1))
        except (TypeError, ValueError):
            page_num = 1
        page_obj = paginator.get_page(page_num)
        detail_rows = enrich_detail_rows(list(page_obj.object_list))

        def _page_url(n):
            q = []
            if date_from:
                q.append(('date_from', date_from.isoformat()))
            if date_to:
                q.append(('date_to', date_to.isoformat()))
            for zg in selected_zg:
                q.append(('zg', zg))
            q.append(('stage', active_stage))
            if archive_reason:
                q.append(('archive_reason', archive_reason))
            if drop_stage:
                q.append(('drop_stage', drop_stage))
            if n > 1:
                q.append(('page', str(n)))
            return '?' + urlencode(q)

        detail = {
            'stage': active_stage,
            'title': detail_title,
            'desc': detail_desc,
            'count': len(filtered),
            'rows': detail_rows,
            'page_obj': page_obj,
            'page_urls': {
                'prev': _page_url(page_obj.previous_page_number()) if page_obj.has_previous() else '',
                'next': _page_url(page_obj.next_page_number()) if page_obj.has_next() else '',
            },
            'archive_reason': archive_reason,
            'drop_stage': drop_stage,
        }

    return {
        'type': 'auction_avito_funnel',
        'filters': {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'zg': selected_zg,
            'stage': active_stage,
            'archive_reason': archive_reason,
            'drop_stage': drop_stage,
        },
        'zg_choices': ZG_ORDER,
        'summary': summary,
        'stages': stages,
        'rows': rows,
        'chart': chart,
        'chart_json': json.dumps(chart, ensure_ascii=False),
        'funnel_colors': FUNNEL_COLORS,
        'outcome_labels': {
            'won': OUTCOME_NAMES.get(OUTCOME_WON, 'Выбрали нас'),
            'not_taken': OUTCOME_NAMES.get(OUTCOME_NOT_TAKEN, 'Не обработан'),
        },
        'archive': archive_stats,
        'detail': detail,
        'hint': (
            'ЦГ — из последнего успешного расчёта выкупа. '
            'Оценка / КД / приём — по рабочему листу выигрыша и статусу интерактивной оценки. '
            'Клик по этапу или причине архива открывает расшифровку лотов и РЛ.'
        ),
    }
