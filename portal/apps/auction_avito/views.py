from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from auction_avito.services.badges import collect_badges_for_display, ensure_badges_synced
from auction_avito.lot_tabs import (
    default_two_months_period,
    lot_estimation_count,
    lot_estimation_page,
    lot_sales_count,
    lot_sales_page,
    lot_stock_count,
    lot_stock_page,
    resolve_autoru_models,
    resolve_period,
)

LOT_DETAIL_TABS = (
    'main', 'autoteka', 'calculations', 'stock', 'sales', 'estimations',
)
from auction_avito.chat_utils import build_aav_feed_embed, build_aav_lot_embed
from auction_avito.models import (
    AvitoAuctionSettings,
    AvitoAutotekaEvent,
    AvitoLot,
    AvitoLotBadge,
    AvitoLotCalculation,
    AvitoLotOffer,
    AvitoOfferBadge,
    AvitoVenue,
)
from auction_avito.services.bid_history import get_lot_bid_history
from auction_avito.services.expiry import expire_overdue_lots
from auction_avito.services.offer_status import active_lots_q, inactive_lots_q, parse_activity_param

# Подписи для фильтра по типу метки (badgeType из API Авито)
BADGE_TYPE_LABELS = {
    'stock-score-1': 'Частично под стратегию выкупа',
    'stock-score-2': 'Под стратегию выкупа',
    'sale-score-3': 'Шанс скидки от продавца (3)',
    'sale-score-4': 'Шанс скидки от продавца (4)',
    'market-score-0': 'В сегменте есть интереснее',
    'market-score-3': 'Хороший вариант в сегменте (3)',
    'market-score-4': 'Хороший вариант в сегменте (4)',
    'trade-in': 'Трейд-ин',
    'loan': 'Кредит',
}


def _coalesce_lot_value(lot, attr: str, raw_key: str):
    val = getattr(lot, attr, None)
    if val is not None:
        return val
    return (lot.raw_lot_json or {}).get(raw_key)


def _coalesce_offer_value(offer, attr: str, raw_key: str):
    if not offer:
        return None
    val = getattr(offer, attr, None)
    if val is not None:
        return val
    return (offer.raw_offer_json or {}).get(raw_key)


def _lot_price_display(lot, offer=None) -> dict:
    return {
        'min_available_bid': _coalesce_lot_value(lot, 'min_available_bid', 'minAvailableBid'),
        'max_available_bid': _coalesce_lot_value(lot, 'max_available_bid', 'maxAvailableBid'),
        'min_price': _coalesce_lot_value(lot, 'min_price', 'minPrice'),
        'max_bid': _coalesce_lot_value(lot, 'max_bid', 'maxBid'),
        'min_bid_step': _coalesce_offer_value(offer, 'min_bid_step', 'minBidStep'),
        'bid': _coalesce_offer_value(offer, 'bid', 'bid') if offer else None,
    }


def _trade_in_display(lot) -> dict:
    raw = (lot.raw_lot_json or {}).get('tradeIn') or {}
    considers = lot.trade_in_considers
    if considers is None:
        considers = raw.get('considersTradeIn')
    looking = lot.trade_in_looking_for_used
    if looking is None:
        looking = raw.get('lookingForUsedCar')
    comment = (lot.trade_in_comment or '').strip() or (raw.get('comment') or '').strip()
    return {
        'considers': considers,
        'looking_for_used': looking,
        'comment': comment,
        'has_any': bool(considers or looking or comment),
    }


def _venue_display(lot, offer=None) -> dict:
    """Данные площадки для списка и карточки лота."""
    if lot.venue_id:
        v = lot.venue
        return {
            'dealer_id': v.dealer_id,
            'name': v.name,
            'city': v.city_name,
            'label': v.display_label,
        }
    dealer_id = None
    if offer and getattr(offer, 'account', None):
        dealer_id = offer.account.dealer_id
    name = (lot.seller_place_name or '').strip()
    city = ''
    if name and ',' in name and not city:
        city_part, _, rest = name.partition(',')
        if rest.strip():
            city = city_part.strip()
            name = rest.strip()
    label_parts = [p for p in (name, city) if p]
    label = ' · '.join(label_parts) if label_parts else '—'
    if dealer_id:
        label = f'{label} (ID {dealer_id})' if label != '—' else f'ID {dealer_id}'
    return {
        'dealer_id': dealer_id,
        'name': name,
        'city': city,
        'label': label,
    }


