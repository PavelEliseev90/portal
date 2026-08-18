# -*- coding: utf-8 -*-
"""Поиск оценки по рабочему листу с fallback на «сестру» с тем же UIN.

Во время перехода между базами 1С у одного UIN бывает несколько DocRLK.
Оценка живёт на старом листе, новый лист из другой базы — без оценки.

Важно: по одному UIN может быть несколько листов (trade-in, ОП, дубли).
Нельзя брать «первую попавшуюся» оценку — в PostgreSQL ORDER BY date DESC
ставит NULL первыми, и выбирается чужой черновик.
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


def estimation_is_usable(est):
    """VIN или дата старта сами по себе — не оценка (иначе берётся пустой новый РЛ)."""
    if est is None:
        return False
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
    """Фото осмотра важнее работ: иначе в лот попадает новый РЛ без схемы кузова."""
    score = 0
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
    try:
        from register.models import RegEstimationPodgotovka
        score += min(RegEstimationPodgotovka.objects.filter(estimation=est).count(), 10)
    except Exception:
        pass
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
        .select_related('rlk')
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
            .select_related('rlk', 'page_vnesh')
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
    """Лучшая оценка: своя или twin с тем же UIN. Побеждает лист с осмотром, не с VIN."""
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

    by_est = (
        RegInteractivOcenkaRLK.objects
        .filter(estimation=est)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .order_by('-id')
    )
    for link in by_est:
        if link.rlk_id == est.rlk_id:
            return link
    link = by_est.first()
    if link is not None:
        return link
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
