# -*- coding: utf-8 -*-
"""Перепривязка приёмки 2КК (RegInteractivOcenkaKolesaReception) к другому DocRLK."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from django.db import transaction

from documents.models import DocRLK
from register.models import RegInteractivOcenka, RegInteractivOcenkaKolesaReception


class KolesaRebindError(Exception):
    """Ожидаемая ошибка валидации перепривязки."""


def _rlk_label(rlk: Optional[DocRLK]) -> str:
    if rlk is None:
        return '—'
    unit_name = ''
    if rlk.unit_id and rlk.unit:
        unit_name = rlk.unit.name or ''
    ib = '?'
    try:
        unit = rlk.unit or rlk.unit_dc
        if unit is not None and getattr(unit, 'ib', None) is not None:
            ib = 'Альфа' if unit.ib.alfa else 'КорсАвто'
    except Exception:
        pass
    return 'id={} №{} UIN={} [{}] {}'.format(
        rlk.pk,
        rlk.nomer or '—',
        (rlk.uin or '').strip() or '—',
        ib,
        unit_name,
    )


def _find_rlk(*, rlk_id: str = '', nomer: str = '', uin: str = '') -> Optional[DocRLK]:
    rlk_id = (rlk_id or '').strip()
    nomer = (nomer or '').strip()
    uin = (uin or '').strip()
    qs = DocRLK.objects.select_related('unit', 'unit__ib', 'unit_dc', 'unit_dc__ib')
    if rlk_id:
        if not rlk_id.isdigit():
            raise KolesaRebindError('id РЛ должен быть числом.')
        rlk = qs.filter(pk=int(rlk_id)).first()
        if rlk is None:
            raise KolesaRebindError('РЛ id={} не найден.'.format(rlk_id))
        return rlk
    if nomer:
        rlk = qs.filter(nomer=nomer).order_by('-dataTime', '-id').first()
        if rlk is None:
            rlk = qs.filter(nomer__iexact=nomer).order_by('-dataTime', '-id').first()
        if rlk is None:
            raise KolesaRebindError('РЛ с номером «{}» не найден.'.format(nomer))
        return rlk
    if uin:
        rlk = qs.filter(uin=uin).order_by('-dataTime', '-id').first()
        if rlk is None:
            raise KolesaRebindError('РЛ с UIN «{}» не найден.'.format(uin))
        return rlk
    return None


def _estimation_for_rlk(rlk: DocRLK) -> Optional[RegInteractivOcenka]:
    try:
        return rlk.reginteractivocenka
    except RegInteractivOcenka.DoesNotExist:
        pass
    try:
        link = rlk.reginteractivocenkarlk
        if link is not None and link.estimation_id:
            return link.estimation
    except Exception:
        pass
    return None


def find_reception(
    *,
    reception_id: str = '',
    source_rlk_id: str = '',
    source_nomer: str = '',
    source_uin: str = '',
) -> RegInteractivOcenkaKolesaReception:
    reception_id = (reception_id or '').strip()
    qs = RegInteractivOcenkaKolesaReception.objects.select_related(
        'rlk',
        'rlk__unit',
        'rlk__unit__ib',
        'estimation',
    )
    if reception_id:
        if not reception_id.isdigit():
            raise KolesaRebindError('id приёмки должен быть числом.')
        reception = qs.filter(pk=int(reception_id)).first()
        if reception is None:
            raise KolesaRebindError('Приёмка #{} не найдена.'.format(reception_id))
        return reception

    source = _find_rlk(rlk_id=source_rlk_id, nomer=source_nomer, uin=source_uin)
    if source is None:
        raise KolesaRebindError(
            'Укажите id приёмки или исходный РЛ (id / номер / UIN).'
        )
    reception = qs.filter(rlk=source).first()
    if reception is None:
        reception = qs.filter(estimation__rlk=source).order_by('-id').first()
    if reception is None:
        raise KolesaRebindError(
            'На РЛ {} нет приёмки 2КК.'.format(_rlk_label(source))
        )
    return reception


@dataclass
class KolesaRebindPlan:
    reception: RegInteractivOcenkaKolesaReception
    source_rlk: Optional[DocRLK]
    target_rlk: DocRLK
    target_estimation: Optional[RegInteractivOcenka] = None
    files_count: int = 0
    relink_estimation: bool = True
    warnings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        est = self.reception.estimation
        return {
            'reception_id': self.reception.pk,
            'source_label': _rlk_label(self.source_rlk),
            'source_rlk_id': self.source_rlk.pk if self.source_rlk else None,
            'target_label': _rlk_label(self.target_rlk),
            'target_rlk_id': self.target_rlk.pk,
            'estimation_id': est.pk if est else None,
            'estimation_vin': (est.vin if est else '') or '',
            'target_estimation_id': (
                self.target_estimation.pk if self.target_estimation else None
            ),
            'files_count': self.files_count,
            'sent': bool(self.reception.send_wheels_ib),
            'send_number': self.reception.send_wheels_ib_number or '',
            'send_uin': getattr(self.reception, 'send_wheels_ib_uin', '') or '',
            'relink_estimation': self.relink_estimation,
            'warnings': self.warnings,
            'actions': self.actions,
            'errors': self.errors,
            'ok': self.ok,
        }


def build_rebind_plan(
    reception: RegInteractivOcenkaKolesaReception,
    target: DocRLK,
    *,
    relink_estimation: bool = True,
) -> KolesaRebindPlan:
    from register.models import RegRegInteractivOcenkaFilesKolesaReception

    source = reception.rlk
    plan = KolesaRebindPlan(
        reception=reception,
        source_rlk=source,
        target_rlk=target,
        relink_estimation=relink_estimation,
    )
    plan.files_count = RegRegInteractivOcenkaFilesKolesaReception.objects.filter(
        kolesa_reception=reception,
    ).count()

    if source is not None and source.pk == target.pk:
        plan.errors.append('Исходный и целевой РЛ совпадают.')
        return plan

    conflict = (
        RegInteractivOcenkaKolesaReception.objects
        .filter(rlk=target)
        .exclude(pk=reception.pk)
        .first()
    )
    if conflict is not None:
        plan.errors.append(
            'На целевом РЛ уже есть приёмка 2КК #{} — перепривязка отклонена.'.format(
                conflict.pk,
            )
        )

    plan.target_estimation = _estimation_for_rlk(target)
    plan.actions.append(
        'Перепривязать приёмку #{}: РЛ {} → РЛ {}'.format(
            reception.pk,
            source.pk if source else '—',
            target.pk,
        )
    )
    if plan.files_count:
        plan.actions.append('Фото приёмки останутся на той же записи ({} шт.).'.format(
            plan.files_count,
        ))

    if relink_estimation:
        if plan.target_estimation is not None:
            if reception.estimation_id != plan.target_estimation.pk:
                plan.actions.append(
                    'Обновить estimation приёмки → оценка #{} целевого РЛ.'.format(
                        plan.target_estimation.pk,
                    )
                )
            else:
                plan.warnings.append('Оценка приёмки уже совпадает с оценкой целевого РЛ.')
        else:
            plan.warnings.append(
                'На целевом РЛ нет оценки — FK estimation у приёмки не меняем.'
            )
    else:
        plan.warnings.append('Оценка приёмки не меняется (только РЛ).')

    if reception.send_wheels_ib:
        plan.warnings.append(
            'Приёмка уже отправлена в БУ колёс'
            + (
                ' (№ {}, УИН {})'.format(
                    reception.send_wheels_ib_number or '—',
                    getattr(reception, 'send_wheels_ib_uin', '') or '—',
                )
            )
            + ' — реквизиты документа сохранятся.'
        )

    if source is not None and target is not None:
        su = (source.uin or '').strip()
        tu = (target.uin or '').strip()
        if su and tu and su != tu:
            plan.warnings.append(
                'UIN исходного и целевого РЛ различаются: «{}» vs «{}».'.format(su, tu)
            )

    return plan


@transaction.atomic
def execute_rebind(plan: KolesaRebindPlan, *, user=None) -> KolesaRebindPlan:
    if plan.errors:
        raise KolesaRebindError('; '.join(plan.errors))

    reception = RegInteractivOcenkaKolesaReception.objects.select_for_update().get(
        pk=plan.reception.pk,
    )
    target = DocRLK.objects.select_for_update().get(pk=plan.target_rlk.pk)

    fresh = build_rebind_plan(
        reception,
        target,
        relink_estimation=plan.relink_estimation,
    )
    if fresh.errors:
        raise KolesaRebindError('; '.join(fresh.errors))

    # OneToOne: сначала освободить, потом назначить
    RegInteractivOcenkaKolesaReception.objects.filter(pk=reception.pk).update(rlk=None)

    update_kwargs = {'rlk_id': target.pk}
    if plan.relink_estimation and fresh.target_estimation is not None:
        update_kwargs['estimation_id'] = fresh.target_estimation.pk

    RegInteractivOcenkaKolesaReception.objects.filter(pk=reception.pk).update(**update_kwargs)
    reception.refresh_from_db()

    plan.reception = reception
    plan.target_rlk = target
    plan.target_estimation = fresh.target_estimation
    plan.actions.append(
        'Готово: приёмка #{} на РЛ #{}.'.format(reception.pk, target.pk)
    )
    if user is not None:
        plan.warnings.append('Выполнил: {}'.format(getattr(user, 'username', user)))
    return plan


def list_recent_receptions(limit: int = 50) -> list[dict[str, Any]]:
    """Последние приёмки для быстрой подстановки в форму."""
    rows = []
    qs = (
        RegInteractivOcenkaKolesaReception.objects
        .select_related('rlk', 'rlk__unit', 'estimation')
        .order_by('-id')[:limit]
    )
    for r in qs:
        rows.append({
            'reception_id': r.pk,
            'rlk_id': r.rlk_id,
            'rlk_nomer': (r.rlk.nomer if r.rlk_id and r.rlk else '') or '',
            'uin': ((r.rlk.uin if r.rlk_id and r.rlk else '') or '').strip(),
            'vin': (r.estimation.vin if r.estimation_id and r.estimation else '') or '',
            'sent': bool(r.send_wheels_ib),
            'date': r.date,
        })
    return rows
