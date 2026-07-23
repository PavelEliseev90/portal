"""Отчёт по согласованию коммерческих предложений (только для УК)."""
from datetime import date
from calendar import monthrange

from django.db.models import OuterRef, Subquery, Q
from django.urls import reverse
from django.utils import timezone

from avtosalon.deal_calc_approval import user_has_deal_calc_uk_access
from documents.models import DocCarShipment
from prices_car.calculations_table import get_soglasovanie_status_display
from prices_car.models import CarCalculations


def _current_month_bounds():
    today = timezone.now().date()
    return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])


def _parse_date(raw):
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _car_mark(car):
    if not car:
        return ''
    if car.mark:
        return car.mark
    mod = getattr(car, 'modification_autoru', None)
    model = getattr(mod, 'model', None) if mod else None
    mark = getattr(model, 'mark', None) if model else None
    return getattr(mark, 'name', '') or ''


def _car_model(car):
    if not car:
        return ''
    if car.model:
        return car.model
    mod = getattr(car, 'modification_autoru', None)
    model = getattr(mod, 'model', None) if mod else None
    return getattr(model, 'name', '') or ''


def _car_complectation(car):
    if not car:
        return ''
    comp = getattr(car, 'complectation_autoru', None)
    if comp and getattr(comp, 'name', None):
        return comp.name
    return ''


def build_approval_report_queryset(request):
    """
    Последнее КП по рабочему листу (active=True).
    Факт доходности при продаже — из CumulativeMarginUS по VIN (если есть).
    """
    date_start = _parse_date(request.GET.get('date_start'))
    date_end = _parse_date(request.GET.get('date_end'))
    if date_start is None and date_end is None:
        date_start, date_end = _current_month_bounds()

    vin = (request.GET.get('vin') or '').strip()
    unit_id = (request.GET.get('unit_id') or '').strip()
    only_shipped = (request.GET.get('only_shipped') or '').strip() in ('1', 'true', 'yes', 'on')
    soglasovanie = (request.GET.get('soglasovanie') or '').strip()

    shipment_qs = (
        DocCarShipment.objects
        .filter(rlk_id=OuterRef('rlk_id'), active=True)
        .order_by('-dataTime')
    )

    sale_kvp_sq = None
    try:
        from powerbi.models import CumulativeMarginUS

        sale_kvp_sq = (
            CumulativeMarginUS.objects
            .filter(VIN=OuterRef('car__vin'))
            .exclude(VIN='')
            .exclude(VIN__isnull=True)
            .order_by('-DataProdazhi', '-pk')
        )
    except Exception:
        sale_kvp_sq = None

    qs = (
        CarCalculations.objects
        .filter(active=True, rlk_id__isnull=False)
        .select_related(
            'unit',
            'unit__city',
            'car',
            'car__modification_autoru',
            'car__modification_autoru__model',
            'car__modification_autoru__model__mark',
            'car__complectation_autoru',
            'rlk',
        )
        .annotate(
            shipment_pk=Subquery(shipment_qs.values('pk')[:1]),
            shipment_nomer=Subquery(shipment_qs.values('nomer')[:1]),
        )
    )
    if sale_kvp_sq is not None:
        qs = qs.annotate(sale_kvp=Subquery(sale_kvp_sq.values('KVP')[:1]))

    if date_start:
        qs = qs.filter(date__date__gte=date_start)
    if date_end:
        qs = qs.filter(date__date__lte=date_end)
    if vin:
        qs = qs.filter(car__vin__icontains=vin)
    if unit_id.isdigit():
        qs = qs.filter(unit_id=int(unit_id))
    if only_shipped:
        qs = qs.filter(shipment_pk__isnull=False)
    if soglasovanie:
        if soglasovanie == 'approved':
            qs = qs.filter(soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
                CarCalculations.SOGLASOVANIE_UK_APPROVED,
            ])
        elif soglasovanie == 'pending':
            qs = qs.filter(
                Q(soglasovanie_status__in=[
                    CarCalculations.SOGLASOVANIE_PENDING,
                    CarCalculations.SOGLASOVANIE_PENDING_UK,
                    CarCalculations.SOGLASOVANIE_AWAITING_1C,
                    '',
                ])
                | Q(soglasovanie_status__isnull=True)
            )
        elif soglasovanie == 'rejected':
            qs = qs.filter(soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
                CarCalculations.SOGLASOVANIE_UK_REJECTED,
            ])
        else:
            qs = qs.filter(soglasovanie_status=soglasovanie)

    filtr = {
        'date_start': date_start.isoformat() if date_start else '',
        'date_end': date_end.isoformat() if date_end else '',
        'vin': vin,
        'unit_id': unit_id if unit_id.isdigit() else '',
        'only_shipped': only_shipped,
        'soglasovanie': soglasovanie,
    }
    return qs.order_by('-date', '-pk'), filtr


def serialize_approval_report_row(calc):
    car = calc.car
    unit = calc.unit
    city = getattr(unit, 'city', None) if unit else None
    shipped = bool(getattr(calc, 'shipment_pk', None))
    sale_kvp = getattr(calc, 'sale_kvp', None)
    if sale_kvp is not None:
        sale_profit = sale_kvp
    elif shipped:
        sale_profit = calc.kvp
    else:
        sale_profit = None
    return {
        'pk': calc.pk,
        'url': reverse('avtosalon:deal_calculation_doc', kwargs={'id': calc.pk}),
        'unit_name': unit.name if unit else '—',
        'city_name': city.name if city else '—',
        'unit_label': (
            '{} ({})'.format(unit.name, city.name)
            if unit and city
            else (unit.name if unit else '—')
        ),
        'mark': _car_mark(car) or '—',
        'model': _car_model(car) or '—',
        'complectation': _car_complectation(car) or '—',
        'year': car.year if car and car.year else '—',
        'vin': car.vin if car and car.vin else '—',
        'rlk_nomer': calc.rlk.nomer if calc.rlk else '—',
        'number': calc.number or '—',
        'date': calc.date,
        'kvp': calc.kvp,
        'km_formula': calc.km_raschet,
        'soglasovanie_status': calc.soglasovanie_status or '',
        'soglasovanie_label': get_soglasovanie_status_display(calc),
        'shipped': shipped,
        'shipment_nomer': getattr(calc, 'shipment_nomer', None) or '',
        'sale_profit': sale_profit,
    }


def build_approval_report_context(request):
    from refs.models import RefUnit

    qs, filtr = build_approval_report_queryset(request)
    units = (
        RefUnit.objects
        .filter(buauto=False, ib__active=True, name__istartswith='дц')
        .select_related('city')
        .order_by('name')
    )
    return {
        'filtr': filtr,
        'units': units,
        'queryset': qs,
        'desktop_url': reverse('prices_car:new_cars_director_desktop'),
        'report_url': reverse('prices_car:deal_calc_approval_report'),
        'is_uk': user_has_deal_calc_uk_access(request.user),
    }
