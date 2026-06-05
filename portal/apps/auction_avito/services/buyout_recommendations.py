"""
Рейтинг продаж БУ по этапу УС на момент отгрузки + подбор похожих лотов Avito.

Источник продаж: DocCarShipment (проведённые отгрузки, unit.buauto=True).
Этап УС: RefCarsOrganization.stage_price на момент продажи (связь через lo).
Веса этапов: Тест-прайс лучше всего, далее РДО, Коррекция, ТХТ.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from auction_avito.lot_tabs import resolve_autoru_models, resolve_period
from auction_avito.models import AvitoLot
from documents.models import DocCarShipment, DocLO
from refs.models import RefCarsOrganization, RefUnit

# PK этапов УС в refStagePrice (как в korsavto_dashboard)
STAGE_TEST_PRICE = 4
STAGE_RDO = 2
STAGE_KOR = 3
STAGE_TXT = 1

STAGE_META = (
    (STAGE_TEST_PRICE, 'test', 'Тест-прайс', 1.0),
    (STAGE_RDO, 'rdo', 'РДО', 0.55),
    (STAGE_KOR, 'kor', 'Коррекция', 0.25),
    (STAGE_TXT, 'txt', 'ТХТ', 0.05),
)

STAGE_WEIGHT_BY_ID = {sid: weight for sid, _key, _label, weight in STAGE_META}
STAGE_LABEL_BY_ID = {sid: label for sid, _key, label, _weight in STAGE_META}


@dataclass
class SegmentRating:
    mark_id: int
    mark_name: str
    model_id: int
    model_name: str
    total: int = 0
    cnt_test: int = 0
    cnt_rdo: int = 0
    cnt_kor: int = 0
    cnt_txt: int = 0
    score: float = 0.0
    test_share: float = 0.0
    matched_lots: List[dict] = field(default_factory=list)

    def as_dict(self):
        return {
            'mark_id': self.mark_id,
            'mark_name': self.mark_name,
            'model_id': self.model_id,
            'model_name': self.model_name,
            'total': self.total,
            'cnt_test': self.cnt_test,
            'cnt_rdo': self.cnt_rdo,
            'cnt_kor': self.cnt_kor,
            'cnt_txt': self.cnt_txt,
            'score': round(self.score, 3),
            'test_share': round(self.test_share, 1),
            'matched_lots': self.matched_lots,
        }


def _car_org_subquery():
    return RefCarsOrganization.objects.filter(lo_id=OuterRef('lo_id'))


def _lo_subquery():
    return DocLO.objects.filter(pk=OuterRef('lo_id'))


def build_shipments_queryset(date_from, date_to, unit_ids=None):
    car_sub = _car_org_subquery()
    lo_sub = _lo_subquery()

    qs = DocCarShipment.objects.filter(
        active=True,
        lo_id__isnull=False,
        dataTime__date__gte=date_from,
        dataTime__date__lte=date_to,
        unit__buauto=True,
    )
    if unit_ids:
        qs = qs.filter(unit_id__in=unit_ids)

    return qs.annotate(
        stage_id=Subquery(car_sub.values('stage_price_id')[:1]),
        mark_id=Coalesce(
            Subquery(car_sub.values('modification_autoru__model__mark_id')[:1]),
            Subquery(lo_sub.values('modification_autoru__model__mark_id')[:1]),
        ),
        mark_name=Coalesce(
            Subquery(car_sub.values('modification_autoru__model__mark__name')[:1]),
            Subquery(lo_sub.values('modification_autoru__model__mark__name')[:1]),
        ),
        model_id=Coalesce(
            Subquery(car_sub.values('modification_autoru__model_id')[:1]),
            Subquery(lo_sub.values('modification_autoru__model_id')[:1]),
        ),
        model_name=Coalesce(
            Subquery(car_sub.values('modification_autoru__model__name')[:1]),
            Subquery(lo_sub.values('modification_autoru__model__name')[:1]),
        ),
    ).exclude(
        stage_id__isnull=True,
    ).filter(
        stage_id__in=[STAGE_TXT, STAGE_RDO, STAGE_KOR, STAGE_TEST_PRICE],
    ).exclude(
        mark_id__isnull=True,
    ).exclude(
        model_id__isnull=True,
    )


def _segment_score(cnt_test, cnt_rdo, cnt_kor, cnt_txt, total):
    if total <= 0:
        return 0.0
    weighted = (
        cnt_test * STAGE_WEIGHT_BY_ID[STAGE_TEST_PRICE]
        + cnt_rdo * STAGE_WEIGHT_BY_ID[STAGE_RDO]
        + cnt_kor * STAGE_WEIGHT_BY_ID[STAGE_KOR]
        + cnt_txt * STAGE_WEIGHT_BY_ID[STAGE_TXT]
    )
    return weighted / total


def compute_segment_ratings(
    date_from,
    date_to,
    unit_ids=None,
    *,
    min_sales=1,
    top_segments=40,
) -> Tuple[List[SegmentRating], dict]:
    """Агрегат продаж по марке/модели с рейтингом этапа УС."""
    qs = build_shipments_queryset(date_from, date_to, unit_ids)

    rows = qs.values('mark_id', 'mark_name', 'model_id', 'model_name').annotate(
        total=Count('pk'),
        cnt_test=Count('pk', filter=Q(stage_id=STAGE_TEST_PRICE)),
        cnt_rdo=Count('pk', filter=Q(stage_id=STAGE_RDO)),
        cnt_kor=Count('pk', filter=Q(stage_id=STAGE_KOR)),
        cnt_txt=Count('pk', filter=Q(stage_id=STAGE_TXT)),
    ).order_by('-total')

    ratings: List[SegmentRating] = []
    for row in rows:
        total = row['total'] or 0
        if total < min_sales:
            continue
        cnt_test = row['cnt_test'] or 0
        rating = SegmentRating(
            mark_id=row['mark_id'],
            mark_name=row['mark_name'] or '—',
            model_id=row['model_id'],
            model_name=row['model_name'] or '—',
            total=total,
            cnt_test=cnt_test,
            cnt_rdo=row['cnt_rdo'] or 0,
            cnt_kor=row['cnt_kor'] or 0,
            cnt_txt=row['cnt_txt'] or 0,
            score=_segment_score(
                cnt_test, row['cnt_rdo'] or 0, row['cnt_kor'] or 0, row['cnt_txt'] or 0, total,
            ),
            test_share=(cnt_test * 100.0 / total) if total else 0.0,
        )
        ratings.append(rating)

    ratings.sort(key=lambda r: (-r.score, -r.total, r.mark_name, r.model_name))
    ratings = ratings[:top_segments]

    summary = {
        'shipments_total': qs.count(),
        'segments_total': len(ratings),
        'date_from': date_from,
        'date_to': date_to,
    }
    return ratings, summary


def _active_lots_queryset():
    return (
        AvitoLot.objects.filter(offers__status_code='inprogress')
        .select_related('vehicle_avito', 'venue', 'venue__city')
        .prefetch_related('images', 'offers')
        .distinct()
        .order_by('-finish_at')
    )


def _lot_card(lot, segment: SegmentRating, match_score: float) -> dict:
    vehicle = getattr(lot, 'vehicle_avito', None)
    offer = lot.offers.first() if hasattr(lot, 'offers') else None
    title = ''
    if vehicle:
        parts = [p for p in (vehicle.brand_name, vehicle.model_name) if p]
        title = ' '.join(parts)
    img = lot.images.first() if hasattr(lot, 'images') else None
    return {
        'pk': lot.pk,
        'lot_id': lot.lot_id,
        'title': title or lot.description[:80] if lot.description else f'Лот {lot.lot_id}',
        'finish_at': lot.finish_at,
        'min_price': lot.min_price,
        'imv_median': lot.imv_median,
        'venue': lot.venue.display_label if lot.venue_id else (lot.seller_place_name or '—'),
        'match_score': round(match_score, 3),
        'segment_mark': segment.mark_name,
        'segment_model': segment.model_name,
        'segment_score': round(segment.score, 3),
        'photo_url': img.file.url if img and img.file else '',
        'offer_bid': offer.bid if offer else None,
    }


def match_lots_to_segments(
    ratings: Sequence[SegmentRating],
    *,
    max_lots_per_segment=3,
    max_lots_total=60,
) -> Tuple[List[SegmentRating], List[dict]]:
    """Подбор активных лотов Avito под сегменты с высоким рейтингом."""
    if not ratings:
        return [], []

    model_rating: Dict[int, SegmentRating] = {r.model_id: r for r in ratings}
    top_model_ids = set(model_rating.keys())

    # Кэш: model_id -> related Autoru model names for fuzzy lot match
    model_names = {
        m.id: (m.name or '', m.nameHuman or '', m.mark.name if m.mark_id else '')
        for m in AutoruModel.objects.filter(id__in=top_model_ids).select_related('mark')
    }

    active_lots = list(_active_lots_queryset()[:400])
    lot_matches: List[Tuple[float, AvitoLot, SegmentRating]] = []

    for lot in active_lots:
        vehicle = getattr(lot, 'vehicle_avito', None)
        if not vehicle:
            continue
        ctx = resolve_autoru_models(vehicle, include_model_choices=False)
        if not ctx or not ctx.get('model_ids'):
            continue
        matched_ids = [mid for mid in ctx['model_ids'] if mid in top_model_ids]
        if not matched_ids:
            continue
        best_mid = max(matched_ids, key=lambda mid: model_rating[mid].score)
        segment = model_rating[best_mid]
        # Чем выше рейтинг сегмента и совпадение — тем лучше
        match_score = segment.score + (0.05 if best_mid in matched_ids[:1] else 0)
        lot_matches.append((match_score, lot, segment))

    lot_matches.sort(key=lambda x: (-x[0], x[1].finish_at or 0))

    seen_lot_pks = set()
    flat_recommendations: List[dict] = []
    per_segment_count: Dict[int, int] = {}

    for match_score, lot, segment in lot_matches:
        if lot.pk in seen_lot_pks:
            continue
        cnt = per_segment_count.get(segment.model_id, 0)
        if cnt >= max_lots_per_segment:
            continue
        if len(flat_recommendations) >= max_lots_total:
            break
        card = _lot_card(lot, segment, match_score)
        segment.matched_lots.append(card)
        flat_recommendations.append(card)
        per_segment_count[segment.model_id] = cnt + 1
        seen_lot_pks.add(lot.pk)

    return list(ratings), flat_recommendations


def build_buyout_page_context(request) -> dict:
    date_from_raw = request.GET.get('date_from')
    date_to_raw = request.GET.get('date_to')
    date_from, date_to = resolve_period(date_from_raw, date_to_raw)

    unit_ids = []
    for raw in request.GET.getlist('unit[]') + request.GET.getlist('unit_ids'):
        if str(raw).isdigit():
            uid = int(raw)
            if uid not in unit_ids:
                unit_ids.append(uid)

    try:
        min_sales = max(1, int(request.GET.get('min_sales') or 2))
    except ValueError:
        min_sales = 2

    try:
        top_segments = min(80, max(10, int(request.GET.get('top') or 30)))
    except ValueError:
        top_segments = 30

    ratings, summary = compute_segment_ratings(
        date_from, date_to, unit_ids or None,
        min_sales=min_sales,
        top_segments=top_segments,
    )
    ratings, recommendations = match_lots_to_segments(ratings)

    bu_units = RefUnit.objects.filter(buauto=True, ib__active=True).order_by('name')

    return {
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'unit_ids': unit_ids,
        'min_sales': min_sales,
        'top_segments': top_segments,
        'ratings': [r.as_dict() for r in ratings],
        'recommendations': recommendations,
        'summary': summary,
        'bu_units': bu_units,
        'stage_meta': [
            {'id': sid, 'key': key, 'label': label, 'weight': weight}
            for sid, key, label, weight in STAGE_META
        ],
    }
