"""Расчёт и чтение KMCar (кэш итога КМ по автомобилю)."""
from datetime import datetime

from prices_car.models import KMCar

# type_km: 1 — план на месяц, 3 — ручной, 4 — спец. условие, 5 — АвтоК, 6 — Вариант 6 (Smart АвтоК)
TYPE_KM_LABELS = {
    0: 'Не рассчитан',
    1: 'План на месяц',
    2: 'Авто+',
    3: 'Ручной КМ',
    4: 'Спец. условие ГК',
    5: 'АвтоК',
    6: 'Вариант 6 (Smart АвтоК)',
}


def resolve_km_priority(
    km_manual,
    km_auto_1,
    km_auto_2,
    km_auto_3,
    km_auto_k=0,
    km_auto_k_tradein=0,
    with_trade_in=False,
    km_auto_6=0,
):
    """
    Итог КМ и type_km:
    ручной > Вариант 6 (Smart АвтоК) > спец. условие > АвтоК (с/без trade-in) > план на месяц.
    Авто+ (km_auto_2) в цепочку не входит — только справочно.
    """
    manual = int(km_manual or 0)
    if manual > 0:
        return manual, 3

    auto6 = int(km_auto_6 or 0)
    if auto6 > 0:
        return auto6, 6

    auto3 = int(km_auto_3 or 0)
    if auto3 > 0:
        return auto3, 4

    auto_k_plain = int(km_auto_k or 0)
    auto_k_ti = int(km_auto_k_tradein or 0)
    auto_k = auto_k_ti if with_trade_in and auto_k_ti > 0 else auto_k_plain
    if auto_k > 0:
        return auto_k, 5

    plan = int(km_auto_1 or 0)
    if plan > 0:
        return plan, 1

    return 0, 0


def resolve_km_car_total(
    km_manual, km_auto_1, km_auto_2, km_auto_3,
    km_auto_k=0, km_auto_k_tradein=0, with_trade_in=False,
    km_auto_6=0,
):
    """Обратная совместимость: km_auto_2 не участвует в итоге."""
    return resolve_km_priority(
        km_manual, km_auto_1, km_auto_2, km_auto_3,
        km_auto_k, km_auto_k_tradein, with_trade_in,
        km_auto_6=km_auto_6,
    )


def resolve_km_from_cumulative(cumulative_data, car=None, with_trade_in=False):
    """Итог КМ из cumulative_data по правилу приоритетов."""
    if not cumulative_data:
        return 0, 0

    manual = 0
    if car and car.min_km:
        manual = int(car.min_km)

    auto1 = int((cumulative_data.get('automatic') or {}).get('km_min_automatic') or 0)
    auto2 = int((cumulative_data.get('automatic_2') or {}).get('km_min_automatic') or 0)
    auto3 = 0
    if cumulative_data.get('automatic_3'):
        auto3 = int(cumulative_data['automatic_3'].get('km_min_automatic') or 0)
    auto_k = int((cumulative_data.get('automatic_k') or {}).get('km_min_automatic') or 0)
    auto_k_ti = int((cumulative_data.get('automatic_k_tradein') or {}).get('km_min_automatic') or 0)
    auto6 = int((cumulative_data.get('automatic_6') or {}).get('km_min_automatic') or 0)

    return resolve_km_priority(
        manual, auto1, auto2, auto3, auto_k, auto_k_ti, with_trade_in,
        km_auto_6=auto6,
    )


def _target_cum_value(info, key):
    block = info.get(key) or {}
    return int(block.get('km_min_automatic') or 0)


def build_km_car_fields_from_car(car):
    """Собрать компоненты KMCar из cumulative_data и min_km автомобиля."""
    if car is None or not car.modification_autoru_id:
        return None

    info = car.cumulative_data()
    auto1 = int(info.get('automatic', {}).get('km_min_automatic') or 0)
    auto2 = int(info.get('automatic_2', {}).get('km_min_automatic') or 0)
    auto3 = 0
    if info.get('automatic_3'):
        auto3 = int(info.get('automatic_3', {}).get('km_min_automatic') or 0)
    auto_k = _target_cum_value(info, 'automatic_k')
    auto_k_tradein = _target_cum_value(info, 'automatic_k_tradein')
    auto6 = int(info.get('automatic_6', {}).get('km_min_automatic') or 0)

    manual = 0
    if car.min_km:
        manual = int(car.min_km)

    return {
        'km_auto_1': auto1,
        'km_auto_2': auto2,
        'km_auto_3': auto3,
        'km_auto_k': auto_k,
        'km_auto_k_tradein': auto_k_tradein,
        'km_auto_6': auto6,
        'km_manual': manual,
    }


def create_km_car_for_car(car, commit=True):
    """Создать запись KMCar по текущим данным автомобиля."""
    fields = build_km_car_fields_from_car(car)
    if fields is None:
        return None

    km_car = KMCar(
        car=car,
        date=datetime.now(),
        km_auto_1=fields['km_auto_1'],
        km_auto_2=fields['km_auto_2'],
        km_auto_3=fields['km_auto_3'],
        km_auto_k=fields['km_auto_k'],
        km_auto_k_tradein=fields['km_auto_k_tradein'],
        km_auto_6=fields.get('km_auto_6', 0),
        km_manual=fields['km_manual'],
    )
    if commit:
        km_car.save()
    return km_car


def resolve_km_from_row(row, with_trade_in=False):
    total, _ = resolve_km_car_total(
        row.km_manual,
        row.km_auto_1,
        row.km_auto_2,
        row.km_auto_3,
        row.km_auto_k,
        row.km_auto_k_tradein,
        with_trade_in=with_trade_in,
        km_auto_6=getattr(row, 'km_auto_6', 0),
    )
    return int(total) if total else None


def get_car_latest_km_car(car):
    if car is None:
        return None
    return KMCar.objects.filter(car=car).order_by('-date', '-pk').first()


def get_car_latest_km_value(car, with_trade_in=False):
    row = get_car_latest_km_car(car)
    if row is not None:
        km = resolve_km_from_row(row, with_trade_in=with_trade_in)
        if km is not None:
            return km

    fields = build_km_car_fields_from_car(car)
    if fields is None:
        return None
    total, _ = resolve_km_car_total(
        fields['km_manual'],
        fields['km_auto_1'],
        fields['km_auto_2'],
        fields['km_auto_3'],
        fields['km_auto_k'],
        fields['km_auto_k_tradein'],
        with_trade_in=with_trade_in,
        km_auto_6=fields.get('km_auto_6', 0),
    )
    return total or None
