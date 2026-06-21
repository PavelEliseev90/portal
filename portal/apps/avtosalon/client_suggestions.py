"""Подбор альтернативных автомобилей на складе ДЦ (KMCar)."""
from django.db.models import OuterRef, Subquery

from prices_car.km_car import get_car_latest_km_value
from prices_car.models import KMCar
from refs.models import RefCarsOrganization

KM_CAR_LAST_QS = KMCar.objects.filter(car_id=OuterRef('pk')).order_by('-date', '-pk')

TYPE_KM_LABELS = {
    0: '—',
    1: 'Авто',
    2: 'Авто+',
    3: 'Ручной КМ',
    4: 'Спец. условие',
}

SUGGESTIONS_LIMIT = 20


def deal_needs_client_suggestions(calc, cumulative_data, car):
    """КП не проходит по правилу — есть смысл искать альтернативы."""
    from avtosalon.deal_calc_approval import is_auto_approved_calculation, kvp_above_km_rule
    from prices_car.km_breakdown import get_km_rule_total

    if not car or not calc:
        return False
    if is_auto_approved_calculation(calc):
        return False
    km_rule = get_km_rule_total(cumulative_data, car)
    if km_rule is None:
        return False
    if kvp_above_km_rule(calc, cumulative_data):
        return False
    return int(calc.kvp or 0) <= int(km_rule)


def get_reference_km_for_car(car):
    return get_car_latest_km_value(car)


def _suggestions_filter_label(car):
    model_name = ''
    complectation_name = ''
    if car and car.modification_autoru_id:
        model_name = car.modification_autoru.model.name
    if car and car.complectation_autoru_id:
        complectation_name = car.complectation_autoru.name
    if model_name and complectation_name:
        return '{} · {}'.format(model_name, complectation_name)
    return model_name


def _suggestions_base_qs(car, unit_id):
    if not car or not unit_id or not car.modification_autoru_id:
        return RefCarsOrganization.objects.none()

    model_id = car.modification_autoru.model_id
    qs = RefCarsOrganization.objects.filter(
        unit_id=unit_id,
        is_new=True,
        quantity__gt=0,
        modification_autoru__model_id=model_id,
    ).exclude(
        pk=car.pk,
    ).exclude(
        modification_autoru__isnull=True,
    )
    if car.complectation_autoru_id:
        qs = qs.filter(complectation_autoru_id=car.complectation_autoru_id)
    return qs


def _annotate_last_km(qs):
    return qs.annotate(
        last_km=Subquery(KM_CAR_LAST_QS.values('km')[:1]),
        last_km_type=Subquery(KM_CAR_LAST_QS.values('type_km')[:1]),
        last_km_date=Subquery(KM_CAR_LAST_QS.values('date')[:1]),
    )


def get_client_suggestions_qs(car, unit_id, reference_km):
    if reference_km is None:
        return RefCarsOrganization.objects.none()

    qs = _annotate_last_km(_suggestions_base_qs(car, unit_id))
    return qs.filter(
        last_km__isnull=False,
        last_km__lt=reference_km,
    ).select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'complectation_autoru',
        'stage_price',
        'unit',
    ).order_by('last_km', 'price', 'name')


def count_client_suggestions(car, unit_id, reference_km):
    return get_client_suggestions_qs(car, unit_id, reference_km).count()


def serialize_client_suggestion(car, reference_km, kvp):
    km = int(car.last_km or 0)
    delta = int(reference_km) - km
    kvp_val = int(kvp or 0)
    model_name = ''
    mark_name = ''
    if car.modification_autoru_id:
        model_name = car.modification_autoru.model.name
        if car.modification_autoru.model.mark_id:
            mark_name = car.modification_autoru.model.mark.name

    complectation = ''
    if car.complectation_autoru_id:
        complectation = car.complectation_autoru.name

    return {
        'id': car.pk,
        'slug': car.slug,
        'vin': car.vin or '',
        'name': car.name or '',
        'mark': mark_name,
        'model': model_name,
        'complectation': complectation,
        'price': car.price or 0,
        'km': km,
        'km_delta': delta,
        'type_km': car.last_km_type or 0,
        'type_km_label': TYPE_KM_LABELS.get(car.last_km_type or 0, '—'),
        'rule_label': TYPE_KM_LABELS.get(car.last_km_type or 0, '—'),
        'days_in_stock': car.days_in_stok or 0,
        'stage_price': str(car.stage_price) if car.stage_price_id else '',
        'approval_passes': kvp_val > km if kvp_val else False,
        'price_url': '/cars/{}/price/'.format(car.slug) if car.slug else '',
        'car_url': '/cars/{}/'.format(car.slug) if car.slug else '',
    }


def list_client_suggestions(car, unit_id, reference_km, kvp, limit=SUGGESTIONS_LIMIT):
    qs = get_client_suggestions_qs(car, unit_id, reference_km)[:limit]
    items = [serialize_client_suggestion(item, reference_km, kvp) for item in qs]
    total = count_client_suggestions(car, unit_id, reference_km)
    filter_label = _suggestions_filter_label(car)
    return {
        'items': items,
        'total': total,
        'shown': len(items),
        'reference_km': reference_km,
        'kvp': int(kvp or 0),
        'model_name': filter_label,
        'filter_label': filter_label,
        'same_complectation': bool(car.complectation_autoru_id),
    }
