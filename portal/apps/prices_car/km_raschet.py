"""Расчётный КМ автомобиля для коммерческого предложения."""


def resolve_car_km_raschet(car, data_value=None):
    """
    Расчетный КМ на момент КП: из 1С, последнего KMCar или cumulative_data автомобиля.
    """
    if data_value is not None and data_value != '':
        try:
            return int(data_value)
        except (TypeError, ValueError):
            pass

    if car is None:
        return None

    from prices_car.models import KMCar

    row = KMCar.objects.filter(car=car).order_by('-date', '-pk').first()
    if row is not None and row.km is not None:
        return int(row.km)

    try:
        from prices_car.km_car import build_km_car_fields_from_car, resolve_km_car_total

        fields = build_km_car_fields_from_car(car)
        if fields:
            total, _ = resolve_km_car_total(
                fields['km_manual'],
                fields['km_auto_1'],
                fields['km_auto_2'],
                fields['km_auto_3'],
            )
            if total:
                return int(total)
    except Exception:
        pass

    return None


def apply_km_raschet_to_calculation(calculation_object, car, data=None):
    raw = None
    if data:
        raw = data.get('KmRaschet') or data.get('KmRaschetny') or data.get('Km')
    km = resolve_car_km_raschet(car, raw)
    if km is not None:
        calculation_object.km_raschet = km
