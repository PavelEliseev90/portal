"""Расчёт и чтение KMCar (кэш итога КМ по автомобилю)."""
from datetime import datetime

from prices_car.models import KMCar


def resolve_km_car_total(
    km_manual, km_auto_1, km_auto_2, km_auto_3,
    km_auto_k=0, km_auto_k_tradein=0, with_trade_in=False,
):
    """
    Итог КМ и type_km — приоритет как в cumulative_data():
    ручной > спец. условие > АвтоК > Авто+ > Авто.
    Для АвтоК выбирается вариант с trade-in или без.
    """
    manual = int(km_manual or 0)
    if manual > 0:
        return manual, 3

    auto3 = int(km_auto_3 or 0)
    if auto3 > 0:
        return auto3, 4

    auto_k_plain = int(km_auto_k or 0)
    auto_k_ti = int(km_auto_k_tradein or 0)
    auto_k = auto_k_ti if with_trade_in and auto_k_ti > 0 else auto_k_plain
    if auto_k > 0:
        return auto_k, 5

    auto1 = int(km_auto_1 or 0)
    auto2 = int(km_auto_2 or 0)
    if auto2 > auto1:
        return auto2, 2
    if auto1 > 0:
        return auto1, 1
    return 0, 0


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

    manual = 0
    if car.min_km:
        manual = int(car.min_km)

    return {
        'km_auto_1': auto1,
        'km_auto_2': auto2,
        'km_auto_3': auto3,
        'km_auto_k': auto_k,
        'km_auto_k_tradein': auto_k_tradein,
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
    )
    return total or None