def _seller_place_display(lot, offer=None) -> dict:
    """Место продажи лота (sellerPlaceName) — отдельно от справочника площадки AvitoVenue."""
    venue = _venue_display(lot, offer)
    seller_raw = (lot.seller_place_name or '').strip()
    seller_name = seller_raw
    seller_city = ''
    if seller_raw and ',' in seller_raw:
        city_part, _, rest = seller_raw.partition(',')
        if rest.strip():
            seller_city = city_part.strip()
            seller_name = rest.strip()

    dealer_id = venue.get('dealer_id')
    if not dealer_id and offer and getattr(offer, 'account', None):
        dealer_id = offer.account.dealer_id

    return {
        'dealer_id': dealer_id,
        'name': seller_name or '—',
        'city': seller_city or '',
        'seller_place_raw': seller_raw or '—',
        'label': seller_raw or '—',
        'has_venue': bool(lot.venue_id),
    }


def _venue_filter_choices():
    return [
        (str(v.dealer_id), v.display_label)
        for v in AvitoVenue.objects.select_related('city').order_by('city__name', 'name', 'dealer_id')
    ]


def _lot_qs_inject(stock_model, est_unit, sales_from, sales_to, est_from, est_to):
    data = {}
    if stock_model:
        data['stock_model'] = stock_model
    if est_unit:
        data['est_unit'] = est_unit
    if sales_from:
        data['sales_from'] = sales_from.isoformat()
    if sales_to:
        data['sales_to'] = sales_to.isoformat()
    if est_from:
        data['est_from'] = est_from.isoformat()
    if est_to:
        data['est_to'] = est_to.isoformat()
    return data


def _page_num(request, key):
    try:
        return max(1, int(request.GET.get(key) or 1))
    except (TypeError, ValueError):
        return 1


def _tab_query_string(request, tab, inject=None, **overrides):
    q = request.GET.copy()
    q['tab'] = tab
    if inject:
        for key, val in inject.items():
            if val is not None and val != '':
                q[key] = str(val)
    for key, val in overrides.items():
        if val is None:
            q.pop(key, None)
        else:
            q[key] = str(val)
    return q.urlencode()


def _equipment_items(lot):
    items = list(lot.equipment.all())
    if items:
        return items
    return [
        {'name': eq.get('name') or '', 'values': eq.get('values') or []}
        for eq in (lot.raw_lot_json or {}).get('equipment') or []
    ]


def _badge_filter_choices():
    types = set()
    types.update(
        AvitoOfferBadge.objects.exclude(badge_type='').values_list('badge_type', flat=True).distinct()
    )
    types.update(
        AvitoLotBadge.objects.exclude(badge_type='').values_list('badge_type', flat=True).distinct()
    )
    for code in BADGE_TYPE_LABELS:
        types.add(code)
    return sorted(
        (t, BADGE_TYPE_LABELS.get(t, t)) for t in types if t
    )


def _lot_queryset():
    offer_qs = AvitoLotOffer.objects.select_related('account').prefetch_related(
        'badges',
    ).order_by('-updated_at')
    return AvitoLot.objects.select_related(
        'venue__city',
        'vehicle_avito',
        'vehicle_autohub',
        'autoteka',
    ).prefetch_related(
        'images',
        'equipment',
        'badges',
        Prefetch('offers', queryset=offer_qs),
        Prefetch(
            'autoteka__events',
            queryset=AvitoAutotekaEvent.objects.all(),
        ),
        Prefetch(
            'calculations',
            queryset=AvitoLotCalculation.objects.select_related('unit', 'user').order_by('-calculated_at'),
        ),
    )


def _lot_detail_queryset():
    """Карточка лота: без тяжёлых prefetch — данные вкладок по запросу."""
    offer_qs = AvitoLotOffer.objects.select_related('account').prefetch_related(
        'badges',
    ).order_by('-updated_at')
    return AvitoLot.objects.select_related(
        'venue__city',
        'vehicle_avito',
        'vehicle_autohub',
        'autoteka',
    ).prefetch_related(
        'images',
        'equipment',
        'badges',
        Prefetch('offers', queryset=offer_qs),
    )


