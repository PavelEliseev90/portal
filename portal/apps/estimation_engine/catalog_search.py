"""
AJAX-поиск справочников для Select2 (пакеты, правила).

Не отдаёт полный каталог на страницу формы — только q + limit.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse

from car_preparation.models import RefCarPreparationWork, RefPreparationMaterial

from .models import (
    PreparationPart,
    PreparationService,
    PreparationServiceOffering,
    PreparationServiceProvider,
    PreparationWorkPackage,
)


def _q(request) -> str:
    return (request.GET.get('q') or request.GET.get('term') or '').strip()


def _limit(request, default=30) -> int:
    try:
        n = int(request.GET.get('limit') or default)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, 100))


def _results(items):
    return JsonResponse({'results': items})


@login_required
def search_works(request):
    q = _q(request)
    qs = (
        RefCarPreparationWork.objects.filter(is_active=True)
        .select_related('stage')
        .order_by('stage__sort_order', 'sort_order', 'name')
    )
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(stage__name__icontains=q)
        )
    rows = []
    for w in qs[: _limit(request)]:
        stage = w.stage.name if w.stage_id else ''
        label = f'{stage} — {w.name}' if stage else w.name
        if w.code:
            label = f'{w.code}: {label}'
        rows.append({'id': w.id, 'text': label})
    return _results(rows)


@login_required
def search_materials(request):
    q = _q(request)
    qs = RefPreparationMaterial.objects.filter(is_active=True).order_by('name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    rows = []
    for m in qs[: _limit(request)]:
        text = m.name
        if m.code:
            text = f'{m.code} — {m.name}'
        rows.append({'id': m.id, 'text': text})
    return _results(rows)


@login_required
def search_parts(request):
    q = _q(request)
    qs = PreparationPart.objects.filter(is_active=True).order_by('sort_order', 'name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(oem_number__icontains=q)
            | Q(manufacturer__icontains=q)
            | Q(category__icontains=q)
        )
    rows = [
        {
            'id': p.id,
            'text': f'{p.code} / {p.name}' + (f' ({p.oem_number})' if p.oem_number else ''),
        }
        for p in qs[: _limit(request)]
    ]
    return _results(rows)


@login_required
def search_services(request):
    q = _q(request)
    qs = PreparationService.objects.filter(is_active=True).order_by('sort_order', 'name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(category__icontains=q)
        )
    rows = [{'id': s.id, 'text': f'{s.code} / {s.name}'} for s in qs[: _limit(request)]]
    return _results(rows)


@login_required
def search_service_offerings(request):
    q = _q(request)
    qs = (
        PreparationServiceOffering.objects.filter(is_active=True)
        .select_related('service', 'provider')
        .order_by('sort_order', 'code')
    )
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(service__name__icontains=q)
            | Q(service__code__icontains=q)
            | Q(provider__name__icontains=q)
            | Q(provider__code__icontains=q)
        )
    rows = []
    for o in qs[: _limit(request)]:
        svc = o.service.name if o.service_id else ''
        prov = o.provider.name if o.provider_id else ''
        rows.append({
            'id': o.id,
            'text': f'{o.code} — {svc} / {prov}'.strip(' —/'),
        })
    return _results(rows)


@login_required
def search_providers(request):
    q = _q(request)
    qs = PreparationServiceProvider.objects.filter(is_active=True).order_by('sort_order', 'name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(inn__icontains=q))
    rows = [{'id': p.id, 'text': f'{p.code} / {p.name}'} for p in qs[: _limit(request)]]
    return _results(rows)


@login_required
def search_packages(request):
    q = _q(request)
    qs = (
        PreparationWorkPackage.objects.filter(is_active=True)
        .exclude(status=PreparationWorkPackage.STATUS_ARCHIVED)
        .order_by('sort_order', 'code')
    )
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    rows = [
        {'id': p.id, 'text': f'{p.code} — {p.name}'}
        for p in qs[: _limit(request)]
    ]
    return _results(rows)
