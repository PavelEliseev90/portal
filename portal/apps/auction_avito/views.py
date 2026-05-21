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
    sort = (request.GET.get('sort') or '-finish_at').strip()

    if search:
        qs = qs.filter(
            Q(lot_id__icontains=search)
            | Q(description__icontains=search)
            | Q(seller_place_name__icontains=search)
            | Q(vehicle_avito__brand_name__icontains=search)
            | Q(vehicle_avito__model_name__icontains=search)
        )

    if status:
        qs = qs.filter(offers__status_code=status).distinct()

    if badge_type:
        qs = qs.filter(
            Q(offers__badges__badge_type=badge_type)
            | Q(badges__badge_type=badge_type)
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
            'sort': sort,
        },
        'badge_choices': _badge_filter_choices(),
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
