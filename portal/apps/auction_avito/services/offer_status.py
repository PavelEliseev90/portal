"""Статусы офферов и фильтры активности лотов."""
from django.db.models import Q
from django.utils import timezone

TERMINAL_OFFER_STATUSES = ('finished', 'won', 'lost')

STATUS_NAMES = {
    'inprogress': 'Активен',
    'finished': 'Завершён',
    'won': 'Выигран',
    'lost': 'Проигран',
}


def normalize_offer_status(status_code: str, finish_at=None, now=None) -> tuple[str, str]:
    """
    Нормализует status_code оффера с учётом finish_at лота.
    Пустой статус + finish_at в будущем → inprogress.
    """
    now = now or timezone.now()
    code = (status_code or '').strip()

    if code in TERMINAL_OFFER_STATUSES:
        return code, STATUS_NAMES.get(code, code)

    if finish_at is not None and finish_at <= now:
        return 'finished', STATUS_NAMES['finished']

    if not code:
        return 'inprogress', STATUS_NAMES['inprogress']

    return code, STATUS_NAMES.get(code, code)


def active_lots_q(now=None):
    """Активный лот: finish_at в будущем или оффер inprogress, без терминального статуса."""
    now = now or timezone.now()
    return (
        Q(finish_at__gt=now)
        | Q(offers__status_code='inprogress')
    ).exclude(
        offers__status_code__in=TERMINAL_OFFER_STATUSES,
    )


def inactive_lots_q(now=None):
    now = now or timezone.now()
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
