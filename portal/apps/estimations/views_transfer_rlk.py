# -*- coding: utf-8 -*-
"""Служебная страница: перенос интерактивной оценки КорсАвто → Альфа."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from estimations.transfer_rlk import (
    TransferError,
    build_plan,
    execute_transfer,
    list_pending_after_alfa_transition,
    list_transition_units,
    resolve_rlks,
)


@login_required
def transfer_estimation_rlk(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Доступ только для суперпользователей.')

    unit_filter = (
        request.GET.get('unit_id', '').strip()
        or request.POST.get('unit_id', '').strip()
    )
    unit_id = int(unit_filter) if unit_filter.isdigit() else None

    context = {
        'uin': request.GET.get('uin', '').strip() or request.POST.get('uin', '').strip(),
        'source_id': request.GET.get('source_id', '').strip() or request.POST.get('source_id', '').strip(),
        'target_id': request.GET.get('target_id', '').strip() or request.POST.get('target_id', '').strip(),
        'plan': None,
        'result': None,
        'unit_id': unit_filter,
        'transition_units': list_transition_units(),
        'pending': list_pending_after_alfa_transition(unit_id=unit_id, limit=200),
    }

    if request.method == 'POST':
        action = request.POST.get('action', 'preview')
        try:
            source, target, warnings = resolve_rlks(
                uin=request.POST.get('uin', ''),
                source_id=request.POST.get('source_id', ''),
                target_id=request.POST.get('target_id', ''),
            )
            plan = build_plan(source, target, warnings)
            context['plan'] = plan.as_dict()
            context['uin'] = context['plan']['uin']
            context['source_id'] = str(source.pk)
            context['target_id'] = str(target.pk)

            if action == 'execute':
                if not plan.ok:
                    messages.error(request, 'Перенос невозможен: исправьте ошибки.')
                elif request.POST.get('confirm') != 'yes':
                    messages.error(request, 'Для выполнения отметьте подтверждение.')
                else:
                    result = execute_transfer(plan, user=request.user)
                    context['result'] = result.as_dict()
                    context['plan'] = result.as_dict()
                    messages.success(
                        request,
                        'Оценка #{} перенесена на РЛ #{} (Альфа).'.format(
                            result.estimation.pk if result.estimation else '?',
                            target.pk,
                        ),
                    )
                    return HttpResponseRedirect(
                        '{}?uin={}&source_id={}&target_id={}&done=1{}'.format(
                            reverse('eco:transfer_estimation_rlk'),
                            context['uin'],
                            plan.source.pk,
                            target.pk,
                            '&unit_id={}'.format(unit_filter) if unit_filter else '',
                        )
                    )
        except TransferError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, 'Ошибка переноса: {}'.format(exc))

    elif request.GET.get('done') == '1' and context['target_id']:
        try:
            from documents.models import DocRLK
            from documents.rlk_estimation import estimation_is_usable
            from register.models import RegInteractivOcenkaKolesaReception, RegInteractivOcenkaRLK

            target = DocRLK.objects.select_related(
                'unit', 'unit__ib', 'unit_dc', 'unit_dc__ib'
            ).get(pk=int(context['target_id']))
            try:
                est = target.reginteractivocenka
            except Exception:
                est = None
            link = RegInteractivOcenkaRLK.objects.filter(rlk=target).first()
            kolesa = RegInteractivOcenkaKolesaReception.objects.filter(rlk=target).first()
            context['result'] = {
                'target_label': 'id={} №{} UIN={}'.format(
                    target.pk, target.nomer or '—', (target.uin or '').strip() or '—'
                ),
                'estimation_id': est.pk if est else None,
                'estimation_usable': estimation_is_usable(est) if est else False,
                'link_id': link.pk if link else None,
                'kolesa_id': kolesa.pk if kolesa else None,
                'ok': True,
            }
            context['plan'] = None
            # обновить очередь после переноса
            context['pending'] = list_pending_after_alfa_transition(unit_id=unit_id, limit=200)
        except Exception as exc:
            messages.error(request, 'Не удалось проверить результат: {}'.format(exc))

    elif context['uin'] or (context['source_id'] and context['target_id']):
        try:
            source, target, warnings = resolve_rlks(
                uin=context['uin'],
                source_id=context['source_id'],
                target_id=context['target_id'],
            )
            plan = build_plan(source, target, warnings)
            context['plan'] = plan.as_dict()
            context['uin'] = context['plan']['uin']
            context['source_id'] = str(source.pk)
            context['target_id'] = str(target.pk)
        except TransferError as exc:
            messages.error(request, str(exc))

    return render(request, 'estimations/transfer_rlk.html', {'params': context})
