"""Разбор и сохранение меток (badges) Авито из API и raw JSON."""

from __future__ import annotations

from types import SimpleNamespace

from auction_avito.models import AvitoLot, AvitoLotBadge, AvitoLotOffer, AvitoOfferBadge


def badge_avito_id(badge: dict, index: int) -> int:
    """ID метки из API или стабильный отрицательный surrogate."""
    raw = badge.get('id')
    if raw is not None and raw != '':
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    key = (badge.get('badgeType') or badge.get('title') or str(index)).strip()
    return -(abs(hash(key)) % 10**11 + index + 1)


def iter_badges_from_payload(
    badges=None,
    badges_by_style=None,
):
    """Плоский список (badge_dict, style) из badges[] и badgesByStyle[]."""
    index = 0
    for b in badges or []:
        if isinstance(b, dict):
            yield b, ''
            index += 1
    for group in badges_by_style or []:
        if not isinstance(group, dict):
            continue
        style = (group.get('style') or '').strip()
        for b in group.get('badges') or []:
            if isinstance(b, dict):
                yield b, style
                index += 1


def badge_is_meaningful(badge: dict) -> bool:
    return bool(
        (badge.get('badgeType') or '').strip()
        or (badge.get('title') or '').strip()
        or (badge.get('description') or '').strip()
    )


def sync_lot_badges_records(lot, badges=None, badges_by_style=None) -> int:
    from auction_avito.models import AvitoLotBadge

    lot.badges.all().delete()
    count = 0
    for idx, (b, style) in enumerate(iter_badges_from_payload(badges, badges_by_style)):
        if not badge_is_meaningful(b):
            continue
        AvitoLotBadge.objects.create(
            lot=lot,
            avito_badge_id=badge_avito_id(b, idx),
            badge_type=(b.get('badgeType') or '').strip(),
            title=(b.get('title') or '').strip(),
            description=(b.get('description') or '').strip(),
            priority=b.get('priority') or 0,
            style=style or (b.get('style') or ''),
        )
        count += 1
    return count


def sync_offer_badges_records(offer, offer_data: dict) -> int:
    from auction_avito.models import AvitoOfferBadge

    offer.badges.all().delete()
    count = 0
    for idx, (b, style) in enumerate(
        iter_badges_from_payload(
            offer_data.get('badges'),
            offer_data.get('badgesByStyle'),
        )
    ):
        if not badge_is_meaningful(b):
            continue
        AvitoOfferBadge.objects.create(
            offer=offer,
            avito_badge_id=badge_avito_id(b, idx),
            badge_type=(b.get('badgeType') or '').strip(),
            title=(b.get('title') or '').strip(),
            description=(b.get('description') or '').strip(),
            priority=b.get('priority') or 0,
            style=style or (b.get('style') or ''),
        )
        count += 1
    return count


def _badge_namespace(b: dict, style: str = '', source: str = '') -> SimpleNamespace:
    return SimpleNamespace(
        badge_type=(b.get('badgeType') or '').strip(),
        title=(b.get('title') or '').strip(),
        description=(b.get('description') or '').strip(),
        style=style or (b.get('style') or ''),
        priority=b.get('priority') or 0,
        source=source,
    )


def badges_from_raw_lot(lot: AvitoLot) -> list:
    raw = lot.raw_lot_json or {}
    result = []
    for b, style in iter_badges_from_payload(raw.get('badges'), raw.get('badgesByStyle')):
        if badge_is_meaningful(b):
            result.append(_badge_namespace(b, style, 'лот'))
    return result


def badges_from_raw_offer(offer: AvitoLotOffer) -> list:
    raw = offer.raw_offer_json or {}
    lot_raw = (raw.get('lot') or {}) if isinstance(raw.get('lot'), dict) else {}
    result = []
    for b, style in iter_badges_from_payload(
        raw.get('badges') or lot_raw.get('badges'),
        raw.get('badgesByStyle') or lot_raw.get('badgesByStyle'),
    ):
        if badge_is_meaningful(b):
            result.append(_badge_namespace(b, style, 'оффер'))
    return result


def ensure_badges_synced(lot: AvitoLot, primary_offer: AvitoLotOffer | None = None) -> None:
    """Дозаписать метки из raw JSON, если в БД пусто (старые лоты / calculate без id)."""
    if not lot.badges.exists():
        raw = lot.raw_lot_json or {}
        sync_lot_badges_records(
            lot,
            badges=raw.get('badges'),
            badges_by_style=raw.get('badgesByStyle'),
        )
    if primary_offer and not primary_offer.badges.exists():
        raw = primary_offer.raw_offer_json or {}
        lot_block = raw.get('lot') if isinstance(raw.get('lot'), dict) else {}
        sync_offer_badges_records(primary_offer, {
            'badges': raw.get('badges') or (lot_block or {}).get('badges'),
            'badgesByStyle': raw.get('badgesByStyle') or (lot_block or {}).get('badgesByStyle'),
        })


def collect_badges_for_display(lot: AvitoLot, primary_offer: AvitoLotOffer | None = None):
    """
    Возвращает (offer_badges, lot_badges, all_badges).
    Элементы — модели или SimpleNamespace с полями badge_type, title, description, style.
    """
    ensure_badges_synced(lot, primary_offer)

    offer_badges = list(primary_offer.badges.all()) if primary_offer else []
    lot_badges = list(lot.badges.all())

    if not offer_badges and primary_offer:
        offer_badges = badges_from_raw_offer(primary_offer)
    if not lot_badges:
        lot_badges = badges_from_raw_lot(lot)

    seen_types = {b.badge_type for b in offer_badges if b.badge_type}
    all_badges = list(offer_badges) + [
        b for b in lot_badges if b.badge_type not in seen_types
    ]
    return offer_badges, lot_badges, all_badges
