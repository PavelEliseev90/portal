"""
Итоги завершённых лотов Maxposter (решение продавца).

Источник: страница лота / dealer/auction/{lotOfferId}/view или API оффера.
Тексты на UI Maxposter (наблюдаемые / эвристики):
- «Аукцион завершен» + «Ждём решения продавца…» → waiting_seller
- формулировки про выбор нас / победу → won
- другой покупатель / не выбраны → lost
- отмена → canceled
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.html import escape

from auction_avito.services.offer_status import STATUS_NAMES, TERMINAL_OFFER_STATUSES

OUTCOME_WAITING = 'waiting_seller'
OUTCOME_WON = 'won'
OUTCOME_LOST = 'lost'
OUTCOME_CANCELED = 'canceled'
OUTCOME_UNKNOWN = 'unknown'

OUTCOME_NAMES = {
    OUTCOME_WAITING: 'Ждём решения продавца',
    OUTCOME_WON: 'Выигран',
    OUTCOME_LOST: 'Проигран',
    OUTCOME_CANCELED: 'Отменён',
    OUTCOME_UNKNOWN: 'Итог неизвестен',
}

# Финальные исходы — повторный опрос не нужен (кроме ручного).
FINAL_OUTCOMES = frozenset({OUTCOME_WON, OUTCOME_LOST, OUTCOME_CANCELED})

# Маппинг сырого status.status с ленты Maxposter → portal status_code.
MAXPOSTER_STATUS_MAP = {
    'ended': 'finished',
    'finished': 'finished',
    'canceled': 'canceled',
    'cancelled': 'canceled',
    'won': 'won',
    'lost': 'lost',
    'inprogress': 'inprogress',
}

_WON_RE = re.compile(
    r'вас\s+выбрали|вы\s+выиграл|выбран[аы]?\s+ваш[аеи]|поздравляем|'
    r'лот\s+ваш|вы\s+победил|продавец\s+выбрал\s+вас|winner|you\s+won',
    re.I,
)
_LOST_RE = re.compile(
    r'выбран\s+друг|другой\s+участник|не\s+выбран|проиграл|'
    r'лот\s+достался|продавец\s+выбрал\s+друг|you\s+lost|another\s+bidder',
    re.I,
)
_WAIT_RE = re.compile(
    r'ждём\s+решения|ждем\s+решения|решения\s+продавца|'
    r'день[-–—]?\s*два|ожида(ем|ние)\s+решени',
    re.I,
)
_CANCEL_RE = re.compile(r'отмен[её]н|canceled|cancelled|снят\s+с\s+аукциона', re.I)
_FINISHED_TITLE_RE = re.compile(r'аукцион\s+заверш', re.I)


def normalize_maxposter_status(status_code: str | None) -> str:
    code = (status_code or '').strip()
    return MAXPOSTER_STATUS_MAP.get(code, code)


def _norm_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip())


def classify_outcome_text(
    *,
    title: str = '',
    detail: str = '',
    blob: str = '',
    status_code: str = '',
) -> dict[str, str]:
    """
    Классифицирует итог по текстам со страницы/API.
    Возвращает outcome_code, outcome_title, outcome_detail, status_code.
    """
    title = _norm_spaces(title)
    detail = _norm_spaces(detail)
    blob = _norm_spaces(blob) or _norm_spaces(f'{title} {detail}')
    raw_status = normalize_maxposter_status(status_code)

    if raw_status == OUTCOME_WON or _WON_RE.search(blob):
        return {
            'outcome_code': OUTCOME_WON,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WON],
            'status_code': OUTCOME_WON,
        }
    if raw_status == OUTCOME_LOST or _LOST_RE.search(blob):
        return {
            'outcome_code': OUTCOME_LOST,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_LOST],
            'status_code': OUTCOME_LOST,
        }
    if raw_status == OUTCOME_CANCELED or _CANCEL_RE.search(blob):
        return {
            'outcome_code': OUTCOME_CANCELED,
            'outcome_title': title or 'Аукцион отменён',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_CANCELED],
            'status_code': 'finished',
        }
    if raw_status == OUTCOME_WAITING or _WAIT_RE.search(blob) or (
        _FINISHED_TITLE_RE.search(blob) and not _WON_RE.search(blob) and not _LOST_RE.search(blob)
    ):
        return {
            'outcome_code': OUTCOME_WAITING,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WAITING],
            'status_code': 'finished',
        }
    if raw_status in ('finished', 'ended') or _FINISHED_TITLE_RE.search(blob):
        return {
            'outcome_code': OUTCOME_WAITING if not detail else OUTCOME_UNKNOWN,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WAITING],
            'status_code': 'finished',
        }
    return {
        'outcome_code': OUTCOME_UNKNOWN if blob else '',
        'outcome_title': title,
        'outcome_detail': detail or blob[:500],
        'status_code': raw_status or 'finished',
    }


def parse_win_notify_emails(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r'[\s,;]+', str(raw))
    seen = set()
    out = []
    for p in parts:
        email = p.strip().lower()
        if not email or '@' not in email or email in seen:
            continue
        seen.add(email)
        out.append(email)
    return out


def offers_needing_outcome_poll(
    *,
    limit: int = 30,
    lookback_days: int = 21,
    recheck_hours: int = 6,
) -> QuerySet:
    """
    Офферы со ставкой по завершённым лотам, где итог ещё не финальный
    или waiting_seller пора перепроверить.
    """
    from auction_avito.models import AvitoLotOffer

    now = timezone.now()
    since = now - timedelta(days=max(1, int(lookback_days)))
    recheck_before = now - timedelta(hours=max(1, int(recheck_hours)))

    qs = (
        AvitoLotOffer.objects
        .select_related('lot', 'account', 'lot__vehicle_avito', 'lot__venue')
        .filter(bid__gt=0)
        .filter(
            Q(lot__finish_at__lte=now) | Q(status_code__in=list(TERMINAL_OFFER_STATUSES) + ['ended', 'canceled'])
        )
        .filter(Q(lot__finish_at__gte=since) | Q(lot__finish_at__isnull=True, updated_at__gte=since))
        .exclude(outcome_code__in=list(FINAL_OUTCOMES))
        .filter(
            Q(outcome_synced_at__isnull=True)
            | Q(outcome_code='')
            | Q(outcome_code=OUTCOME_UNKNOWN)
            | Q(outcome_code=OUTCOME_WAITING, outcome_synced_at__lte=recheck_before)
        )
        .order_by('outcome_synced_at', 'lot__finish_at')
    )
    return qs[:max(1, min(int(limit or 30), 100))]


def serialize_outcome_queue_item(offer) -> dict[str, Any]:
    lot = offer.lot
    vehicle = getattr(lot, 'vehicle_avito', None)
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    year = getattr(vehicle, 'year', None)
    return {
        'lotOfferId': offer.lot_offer_id,
        'lotId': lot.lot_id if lot else None,
        'lotPk': lot.pk if lot else None,
        'dealerId': getattr(offer.account, 'dealer_id', None),
        'bid': offer.bid,
        'statusCode': offer.status_code,
        'outcomeCode': offer.outcome_code or '',
        'outcomeTitle': offer.outcome_title or '',
        'outcomeDetail': offer.outcome_detail or '',
        'outcomeSyncedAt': offer.outcome_synced_at.isoformat() if offer.outcome_synced_at else '',
        'finishAt': lot.finish_at.isoformat() if lot and lot.finish_at else '',
        'maxposterUrl': (
            f'https://app.maxposter.ru/dealer/auction/{offer.lot_offer_id}/view'
            if offer.lot_offer_id else ''
        ),
        'car': ' '.join(str(x) for x in (brand, model, year) if x).strip(),
        'viewUrl': f'/auction_avito/lots/{lot.pk}/' if lot else '',
    }


def _last_calc(lot):
    if lot is None:
        return None
    return lot.calculations.filter(is_success=True).order_by('-calculated_at').first()


def _portal_lot_url(lot) -> str:
    if lot is None:
        return ''
    base = getattr(settings, 'SITE_URL', '') or getattr(settings, 'PORTAL_BASE_URL', '') or ''
    path = f'/auction_avito/lots/{lot.pk}/'
    if base:
        return base.rstrip('/') + path
    return path


def _maxposter_url(offer) -> str:
    if not offer or not offer.lot_offer_id:
        return ''
    return f'https://app.maxposter.ru/dealer/auction/{offer.lot_offer_id}/view'


def build_win_email_html(offer) -> tuple[str, str]:
    """subject, html для письма о победе."""
    lot = offer.lot
    vehicle = getattr(lot, 'vehicle_avito', None) if lot else None
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    year = getattr(vehicle, 'year', '') or ''
    car = ' '.join(str(x) for x in (brand, model, year) if x).strip() or f'лот {getattr(lot, "lot_id", "—")}'
    calc = _last_calc(lot)
    buyout = getattr(calc, 'estimation_price', None) if calc else None
    profit = getattr(calc, 'profit', None) if calc else None
    zna = getattr(calc, 'zna', None) if calc else None

    def money(v):
        if v in (None, ''):
            return '—'
        try:
            return f'{int(round(float(v))):,}'.replace(',', ' ') + ' ₽'
        except (TypeError, ValueError):
            return str(v)

    subject = f'Аукцион Авито: выигран лот {getattr(lot, "lot_id", "—")} — {car}'
    rows = [
        ('Автомобиль', car),
        ('Лот', getattr(lot, 'lot_id', '—')),
        ('lotOfferId', offer.lot_offer_id),
        ('Наша ставка', money(offer.bid)),
        ('Выкуп (расчёт)', money(buyout)),
        ('Прибыль (расчёт)', money(profit)),
        ('ЦНА (расчёт)', money(zna)),
        ('Итог Maxposter', f'{offer.outcome_title or ""}\n{offer.outcome_detail or ""}'.strip()),
        ('Maxposter', _maxposter_url(offer)),
        ('Портал', _portal_lot_url(lot)),
    ]
    body_rows = ''.join(
        f'<tr><td style="padding:6px 10px;color:#64748b;vertical-align:top">{escape(str(k))}</td>'
        f'<td style="padding:6px 10px;color:#0f172a">{escape(str(v)).replace(chr(10), "<br>")}</td></tr>'
        for k, v in rows
    )
    html = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#0f172a">'
        '<h2 style="color:#166534;margin:0 0 12px">Мы выиграли лот на аукционе Авито</h2>'
        f'<p style="margin:0 0 16px">{escape(car)}</p>'
        f'<table style="border-collapse:collapse;width:100%;max-width:640px">{body_rows}</table>'
        '</div>'
    )
    return subject, html


def send_win_email(offer, *, emails: list[str] | None = None) -> dict[str, Any]:
    from django.core.mail import EmailMultiAlternatives

    from auction_avito.models import AvitoAuctionSettings

    if emails is None:
        emails = parse_win_notify_emails(AvitoAuctionSettings.get_solo().win_notify_emails)
    if not emails:
        return {'sent': False, 'reason': 'no recipients'}

    subject, html = build_win_email_html(offer)
    from_email = getattr(settings, 'EMAIL_HOST_USER_INFO', None) or settings.EMAIL_HOST_USER
    msg = EmailMultiAlternatives(subject, html, from_email, emails)
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)
    return {'sent': True, 'to': emails, 'subject': subject}


def apply_offer_outcome(
    offer,
    *,
    title: str = '',
    detail: str = '',
    blob: str = '',
    status_code: str = '',
    outcome_code: str = '',
    raw: str = '',
    send_email: bool = True,
) -> dict[str, Any]:
    """
    Сохраняет итог на оффере, при необходимости меняет status_code,
    шлёт письмо и чат при первом переходе в won.
    """
    from auction_avito.chat_utils import notify_auction_won

    prev_outcome = (offer.outcome_code or '').strip()
    prev_status = (offer.status_code or '').strip()

    if outcome_code in FINAL_OUTCOMES or outcome_code in (
        OUTCOME_WAITING, OUTCOME_UNKNOWN,
    ):
        classified = {
            'outcome_code': outcome_code,
            'outcome_title': _norm_spaces(title) or OUTCOME_NAMES.get(outcome_code, ''),
            'outcome_detail': _norm_spaces(detail),
            'status_code': (
                outcome_code if outcome_code in ('won', 'lost')
                else normalize_maxposter_status(status_code) or 'finished'
            ),
        }
        if outcome_code == OUTCOME_CANCELED:
            classified['status_code'] = 'finished'
    else:
        classified = classify_outcome_text(
            title=title,
            detail=detail,
            blob=blob,
            status_code=status_code,
        )

    now = timezone.now()
    offer.outcome_code = classified['outcome_code'] or offer.outcome_code
    offer.outcome_title = classified['outcome_title'] or offer.outcome_title
    offer.outcome_detail = classified['outcome_detail'] or offer.outcome_detail
    if raw:
        offer.outcome_raw = raw[:20000]
    elif blob or title or detail:
        offer.outcome_raw = _norm_spaces(f'{title}\n{detail}\n{blob}')[:20000]
    offer.outcome_synced_at = now

    new_status = classified.get('status_code') or offer.status_code
    new_status = normalize_maxposter_status(new_status)
    if new_status in ('won', 'lost', 'finished', 'inprogress', 'canceled'):
        offer.status_code = new_status if new_status != 'canceled' else 'finished'
        offer.status_name = STATUS_NAMES.get(
            offer.status_code,
            classified.get('outcome_title') or offer.status_name or offer.status_code,
        )
        if offer.outcome_code == OUTCOME_WON:
            offer.status_code = 'won'
            offer.status_name = STATUS_NAMES['won']
        elif offer.outcome_code == OUTCOME_LOST:
            offer.status_code = 'lost'
            offer.status_name = STATUS_NAMES['lost']

    update_fields = [
        'outcome_code', 'outcome_title', 'outcome_detail', 'outcome_raw',
        'outcome_synced_at', 'status_code', 'status_name',
    ]

    email_result = {'sent': False, 'reason': 'skipped'}
    became_won = (
        offer.outcome_code == OUTCOME_WON
        and prev_outcome != OUTCOME_WON
        and offer.win_email_sent_at is None
    )
    if became_won:
        try:
            notify_auction_won(offer)
        except Exception as exc:
            email_result = {'sent': False, 'reason': f'chat error: {exc}'}
        if send_email:
            try:
                email_result = send_win_email(offer)
                if email_result.get('sent'):
                    offer.win_email_sent_at = now
                    update_fields.append('win_email_sent_at')
            except Exception as exc:
                email_result = {'sent': False, 'reason': str(exc)}

    offer.save(update_fields=update_fields)
    return {
        'ok': True,
        'lotOfferId': offer.lot_offer_id,
        'lotId': offer.lot.lot_id if offer.lot_id else None,
        'prevOutcome': prev_outcome,
        'prevStatus': prev_status,
        'outcomeCode': offer.outcome_code,
        'outcomeTitle': offer.outcome_title,
        'outcomeDetail': offer.outcome_detail,
        'statusCode': offer.status_code,
        'statusName': offer.status_name,
        'becameWon': became_won,
        'email': email_result,
        'outcomeSyncedAt': now.isoformat(),
    }
