import logging
from typing import Optional

from django.db import transaction

from analytics.models import InteractivePricingSnapshot

logger = logging.getLogger(__name__)


def upsert_pricing_snapshot(estimation_id: int, payload: dict) -> InteractivePricingSnapshot:
    """
    Сервисная функция для сохранения данных витрины.
    Ожидает готовый payload (значения полей модели), что позволяет заполнять витрину в месте,
    где уже есть вся бизнес-логика обработки RegInteractivOcenka.
    """
    allowed_fields = {
        field.name for field in InteractivePricingSnapshot._meta.get_fields() if hasattr(field, 'attname')
    }
    filtered_payload = {key: value for key, value in payload.items() if key in allowed_fields and key != 'estimation_id'}

    if not filtered_payload:
        raise ValueError('Передан пустой payload для витрины интерактивных согласований')

    with transaction.atomic():
        snapshot, _ = InteractivePricingSnapshot.objects.update_or_create(
            estimation_id=estimation_id,
            defaults=filtered_payload,
        )
    return snapshot