@login_required
def lot_list(request):
    expire_overdue_lots()

    qs = _lot_queryset()

    search = (request.GET.get('q') or '').strip()
    activity = parse_activity_param(request)
    status = (request.GET.get('status') or '').strip()
    badge_type = (request.GET.get('badge') or '').strip()
    trade_in = (request.GET.get('trade_in') or '').strip()
    venue_dealer = (request.GET.get('venue') or '').strip()
    sort = (request.GET.get('sort') or '-finish_at').strip()

    if search:
        qs = qs.filter(
            Q(lot_id__icontains=search)
            | Q(description__icontains=search)
            | Q(seller_place_name__icontains=search)
            | Q(venue__name__icontains=search)
            | Q(venue__city__name__icontains=search)
            | Q(vehicle_avito__brand_name__icontains=search)
            | Q(vehicle_avito__model_name__icontains=search)
        )

    if venue_dealer:
        try:
            qs = qs.filter(venue__dealer_id=int(venue_dealer))
        except ValueError:
            pass

    if activity == 'active':
        qs = qs.filter(active_lots_q()).distinct()
    elif activity == 'inactive':
        qs = qs.filter(inactive_lots_q()).distinct()

    if status:
        qs = qs.filter(offers__status_code=status).distinct()

    if badge_type:
        qs = qs.filter(
            Q(offers__badges__badge_type=badge_type)
            | Q(badges__badge_type=badge_type)
        ).distinct()

    if trade_in == 'considers':
        qs = qs.filter(trade_in_considers=True)
    elif trade_in == 'used':
        qs = qs.filter(trade_in_looking_for_used=True)
    elif trade_in == 'any':
        qs = qs.filter(
            Q(trade_in_considers=True)
            | Q(trade_in_looking_for_used=True)
            | Q(trade_in_comment__gt='')
        ).distinct()

    allowed_sort = {
        'finish_at', '-finish_at',
        'min_price', '-min_price',
        'imv_median', '-imv_median',
        'lot_id', '-lot_id',
    }
    if sort not in allowed_sort:
        sort = '-finish_at'

    latest_calc = AvitoLotCalculation.objects.filter(
        lot=OuterRef('pk'),
        is_success=True,
    ).order_by('-calculated_at')
    qs = qs.annotate(
        latest_estimation_price=Subquery(latest_calc.values('estimation_price')[:1]),
        latest_calc_at=Subquery(latest_calc.values('calculated_at')[:1]),
    ).order_by(sort)

    page_obj = Paginator(qs, 24).get_page(request.GET.get('page') or 1)
    for lot in page_obj.object_list:
        offers = list(lot.offers.all())
        ensure_badges_synced(lot, offers[0] if offers else None)

    params = {
        'type': 'auction_avito_list',
        'page_obj': page_obj,
        'filters': {
            'q': search,
            'activity': activity,
            'status': status,
            'badge': badge_type,
            'trade_in': trade_in,
            'venue': venue_dealer,
            'sort': sort,
        },
        'activity_choices': [
            ('active', 'Активные'),
            ('inactive', 'Неактивные'),
            ('', 'Все'),
        ],
        'badge_choices': _badge_filter_choices(),
        'venue_choices': _venue_filter_choices(),
        'trade_in_choices': [
            ('considers', 'Рассматривает трейд-ин'),
            ('used', 'Ищет б/у в зачёт'),
            ('any', 'Любой трейд-ин'),
        ],
        'status_choices': [
            ('inprogress', 'Активен'),
            ('finished', 'Завершён'),
            ('won', 'Выигран'),
            ('lost', 'Проигран'),
        ],
    }
    params.update({'feed_chat': build_aav_feed_embed(request)})
    return render(request, 'auction_avito/lot_list.html', {'params': params})


