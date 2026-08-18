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


def estimation_is_usable(est):
    """Черновик без осмотра не считаем оценкой (иначе fallback не сработает)."""
    if est is None:
        return False
    if est.end_estimation or est.start_estimation:
        return True
    if _norm_vin(getattr(est, 'vin', None)) or _norm_vin(getattr(est, 'number_body', None)):
        return True
    try:
        from register.models import RegRegInteractivOcenkaFiles
        return RegRegInteractivOcenkaFiles.objects.filter(estimation=est).exists()
    except Exception:
        return False


def _score_estimation(est, vin=''):
    score = 0
    if est.end_estimation:
        score += 100
    if est.start_estimation:
        score += 40
    est_vin = _norm_vin(getattr(est, 'vin', None))
    if vin and est_vin and est_vin == vin:
        score += 80
    elif est_vin:
        score += 10
    try:
        from register.models import RegRegInteractivOcenkaFiles
        files = RegRegInteractivOcenkaFiles.objects.filter(estimation=est).count()
        score += min(files, 40)
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
    if vin:
        matched = [est for est in usable if _norm_vin(est.vin) == vin]
        if matched:
            usable = matched
    usable.sort(key=lambda est: _score_estimation(est, vin), reverse=True)
    return usable[0]


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


def resolve_estimation_for_rlk(rlk, vin=None):
    """Оценка текущего РЛ (если это не черновик) или twin с тем же UIN."""
    if rlk is None:
        return None
    vin = _norm_vin(vin) or _rlk_vin(rlk)

    own = None
    try:
        own = rlk.reginteractivocenka
    except Exception:
        own = None
    if estimation_is_usable(own):
        return own

    try:
        link = rlk.reginteractivocenkarlk
        if link is not None and estimation_is_usable(link.estimation):
            return link.estimation
    except Exception:
        pass

    twin = sibling_rlk_with_estimation(rlk, vin=vin)
    if twin is None:
        return None
    try:
        est = twin.reginteractivocenka
        if estimation_is_usable(est):
            return est
    except Exception:
        pass
    try:
        est = twin.reginteractivocenkarlk.estimation
        if estimation_is_usable(est):
            return est
    except Exception:
        pass
    return None


def resolve_interactiv_rlk_for_rlk(rlk, vin=None):
    """RegInteractivOcenkaRLK текущего листа или twin с настоящей оценкой."""
    from register.models import RegInteractivOcenkaRLK

    if rlk is None:
        return None
    vin = _norm_vin(vin) or _rlk_vin(rlk)

    own = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk=rlk)
        .exclude(estimation_id__isnull=True)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .first()
    )
    if own is not None and estimation_is_usable(own.estimation):
        return own

    est = resolve_estimation_for_rlk(rlk, vin=vin)
    if est is None:
        return None
    return (
        RegInteractivOcenkaRLK.objects
        .filter(estimation=est)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .order_by('-id')
        .first()
    ) or (
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
