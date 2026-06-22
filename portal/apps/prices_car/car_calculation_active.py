"""Активное коммерческое предложение по рабочему листу (только последнее)."""
from django.utils import timezone


INACTIVE_REASON_PREFIX = 'Неактивно: есть другое активное коммерческое предложение'


def _format_calc_label(calc):
    number = (calc.number or '').strip() or '—'
    if calc.date:
        date_str = timezone.localtime(calc.date).strftime('%d.%m.%Y %H:%M')
    else:
        date_str = '—'
    return '№{} от {}'.format(number, date_str)


def sync_active_calculations_for_rlk(rlk_id):
    """
    По рабочему листу оставить активным только самое последнее КП (date, pk).
    Остальным — active=False и пояснение.
    """
    if not rlk_id:
        return None

    from prices_car.models import CarCalculations

    calcs = list(
        CarCalculations.objects.filter(rlk_id=rlk_id).order_by('-date', '-pk')
    )
    if not calcs:
        return None

    active_calc = calcs[0]
    active_label = _format_calc_label(active_calc)
    inactive_reason = '{} {}.'.format(INACTIVE_REASON_PREFIX, active_label)

    inactive_ids = [c.pk for c in calcs[1:]]
    if inactive_ids:
        CarCalculations.objects.filter(pk__in=inactive_ids).update(
            active=False,
            inactive_reason=inactive_reason,
        )

    if not active_calc.active or active_calc.inactive_reason:
        CarCalculations.objects.filter(pk=active_calc.pk).update(
            active=True,
            inactive_reason='',
        )

    return active_calc.pk