@login_required
def lot_detail(request, pk):
    expire_overdue_lots()
    lot = get_object_or_404(_lot_detail_queryset(), pk=pk)
    autoteka_report = getattr(lot, 'autoteka', None)
    primary_offer = lot.offers.first()
    offer_badges, lot_badges, all_badges = collect_badges_for_display(lot, primary_offer)

    vehicle = getattr(lot, 'vehicle_avito', None)
    stock_model_raw = (request.GET.get('stock_model') or '').strip()
    stock_model_id = None
    if stock_model_raw:
        try:
            stock_model_id = int(stock_model_raw)
        except ValueError:
            pass
    tab = (request.GET.get('tab') or 'main').strip()
    if tab not in LOT_DETAIL_TABS:
        tab = 'main'

    default_from, default_to = default_two_months_period()
    sales_from, sales_to = resolve_period(
        request.GET.get('sales_from'),
        request.GET.get('sales_to'),
    )
    est_from, est_to = resolve_period(
        request.GET.get('est_from'),
        request.GET.get('est_to'),
    )
    est_unit_raw = (request.GET.get('est_unit') or '').strip()
    est_unit_id = None
    if est_unit_raw:
        try:
            est_unit_id = int(est_unit_raw)
        except ValueError:
            pass

    model_ctx = resolve_autoru_models(
        vehicle,
        include_model_choices=(tab == 'stock'),
    )
    model_ids = (model_ctx or {}).get('model_ids') or []
    brand = (model_ctx or {}).get('brand_name') or (
        vehicle.brand_name if vehicle else ''
    )
    model_label = (model_ctx or {}).get('model_name') or (
        vehicle.model_name if vehicle else ''
    )

    tab_counts = {
        'autoteka': (
            AvitoAutotekaEvent.objects.filter(report=autoteka_report).count()
            if autoteka_report
            else 0
        ),
        'stock': lot_stock_count(model_ids, stock_model_id) if model_ids else 0,
        'sales': lot_sales_count(model_ids, sales_from, sales_to) if model_ids else 0,
        'estimations': lot_estimation_count(
            model_ctx,
            brand_name=brand,
            model_name=model_label,
            date_from=est_from,
            date_to=est_to,
            unit_id=est_unit_id,
        ),
        'calculations': AvitoLotCalculation.objects.filter(lot_id=lot.pk).count(),
    }

    stock_rows, stock_total, stock_page_obj = [], 0, None
    sales_rows, sales_total, sales_page_obj = [], 0, None
    estimation_rows, estimation_total, est_page_obj = [], 0, None
    estimation_unit_choices = []
    autoteka_events = []
    calculations = []
    latest_calculation = None

    if tab == 'stock' and model_ids:
        stock_rows, stock_total, stock_page_obj = lot_stock_page(
            model_ids,
            model_filter_id=stock_model_id,
            page=_page_num(request, 'stock_page'),
        )
    elif tab == 'sales' and model_ids:
        sales_rows, sales_total, sales_page_obj = lot_sales_page(
            model_ids,
            sales_from,
            sales_to,
            page=_page_num(request, 'sales_page'),
        )
    elif tab == 'estimations':
        estimation_rows, estimation_total, est_page_obj, estimation_unit_choices = (
            lot_estimation_page(
                model_ctx,
                brand_name=brand,
                model_name=model_label,
                date_from=est_from,
                date_to=est_to,
                unit_id=est_unit_id,
                page=_page_num(request, 'est_page'),
                load_unit_choices=True,
            )
        )
    elif tab == 'autoteka' and autoteka_report:
        autoteka_events = list(
            AvitoAutotekaEvent.objects.filter(report=autoteka_report).order_by('pk')
        )
    elif tab == 'calculations':
        calculations = list(
            AvitoLotCalculation.objects.filter(lot_id=lot.pk)
            .select_related('unit', 'user')
            .order_by('-calculated_at')
        )
        latest_calculation = next((c for c in calculations if c.is_success), None)
        if latest_calculation is None and calculations:
            latest_calculation = calculations[0]

    params = {
        'type': 'auction_avito_detail',
        'lot': lot,
        'vehicle': vehicle,
        'tab': tab,
        'model_ctx': model_ctx,
        'stock_model': stock_model_raw,
        'stock_model_id': stock_model_id,
        'stock_rows': stock_rows,
        'stock_total': tab_counts['stock'],
        'stock_page_obj': stock_page_obj,
        'sales_rows': sales_rows,
        'sales_total': tab_counts['sales'],
        'sales_page_obj': sales_page_obj,
        'sales_from': sales_from,
        'sales_to': sales_to,
        'sales_from_default': default_from,
        'sales_to_default': default_to,
        'estimation_rows': estimation_rows,
        'estimation_total': tab_counts['estimations'],
        'est_page_obj': est_page_obj,
        'est_from': est_from,
        'est_to': est_to,
        'est_unit': est_unit_raw,
        'est_unit_id': est_unit_id,
        'estimation_unit_choices': estimation_unit_choices,
        'tab_counts': tab_counts,
        'autoteka_events': autoteka_events,
        'calculations': calculations,
        'latest_calculation': latest_calculation,
        'qs_main': _tab_query_string(
            request, 'main', inject=_lot_qs_inject(
                stock_model_raw, est_unit_raw, sales_from, sales_to, est_from, est_to,
            ),
            stock_page=None, sales_page=None, est_page=None,
        ),
        'qs_autoteka': _tab_query_string(
            request, 'autoteka', inject=_lot_qs_inject(
                stock_model_raw, est_unit_raw, sales_from, sales_to, est_from, est_to,
            ),
            stock_page=None, sales_page=None, est_page=None,
        ),
        'qs_calculations': _tab_query_string(
            request, 'calculations', inject=_lot_qs_inject(
                stock_model_raw, est_unit_raw, sales_from, sales_to, est_from, est_to,
            ),
            stock_page=None, sales_page=None, est_page=None,
        ),
        'qs_stock': _tab_query_string(
            request, 'stock', inject=_lot_qs_inject(
                stock_model_raw, est_unit_raw, sales_from, sales_to, est_from, est_to,
            ),
            stock_page=None, sales_page=None, est_page=None,
        ),
        'qs_sales': _tab_query_string(
            request, 'sales', inject=_lot_qs_inject(
                stock_model_raw, est_unit_raw, sales_from, sales_to, est_from, est_to,
            ),
            stock_page=None, sales_page=None, est_page=None,
        ),
        'qs_sales_reset': _tab_query_string(
            request, 'sales', inject=_lot_qs_inject(stock_model_raw, est_unit_raw, None, None, est_from, est_to),
            sales_from=None, sales_to=None, sales_page=None,
            stock_page=None, est_page=None,
        ),
        'qs_estimations': _tab_query_string(
            request, 'estimations', inject=_lot_qs_inject(
                stock_model_raw, est_unit_raw, sales_from, sales_to, est_from, est_to,
            ),
            stock_page=None, sales_page=None, est_page=None,
        ),
        'qs_est_reset': _tab_query_string(
            request, 'estimations', inject=_lot_qs_inject(stock_model_raw, None, sales_from, sales_to, None, None),
            est_from=None, est_to=None, est_unit=None, est_page=None,
            stock_page=None, sales_page=None,
        ),
        'autohub': getattr(lot, 'vehicle_autohub', None),
        'autoteka': autoteka_report,
        'primary_offer': primary_offer,
        'offers': lot.offers.all(),
        'images': lot.images.all(),
        'all_badges': all_badges,
        'offer_badges': offer_badges,
        'lot_badges': lot_badges,
        'badge_type_labels': BADGE_TYPE_LABELS,
        'equipment_items': _equipment_items(lot),
        'trade_in': _trade_in_display(lot),
        'prices': _lot_price_display(lot, primary_offer),
        'venue': _venue_display(lot, primary_offer),
        'seller_place': _seller_place_display(lot, primary_offer),
        'lot_chat': build_aav_lot_embed(request, lot),
        'bid_history': get_lot_bid_history(lot),
    }
    return render(request, 'auction_avito/lot_detail.html', {'params': params})


