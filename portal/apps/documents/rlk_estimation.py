# -*- coding: utf-8 -*-
"""Поиск оценки по рабочему листу с fallback на «сестру» с тем же UIN.

Во время перехода между базами 1С у одного UIN бывает несколько DocRLK.
Оценка живёт на старом листе, новый лист из другой базы — без оценки.

Выбираем оценку с согласованной ценой ЕЦО (после КД, иначе до КД).
Нельзя брать «первую попавшуюся»: черновик нового РЛ с VIN/работами
перебивал готовую оценку без фото.
"""
from __future__ import annotations

from django.db.models import F, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce


def _norm_vin(value):
    return (value or '').strip().upper()


def _rlk_vin(rlk):
    if rlk is None:
        return ''
    vin = _norm_vin(getattr(rlk, 'vin_trade_in', None))
    if vin:
        return vin
    cars = getattr(rlk, 'cars', None)
    if cars is not None:
        vin = _norm_vin(getattr(cars, 'vin', None) or getattr(cars, 'name', None))
        if vin:
            return vin
    try:
        from documents.models import DocLO
        lo = DocLO.objects.filter(rlk=rlk).exclude(vin='').order_by('-id').first()
        if lo is not None:
            return _norm_vin(lo.vin)
    except Exception:
        pass
    return ''


OSMOTR_FILE_TYPES = (
    'vnesh_car_osmotr_pered',
    'vnesh_car_osmotr_zad',
    'vnesh_car_osmotr_up',
    'vnesh_car_osmotr_pass',
    'vnesh_car_osmotr_vod',
    'vnesh_car_osmotr_pol',
    'vnesh_car_all',
)


def _osmotr_photo_count(est):
    if est is None:
        return 0
    try:
        from register.models import RegRegInteractivOcenkaFiles
        return RegRegInteractivOcenkaFiles.objects.filter(
            estimation=est,
            type_file__in=OSMOTR_FILE_TYPES,
        ).count()
    except Exception:
        return 0


def estimation_has_inspection(est):
    """Есть внешний осмотр: фото схемы/кузова или закрытая страница осмотра."""
    if est is None:
        return False
    if _osmotr_photo_count(est) > 0:
        return True
    try:
        vnesh = getattr(est, 'page_vnesh', None)
        if vnesh is not None and getattr(vnesh, 'end_estimation', None):
            return True
    except Exception:
        pass
    return False


def _soglasovanie_prices(sog):
    if sog is None:
        return 0, 0
    return int(sog.price_after_kd or 0), int(sog.price_before_kd or 0)


def _agreed_eco_prices(est):
    """Согласованные цены ЕЦО: (после КД, до КД). Смотрим и оценку, и обёртку РЛ."""
    after, before = 0, 0
    if est is None:
        return after, before
    a, b = _soglasovanie_prices(getattr(est, 'page_soglasovanie', None))
    after, before = max(after, a), max(before, b)
    try:
        from register.models import RegInteractivOcenkaRLK
        for link in RegInteractivOcenkaRLK.objects.filter(estimation=est).select_related('page_soglasovanie'):
            a, b = _soglasovanie_prices(link.page_soglasovanie)
            after, before = max(after, a), max(before, b)
    except Exception:
        pass
    return after, before


def estimation_has_agreed_eco_price(est):
    after, before = _agreed_eco_prices(est)
    return after > 0 or before > 0


def estimation_is_usable(est):
    """Пустышка без согласования/осмотра не оценка — иначе берётся новый РЛ без цены ЕЦО."""
    if est is None:
        return False
    if estimation_has_agreed_eco_price(est):
        return True
    if est.end_estimation:
        return True
    if estimation_has_inspection(est):
        return True
    try:
        from register.models import RegEstimationPodgotovka
        if RegEstimationPodgotovka.objects.filter(estimation=est).exists():
            return True
    except Exception:
        pass
    try:
        from register.models import RegRegInteractivOcenkaFiles
        return RegRegInteractivOcenkaFiles.objects.filter(estimation=est).exists()
    except Exception:
        return False


def _score_estimation(est, vin=''):
    """Главный признак — согласованная цена ЕЦО, затем осмотр."""
    score = 0
    after, before = _agreed_eco_prices(est)
    if after > 0:
        score += 1000
    elif before > 0:
        score += 400
    osmotr = _osmotr_photo_count(est)
    score += min(osmotr, 20) * 15
    if estimation_has_inspection(est):
        score += 80
    if est.end_estimation:
        score += 100
    if est.start_estimation:
        score += 20
    est_vin = _norm_vin(getattr(est, 'vin', None))
    if vin and est_vin and est_vin == vin:
        score += 80
    elif est_vin:
        score += 10
    rlk = getattr(est, 'rlk', None)
    if rlk is not None and getattr(rlk, 'eco', False):
        score += 15
    return score


