"""Отчёт по лотам: анализ проигрышей и экономика ставок за период."""
from __future__ import annotations

from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.urls import reverse

from auction_avito.models import (
    AvitoBidHistory,
    AvitoLot,
    AvitoLotCalculation,
    AvitoLotOffer,
)
from auction_avito.services.analytics import (
    _day_bounds,
    _pct,
    resolve_period,
)
from auction_avito.services.outcome import OUTCOME_NAMES


def _int(v):
    if v in (None, ''):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _lot_title(lot) -> str:
    vehicle = getattr(lot, 'vehicle_avito', None) or getattr(lot, 'vehicle_autohub', None)
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    title = f'{brand} {model}'.strip()
    return title or f'Лот {lot.lot_id}'


def _period_lots_qs(start, end):
    return AvitoLot.objects.filter(
        Q(finish_at__gte=start, finish_at__lte=end)
        | Q(finish_at__isnull=True, synced_at__gte=start, synced_at__lte=end)
    )


def build_loss_report_context(request, *, row_limit: int = 500) -> dict:
    from django.db.models import Avg

    date_from, date_to = resolve_period(request)
    start, end = _day_bounds(date_from, date_to)

    outcome = (request.GET.get('outcome') or '').strip()
    status = (request.GET.get('status') or '').strip()
    with_bids_raw = (request.GET.get('with_bids') or '1').strip().lower()
    with_bids = with_bids_raw not in ('0', 'false', 'no', 'off')

    period_qs = f'date_from={date_from.isoformat()}&date_to={date_to.isoformat()}'
    report_base = reverse('auction_avito:loss_report')

    lots_base = _period_lots_qs(start, end)
    lots_total = lots_base.count()

    offers_in_period = AvitoLotOffer.objects.filter(lot__in=lots_base)
    lots_with_bids = (
        offers_in_period.filter(bid__gt=0).values('lot_id').distinct().count()
    )

    # Ставки за период (история), fallback — текущие ненулевые
    bids_total = AvitoBidHistory.objects.filter(
        Q(bid_made_at__gte=start, bid_made_at__lte=end)
        | Q(bid_made_at__isnull=True, recorded_at__gte=start, recorded_at__lte=end)
    ).count()
    if bids_total == 0:
        bids_total = offers_in_period.filter(bid__gt=0).count()

    avg_bids_per_lot = round(bids_total / lots_with_bids, 2) if lots_with_bids else 0

    avg_mileage_all = lots_base.filter(
        vehicle_avito__mileage__gt=0,
    ).aggregate(v=Avg('vehicle_avito__mileage'))['v']
    avg_year_all = lots_base.filter(
        vehicle_avito__year__gt=0,
    ).aggregate(v=Avg('vehicle_avito__year'))['v']

    # Итоги торгов — клик фильтрует таблицу на этой же странице
    outcome_rows = list(
        offers_in_period
        .exclude(outcome_code='')
        .values('outcome_code')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
    )
    outcome_counters = []
    for row in outcome_rows:
        code = row['outcome_code']
        qs_parts = [period_qs, f'outcome={code}']
        if with_bids:
            qs_parts.append('with_bids=1')
        else:
            qs_parts.append('with_bids=0')
        outcome_counters.append({
            'code': code,
            'label': OUTCOME_NAMES.get(code, code),
            'count': row['cnt'],
            'pct': 0,
            'list_url': f'{report_base}?{"&".join(qs_parts)}',
            'filter_kind': 'outcome',
            'active': outcome == code,
        })

    status_extra = list(
        offers_in_period
        .filter(outcome_code='', status_code__in=('won', 'lost', 'finished'))
        .values('status_code')
        .annotate(cnt=Count('id'))
    )
    for row in status_extra:
        code = row['status_code']
        qs_parts = [period_qs, f'status={code}']
        qs_parts.append('with_bids=1' if with_bids else 'with_bids=0')
        outcome_counters.append({
            'code': code,
            'label': f'Статус: {code}',
            'count': row['cnt'],
            'pct': 0,
            'list_url': f'{report_base}?{"&".join(qs_parts)}',
            'filter_kind': 'status',
            'active': (not outcome) and status == code,
        })

    outcomes_sum = sum(o['count'] for o in outcome_counters) or 0
    for o in outcome_counters:
        o['pct'] = _pct(o['count'], outcomes_sum)

    # Таблица лотов
    latest_calc = AvitoLotCalculation.objects.filter(
        lot=OuterRef('pk'),
        is_success=True,
    ).order_by('-calculated_at')

    lots_qs = lots_base.select_related(
        'venue', 'venue__city', 'vehicle_avito',
    ).annotate(
        latest_estimation_price=Subquery(latest_calc.values('estimation_price')[:1]),
        latest_zna=Subquery(latest_calc.values('zna')[:1]),
        our_bids_count=Count('offers__bid_history', distinct=True),
    ).prefetch_related(
        Prefetch(
            'offers',
            queryset=AvitoLotOffer.objects.select_related('account').order_by('-updated_at'),
        ),
        Prefetch(
            'offers__bid_history',
            queryset=AvitoBidHistory.objects.order_by('-bid_made_at', '-recorded_at'),
        ),
    )

    if with_bids:
        lots_qs = lots_qs.filter(offers__bid__gt=0)
    if outcome:
        lots_qs = lots_qs.filter(offers__outcome_code=outcome)
    elif status:
        lots_qs = lots_qs.filter(offers__status_code=status, offers__outcome_code='')

    lots_qs = lots_qs.distinct().order_by('-finish_at', '-lot_id')

    limit = max(1, int(row_limit or 500))
    rows = []
    for lot in lots_qs[:limit]:
        offers = list(lot.offers.all())
        primary = None
        for o in offers:
            if (o.bid or 0) > 0:
                primary = o
                break
        if primary is None and offers:
            primary = offers[0]

        buyout = _int(getattr(lot, 'latest_estimation_price', None))
        min_bid = _int(lot.min_available_bid)
        wish = _int(lot.min_price)
        max_bid = _int(lot.max_bid)
        our_bid = _int(primary.bid) if primary else None
        l1 = _int(lot.bid_l1)
        l2 = _int(lot.bid_l2)

        # На сколько выкуп ниже maxBid (положительное = выкуп меньше максимума)
        buyout_below_max = None
        buyout_below_max_pct = None
        if buyout is not None and max_bid is not None:
            buyout_below_max = max_bid - buyout
            if max_bid > 0:
                buyout_below_max_pct = round(100.0 * buyout_below_max / max_bid, 1)

        # На сколько выкуп выше/ниже minAvailableBid (положит. = выкуп выше минимума)
        buyout_vs_min = None
        buyout_vs_min_pct = None
        if buyout is not None and min_bid is not None:
            buyout_vs_min = buyout - min_bid
            if min_bid > 0:
                buyout_vs_min_pct = round(100.0 * buyout_vs_min / min_bid, 1)

        # Насколько выкуп не дотягивает до пожелания продавца (положит. = wish выше выкупа)
        buyout_below_wish = None
        buyout_below_wish_pct = None
        if buyout is not None and wish is not None:
            buyout_below_wish = wish - buyout
            if wish > 0:
                buyout_below_wish_pct = round(100.0 * buyout_below_wish / wish, 1)

        hist_count = 0
        for o in offers:
            hist_count += len(list(o.bid_history.all()))
        if hist_count == 0 and our_bid:
            hist_count = 1

        vehicle = getattr(lot, 'vehicle_avito', None)
        rows.append({
            'lotPk': lot.pk,
            'lotId': lot.lot_id,
            'title': _lot_title(lot),
            'year': getattr(vehicle, 'year', None) if vehicle else None,
            'mileage': getattr(vehicle, 'mileage', None) if vehicle else None,
            'buyout': buyout,
            'zna': _int(getattr(lot, 'latest_zna', None)),
            'minAvailableBid': min_bid,
            'sellerWish': wish,
            'bidL1': l1,
            'bidL2': l2,
            'corridor': (
                f'{l1:,} – {l2:,}'.replace(',', ' ')
                if l1 is not None and l2 is not None else ''
            ),
            'maxBid': max_bid,
            'ourBid': our_bid,
            'ourBidsCount': hist_count,
            'buyoutBelowMax': buyout_below_max,
            'buyoutBelowMaxPct': buyout_below_max_pct,
            'buyoutVsMin': buyout_vs_min,
            'buyoutVsMinPct': buyout_vs_min_pct,
            'buyoutBelowWish': buyout_below_wish,
            'buyoutBelowWishPct': buyout_below_wish_pct,
            'outcomeCode': (primary.outcome_code if primary else '') or '',
            'outcomeTitle': (primary.outcome_title if primary else '') or '',
            'outcomeLabel': OUTCOME_NAMES.get(
                (primary.outcome_code if primary else '') or '',
                (primary.outcome_code if primary else '')
                or (primary.status_name if primary else '')
                or (primary.status_code if primary else '')
                or '—',
            ),
            'statusCode': primary.status_code if primary else '',
            'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
            'place': (lot.venue.display_label if lot.venue_id else '') or (lot.seller_place_name or ''),
        })

    clear_outcome_url = f'{report_base}?{period_qs}&with_bids={"1" if with_bids else "0"}'

    # Средние % по показанным строкам (где есть данные)
    wish_pcts = [r['buyoutBelowWishPct'] for r in rows if r.get('buyoutBelowWishPct') is not None]
    max_pcts = [r['buyoutBelowMaxPct'] for r in rows if r.get('buyoutBelowMaxPct') is not None]
    avg_below_wish_pct = round(sum(wish_pcts) / len(wish_pcts), 1) if wish_pcts else None
    avg_below_max_pct = round(sum(max_pcts) / len(max_pcts), 1) if max_pcts else None

    return {
        'type': 'auction_avito_loss_report',
        'filters': {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'outcome': outcome,
            'status': status,
            'with_bids': with_bids,
        },
        'kpis': {
            'lots_total': lots_total,
            'lots_with_bids': lots_with_bids,
            'bids_total': bids_total,
            'avg_bids_per_lot': avg_bids_per_lot,
            'bid_share': _pct(lots_with_bids, lots_total),
            'avg_mileage': int(avg_mileage_all or 0),
            'avg_year': int(avg_year_all or 0) if avg_year_all else None,
            'outcomes_total': outcomes_sum,
            'rows_shown': len(rows),
            'avg_below_wish_pct': avg_below_wish_pct,
            'avg_below_max_pct': avg_below_max_pct,
            'below_wish_n': len(wish_pcts),
            'below_max_n': len(max_pcts),
        },
        'outcomes': outcome_counters,
        'rows': rows,
        'clear_outcome_url': clear_outcome_url,
        'period_qs': period_qs,
        'export_url': (
            f'{report_base}?{period_qs}'
            f'&with_bids={"1" if with_bids else "0"}'
            f'{"&outcome=" + outcome if outcome else ""}'
            f'{"&status=" + status if status else ""}'
            f'&export=xlsx'
        ),
    }