@login_required
@require_POST
def lot_load_images(request, pk):
    """Загрузить фото: API (если настроен) или из сохранённого JSON."""
    lot = get_object_or_404(AvitoLot, pk=pk)
    from auction_avito.services.images import load_lot_images

    result = load_lot_images(lot, try_api=True)
    if result['ok']:
        messages.success(request, result['message'])
    else:
        messages.warning(request, result['message'])
    return redirect('auction_avito:lot_detail', pk=pk)


@login_required
@require_POST
def lot_upload_images(request, pk):
    """Загрузить фото с диска (дополняет галерею)."""
    lot = get_object_or_404(AvitoLot, pk=pk)
    from auction_avito.services.images import save_uploaded_files

    files = request.FILES.getlist('photos')
    count, msg = save_uploaded_files(lot, files)
    if count:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)
    return redirect('auction_avito:lot_detail', pk=pk)


@login_required
def buyout_recommendations(request):
    """Рейтинг продаж БУ по этапу УС + рекомендации лотов Avito на выкуп."""
    from auction_avito.services.buyout_recommendations import build_buyout_page_context

    ctx = build_buyout_page_context(request)
    return render(request, 'auction_avito/buyout_recommendations.html', {'params': ctx})


def _parse_optional_int(raw):
    raw = (raw or '').strip()
    if raw == '':
        return None
    return int(raw)