def _estimations_by_uin(uin, exclude_rlk_id=None):
    from register.models import RegInteractivOcenka

    qs = (
        RegInteractivOcenka.objects
        .filter(rlk__uin=uin)
        .exclude(rlk__uin='')
        .select_related('rlk', 'page_soglasovanie')
        .order_by(
            F('end_estimation').desc(nulls_last=True),
            F('start_estimation').desc(nulls_last=True),
            '-id',
        )
    )
    if exclude_rlk_id:
        qs = qs.exclude(rlk_id=exclude_rlk_id)
    return qs


def pick_best_estimation(estimations, vin=''):
    usable = [est for est in estimations if estimation_is_usable(est)]
    if not usable:
        return None
    vin = _norm_vin(vin)

    def _sort(items):
        items.sort(key=lambda est: _score_estimation(est, vin), reverse=True)
        return items[0]

    agreed = [est for est in usable if estimation_has_agreed_eco_price(est)]
    if agreed:
        if vin:
            vin_agreed = [est for est in agreed if _norm_vin(est.vin) == vin]
            if vin_agreed:
                return _sort(vin_agreed)
            unknown_agreed = [est for est in agreed if not _norm_vin(est.vin)]
            if unknown_agreed:
                return _sort(unknown_agreed)
        return _sort(agreed)

    vin_matched = [est for est in usable if vin and _norm_vin(est.vin) == vin]
    vin_unknown = [est for est in usable if not _norm_vin(est.vin)]
    vin_osmotr = [est for est in vin_matched if estimation_has_inspection(est)]
    if vin_osmotr:
        return _sort(vin_osmotr)
    unknown_osmotr = [est for est in vin_unknown if estimation_has_inspection(est)]
    if unknown_osmotr:
        return _sort(unknown_osmotr)
    if vin_matched:
        return _sort(vin_matched)
    with_osmotr = [est for est in usable if estimation_has_inspection(est)]
    if with_osmotr:
        return _sort(with_osmotr)
    return _sort(usable)


def sibling_rlk_with_estimation(rlk, vin=None):
    """Другой DocRLK с тем же UIN, у которого есть настоящая оценка."""
    from register.models import RegInteractivOcenkaRLK

    if rlk is None:
        return None
    uin = (getattr(rlk, 'uin', None) or '').strip()
    if not uin:
        return None

    vin = _norm_vin(vin) or _rlk_vin(rlk)
    exclude_id = getattr(rlk, 'pk', None)
    est = pick_best_estimation(_estimations_by_uin(uin, exclude_id)[:20], vin)
    if est is not None and est.rlk_id:
        return est.rlk

    link_qs = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk__uin=uin)
        .exclude(estimation_id__isnull=True)
        .exclude(rlk__uin='')
        .select_related('rlk', 'estimation', 'estimation__rlk')
        .order_by(
            F('estimation__end_estimation').desc(nulls_last=True),
            F('estimation__start_estimation').desc(nulls_last=True),
            '-id',
        )
    )
    if exclude_id:
        link_qs = link_qs.exclude(rlk_id=exclude_id)
    links = list(link_qs[:20])
    est = pick_best_estimation([link.estimation for link in links if link.estimation_id], vin)
    if est is not None and est.rlk_id:
        return est.rlk
    return None


def _collect_estimations_for_rlk(rlk, vin=None):
    """Своя оценка + все по UIN. Не останавливаемся на черновике текущего листа."""
    from register.models import RegInteractivOcenka

    candidates = []
    if rlk is None:
        return candidates
    try:
        own = rlk.reginteractivocenka
        if own is not None:
            candidates.append(own)
    except Exception:
        pass
    try:
        link = rlk.reginteractivocenkarlk
        if link is not None and link.estimation_id:
            candidates.append(link.estimation)
    except Exception:
        pass
    uin = (getattr(rlk, 'uin', None) or '').strip()
    if uin:
        qs = (
            RegInteractivOcenka.objects
            .filter(rlk__uin=uin)
            .exclude(rlk__uin='')
            .select_related('rlk', 'page_vnesh', 'page_soglasovanie')
        )
        candidates.extend(list(qs[:40]))
    seen = set()
    unique = []
    for est in candidates:
        if est is None or est.pk in seen:
            continue
        seen.add(est.pk)
        unique.append(est)
    return unique


def resolve_estimation_for_rlk(rlk, vin=None):
    """Лучшая оценка: twin с согласованной ценой ЕЦО, иначе осмотр."""
    if rlk is None:
        return None
    vin = _norm_vin(vin) or _rlk_vin(rlk)
    return pick_best_estimation(_collect_estimations_for_rlk(rlk, vin=vin), vin)