def export_loss_report_xlsx(request):
    """Собрать Excel по текущим фильтрам отчёта."""
    from datetime import datetime
    from io import BytesIO

    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    ctx = build_loss_report_context(request, row_limit=5000)
    rows = ctx.get('rows') or []
    filters = ctx.get('filters') or {}
    kpis = ctx.get('kpis') or {}

    wb = Workbook()

    # --- Лист KPI ---
    ws_kpi = wb.active
    ws_kpi.title = 'Сводка'
    ws_kpi.append(['Параметр', 'Значение'])
    header_fill = PatternFill(start_color='002A5A', end_color='002A5A', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    for cell in ws_kpi[1]:
        cell.fill = header_fill
        cell.font = header_font

    kpi_lines = [
        ('Период с', filters.get('date_from') or ''),
        ('Период по', filters.get('date_to') or ''),
        ('Только со ставками', 'да' if filters.get('with_bids') else 'нет'),
        ('Фильтр итога', filters.get('outcome') or filters.get('status') or 'все'),
        ('Всего лотов', kpis.get('lots_total')),
        ('Лотов со ставками', kpis.get('lots_with_bids')),
        ('% лотов со ставками', kpis.get('bid_share')),
        ('Всего ставок', kpis.get('bids_total')),
        ('Ср. ставок на лот', kpis.get('avg_bids_per_lot')),
        ('Ср. пробег', kpis.get('avg_mileage')),
        ('Ср. год', kpis.get('avg_year')),
        ('Ср. до пожелания %', kpis.get('avg_below_wish_pct')),
        ('Ср. ниже maxBid %', kpis.get('avg_below_max_pct')),
        ('Строк в выгрузке', kpis.get('rows_shown')),
    ]
    for label, value in kpi_lines:
        ws_kpi.append([label, value if value is not None else ''])
    ws_kpi.column_dimensions['A'].width = 28
    ws_kpi.column_dimensions['B'].width = 18

    # --- Лист лотов ---
    ws = wb.create_sheet('Лоты')
    headers = [
        'Лот ID',
        'Авто',
        'Год',
        'Пробег',
        'Выкуп',
        'ЦНА',
        'Мин. ставка',
        'Пожелание',
        'L1',
        'L2',
        'maxBid',
        'Наша ставка',
        'Число ставок',
        'До пожелания ₽',
        'До пожелания %',
        'Выкуп ниже max ₽',
        'Выкуп ниже max %',
        'Выкуп vs min ₽',
        'Выкуп vs min %',
        'Код итога',
        'Итог',
        'Место',
        'Ссылка',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for r in rows:
        ws.append([
            r.get('lotId'),
            r.get('title') or '',
            r.get('year') or '',
            r.get('mileage') or '',
            r.get('buyout') if r.get('buyout') is not None else '',
            r.get('zna') if r.get('zna') is not None else '',
            r.get('minAvailableBid') if r.get('minAvailableBid') is not None else '',
            r.get('sellerWish') if r.get('sellerWish') is not None else '',
            r.get('bidL1') if r.get('bidL1') is not None else '',
            r.get('bidL2') if r.get('bidL2') is not None else '',
            r.get('maxBid') if r.get('maxBid') is not None else '',
            r.get('ourBid') if r.get('ourBid') is not None else '',
            r.get('ourBidsCount') if r.get('ourBidsCount') is not None else '',
            r.get('buyoutBelowWish') if r.get('buyoutBelowWish') is not None else '',
            r.get('buyoutBelowWishPct') if r.get('buyoutBelowWishPct') is not None else '',
            r.get('buyoutBelowMax') if r.get('buyoutBelowMax') is not None else '',
            r.get('buyoutBelowMaxPct') if r.get('buyoutBelowMaxPct') is not None else '',
            r.get('buyoutVsMin') if r.get('buyoutVsMin') is not None else '',
            r.get('buyoutVsMinPct') if r.get('buyoutVsMinPct') is not None else '',
            r.get('outcomeCode') or '',
            r.get('outcomeLabel') or '',
            r.get('place') or '',
            r.get('portalLotUrl') or '',
        ])

    widths = [12, 28, 8, 12, 12, 12, 12, 12, 10, 10, 12, 12, 10, 14, 12, 14, 12, 12, 12, 14, 28, 22, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # --- Лист итогов ---
    ws_out = wb.create_sheet('Итоги')
    ws_out.append(['Итог', 'Код', 'Количество', '%'])
    for cell in ws_out[1]:
        cell.fill = header_fill
        cell.font = header_font
    for o in ctx.get('outcomes') or []:
        ws_out.append([o.get('label'), o.get('code'), o.get('count'), o.get('pct')])
    for col, w in enumerate([36, 18, 12, 10], start=1):
        ws_out.column_dimensions[get_column_letter(col)].width = w

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'avito_lots_report_{filters.get("date_from")}_{filters.get("date_to")}_{stamp}.xlsx'
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
