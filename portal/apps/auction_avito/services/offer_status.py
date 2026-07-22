"""Статусы офферов и фильтры активности лотов."""
from django.db.models import Q
from django.utils import timezone

from auction_avito.services.sync import _dt

TERMINAL_OFFER_STATUSES = ('finished', 'won', 'lost')

STATUS_NAMES = {
    'inprogress': 'Активен',
    'finished': 'Завершён',
    'won': 'Выигран',
    'lost': 'Проигран',
    'ended': 'Завершён',
    'canceled': 'Отменён',
    'cancelled': 'Отменён',
}

# Сырые коды Maxposter → портальные.
STATUS_ALIASES = {
    'ended': 'finished',
    'cancelled': 'canceled',
}


def normalize_offer_status(status_code: str, finish_at=None, now=None) -> tuple[str, str]:
    """
    Нормализует status_code оффера с учётом finish_at лота.
    Пустой статус + finish_at в будущем → inprogress.
    won/lost сохраняются; ended → finished.
    """
    now = _dt(now) or timezone.now()
    finish_at = _dt(finish_at)
    code = (status_code or '').strip()
    code = STATUS_ALIASES.get(code, code)

    if code in ('won', 'lost'):
        return code, STATUS_NAMES.get(code, code)

    if code in TERMINAL_OFFER_STATUSES or code == 'canceled':
        # canceled показываем как finished в фильтрах активности
        if code == 'canceled':
            return 'finished', STATUS_NAMES.get('canceled', 'Отменён')
        return code, STATUS_NAMES.get(code, code)

    if finish_at is not None and finish_at <= now:
        return 'finished', STATUS_NAMES['finished']

    if not code:
        return 'inprogress', STATUS_NAMES['inprogress']

    return code, STATUS_NAMES.get(code, code)


def active_lots_q(now=None):
    """Активный лот: finish_at в будущем или оффер inprogress, без терминального статуса."""
    now = _dt(now) or timezone.now()
    return (
        Q(finish_at__gt=now) | Q(offers__status_code='inprogress')
    ) & ~Q(offers__status_code__in=TERMINAL_OFFER_STATUSES)


def inactive_lots_q(now=None):
    now = _dt(now) or timezone.now()
    return (
        Q(finish_at__lte=now, finish_at__isnull=False)
        | Q(offers__status_code__in=TERMINAL_OFFER_STATUSES)
    )


def parse_activity_param(request, *, default='active'):
    """
    activity= в query — явный выбор «Все» (пустая строка).
    Без параметра activity — значение по умолчанию (active).
    """
    if 'activity' in request.GET:
        return (request.GET.get('activity') or '').strip()
    return default