def resolve_interactiv_rlk_for_rlk(rlk, vin=None):
    """Связка РЛ↔оценка для той же оценки, что и предпросмотр/фото."""
    from register.models import RegInteractivOcenkaRLK

    if rlk is None:
        return None
    vin = _norm_vin(vin) or _rlk_vin(rlk)
    est = resolve_estimation_for_rlk(rlk, vin=vin)
    if est is None:
        return None

    by_est = list(
        RegInteractivOcenkaRLK.objects
        .filter(estimation=est)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .order_by('-id')
    )
    agreed_links = []
    for link in by_est:
        after, before = _soglasovanie_prices(link.page_soglasovanie)
        if after > 0 or before > 0:
            agreed_links.append(link)
    if agreed_links:
        agreed_links.sort(
            key=lambda link: (
                _soglasovanie_prices(link.page_soglasovanie)[0],
                _soglasovanie_prices(link.page_soglasovanie)[1],
                link.id,
            ),
            reverse=True,
        )
        return agreed_links[0]
    for link in by_est:
        if link.rlk_id == est.rlk_id:
            return link
    if by_est:
        return by_est[0]
    return (
        RegInteractivOcenkaRLK.objects
        .filter(rlk_id=est.rlk_id)
        .exclude(estimation_id__isnull=True)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .first()
    )


def resolve_estimation_rlk_id(rlk, vin=None):
    """pk рабочего листа, на котором лежит выбранная оценка."""
    if rlk is None:
        return None
    est = resolve_estimation_for_rlk(rlk, vin=vin)
    if est is not None and est.rlk_id:
        return est.rlk_id
    twin = sibling_rlk_with_estimation(rlk, vin=vin)
    if twin is not None:
        return twin.pk
    return rlk.pk


def subquery_estimation_id(rlk_id_ref, rlk_uin_ref):
    """Coalesce: оценка по rlk_id, иначе по тому же UIN (с датой, NULLS LAST)."""
    from register.models import RegInteractivOcenka

    direct = RegInteractivOcenka.objects.filter(rlk_id=OuterRef(rlk_id_ref)).filter(
        Q(end_estimation__isnull=False) | Q(start_estimation__isnull=False)
    )
    by_uin = (
        RegInteractivOcenka.objects
        .filter(rlk__uin=OuterRef(rlk_uin_ref))
        .exclude(rlk__uin='')
        .exclude(rlk__uin__isnull=True)
        .filter(Q(end_estimation__isnull=False) | Q(start_estimation__isnull=False))
        .order_by(
            F('end_estimation').desc(nulls_last=True),
            F('start_estimation').desc(nulls_last=True),
            '-id',
        )
    )
    return Coalesce(
        Subquery(direct.values('id')[:1], output_field=IntegerField()),
        Subquery(by_uin.values('id')[:1], output_field=IntegerField()),
        output_field=IntegerField(),
    )


def subquery_interactiv_rlk_id(rlk_id_ref, rlk_uin_ref):
    from register.models import RegInteractivOcenkaRLK

    direct = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk_id=OuterRef(rlk_id_ref))
        .exclude(estimation_id__isnull=True)
        .filter(
            Q(estimation__end_estimation__isnull=False)
            | Q(estimation__start_estimation__isnull=False)
        )
    )
    by_uin = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk__uin=OuterRef(rlk_uin_ref))
        .exclude(estimation_id__isnull=True)
        .exclude(rlk__uin='')
        .exclude(rlk__uin__isnull=True)
        .filter(
            Q(estimation__end_estimation__isnull=False)
            | Q(estimation__start_estimation__isnull=False)
        )
        .order_by(
            F('estimation__end_estimation').desc(nulls_last=True),
            F('estimation__start_estimation').desc(nulls_last=True),
            '-id',
        )
    )
    return Coalesce(
        Subquery(direct.values('id')[:1], output_field=IntegerField()),
        Subquery(by_uin.values('id')[:1], output_field=IntegerField()),
        output_field=IntegerField(),
    )


def subquery_estimation_rlk_pk(rlk_id_ref, rlk_uin_ref):
    from register.models import RegInteractivOcenka

    direct = RegInteractivOcenka.objects.filter(rlk_id=OuterRef(rlk_id_ref)).filter(
        Q(end_estimation__isnull=False) | Q(start_estimation__isnull=False)
    )
    by_uin = (
        RegInteractivOcenka.objects
        .filter(rlk__uin=OuterRef(rlk_uin_ref))
        .exclude(rlk__uin='')
        .exclude(rlk__uin__isnull=True)
        .filter(Q(end_estimation__isnull=False) | Q(start_estimation__isnull=False))
        .order_by(
            F('end_estimation').desc(nulls_last=True),
            F('start_estimation').desc(nulls_last=True),
            '-id',
        )
    )
    return Coalesce(
        Subquery(direct.values('rlk_id')[:1], output_field=IntegerField()),
        Subquery(by_uin.values('rlk_id')[:1], output_field=IntegerField()),
        output_field=IntegerField(),
    )
