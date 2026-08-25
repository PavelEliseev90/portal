# -*- coding: utf-8 -*-
"""Служебная страница: перепривязка приёмки 2КК к другому РЛ."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from estimations.transfer_kolesa_reception import (
    KolesaRebindError,
    _find_rlk,
    _rlk_label,
    build_rebind_plan,
    execute_rebind,
    find_reception,
    list_recent_receptions,
)


def _req_val(request, key):
    return (request.GET.get(key, '') or request.POST.get(key, '')).strip()


@login_required
def transfer_kolesa_reception(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Доступ только для суперпользователей.')

    context = {
        'reception_id': _req_val(request, 'reception_id'),
        'source_rlk_id': _req_val(request, 'source_rlk_id'),
        'source_nomer': _req_val(request, 'source_nomer'),
        'source_uin': _req_val(request, 'source_uin'),
        'target_rlk_id': _req_val(request, 'target_rlk_id'),
        'target_nomer': _req_val(request, 'target_nomer'),
        'target_uin': _req_val(request, 'target_uin'),
        'relink_estimation': True,
        'plan': None,
        'result': None,
        'recent': list_recent_receptions(40),
    }

    if request.method == 'POST':
        context['relink_estimation'] = request.POST.get('relink_estimation') == '1'
        action = request.POST.get('action', 'preview')
        try:
            reception = find_reception(
                reception_id=request.POST.get('reception_id', ''),
                source_rlk_id=request.POST.get('source_rlk_id', ''),
                source_nomer=request.POST.get('source_nomer', ''),
                source_uin=request.POST.get('source_uin', ''),
            )
            target = _find_rlk(
                rlk_id=request.POST.get('target_rlk_id', ''),
                nomer=request.POST.get('target_nomer', ''),
                uin=request.POST.get('target_uin', ''),
            )
            if target is None:
                raise KolesaRebindError('Укажите целевой РЛ (id / номер / UIN).')

            plan = build_rebind_plan(
                reception,
                target,
                relink_estimation=context['relink_estimation'],
            )
            context['plan'] = plan.as_dict()
            context['reception_id'] = str(plan.reception.pk)
            if plan.source_rlk:
                context['source_rlk_id'] = str(plan.source_rlk.pk)
                context['source_nomer'] = plan.source_rlk.nomer or ''
                context['source_uin'] = (plan.source_rlk.uin or '').strip()
            context['target_rlk_id'] = str(plan.target_rlk.pk)
            context['target_nomer'] = plan.target_rlk.nomer or ''
            context['target_uin'] = (plan.target_rlk.uin or '').strip()

            if action == 'execute':
                if not plan.ok:
                    messages.error(request, 'Перепривязка невозможна: исправьте ошибки.')
                elif request.POST.get('confirm') != 'yes':
                    messages.error(request, 'Для выполнения отметьте подтверждение.')
                else:
                    result = execute_rebind(plan, user=request.user)
                    messages.success(
                        request,
                        'Приёмка #{} перепривязана на РЛ #{}.'.format(
                            result.reception.pk,
                            result.target_rlk.pk,
                        ),
                    )
                    return HttpResponseRedirect(
                        '/estimations/transfer-kolesa-reception/'
                        '?reception_id={}&target_rlk_id={}&done=1'.format(
                            result.reception.pk,
                            result.target_rlk.pk,
                        )
                    )
        except KolesaRebindError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, 'Ошибка перепривязки: {}'.format(exc))

    elif request.GET.get('done') == '1' and context['reception_id']:
        try:
            from register.models import RegInteractivOcenkaKolesaReception

            reception = RegInteractivOcenkaKolesaReception.objects.select_related(
                'rlk', 'rlk__unit', 'rlk__unit__ib', 'estimation',
            ).get(pk=int(context['reception_id']))
            context['result'] = {
                'reception_id': reception.pk,
                'rlk_id': reception.rlk_id,
                'rlk_label': _rlk_label(reception.rlk),
                'estimation_id': reception.estimation_id,
                'ok': True,
            }
            context['recent'] = list_recent_receptions(40)
        except Exception as exc:
            messages.error(request, 'Не удалось проверить результат: {}'.format(exc))

    else:
        # GET preview when source + target keys are present
        relink_raw = request.GET.get('relink_estimation')
        if relink_raw is not None:
            context['relink_estimation'] = relink_raw != '0'
        has_source = bool(
            context['reception_id']
            or context['source_rlk_id']
            or context['source_nomer']
            or context['source_uin']
        )
        has_target = bool(
            context['target_rlk_id']
            or context['target_nomer']
            or context['target_uin']
        )
        if has_source and has_target:
            try:
                reception = find_reception(
                    reception_id=context['reception_id'],
                    source_rlk_id=context['source_rlk_id'],
                    source_nomer=context['source_nomer'],
                    source_uin=context['source_uin'],
                )
                target = _find_rlk(
                    rlk_id=context['target_rlk_id'],
                    nomer=context['target_nomer'],
                    uin=context['target_uin'],
                )
                if target is None:
                    raise KolesaRebindError('Укажите целевой РЛ (id / номер / UIN).')
                plan = build_rebind_plan(
                    reception,
                    target,
                    relink_estimation=context['relink_estimation'],
                )
                context['plan'] = plan.as_dict()
                context['reception_id'] = str(plan.reception.pk)
                if plan.source_rlk:
                    context['source_rlk_id'] = str(plan.source_rlk.pk)
                context['target_rlk_id'] = str(plan.target_rlk.pk)
            except KolesaRebindError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, str(exc))

    return render(
        request,
        'estimations/transfer_kolesa_reception.html',
        {'params': context},
    )
