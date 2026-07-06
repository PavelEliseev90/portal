"""
Рейтинг продаж БУ по этапу УС на момент отгрузки + подбор похожих лотов Avito.

Источник продаж: DocCarShipment (проведённые отгрузки, unit.buauto=True).
Этап УС: RefCarsOrganization.stage_price на момент продажи (связь через lo).
Веса этапов: Тест-прайс лучше всего, далее РДО, Коррекция, ТХТ.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from auction_avito.lot_tabs import (
    resolve_period,
)
from auction_avito.models import AvitoLot
from avtosalon.models import AvtohubModifications
from documents.models import DocCarShipment, DocLO
from refs.models import AutoruModification, RefCarsOrganization, RefUnit

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

RATINGS_PAGE_SIZE = 25
TOP_SHOWCASE_SIZE = 15


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


def _filter_ratings_by_search(ratings: List[SegmentRating], search: str) -> List[SegmentRating]:
    search = (search or '').strip().lower()
    if not search:
        return ratings
    tokens = [t for t in search.split() if t]
    result = []
    for r in ratings:
        hay = f'{r.mark_name} {r.model_name}'.lower()
        if all(token in hay for token in tokens):
            result.append(r)
    return result


def compute_segment_ratings(
    date_from,
    date_to,
    unit_ids=None,
    *,
    min_sales=1,
) -> Tuple[List[SegmentRating], dict]:
    """Агрегат продаж по марке/модели с рейтингом этапа УС (без обрезки)."""
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

    summary = {
        'shipments_total': qs.count(),
        'segments_total': len(ratings),
        'date_from': date_from,
        'date_to': date_to,
    }
    return ratings, summary


def _active_lots_queryset():
    from auction_avito.services.offer_status import active_lots_q
    return (
        AvitoLot.objects.filter(active_lots_q())
        .select_related('vehicle_avito', 'vehicle_autohub', 'venue', 'venue__city')
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


def _build_autohub_mod_to_model_ids_map_for_models(model_ids: Sequence[int]) -> Dict[int, set]:
    """
    Матчинг только через AutohubModifications:
      AutoruModification.idSiteTech -> AvtohubModifications(autoruId) -> id_avtohub (modification_id лота)
    """
    model_ids = [int(x) for x in model_ids if x]
    if not model_ids:
        return {}

    tech_to_models: Dict[int, set] = {}
    tech_ids: set = set()

    for tech_id, model_id in AutoruModification.objects.filter(
        model_id__in=model_ids,
    ).values_list('idSiteTech', 'model_id'):
        if not tech_id or not model_id:
            continue
        tech_to_models.setdefault(int(tech_id), set()).add(int(model_id))
        tech_ids.add(int(tech_id))

    if not tech_ids:
        return {}

    autohub_to_models: Dict[int, set] = {}
    for autoru_id, ah_mod_id in AvtohubModifications.objects.filter(
        autoruId__in=tech_ids,
    ).values_list('autoruId', 'id_avtohub'):
        if not autoru_id or not ah_mod_id:
            continue
        models = tech_to_models.get(int(autoru_id))
        if not models:
            continue
        autohub_to_models.setdefault(int(ah_mod_id), set()).update(models)

    return autohub_to_models


def match_lots_to_segments(
    ratings: Sequence[SegmentRating],
    *,
    max_lots_per_segment=3,
    max_lots_total=60,
) -> Tuple[List[SegmentRating], List[dict], dict]:
    """Подбор активных лотов Avito под сегменты с высоким рейтингом."""
    empty_stats = {
        'active_lots': 0,
        'with_vehicle_autohub_mod': 0,
        'autohub_mod_mapped': 0,
        'matched_to_segment': 0,
    }
    if not ratings:
        return [], [], empty_stats

    model_rating: Dict[int, SegmentRating] = {r.model_id: r for r in ratings}
    top_model_ids = set(model_rating.keys())

    active_lots = list(_active_lots_queryset()[:400])
    stats = {
        'active_lots': len(active_lots),
        'with_vehicle_autohub_mod': 0,
        'autohub_mod_mapped': 0,
        'matched_to_segment': 0,
    }

    autohub_mod_to_model_ids = _build_autohub_mod_to_model_ids_map_for_models(top_model_ids)

    lot_matches: List[Tuple[float, AvitoLot, SegmentRating]] = []

    for lot in active_lots:
        autohub = getattr(lot, 'vehicle_autohub', None)
        autohub_mod_id = getattr(autohub, 'modification_id', None) if autohub else None
        if not autohub_mod_id:
            continue
        stats['with_vehicle_autohub_mod'] += 1

        candidate_model_ids = autohub_mod_to_model_ids.get(int(autohub_mod_id))
        if not candidate_model_ids:
            continue
        stats['autohub_mod_mapped'] += 1

        matched_ids = [mid for mid in candidate_model_ids if mid in top_model_ids]
        if not matched_ids:
            continue
        stats['matched_to_segment'] += 1
        best_mid = max(matched_ids, key=lambda mid: model_rating[mid].score)
        segment = model_rating[best_mid]
        match_score = segment.score
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

    return list(ratings), flat_recommendations, stats


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
        top_showcase = min(30, max(5, int(request.GET.get('top_showcase') or TOP_SHOWCASE_SIZE)))
    except ValueError:
        top_showcase = TOP_SHOWCASE_SIZE

    search = (request.GET.get('q') or '').strip()

    all_ratings, summary = compute_segment_ratings(
        date_from, date_to, unit_ids or None,
        min_sales=min_sales,
    )

    # Витрина ТОП — только для рекомендаций лотов
    top_ratings = all_ratings[:top_showcase]
    top_copy = [
        SegmentRating(
            mark_id=r.mark_id,
            mark_name=r.mark_name,
            model_id=r.model_id,
            model_name=r.model_name,
            total=r.total,
            cnt_test=r.cnt_test,
            cnt_rdo=r.cnt_rdo,
            cnt_kor=r.cnt_kor,
            cnt_txt=r.cnt_txt,
            score=r.score,
            test_share=r.test_share,
        )
        for r in top_ratings
    ]
    _, recommendations, match_stats = match_lots_to_segments(top_copy)
    summary['match_stats'] = match_stats

    matched_counts = {r.model_id: len(r.matched_lots) for r in top_copy}

    filtered_ratings = _filter_ratings_by_search(all_ratings, search)
    summary['segments_filtered'] = len(filtered_ratings)

    paginator = Paginator(filtered_ratings, RATINGS_PAGE_SIZE)
    page_number = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ratings_page = []
    start_rank = (page_obj.number - 1) * paginator.per_page
    for idx, r in enumerate(page_obj.object_list):
        row = r.as_dict()
        row['rank'] = start_rank + idx + 1
        row['matched_lots_count'] = matched_counts.get(r.model_id, 0)
        ratings_page.append(row)

    bu_units = RefUnit.objects.filter(buauto=True, ib__active=True).order_by('name')

    return {
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'unit_ids': unit_ids,
        'min_sales': min_sales,
        'top_showcase': top_showcase,
        'search': search,
        'top_ratings': [r.as_dict() for r in top_ratings],
        'ratings_page': ratings_page,
        'page_obj': page_obj,
        'recommendations': recommendations,
        'summary': summary,
        'bu_units': bu_units,
        'stage_meta': [
            {'id': sid, 'key': key, 'label': label, 'weight': weight}
            for sid, key, label, weight in STAGE_META
        ],
    }
