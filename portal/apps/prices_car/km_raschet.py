"""Расчётный КМ автомобиля для коммерческого предложения."""


def calculation_has_applied_trade_in(calculation=None, data=None) -> bool:
    """
    Сделка с trade-in определяется по детальному расчёту КП:
    применённый показатель (success=True) с флагом is_trade_in на типе.
    """
    from prices_car.models import CarCalculationsDetail, CarCalculationsTypeDetail

    if calculation is not None and calculation.pk:
        if CarCalculationsDetail.objects.filter(
            calculation=calculation,
            success=True,
            detail_type__is_trade_in=True,
        ).exists():
            return True

    if data:
        trade_in_types = set(
            CarCalculationsTypeDetail.objects.filter(is_trade_in=True)
            .exclude(name='')
            .values_list('name', flat=True)
        )
        if trade_in_types:
            for item in data.get('Detail') or []:
                if item.get('Success') and item.get('Type') in trade_in_types:
                    return True

    if calculation is not None and int(calculation.custom_tradein or 0) > 0:
        return True

    return False


def _resolve_from_km_car_row(row, with_trade_in=False):
    from prices_car.km_car import resolve_km_from_row
    return resolve_km_from_row(row, with_trade_in=with_trade_in)


def resolve_car_km_raschet(car, data_value=None, calculation=None, data=None, with_trade_in=None):
    """
    Расчетный КМ на момент КП: из 1С, последнего KMCar или cumulative_data автомобиля.
    Учитывает сегмент trade-in по детальному расчёту КП.
    """
    if data_value is not None and data_value != '':
        try:
            return int(data_value)
        except (TypeError, ValueError):
            pass

    if car is None:
        return None

    if with_trade_in is None:
        with_trade_in = calculation_has_applied_trade_in(calculation, data)

    from prices_car.models import KMCar

    row = KMCar.objects.filter(car=car).order_by('-date', '-pk').first()
    if row is not None:
        km = _resolve_from_km_car_row(row, with_trade_in=with_trade_in)
        if km is not None:
            return km

    try:
        from prices_car.km_car import build_km_car_fields_from_car, resolve_km_car_total

        fields = build_km_car_fields_from_car(car)
        if fields:
            total, _ = resolve_km_car_total(
                fields['km_manual'],
                fields['km_auto_1'],
                fields['km_auto_2'],
                fields['km_auto_3'],
                fields.get('km_auto_k'),
                fields.get('km_auto_k_tradein'),
                with_trade_in=with_trade_in,
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
    km = resolve_car_km_raschet(
        car,
        raw,
        calculation=calculation_object,
        data=data,
    )
    if km is not None:
        calculation_object.km_raschet = km


def refresh_km_raschet_after_details(calculation_object, car, data=None):
    """Пересчитать km_raschet после сохранения детализации КП (показатели trade-in)."""
    km = resolve_car_km_raschet(car, calculation=calculation_object, data=data)
    if km is not None and calculation_object.km_raschet != km:
        calculation_object.km_raschet = km
        calculation_object.save(update_fields=['km_raschet'])
