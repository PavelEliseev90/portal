# -*- coding: utf-8 -*-
"""Служебная страница: перенос сообщений чата ЕЦО между РЛ."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render

from estimations.transfer_rlk_chat import (
    ChatTransferError,
    build_chat_transfer_plan,
    execute_chat_transfer,
    resolve_rlk_pair,
)


def _req_val(request, key):
    return (request.GET.get(key, '') or request.POST.get(key, '')).strip()


@login_required
def transfer_rlk_chat(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Доступ только для суперпользователей.')

    context = {
        'source_id': _req_val(request, 'source_id'),
        'source_nomer': _req_val(request, 'source_nomer'),
        'source_uin': _req_val(request, 'source_uin'),
        'target_id': _req_val(request, 'target_id'),
        'target_nomer': _req_val(request, 'target_nomer'),
        'target_uin': _req_val(request, 'target_uin'),
        'plan': None,
        'result': None,
    }

    has_source = bool(context['source_id'] or context['source_nomer'] or context['source_uin'])
    has_target = bool(context['target_id'] or context['target_nomer'] or context['target_uin'])

    def _load_plan():
        source, target = resolve_rlk_pair(
            source_id=context['source_id'],
            source_nomer=context['source_nomer'],
            source_uin=context['source_uin'],
            target_id=context['target_id'],
            target_nomer=context['target_nomer'],
            target_uin=context['target_uin'],
        )
        plan = build_chat_transfer_plan(source, target)
        context['source_id'] = str(source.pk)
        context['source_nomer'] = source.nomer or ''
        context['source_uin'] = (source.uin or '').strip()
        context['target_id'] = str(target.pk)
        context['target_nomer'] = target.nomer or ''
        context['target_uin'] = (target.uin or '').strip()
        context['plan'] = plan.as_dict()
        return source, target, plan

    if request.method == 'POST':
        action = request.POST.get('action', 'preview')
        try:
            source, target, plan = _load_plan()
            if action == 'execute':
                if not plan.ok:
                    messages.error(request, 'Перенос невозможен: исправьте ошибки.')
                elif request.POST.get('confirm') != 'yes':
                    messages.error(request, 'Для выполнения отметьте подтверждение.')
                else:
                    result = execute_chat_transfer(plan, user=request.user)
                    messages.success(
                        request,
                        'Чат перенесён: {} сообщ. → РЛ #{}.'.format(
                            result.moved_count,
                            target.pk,
                        ),
                    )
                    return HttpResponseRedirect(
                        '/estimations/transfer-rlk-chat/'
                        '?source_id={}&target_id={}&done=1'.format(source.pk, target.pk)
                    )
        except ChatTransferError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, 'Ошибка переноса чата: {}'.format(exc))

    elif request.GET.get('done') == '1' and context['target_id']:
        try:
            from documents.models import DocRLK
            from estimations.transfer_rlk import _count_chat_messages_for_rlk

            target = DocRLK.objects.get(pk=int(context['target_id']))
            context['result'] = {
                'target_label': 'id={} №{} UIN={}'.format(
                    target.pk, target.nomer or '—', (target.uin or '').strip() or '—',
                ),
                'target_id': target.pk,
                'message_count': _count_chat_messages_for_rlk(target),
                'ok': True,
            }
        except Exception as exc:
            messages.error(request, 'Не удалось проверить результат: {}'.format(exc))

    elif has_source and has_target:
        try:
            _load_plan()
        except ChatTransferError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, 'estimations/transfer_rlk_chat.html', {'params': context})
