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


def _req_val(request, key):
    return (request.GET.get(key, '') or request.POST.get(key, '')).strip()


@login_required
def transfer_estimation_rlk(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Доступ только для суперпользователей.')

    unit_filter = _req_val(request, 'unit_id')
    unit_id = int(unit_filter) if unit_filter.isdigit() else None

    context = {
        'uin': _req_val(request, 'uin'),
        'nomer': _req_val(request, 'nomer'),
        'source_id': _req_val(request, 'source_id'),
        'target_id': _req_val(request, 'target_id'),
        'plan': None,
        'result': None,
        'unit_id': unit_filter,
        'transition_units': list_transition_units(),
        'pending': list_pending_after_alfa_transition(unit_id=unit_id, limit=200),
    }

    lookup_ready = bool(
        context['nomer']
        or context['uin']
        or (context['source_id'] and context['target_id'])
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'preview')
        try:
            source, target, warnings = resolve_rlks(
                uin=request.POST.get('uin', ''),
                nomer=request.POST.get('nomer', ''),
                source_id=request.POST.get('source_id', ''),
                target_id=request.POST.get('target_id', ''),
            )
            plan = build_plan(source, target, warnings)
            context['plan'] = plan.as_dict()
            context['uin'] = context['plan']['uin']
            context['nomer'] = (source.nomer or target.nomer or context['nomer'] or '').strip()
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
            from register.models import RegInteractivOcenkaKolesaReception, RegInteractivOcenkaRLK

            target = DocRLK.objects.select_related(
                'unit', 'unit__ib', 'unit_dc', 'unit_dc__ib'
            ).get(pk=int(context['target_id']))
            est_id = None
            try:
                est = target.reginteractivocenka
                est_id = est.pk
            except Exception:
                link_est = RegInteractivOcenkaRLK.objects.filter(rlk=target).only('estimation_id').first()
                est_id = link_est.estimation_id if link_est else None
            link = RegInteractivOcenkaRLK.objects.filter(rlk=target).only('id').first()
            kolesa = RegInteractivOcenkaKolesaReception.objects.filter(rlk=target).only('id').first()
            context['result'] = {
                'target_label': 'id={} №{} UIN={}'.format(
                    target.pk, target.nomer or '—', (target.uin or '').strip() or '—'
                ),
                'estimation_id': est_id,
                'estimation_usable': True,
                'link_id': link.pk if link else None,
                'kolesa_id': kolesa.pk if kolesa else None,
                'ok': True,
            }
            context['plan'] = None
            context['pending'] = list_pending_after_alfa_transition(unit_id=unit_id, limit=200)
        except Exception as exc:
            messages.error(request, 'Не удалось проверить результат: {}'.format(exc))

    elif lookup_ready:
        try:
            source, target, warnings = resolve_rlks(
                uin=context['uin'],
                nomer=context['nomer'],
                source_id=context['source_id'],
                target_id=context['target_id'],
            )
            plan = build_plan(source, target, warnings)
            context['plan'] = plan.as_dict()
            context['uin'] = context['plan']['uin']
            context['nomer'] = (source.nomer or target.nomer or context['nomer'] or '').strip()
            context['source_id'] = str(source.pk)
            context['target_id'] = str(target.pk)
        except TransferError as exc:
            messages.error(request, str(exc))

    return render(request, 'estimations/transfer_rlk.html', {'params': context})