@login_required
@require_http_methods(['GET', 'POST'])
def auction_settings(request):
    """Настройки автоставок и коэффициентов рекомендаций выкупа."""
    settings_obj = AvitoAuctionSettings.get_solo()

    if request.method == 'POST':
        try:
            settings_obj.auto_bid_enabled = request.POST.get('auto_bid_enabled') == 'on'
            settings_obj.mileage_min = _parse_optional_int(request.POST.get('mileage_min'))
            settings_obj.mileage_max = _parse_optional_int(request.POST.get('mileage_max'))
            settings_obj.year_min = _parse_optional_int(request.POST.get('year_min'))
            settings_obj.year_max = _parse_optional_int(request.POST.get('year_max'))
            settings_obj.block_taxi = request.POST.get('block_taxi') == 'on'
            settings_obj.block_carsharing = request.POST.get('block_carsharing') == 'on'
            settings_obj.block_mileage_twisted = request.POST.get('block_mileage_twisted') == 'on'
            settings_obj.bid_round_to = max(1, int(request.POST.get('bid_round_to') or 1000))
            settings_obj.weight_test_price = request.POST.get('weight_test_price') or 1
            settings_obj.weight_rdo = request.POST.get('weight_rdo') or '0.55'
            settings_obj.weight_kor = request.POST.get('weight_kor') or '0.25'
            settings_obj.weight_txt = request.POST.get('weight_txt') or '0.05'
            settings_obj.outcome_poll_enabled = request.POST.get('outcome_poll_enabled') == 'on'
            settings_obj.win_notify_emails = (request.POST.get('win_notify_emails') or '').strip()
            settings_obj.full_clean()
            settings_obj.save()
            messages.success(request, 'Настройки сохранены.')
            return redirect('auction_avito:auction_settings')
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, 'auction_avito/auction_settings.html', {
        'settings': settings_obj,
    })


@login_required
def feed_chat_messages(request):
    """Подгрузка сообщений ленты Авито (старые, пагинация при прокрутке)."""
    from django.http import JsonResponse

    from auction_avito.chat_utils import (
        AAV_FEED_PAGE_SIZE,
        get_aav_chat_messages,
        get_or_create_feed_chat,
        serialize_aav_chat_message,
    )

    chat = get_or_create_feed_chat()
    before_id = request.GET.get('before_id')
    try:
        limit = min(int(request.GET.get('limit', AAV_FEED_PAGE_SIZE)), 50)
    except (TypeError, ValueError):
        limit = AAV_FEED_PAGE_SIZE

    if before_id:
        try:
            before_id = int(before_id)
        except (TypeError, ValueError):
            before_id = None

    messages = get_aav_chat_messages(
        chat,
        newest_first=True,
        limit=limit,
        before_id=before_id,
    )
    return JsonResponse({
        'messages': [serialize_aav_chat_message(m, request.user) for m in messages],
        'has_more': len(messages) >= limit,
    })


@login_required
def feed_chat_send(request):
    """HTTP-отправка сообщения в общий чат ленты Авито (fallback без WebSocket)."""
    from django.http import JsonResponse

    from auction_avito.chat_utils import broadcast_aav_feed_message, get_or_create_feed_chat
    from chats.models import ChatMessage

    if request.method != 'POST':
        return JsonResponse({'error': 'method'}, status=405)

    profile = getattr(request.user, 'profiles', None)
    if profile and profile.user_sb:
        return JsonResponse({'error': 'forbidden'}, status=403)

    message = (request.POST.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'empty'}, status=400)

    chat = get_or_create_feed_chat()
    msg = ChatMessage.objects.create(user=request.user, chat=chat, content=message)
    broadcast_aav_feed_message(chat, message, request.user)
    return JsonResponse({'ok': True, 'message_id': msg.pk})


@login_required
def lot_chat_send(request, pk):
    """HTTP-отправка сообщения в чат конкретного лота."""
    from django.http import JsonResponse

    from auction_avito.chat_utils import broadcast_aav_message, get_or_create_lot_chat
    from auction_avito.models import AvitoLot
    from chats.models import ChatMessage

    if request.method != 'POST':
        return JsonResponse({'error': 'method'}, status=405)

    profile = getattr(request.user, 'profiles', None)
    if profile and profile.user_sb:
        return JsonResponse({'error': 'forbidden'}, status=403)

    lot = get_object_or_404(AvitoLot, pk=pk)
    message = (request.POST.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'empty'}, status=400)

    chat = get_or_create_lot_chat(lot)
    msg = ChatMessage.objects.create(user=request.user, chat=chat, content=message)
    broadcast_aav_message(chat, message, request.user)
    return JsonResponse({'ok': True, 'message_id': msg.pk})
