# -*- coding: utf-8 -*-
"""Поиск оценки по рабочему листу с fallback на «сестру» с тем же UIN.

Во время перехода между базами 1С у одного UIN бывает несколько DocRLK.
Оценка живёт на старом листе, новый лист из другой базы — без оценки.
"""
from __future__ import annotations

from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce


def sibling_rlk_with_estimation(rlk):
    """Другой DocRLK с тем же UIN, у которого есть интерактивная оценка."""
    from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK

    if rlk is None:
        return None
    uin = (getattr(rlk, 'uin', None) or '').strip()
    if not uin:
        return None

    exclude_id = getattr(rlk, 'pk', None)
    est_qs = (
        RegInteractivOcenka.objects
        .filter(rlk__uin=uin)
        .select_related('rlk')
        .order_by('-end_estimation', '-start_estimation', '-id')
    )
    if exclude_id:
        est_qs = est_qs.exclude(rlk_id=exclude_id)
    est = est_qs.first()
    if est is not None and est.rlk_id:
        return est.rlk

    link_qs = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk__uin=uin)
        .exclude(estimation_id__isnull=True)
        .select_related('rlk', 'estimation')
        .order_by('-estimation__end_estimation', '-estimation__start_estimation', '-id')
    )
    if exclude_id:
        link_qs = link_qs.exclude(rlk_id=exclude_id)
    link = link_qs.first()
    if link is not None:
        return link.rlk
    return None


def resolve_estimation_for_rlk(rlk):
    """Оценка текущего РЛ или twin с тем же UIN."""
    from register.models import RegInteractivOcenka

    if rlk is None:
        return None
    try:
        est = rlk.reginteractivocenka
        if est is not None:
            return est
    except Exception:
        pass
    try:
        link = rlk.reginteractivocenkarlk
        if link is not None and link.estimation_id:
            return link.estimation
    except Exception:
        pass
    twin = sibling_rlk_with_estimation(rlk)
    if twin is None:
        return None
    try:
        return twin.reginteractivocenka
    except Exception:
        pass
    try:
        return twin.reginteractivocenkarlk.estimation
    except Exception:
        return None


def resolve_interactiv_rlk_for_rlk(rlk):
    """RegInteractivOcenkaRLK текущего листа или twin с оценкой."""
    from register.models import RegInteractivOcenkaRLK

    if rlk is None:
        return None
    own = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk=rlk)
        .exclude(estimation_id__isnull=True)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .first()
    )
    if own is not None:
        return own
    twin = sibling_rlk_with_estimation(rlk)
    if twin is None:
        return None
    return (
        RegInteractivOcenkaRLK.objects
        .filter(rlk=twin)
        .exclude(estimation_id__isnull=True)
        .select_related('rlk', 'estimation', 'page_soglasovanie', 'status')
        .first()
    )


def resolve_estimation_rlk_id(rlk):
    """pk рабочего листа, по которому реально смотреть оценку (свой или twin)."""
    if rlk is None:
        return None
    est = resolve_estimation_for_rlk(rlk)
    if est is not None and est.rlk_id:
        return est.rlk_id
    twin = sibling_rlk_with_estimation(rlk)
    if twin is not None:
        return twin.pk
    return rlk.pk


def subquery_estimation_id(rlk_id_ref, rlk_uin_ref):
    """Coalesce: оценка по rlk_id, иначе по тому же UIN."""
    from register.models import RegInteractivOcenka

    direct = RegInteractivOcenka.objects.filter(rlk_id=OuterRef(rlk_id_ref))
    by_uin = (
        RegInteractivOcenka.objects
        .filter(rlk__uin=OuterRef(rlk_uin_ref))
        .exclude(rlk__uin='')
        .exclude(rlk__uin__isnull=True)
        .order_by('-end_estimation', '-start_estimation', '-id')
    )
    return Coalesce(
        Subquery(direct.values('id')[:1]),
        Subquery(by_uin.values('id')[:1]),
    )


def subquery_interactiv_rlk_id(rlk_id_ref, rlk_uin_ref):
    """Coalesce: RegInteractivOcenkaRLK по rlk_id, иначе по UIN (только с оценкой)."""
    from register.models import RegInteractivOcenkaRLK

    direct = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk_id=OuterRef(rlk_id_ref))
        .exclude(estimation_id__isnull=True)
    )
    by_uin = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk__uin=OuterRef(rlk_uin_ref))
        .exclude(estimation_id__isnull=True)
        .exclude(rlk__uin='')
        .exclude(rlk__uin__isnull=True)
        .order_by('-estimation__end_estimation', '-estimation__start_estimation', '-id')
    )
    return Coalesce(
        Subquery(direct.values('id')[:1]),
        Subquery(by_uin.values('id')[:1]),
    )


def subquery_estimation_rlk_pk(rlk_id_ref, rlk_uin_ref):
    """pk РЛ, на котором лежит оценка (свой или twin по UIN)."""
    from register.models import RegInteractivOcenka

    direct = RegInteractivOcenka.objects.filter(rlk_id=OuterRef(rlk_id_ref))
    by_uin = (
        RegInteractivOcenka.objects
        .filter(rlk__uin=OuterRef(rlk_uin_ref))
        .exclude(rlk__uin='')
        .exclude(rlk__uin__isnull=True)
        .order_by('-end_estimation', '-start_estimation', '-id')
    )
    return Coalesce(
        Subquery(direct.values('rlk_id')[:1]),
        Subquery(by_uin.values('rlk_id')[:1]),
    )
