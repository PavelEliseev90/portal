"""Ручной максимум автоставки (manual_max_bid) на оффере."""
from __future__ import annotations

from typing import Any

from django.utils import timezone


def parse_manual_max_amount(raw) -> tuple[int | None, str | None]:
    """
    Парсит сумму максимума.
    Возвращает (value_or_None_для_сброса, error_or_None).
    Пустая строка / 0 / null → сброс (None).
    """
    text = ('' if raw is None else str(raw)).strip()
    if text in ('', '0', 'null', 'None'):
        return None, None
    try:
        value = int(float(text.replace(' ', '').replace(',', '.')))
    except (TypeError, ValueError):
        return None, 'invalid amount'
    if value < 1:
        return None, None
    return value, None


def resolve_effective_buyout(calc_buyout, manual_max_bid):
    """
    Целевой потолок для decide_auto_bid.

    Если задан ручной максимум — торгуемся до него независимо от расчёта
    (и когда manual выше calc, и когда ниже). Иначе — расчётный выкуп.
    Возвращает (effective_buyout, manual_max_or_None).
    """
    manual = None
    if manual_max_bid not in (None, '', 0, '0'):
        try:
            manual = int(float(str(manual_max_bid).replace(' ', '').replace(',', '.')))
        except (TypeError, ValueError):
            manual = None
    if manual is not None and manual > 0:
        return manual, manual
    return calc_buyout, None


def user_display_name(user) -> str:
    if user is None:
        return ''
    full = (user.get_full_name() or '').strip()
    if full:
        return full
    return (getattr(user, 'username', None) or '').strip() or str(user.pk)


def apply_manual_max_bid(offer, raw_amount, *, user=None) -> dict[str, Any]:
    """
    Задаёт или сбрасывает ручной максимум на оффере.
    Пишет кто и когда. Возвращает dict ok/error/manualMaxBid/…
    """
    value, error = parse_manual_max_amount(raw_amount)
    if error:
        return {'ok': False, 'error': error}

    offer.manual_max_bid = value
    offer.manual_max_bid_set_at = timezone.now()
    offer.manual_max_bid_set_by = user if user is not None and getattr(user, 'is_authenticated', False) else None
    offer.save(update_fields=[
        'manual_max_bid',
        'manual_max_bid_set_at',
        'manual_max_bid_set_by',
    ])
    return {
        'ok': True,
        'lotOfferId': offer.lot_offer_id,
        'manualMaxBid': offer.manual_max_bid,
        'manualMaxBidSetAt': offer.manual_max_bid_set_at,
        'manualMaxBidSetBy': user_display_name(offer.manual_max_bid_set_by),
        'manualMaxBidSetById': offer.manual_max_bid_set_by_id,
    }


def manual_max_meta(offer) -> dict[str, Any]:
    """Краткие поля для API/монитора."""
    if offer is None:
        return {
            'manualMaxBid': None,
            'manualMaxBidSetAt': None,
            'manualMaxBidSetBy': '',
        }
    set_at = offer.manual_max_bid_set_at
    return {
        'manualMaxBid': offer.manual_max_bid,
        'manualMaxBidSetAt': set_at.isoformat() if set_at else None,
        'manualMaxBidSetBy': user_display_name(getattr(offer, 'manual_max_bid_set_by', None)),
    }
