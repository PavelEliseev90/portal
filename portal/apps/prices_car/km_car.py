"""Расчёт и чтение KMCar (кэш итога КМ по автомобилю)."""
from datetime import datetime

from prices_car.models import KMCar


def resolve_km_car_total(km_manual, km_auto_1, km_auto_2, km_auto_3):
    """
    Итог КМ и type_km — приоритет как в cumulative_data():
    ручной > спец. условие > Авто+ > Авто.
    """
    manual = int(km_manual or 0)
    if manual > 0:
        return manual, 3

    auto3 = int(km_auto_3 or 0)
    if auto3 > 0:
        return auto3, 4

    auto1 = int(km_auto_1 or 0)
    auto2 = int(km_auto_2 or 0)
    if auto2 > auto1:
        return auto2, 2
    if auto1 > 0:
        return auto1, 1
    return 0, 0


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

    manual = 0
    if car.min_km:
        manual = int(car.min_km)

    return {
        'km_auto_1': auto1,
        'km_auto_2': auto2,
        'km_auto_3': auto3,
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
        km_manual=fields['km_manual'],
    )
    if commit:
        km_car.save()
    return km_car


def get_car_latest_km_car(car):
    if car is None:
        return None
    return KMCar.objects.filter(car=car).order_by('-date', '-pk').first()


def get_car_latest_km_value(car):
    row = get_car_latest_km_car(car)
    if row is not None and row.km is not None:
        return int(row.km)

    fields = build_km_car_fields_from_car(car)
    if fields is None:
        return None
    total, _ = resolve_km_car_total(
        fields['km_manual'],
        fields['km_auto_1'],
        fields['km_auto_2'],
        fields['km_auto_3'],
    )
    return total or None
