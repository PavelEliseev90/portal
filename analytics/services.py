from typing import Dict

from django.db import transaction

from analytics.models import (
    AppraiserPerformanceSnapshot,
    EcoAnalystSnapshot,
    InteractivePricingSnapshot,
    TradeInFunnelSnapshot,
)


def _filter_payload(model, payload: Dict):
    allowed = {field.name for field in model._meta.get_fields() if hasattr(field, 'attname')}
    return {key: value for key, value in payload.items() if key in allowed}


def upsert_pricing_snapshot(estimation_id: int, payload: Dict) -> InteractivePricingSnapshot:
    """
    Сохранить/обновить запись витрины интерактивных согласований.
    """
    filtered = _filter_payload(InteractivePricingSnapshot, payload)
    if not filtered:
        raise ValueError('Передан пустой payload для InteractivePricingSnapshot')

    with transaction.atomic():
        snapshot, _ = InteractivePricingSnapshot.objects.update_or_create(
            estimation_id=estimation_id,
            defaults=filtered,
        )
    return snapshot


def upsert_eco_analyst_snapshot(estimation_id: int, role: str, payload: Dict) -> EcoAnalystSnapshot:
    """
    Сохранить/обновить запись витрины аналитиков ЕЦО.
    """
    filtered = _filter_payload(EcoAnalystSnapshot, payload)
    filtered['role'] = role
    filtered['estimation_id'] = estimation_id

    if not filtered:
        raise ValueError('Передан пустой payload для EcoAnalystSnapshot')

    with transaction.atomic():
        snapshot, _ = EcoAnalystSnapshot.objects.update_or_create(
            estimation_id=estimation_id,
            role=role,
            defaults=filtered,
        )
    return snapshot


def upsert_appraiser_snapshot(estimation_id: int, payload: Dict) -> AppraiserPerformanceSnapshot:
    filtered = _filter_payload(AppraiserPerformanceSnapshot, payload)
    if not filtered:
        raise ValueError('Передан пустой payload для AppraiserPerformanceSnapshot')

    with transaction.atomic():
        snapshot, _ = AppraiserPerformanceSnapshot.objects.update_or_create(
            estimation_id=estimation_id,
            defaults=filtered,
        )
    return snapshot


def upsert_tradein_snapshot(rlk_id: int, payload: Dict) -> TradeInFunnelSnapshot:
    filtered = _filter_payload(TradeInFunnelSnapshot, payload)
    if not filtered:
        raise ValueError('Передан пустой payload для TradeInFunnelSnapshot')

    with transaction.atomic():
        snapshot, _ = TradeInFunnelSnapshot.objects.update_or_create(
            rlk_id=rlk_id,
            defaults=filtered,
        )
    return snapshot

