"""
Портальные справочники подготовки: работы, материалы (ссылка), детали, услуги.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from car_preparation.models import RefCarPreparationStage, RefCarPreparationWork, RefPreparationMaterial

from .models import (
    PreparationPart,
    PreparationService,
    PreparationServiceOffering,
    PreparationServiceProvider,
)


def _q(request):
    return (request.GET.get('q') or '').strip()


# ---------------------------------------------------------------------------
# Работы (RefCarPreparationWork)
# ---------------------------------------------------------------------------


@login_required
def works_list(request):
    q = _q(request)
    qs = (
        RefCarPreparationWork.objects.select_related('stage')
        .order_by('stage__sort_order', 'sort_order', 'name')
    )
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(stage__name__icontains=q)
        )
    return render(request, 'estimation_engine/prep_works_list.html', {
        'items': qs[:500],
        'q': q,
        'total': qs.count(),
    })


def _work_form_context(item=None):
    return {
        'item': item,
        'stages': RefCarPreparationStage.objects.all().order_by('sort_order', 'name'),
    }


@login_required
def work_create(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, 'Наименование обязательно.')
            return render(request, 'estimation_engine/prep_work_form.html', _work_form_context())
        item = RefCarPreparationWork.objects.create(
            name=name,
            code=(request.POST.get('code') or '').strip() or None,
            stage_id=request.POST.get('stage_id') or None,
            description=(request.POST.get('description') or '').strip(),
            sort_order=int(request.POST.get('sort_order') or 0),
            is_active=request.POST.get('is_active') == 'on',
            default_required=request.POST.get('default_required') == 'on',
            estimated_time=int(request.POST.get('estimated_time') or 0),
        )
        messages.success(request, 'Работа создана.')
        return redirect('estimation_engine:work_edit', item_id=item.id)
    return render(request, 'estimation_engine/prep_work_form.html', _work_form_context())


@login_required
def work_edit(request, item_id):
    item = get_object_or_404(RefCarPreparationWork, pk=item_id)
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, 'Наименование обязательно.')
            return render(request, 'estimation_engine/prep_work_form.html', _work_form_context(item))
        item.name = name
        item.code = (request.POST.get('code') or '').strip() or None
        item.stage_id = request.POST.get('stage_id') or None
        item.description = (request.POST.get('description') or '').strip()
        item.sort_order = int(request.POST.get('sort_order') or 0)
        item.is_active = request.POST.get('is_active') == 'on'
        item.default_required = request.POST.get('default_required') == 'on'
        item.estimated_time = int(request.POST.get('estimated_time') or 0)
        item.save()
        messages.success(request, 'Работа сохранена.')
        return redirect('estimation_engine:works_list')
    return render(request, 'estimation_engine/prep_work_form.html', _work_form_context(item))


# ---------------------------------------------------------------------------
# Материалы — список-прокси + ссылка на car_preparation
# ---------------------------------------------------------------------------


@login_required
def materials_list(request):
    q = _q(request)
    qs = RefPreparationMaterial.objects.order_by('name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    return render(request, 'estimation_engine/prep_materials_list.html', {
        'items': qs[:500],
        'q': q,
        'total': qs.count(),
        'cp_list_url': '/car_preparation/materials/',
        'cp_add_url': '/car_preparation/materials/add/',
    })


# ---------------------------------------------------------------------------
# Детали
# ---------------------------------------------------------------------------


@login_required
def parts_list(request):
    q = _q(request)
    qs = PreparationPart.objects.order_by('sort_order', 'name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(oem_number__icontains=q)
            | Q(category__icontains=q)
        )
    return render(request, 'estimation_engine/prep_parts_list.html', {
        'items': qs[:500],
        'q': q,
        'total': qs.count(),
    })


def _part_form_context(item=None):
    return {
        'item': item,
        'kind_choices': PreparationPart.KIND_CHOICES,
    }


def _apply_part_post(item, request):
    item.code = (request.POST.get('code') or '').strip()
    item.name = (request.POST.get('name') or '').strip()
    item.category = (request.POST.get('category') or '').strip()
    item.oem_number = (request.POST.get('oem_number') or '').strip()
    item.manufacturer = (request.POST.get('manufacturer') or '').strip()
    item.kind = request.POST.get('kind') or PreparationPart.KIND_ORIGINAL
    item.description = (request.POST.get('description') or '').strip()
    item.sort_order = int(request.POST.get('sort_order') or 0)
    item.is_active = request.POST.get('is_active') == 'on'
    return item


@login_required
def part_create(request):
    if request.method == 'POST':
        item = _apply_part_post(PreparationPart(), request)
        if not item.code or not item.name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/prep_part_form.html', _part_form_context())
        if PreparationPart.objects.filter(code=item.code).exists():
            messages.error(request, f'Деталь с кодом {item.code} уже есть.')
            return render(request, 'estimation_engine/prep_part_form.html', _part_form_context())
        item.save()
        messages.success(request, 'Деталь создана.')
        return redirect('estimation_engine:parts_list')
    return render(request, 'estimation_engine/prep_part_form.html', _part_form_context())


@login_required
def part_edit(request, item_id):
    item = get_object_or_404(PreparationPart, pk=item_id)
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        if PreparationPart.objects.exclude(pk=item.pk).filter(code=code).exists():
            messages.error(request, f'Деталь с кодом {code} уже есть.')
            return render(request, 'estimation_engine/prep_part_form.html', _part_form_context(item))
        _apply_part_post(item, request)
        if not item.code or not item.name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/prep_part_form.html', _part_form_context(item))
        item.save()
        messages.success(request, 'Деталь сохранена.')
        return redirect('estimation_engine:parts_list')
    return render(request, 'estimation_engine/prep_part_form.html', _part_form_context(item))


# ---------------------------------------------------------------------------
# Услуги + предложения
# ---------------------------------------------------------------------------


@login_required
def services_list(request):
    q = _q(request)
    qs = PreparationService.objects.order_by('sort_order', 'name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(category__icontains=q)
        )
    return render(request, 'estimation_engine/prep_services_list.html', {
        'items': qs[:500],
        'q': q,
        'total': qs.count(),
    })


def _service_form_context(item=None):
    offerings = []
    if item and item.pk:
        offerings = list(
            item.offerings.select_related('provider').order_by('sort_order', 'code')
        )
    return {
        'item': item,
        'offerings': offerings,
        'providers': PreparationServiceProvider.objects.filter(is_active=True).order_by('name'),
    }


def _apply_service_post(item, request):
    item.code = (request.POST.get('code') or '').strip()
    item.name = (request.POST.get('name') or '').strip()
    item.category = (request.POST.get('category') or '').strip()
    item.description = (request.POST.get('description') or '').strip()
    item.sort_order = int(request.POST.get('sort_order') or 0)
    item.is_active = request.POST.get('is_active') == 'on'
    return item


@login_required
def service_create(request):
    if request.method == 'POST':
        item = _apply_service_post(PreparationService(), request)
        if not item.code or not item.name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/prep_service_form.html', _service_form_context())
        if PreparationService.objects.filter(code=item.code).exists():
            messages.error(request, f'Услуга с кодом {item.code} уже есть.')
            return render(request, 'estimation_engine/prep_service_form.html', _service_form_context())
        item.save()
        messages.success(request, 'Услуга создана.')
        return redirect('estimation_engine:service_edit', item_id=item.id)
    return render(request, 'estimation_engine/prep_service_form.html', _service_form_context())


@login_required
def service_edit(request, item_id):
    item = get_object_or_404(PreparationService, pk=item_id)
    if request.method == 'POST':
        action = request.POST.get('action') or 'save'
        if action == 'add_offering':
            prov_id = request.POST.get('provider_id') or None
            code = (request.POST.get('offering_code') or '').strip()
            if not prov_id or not code:
                messages.error(request, 'Для предложения нужны код и исполнитель.')
            elif PreparationServiceOffering.objects.filter(code=code).exists():
                messages.error(request, f'Предложение с кодом {code} уже есть.')
            elif PreparationServiceOffering.objects.filter(service=item, provider_id=prov_id).exists():
                messages.error(request, 'У этого исполнителя уже есть предложение по услуге.')
            else:
                PreparationServiceOffering.objects.create(
                    service=item,
                    provider_id=prov_id,
                    code=code,
                    is_active=True,
                )
                messages.success(request, 'Предложение добавлено.')
            return redirect('estimation_engine:service_edit', item_id=item.id)

        code = (request.POST.get('code') or '').strip()
        if PreparationService.objects.exclude(pk=item.pk).filter(code=code).exists():
            messages.error(request, f'Услуга с кодом {code} уже есть.')
            return render(request, 'estimation_engine/prep_service_form.html', _service_form_context(item))
        _apply_service_post(item, request)
        if not item.code or not item.name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/prep_service_form.html', _service_form_context(item))
        item.save()
        messages.success(request, 'Услуга сохранена.')
        return redirect('estimation_engine:services_list')
    return render(request, 'estimation_engine/prep_service_form.html', _service_form_context(item))


@login_required
def providers_list(request):
    q = _q(request)
    qs = PreparationServiceProvider.objects.order_by('sort_order', 'name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(inn__icontains=q))
    return render(request, 'estimation_engine/prep_providers_list.html', {
        'items': qs[:500],
        'q': q,
        'total': qs.count(),
    })


def _provider_form_context(item=None):
    return {'item': item}


@login_required
def provider_create(request):
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        name = (request.POST.get('name') or '').strip()
        if not code or not name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/prep_provider_form.html', _provider_form_context())
        if PreparationServiceProvider.objects.filter(code=code).exists():
            messages.error(request, f'Исполнитель с кодом {code} уже есть.')
            return render(request, 'estimation_engine/prep_provider_form.html', _provider_form_context())
        PreparationServiceProvider.objects.create(
            code=code,
            name=name,
            legal_name=(request.POST.get('legal_name') or '').strip(),
            inn=(request.POST.get('inn') or '').strip(),
            contacts=(request.POST.get('contacts') or '').strip(),
            notes=(request.POST.get('notes') or '').strip(),
            sort_order=int(request.POST.get('sort_order') or 0),
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, 'Исполнитель создан.')
        return redirect('estimation_engine:providers_list')
    return render(request, 'estimation_engine/prep_provider_form.html', _provider_form_context())


@login_required
def provider_edit(request, item_id):
    item = get_object_or_404(PreparationServiceProvider, pk=item_id)
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        name = (request.POST.get('name') or '').strip()
        if not code or not name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/prep_provider_form.html', _provider_form_context(item))
        if PreparationServiceProvider.objects.exclude(pk=item.pk).filter(code=code).exists():
            messages.error(request, f'Исполнитель с кодом {code} уже есть.')
            return render(request, 'estimation_engine/prep_provider_form.html', _provider_form_context(item))
        item.code = code
        item.name = name
        item.legal_name = (request.POST.get('legal_name') or '').strip()
        item.inn = (request.POST.get('inn') or '').strip()
        item.contacts = (request.POST.get('contacts') or '').strip()
        item.notes = (request.POST.get('notes') or '').strip()
        item.sort_order = int(request.POST.get('sort_order') or 0)
        item.is_active = request.POST.get('is_active') == 'on'
        item.save()
        messages.success(request, 'Исполнитель сохранён.')
        return redirect('estimation_engine:providers_list')
    return render(request, 'estimation_engine/prep_provider_form.html', _provider_form_context(item))
