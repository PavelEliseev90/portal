from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404, render

from auction_avito.models import (
    AvitoAutotekaEvent,
    AvitoLot,
    AvitoLotCalculation,
    AvitoLotOffer,
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
            'sort': sort,
        },
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
    }
    return render(request, 'auction_avito/lot_detail.html', {'params': params})
