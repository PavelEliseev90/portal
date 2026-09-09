# -*- coding: utf-8 -*-
"""Сводка оценки для клиента — только суперпользователь (тест)."""
from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from documents.models import DocRLK
from estimations.brief_factors import BASE_SCORE, DEFAULT_FACTORS, SALES_STAR_KEYS, ensure_default_factors
from estimations.client_brief import build_client_brief
from register.models import RegInteractivOcenkaRLK


@login_required
def estimation_client_brief(request, rlk_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Тестовый режим: страница доступна только суперпользователю.')

    rlk = get_object_or_404(DocRLK, pk=rlk_id)
    from documents.rlk_estimation import resolve_estimation_rlk_id
    target_id = resolve_estimation_rlk_id(rlk)
    if target_id and int(target_id) != int(rlk.pk):
        return HttpResponseRedirect('/estimations/{}/client-brief/'.format(target_id))

    link = (
        RegInteractivOcenkaRLK.objects
        .filter(rlk=rlk)
        .select_related(
            'estimation',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
            'estimation__status',
            'estimation__type_body',
            'estimation__type_engine',
            'estimation__type_gear',
            'estimation__page_documents',
            'estimation__page_salon',
            'estimation__page_vnesh',
            'estimation__page_complectnost',
            'estimation__page_kolesa',
            'estimation__page_test_drive',
            'estimation__page_proverki',
            'estimation__page_soglasovanie',
            'estimation__page_remote',
        )
        .first()
    )
    estimation = link.estimation if link else None
    brief = build_client_brief(estimation) if estimation else None
    return render(request, 'estimations/estimation_client_brief.html', {
        'params': {
            'rlk': rlk,
            'estimation': estimation,
            'brief': brief,
        },
    })


def _parse_weight(raw, fallback):
    if raw is None or str(raw).strip() == '':
        return fallback
    try:
        return float(str(raw).replace(',', '.').replace(' ', ''))
    except ValueError:
        return fallback


@login_required
def client_brief_settings(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Тестовый режим: страница доступна только суперпользователю.')

    from estimations.models import EstimationBriefFactor

    migrate_error = ''
    rows = []
    try:
        rows = list(ensure_default_factors())
    except Exception as exc:
        migrate_error = (
            'Таблица весов ещё не создана. Нужно выполнить migrate estimations. ({})'.format(exc)
        )

    saved = False
    if request.method == 'POST' and not migrate_error:
        if request.POST.get('reset_defaults'):
            defaults = {
                key: {
                    'label': label,
                    'group': group,
                    'weight': weight,
                    'objection': objection,
                    'answer': answer,
                }
                for key, label, group, weight, objection, answer in DEFAULT_FACTORS
            }
            with transaction.atomic():
                for row in EstimationBriefFactor.objects.all():
                    spec = defaults.get(row.key)
                    if not spec:
                        continue
                    row.label = spec['label']
                    row.group = spec['group']
                    row.weight = spec['weight']
                    row.objection = spec['objection']
                    row.answer = spec['answer']
                    row.active = row.key not in SALES_STAR_KEYS
                    row.save()
        else:
            with transaction.atomic():
                for row in EstimationBriefFactor.objects.all():
                    row.weight = _parse_weight(
                        request.POST.get('weight_{}'.format(row.pk)),
                        row.weight,
                    )
                    if 'objection_{}'.format(row.pk) in request.POST:
                        row.objection = (request.POST.get('objection_{}'.format(row.pk)) or '')[:300]
                    if 'answer_{}'.format(row.pk) in request.POST:
                        row.answer = request.POST.get('answer_{}'.format(row.pk)) or ''
                    row.active = request.POST.get('active_{}'.format(row.pk)) == '1'
                    row.save()
        saved = True
        rows = list(ensure_default_factors())

    grouped = OrderedDict()
    for row in rows:
        grouped.setdefault(row.group or 'Прочее', []).append(row)

    return render(request, 'estimations/estimation_client_brief_settings.html', {
        'params': {
            'groups': [{'name': name, 'rows': items} for name, items in grouped.items()],
            'saved': saved,
            'migrate_error': migrate_error,
            'base_score': BASE_SCORE,
        },
    })

