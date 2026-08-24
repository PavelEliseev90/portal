# -*- coding: utf-8 -*-
"""Перенос интерактивной оценки с РЛ КорсАвто на РЛ Альфа (один UIN).

Цепочка:
  RegInteractivOcenka (O2O rlk)
  RegInteractivOcenkaRLK (O2O rlk → estimation)
  RegInteractivOcenkaKolesaReception (O2O rlk → estimation)
  DocLO / RegSwapKors / EmailPush по старому rlk
  DocRLK.estimation_id
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from django.db import transaction
from django.db.models import Q

from documents.models import DocLO, DocRLK
from documents.rlk_estimation import estimation_is_usable
from register.models import (
    RegInteractivOcenka,
    RegInteractivOcenkaEmailPush,
    RegInteractivOcenkaKolesaReception,
    RegInteractivOcenkaRLK,
    RegSwapKors,
)


class TransferError(Exception):
    """Ожидаемая ошибка валидации переноса."""


def _unit_ib_alfa(rlk: Optional[DocRLK]) -> Optional[bool]:
    if rlk is None:
        return None
    for attr in ('unit', 'unit_dc'):
        unit = getattr(rlk, attr, None)
        if unit is not None and getattr(unit, 'ib', None) is not None:
            return bool(unit.ib.alfa)
    return None


def is_kors_rlk(rlk: DocRLK) -> bool:
    flag = _unit_ib_alfa(rlk)
    return flag is False


def is_alfa_rlk(rlk: DocRLK) -> bool:
    flag = _unit_ib_alfa(rlk)
    return flag is True


def _rlk_label(rlk: DocRLK) -> str:
    unit_name = ''
    if rlk.unit_id and rlk.unit:
        unit_name = rlk.unit.name or ''
    ib = ''
    alfa = _unit_ib_alfa(rlk)
    if alfa is True:
        ib = 'Альфа'
    elif alfa is False:
        ib = 'КорсАвто'
    else:
        ib = 'ИБ?'
    return 'id={} №{} UIN={} [{}] {}'.format(
        rlk.pk,
        rlk.nomer or '—',
        (rlk.uin or '').strip() or '—',
        ib,
        unit_name,
    )


def _get_estimation_for_rlk(rlk: DocRLK) -> Optional[RegInteractivOcenka]:
    try:
        return rlk.reginteractivocenka
    except RegInteractivOcenka.DoesNotExist:
        pass
    try:
        link = rlk.reginteractivocenkarlk
        if link is not None and link.estimation_id:
            return link.estimation
    except RegInteractivOcenkaRLK.DoesNotExist:
        pass
    return None


def _get_link(rlk: DocRLK) -> Optional[RegInteractivOcenkaRLK]:
    try:
        return rlk.reginteractivocenkarlk
    except RegInteractivOcenkaRLK.DoesNotExist:
        return None


def _get_kolesa(rlk: DocRLK) -> Optional[RegInteractivOcenkaKolesaReception]:
    try:
        return rlk.reginteractivocenkakolesareception
    except RegInteractivOcenkaKolesaReception.DoesNotExist:
        return None


def find_pair_by_uin(uin: str) -> tuple[Optional[DocRLK], Optional[DocRLK], list[str]]:
    """Найти пару Корс / Альфа по UIN. Возвращает (source_kors, target_alfa, warnings)."""
    uin = (uin or '').strip()
    warnings: list[str] = []
    if not uin:
        raise TransferError('Укажите UIN рабочего листа.')

    qs = (
        DocRLK.objects.filter(uin=uin)
        .select_related('unit', 'unit__ib', 'unit_dc', 'unit_dc__ib')
        .order_by('-dataTime', '-id')
    )
    kors = [r for r in qs if is_kors_rlk(r)]
    alfa = [r for r in qs if is_alfa_rlk(r)]
    other = [r for r in qs if _unit_ib_alfa(r) is None]

    if other:
        warnings.append(
            'Есть РЛ без определённой ИБ (нет unit.ib): {}'.format(
                ', '.join(str(r.pk) for r in other)
            )
        )
    if not kors:
        raise TransferError('Не найден РЛ КорсАвто с UIN «{}».'.format(uin))
    if not alfa:
        raise TransferError('Не найден РЛ Альфа с UIN «{}».'.format(uin))

    source = None
    for r in kors:
        est = _get_estimation_for_rlk(r)
        if est is not None and estimation_is_usable(est):
            source = r
            break
    if source is None:
        source = kors[0]
        warnings.append('У Корс-РЛ нет «полноценной» оценки — будет перенесена имеющаяся, если есть.')

    if len(kors) > 1:
        warnings.append(
            'Несколько Корс-РЛ с этим UIN: {} — выбран {}.'.format(
                ', '.join(str(r.pk) for r in kors),
                source.pk,
            )
        )
    if len(alfa) > 1:
        warnings.append(
            'Несколько Альфа-РЛ с этим UIN: {} — выбран {}.'.format(
                ', '.join(str(r.pk) for r in alfa),
                alfa[0].pk,
            )
        )

    return source, alfa[0], warnings


def resolve_rlks(
    *,
    uin: str = '',
    source_id: str = '',
    target_id: str = '',
) -> tuple[DocRLK, DocRLK, list[str]]:
    warnings: list[str] = []
    source_id = (source_id or '').strip()
    target_id = (target_id or '').strip()
    uin = (uin or '').strip()

    if source_id and target_id:
        try:
            source = DocRLK.objects.select_related(
                'unit', 'unit__ib', 'unit_dc', 'unit_dc__ib'
            ).get(pk=int(source_id))
        except (DocRLK.DoesNotExist, ValueError):
            raise TransferError('Исходный РЛ id={} не найден.'.format(source_id))
        try:
            target = DocRLK.objects.select_related(
                'unit', 'unit__ib', 'unit_dc', 'unit_dc__ib'
            ).get(pk=int(target_id))
        except (DocRLK.DoesNotExist, ValueError):
            raise TransferError('Целевой РЛ id={} не найден.'.format(target_id))
        if (source.uin or '').strip() and (target.uin or '').strip():
            if (source.uin or '').strip() != (target.uin or '').strip():
                warnings.append(
                    'UIN исходного и целевого РЛ различаются: «{}» vs «{}».'.format(
                        source.uin, target.uin
                    )
                )
        return source, target, warnings

    if uin:
        return find_pair_by_uin(uin)

    raise TransferError('Укажите UIN или пару id исходного и целевого РЛ.')


@dataclass
class TransferPlan:
    source: DocRLK
    target: DocRLK
    estimation: Optional[RegInteractivOcenka]
    link: Optional[RegInteractivOcenkaRLK]
    kolesa: Optional[RegInteractivOcenkaKolesaReception]
    doc_lo_count: int = 0
    swap_count: int = 0
    email_push_count: int = 0
    target_stub_estimation: Optional[RegInteractivOcenka] = None
    target_stub_link: Optional[RegInteractivOcenkaRLK] = None
    target_stub_kolesa: Optional[RegInteractivOcenkaKolesaReception] = None
    warnings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            'source_label': _rlk_label(self.source),
            'target_label': _rlk_label(self.target),
            'source_id': self.source.pk,
            'target_id': self.target.pk,
            'uin': (self.source.uin or self.target.uin or '').strip(),
            'estimation_id': self.estimation.pk if self.estimation else None,
            'estimation_vin': (self.estimation.vin if self.estimation else '') or '',
            'estimation_usable': estimation_is_usable(self.estimation) if self.estimation else False,
            'link_id': self.link.pk if self.link else None,
            'kolesa_id': self.kolesa.pk if self.kolesa else None,
            'doc_lo_count': self.doc_lo_count,
            'swap_count': self.swap_count,
            'email_push_count': self.email_push_count,
            'target_stub_estimation_id': (
                self.target_stub_estimation.pk if self.target_stub_estimation else None
            ),
            'target_stub_link_id': self.target_stub_link.pk if self.target_stub_link else None,
            'target_stub_kolesa_id': self.target_stub_kolesa.pk if self.target_stub_kolesa else None,
            'warnings': self.warnings,
            'actions': self.actions,
            'errors': self.errors,
            'ok': not self.errors,
        }


def build_plan(source: DocRLK, target: DocRLK, warnings: Optional[list[str]] = None) -> TransferPlan:
    plan = TransferPlan(
        source=source,
        target=target,
        estimation=None,
        link=None,
        kolesa=None,
        warnings=list(warnings or []),
    )

    if source.pk == target.pk:
        plan.errors.append('Исходный и целевой РЛ совпадают.')
        return plan

    if not is_kors_rlk(source):
        plan.errors.append(
            'Исходный РЛ должен быть из КорсАвто (unit.ib.alfa=False). Сейчас: {}.'.format(
                _rlk_label(source)
            )
        )
    if not is_alfa_rlk(target):
        plan.errors.append(
            'Целевой РЛ должен быть из Альфа (unit.ib.alfa=True). Сейчас: {}.'.format(
                _rlk_label(target)
            )
        )

    estimation = _get_estimation_for_rlk(source)
    link = _get_link(source)
    kolesa = _get_kolesa(source)

    if estimation is None and link is not None and link.estimation_id:
        estimation = link.estimation
    if estimation is None:
        plan.errors.append('На исходном РЛ нет интерактивной оценки.')
    else:
        plan.estimation = estimation
        plan.actions.append(
            'Перепривязать RegInteractivOcenka #{} → РЛ #{}'.format(estimation.pk, target.pk)
        )

    plan.link = link
    if link is not None:
        plan.actions.append(
            'Перепривязать RegInteractivOcenkaRLK #{} → РЛ #{}'.format(link.pk, target.pk)
        )
    else:
        plan.warnings.append('На исходном РЛ нет RegInteractivOcenkaRLK — будет создана при необходимости.')

    plan.kolesa = kolesa
    if kolesa is not None:
        plan.actions.append(
            'Перепривязать приёмку 2КК #{} → РЛ #{}'.format(kolesa.pk, target.pk)
        )

    tgt_est = None
    try:
        tgt_est = target.reginteractivocenka
    except RegInteractivOcenka.DoesNotExist:
        tgt_est = None
    if tgt_est is not None and estimation is not None and tgt_est.pk == estimation.pk:
        plan.warnings.append('Оценка уже привязана к целевому РЛ.')
    elif tgt_est is not None:
        if estimation_is_usable(tgt_est):
            plan.errors.append(
                'На целевом РЛ уже есть полноценная оценка #{} — перенос отклонён.'.format(tgt_est.pk)
            )
        else:
            plan.target_stub_estimation = tgt_est
            plan.actions.append(
                'Отвязать/удалить пустую оценку-заглушку #{} с целевого РЛ.'.format(tgt_est.pk)
            )

    tgt_link = _get_link(target)
    if tgt_link is not None:
        if (
            link is not None
            and tgt_link.pk != link.pk
            and tgt_link.estimation_id
            and estimation is not None
            and tgt_link.estimation_id != estimation.pk
            and estimation_is_usable(tgt_link.estimation)
        ):
            plan.errors.append(
                'На целевом РЛ уже есть обёртка RLK #{} с другой оценкой.'.format(tgt_link.pk)
            )
        elif link is None or tgt_link.pk != link.pk:
            plan.target_stub_link = tgt_link
            plan.actions.append(
                'Освободить RegInteractivOcenkaRLK #{} на целевом РЛ.'.format(tgt_link.pk)
            )

    tgt_kolesa = _get_kolesa(target)
    if tgt_kolesa is not None:
        if kolesa is not None and tgt_kolesa.pk != kolesa.pk:
            plan.errors.append(
                'На целевом РЛ уже есть приёмка 2КК #{} — перенос отклонён.'.format(tgt_kolesa.pk)
            )
        elif kolesa is None:
            plan.target_stub_kolesa = tgt_kolesa
            plan.warnings.append(
                'На целевом РЛ уже есть приёмка 2КК #{} (исходной нет) — не трогаем.'.format(
                    tgt_kolesa.pk
                )
            )

    if estimation is not None:
        plan.doc_lo_count = DocLO.objects.filter(rlk=source).count()
        plan.swap_count = RegSwapKors.objects.filter(rlk=source, estimation=estimation).count()
        plan.email_push_count = RegInteractivOcenkaEmailPush.objects.filter(
            Q(rlk=source) | Q(estimation=estimation, rlk=source)
        ).count()
        if plan.doc_lo_count:
            plan.actions.append('Перепривязать DocLO: {} шт.'.format(plan.doc_lo_count))
        if plan.swap_count:
            plan.actions.append('Перепривязать RegSwapKors: {} шт.'.format(plan.swap_count))
        if plan.email_push_count:
            plan.actions.append(
                'Перепривязать EmailPush: {} шт.'.format(plan.email_push_count)
            )
        plan.actions.append(
            'Обновить DocRLK.estimation_id: source→0, target→{}'.format(estimation.pk)
        )

    return plan


def _clear_target_stub_estimation(est: RegInteractivOcenka) -> None:
    """Пустышку с целевого РЛ отвязываем (не удаляем историю жёстко)."""
    RegInteractivOcenka.objects.filter(pk=est.pk).update(rlk=None)


def _clear_target_stub_link(link: RegInteractivOcenkaRLK) -> None:
    RegInteractivOcenkaRLK.objects.filter(pk=link.pk).update(rlk=None, estimation=None)


@transaction.atomic
def execute_transfer(plan: TransferPlan, *, user=None) -> TransferPlan:
    if plan.errors:
        raise TransferError('; '.join(plan.errors))
    if plan.estimation is None:
        raise TransferError('Нет оценки для переноса.')

    source = DocRLK.objects.select_for_update().get(pk=plan.source.pk)
    target = DocRLK.objects.select_for_update().get(pk=plan.target.pk)
    estimation = RegInteractivOcenka.objects.select_for_update().get(pk=plan.estimation.pk)

    # Повторная проверка после lock
    fresh = build_plan(source, target, plan.warnings)
    if fresh.errors:
        raise TransferError('; '.join(fresh.errors))

    if fresh.target_stub_estimation is not None:
        stub = RegInteractivOcenka.objects.filter(pk=fresh.target_stub_estimation.pk).first()
        if stub is not None and stub.pk != estimation.pk:
            _clear_target_stub_estimation(stub)

    if fresh.target_stub_link is not None:
        stub_link = RegInteractivOcenkaRLK.objects.filter(pk=fresh.target_stub_link.pk).first()
        if stub_link is not None and (plan.link is None or stub_link.pk != plan.link.pk):
            _clear_target_stub_link(stub_link)

    # Оценка: O2O — сначала null, потом target
    if estimation.rlk_id != target.pk:
        RegInteractivOcenka.objects.filter(pk=estimation.pk).update(rlk=None)
        RegInteractivOcenka.objects.filter(pk=estimation.pk).update(rlk=target.pk)
        estimation.rlk_id = target.pk

    # Обёртка РЛ
    link = plan.link
    if link is not None:
        link = RegInteractivOcenkaRLK.objects.select_for_update().get(pk=link.pk)
        # O2O: сначала освободить rlk, потом назначить target
        RegInteractivOcenkaRLK.objects.filter(pk=link.pk).update(rlk=None)
        kwargs = {
            'rlk_id': target.pk,
            'estimation_id': estimation.pk,
        }
        if target.unit_id:
            kwargs['unit_id'] = target.unit_id
        RegInteractivOcenkaRLK.objects.filter(pk=link.pk).update(**kwargs)
        link.refresh_from_db()
        link.save()
    else:
        link, _created = RegInteractivOcenkaRLK.objects.get_or_create(
            rlk=target,
            defaults={
                'estimation': estimation,
                'unit_id': target.unit_id,
            },
        )
        if link.estimation_id != estimation.pk:
            link.estimation = estimation
            if target.unit_id:
                link.unit_id = target.unit_id
            link.save()

    # Приёмка 2КК
    kolesa = plan.kolesa
    if kolesa is not None:
        RegInteractivOcenkaKolesaReception.objects.filter(pk=kolesa.pk).update(rlk=None)
        RegInteractivOcenkaKolesaReception.objects.filter(pk=kolesa.pk).update(
            rlk_id=target.pk,
            estimation_id=estimation.pk,
        )

    DocLO.objects.filter(rlk=source).update(rlk=target)
    RegSwapKors.objects.filter(rlk=source, estimation=estimation).update(rlk=target)
    RegInteractivOcenkaEmailPush.objects.filter(rlk=source).update(rlk=target)

    DocRLK.objects.filter(pk=source.pk).update(estimation_id=0)
    DocRLK.objects.filter(pk=target.pk).update(estimation_id=estimation.pk)

    # Avito win_rlk — если оффер смотрел на старый РЛ
    try:
        from auction_avito.models import AvitoLotOffer
        AvitoLotOffer.objects.filter(win_rlk_id=source.pk).update(win_rlk_id=target.pk)
    except Exception:
        pass

    plan.actions.append('Готово: оценка #{} на РЛ #{}.'.format(estimation.pk, target.pk))
    if user is not None:
        plan.warnings.append('Выполнил: {}'.format(getattr(user, 'username', user)))
    return plan


# Статусы, которые считаем «закрытыми» для очереди переноса (принят / дубль принят).
_CLOSED_STATUS_IDS = (8, 10)


def list_pending_after_alfa_transition(*, unit_id: Optional[int] = None, limit: int = 200) -> list[dict[str, Any]]:
    """Активные оценки на Корс-РЛ по подразделениям с датой перехода на Альфа-Авто.

    Берём обёртки RegInteractivOcenkaRLK, где:
    - подразделение (link.unit / rlk.unit / rlk.unit_dc) имеет alfa_auto_transition_date;
    - РЛ КорсАвто (ib.alfa=False);
    - есть оценка;
    - статус не «принят» (8/10) ИЛИ оценка начата/идёт после даты перехода;
    - оценка ещё на корс-РЛ (не перенесена).
    """
    from django.utils import timezone

    from refs.models import RefUnit

    units_qs = RefUnit.objects.filter(alfa_auto_transition_date__isnull=False).select_related('ib')
    if unit_id:
        units_qs = units_qs.filter(pk=unit_id)
    units = list(units_qs.order_by('name'))
    if not units:
        return []

    unit_by_id = {u.pk: u for u in units}
    unit_ids = list(unit_by_id.keys())

    links = (
        RegInteractivOcenkaRLK.objects
        .filter(estimation_id__isnull=False)
        .filter(
            Q(unit_id__in=unit_ids)
            | Q(rlk__unit_id__in=unit_ids)
            | Q(rlk__unit_dc_id__in=unit_ids)
        )
        .filter(
            Q(rlk__unit__ib__alfa=False)
            | Q(rlk__unit__isnull=True, rlk__unit_dc__ib__alfa=False)
        )
        .select_related(
            'estimation',
            'estimation__rlk',
            'estimation__rlk__unit',
            'estimation__rlk__unit__ib',
            'status',
            'unit',
            'unit__ib',
            'rlk',
            'rlk__unit',
            'rlk__unit__ib',
            'rlk__unit_dc',
            'rlk__unit_dc__ib',
        )
        .order_by('-estimation__start_estimation', '-id')[: max(limit * 3, 300)]
    )

    rows: list[dict[str, Any]] = []
    seen_est = set()
    candidate_links = []

    for link in links:
        est = link.estimation
        rlk = link.rlk
        if est is None or rlk is None:
            continue
        if not is_kors_rlk(rlk):
            continue
        # Уже на альфе — пропускаем
        if est.rlk_id and est.rlk_id != rlk.pk:
            try:
                if is_alfa_rlk(est.rlk):
                    continue
            except Exception:
                pass

        transition_unit = None
        for uid in (link.unit_id, rlk.unit_id, getattr(rlk, 'unit_dc_id', None)):
            if uid in unit_by_id:
                transition_unit = unit_by_id[uid]
                break
        if transition_unit is None:
            continue

        transition_date = transition_unit.alfa_auto_transition_date
        status_id = link.status_id
        closed = status_id in _CLOSED_STATUS_IDS

        start = est.start_estimation
        start_date = None
        if start is not None:
            start_date = timezone.localtime(start).date() if timezone.is_aware(start) else start.date()

        after_transition = bool(start_date and transition_date and start_date >= transition_date)
        active_open = (not closed) and (estimation_is_usable(est) or bool(start))

        if not (after_transition or active_open):
            continue
        if est.pk in seen_est:
            continue
        seen_est.add(est.pk)
        candidate_links.append((link, est, rlk, transition_unit, transition_date, after_transition, closed, start))
        if len(candidate_links) >= limit:
            break

    kolesa_rlk_ids = set(
        RegInteractivOcenkaKolesaReception.objects.filter(
            rlk_id__in=[r.pk for _l, _e, r, *_rest in candidate_links]
        ).values_list('rlk_id', flat=True)
    )

    uins = {(r.uin or '').strip() for _l, _e, r, *_rest in candidate_links if (r.uin or '').strip()}
    alfa_by_uin = {}
    if uins:
        for twin in (
            DocRLK.objects.filter(uin__in=uins)
            .filter(Q(unit__ib__alfa=True) | Q(unit_dc__ib__alfa=True))
            .select_related('unit', 'unit__ib', 'unit_dc', 'unit_dc__ib')
            .order_by('uin', '-dataTime', '-id')
        ):
            key = (twin.uin or '').strip()
            if key and key not in alfa_by_uin and is_alfa_rlk(twin):
                alfa_by_uin[key] = twin

    for link, est, rlk, transition_unit, transition_date, after_transition, closed, start in candidate_links:
        uin = (rlk.uin or '').strip()
        alfa_twin = alfa_by_uin.get(uin)
        rows.append({
            'estimation_id': est.pk,
            'vin': (est.vin or '').strip(),
            'start_estimation': start,
            'status': link.status.name if link.status_id else '—',
            'status_id': link.status_id,
            'closed': closed,
            'after_transition': after_transition,
            'unit_id': transition_unit.pk,
            'unit_name': transition_unit.name,
            'transition_date': transition_date,
            'source_rlk_id': rlk.pk,
            'source_nomer': rlk.nomer or '',
            'uin': uin,
            'target_rlk_id': alfa_twin.pk if alfa_twin else None,
            'target_nomer': (alfa_twin.nomer if alfa_twin else '') or '',
            'has_alfa_twin': alfa_twin is not None,
            'kolesa': rlk.pk in kolesa_rlk_ids,
        })

    return rows


def list_transition_units() -> list[dict[str, Any]]:
    from refs.models import RefUnit

    return list(
        RefUnit.objects.filter(alfa_auto_transition_date__isnull=False)
        .order_by('name')
        .values('id', 'name', 'alfa_auto_transition_date')
    )
