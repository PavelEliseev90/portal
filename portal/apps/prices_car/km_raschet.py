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
        info = car.cumulative_data()
        auto1 = int(info.get('automatic', {}).get('km_min_automatic') or 0)
        auto2 = int(info.get('automatic_2', {}).get('km_min_automatic') or 0)
        auto3 = int(info.get('automatic_3', {}).get('km_min_automatic') or 0)
        if auto3:
            return auto3
        if auto1 or auto2:
            return max(auto1, auto2)
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
