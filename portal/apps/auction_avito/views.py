from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from auction_avito.models import (
    AvitoAutotekaEvent,
    AvitoLot,
    AvitoLotBadge,
    AvitoLotCalculation,
    AvitoLotOffer,
    AvitoOfferBadge,
    AvitoVenue,
)

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


def _venue_filter_choices():
    return [
        (str(v.dealer_id), v.display_label)
        for v in AvitoVenue.objects.select_related('city').order_by('city__name', 'name', 'dealer_id')
    ]


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


@login_required
def lot_list(request):
    qs = _lot_queryset()

    search = (request.GET.get('q') or '').strip()
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

    params = {
        'type': 'auction_avito_list',
        'page_obj': page_obj,
        'filters': {
            'q': search,
            'status': status,
            'badge': badge_type,
            'trade_in': trade_in,
            'venue': venue_dealer,
            'sort': sort,
        },
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
    return render(request, 'auction_avito/lot_list.html', {'params': params})


@login_required
def lot_detail(request, pk):
    lot = get_object_or_404(_lot_queryset(), pk=pk)
    primary_offer = lot.offers.first()
    offer_badges = list(primary_offer.badges.all()) if primary_offer else []
    lot_badges = list(lot.badges.all())
    seen_types = {b.badge_type for b in offer_badges}
    all_badges = offer_badges + [b for b in lot_badges if b.badge_type not in seen_types]

    params = {
        'type': 'auction_avito_detail',
        'lot': lot,
        'vehicle': getattr(lot, 'vehicle_avito', None),
        'autohub': getattr(lot, 'vehicle_autohub', None),
        'autoteka': getattr(lot, 'autoteka', None),
        'autoteka_events': (
            lot.autoteka.events.all()
            if getattr(lot, 'autoteka', None)
            else []
        ),
        'primary_offer': primary_offer,
        'offers': lot.offers.all(),
        'images': lot.images.all(),
        'calculations': lot.calculations.all(),
        'latest_calculation': (
            lot.calculations.filter(is_success=True).first()
            or lot.calculations.first()
        ),
        'all_badges': all_badges,
        'offer_badges': offer_badges,
        'lot_badges': lot_badges,
        'badge_type_labels': BADGE_TYPE_LABELS,
        'equipment_items': _equipment_items(lot),
        'trade_in': _trade_in_display(lot),
        'prices': _lot_price_display(lot, primary_offer),
        'venue': _venue_display(lot, primary_offer),
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
