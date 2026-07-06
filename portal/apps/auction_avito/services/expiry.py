"""
Автоматическое завершение лотов, у которых истекло время окончания (finish_at).
"""
from django.utils import timezone

from auction_avito.models import AvitoLotOffer


def expire_overdue_lots() -> int:
    """
    Переводит офферы со статусом inprogress в finished, если finish_at лота уже прошло.
    Возвращает количество обновлённых офферов.
    """
    now = timezone.now()
    offers = AvitoLotOffer.objects.filter(
        status_code='inprogress',
        lot__finish_at__isnull=False,
        lot__finish_at__lte=now,
    )
    return offers.update(status_code='finished', status_name='Завершён')
