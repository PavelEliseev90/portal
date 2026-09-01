# -*- coding: utf-8 -*-
"""Перенос сообщений чата ЕЦО с одного DocRLK на другой (slug rlk_{id})."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from django.db import transaction

from documents.models import DocRLK
from estimations.transfer_kolesa_reception import (
    KolesaRebindError,
    _find_rlk,
    _rlk_label,
)
from estimations.transfer_rlk import (
    _chats_for_rlk,
    _count_chat_messages_for_rlk,
    transfer_rlk_chats,
)


class ChatTransferError(KolesaRebindError):
    """Ожидаемая ошибка переноса чата."""


def resolve_rlk_pair(
    *,
    source_id: str = '',
    source_nomer: str = '',
    source_uin: str = '',
    target_id: str = '',
    target_nomer: str = '',
    target_uin: str = '',
) -> tuple[DocRLK, DocRLK]:
    source = _find_rlk(rlk_id=source_id, nomer=source_nomer, uin=source_uin)
    if source is None:
        raise ChatTransferError('Укажите исходный РЛ (id / номер / UIN).')
    target = _find_rlk(rlk_id=target_id, nomer=target_nomer, uin=target_uin)
    if target is None:
        raise ChatTransferError('Укажите целевой РЛ (id / номер / UIN).')
    if source.pk == target.pk:
        raise ChatTransferError('Исходный и целевой РЛ совпадают.')
    return source, target


@dataclass
class ChatTransferPlan:
    source: DocRLK
    target: DocRLK
    source_message_count: int = 0
    target_message_count: int = 0
    source_chat_count: int = 0
    moved_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            'source_label': _rlk_label(self.source),
            'target_label': _rlk_label(self.target),
            'source_id': self.source.pk,
            'target_id': self.target.pk,
            'source_message_count': self.source_message_count,
            'target_message_count': self.target_message_count,
            'source_chat_count': self.source_chat_count,
            'moved_count': self.moved_count,
            'warnings': self.warnings,
            'errors': self.errors,
            'actions': self.actions,
            'ok': self.ok,
        }


def build_chat_transfer_plan(source: DocRLK, target: DocRLK) -> ChatTransferPlan:
    plan = ChatTransferPlan(source=source, target=target)
    if source.pk == target.pk:
        plan.errors.append('Исходный и целевой РЛ совпадают.')
        return plan

    plan.source_message_count = _count_chat_messages_for_rlk(source)
    plan.target_message_count = _count_chat_messages_for_rlk(target)
    plan.source_chat_count = len(_chats_for_rlk(source))

    if plan.source_message_count == 0:
        plan.errors.append(
            'На исходном РЛ нет сообщений чата (slug rlk_{}).'.format(source.pk)
        )
    else:
        plan.actions.append(
            'Перенести {} сообщ. с rlk_{} → rlk_{}.'.format(
                plan.source_message_count, source.pk, target.pk,
            )
        )

    if plan.target_message_count:
        plan.warnings.append(
            'На целевом РЛ уже есть {} сообщ. — история будет объединена.'.format(
                plan.target_message_count,
            )
        )

    suin = (source.uin or '').strip()
    tuin = (target.uin or '').strip()
    if suin and tuin and suin != tuin:
        plan.warnings.append(
            'UIN различаются: «{}» vs «{}».'.format(suin, tuin)
        )

    return plan


@transaction.atomic
def execute_chat_transfer(plan: ChatTransferPlan, *, user=None) -> ChatTransferPlan:
    if plan.errors:
        raise ChatTransferError('; '.join(plan.errors))

    source = DocRLK.objects.select_for_update().get(pk=plan.source.pk)
    target = DocRLK.objects.select_for_update().get(pk=plan.target.pk)
    moved = transfer_rlk_chats(source, target)
    if moved == 0:
        raise ChatTransferError('Сообщения не перенесены (возможно, уже перенесены).')

    plan.moved_count = moved

    plan.actions.append(
        'Перенесено сообщений: {} → slug rlk_{}.'.format(moved, target.pk)
    )
    plan.source_message_count = _count_chat_messages_for_rlk(source)
    plan.target_message_count = _count_chat_messages_for_rlk(target)
    if user is not None:
        plan.warnings.append('Выполнил: {}'.format(getattr(user, 'username', user)))
    return plan
