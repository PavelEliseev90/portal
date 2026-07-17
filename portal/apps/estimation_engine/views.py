"""
UI настроек конструктора оценки и пакетов работ.

Не вызывает legacy-расчёт и не пишет в RegEstimation*.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from car_preparation.models import (
    RefCarPreparationWork,
    RefPreparationMaterial,
    RefRepairZone,
)
from refs.models import RefUnit

from .models import (
    DamageType,
    EstimationRule,
    EstimationRulePackage,
    PreparationPart,
    PreparationService,
    PreparationServiceOffering,
    PreparationWorkPackage,
    PreparationWorkPackageLine,
    SchemeElement,
)


def _parse_decimal(value, default='0'):
    try:
        return Decimal(str(value or default).replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


@login_required
def settings_hub(request):
    """Единая точка входа: что настраивать и зачем."""
    context = {
        'packages_count': PreparationWorkPackage.objects.count(),
        'packages_published': PreparationWorkPackage.objects.filter(
            status=PreparationWorkPackage.STATUS_PUBLISHED,
            is_active=True,
        ).count(),
        'parts_count': PreparationPart.objects.filter(is_active=True).count(),
        'services_count': PreparationService.objects.filter(is_active=True).count(),
        'glossary': [
            {
                'name': 'Пакет работ (каталог)',
                'role': 'Единственная техкарта: состав WORK/MATERIAL/PART/SERVICE + маршрут.',
                'when': 'Настройка один раз; используется в оценке и на подготовке.',
            },
            {
                'name': 'Правило',
                'role': 'Условия осмотра → какие пакеты применить.',
                'when': 'Симулятор preview показывает состав и сумму.',
            },
            {
                'name': 'Пакет на подготовке (экземпляр)',
                'role': 'Конкретный пакет на документе CarPreparation со статусом и согласованием.',
                'when': 'После передачи из оценки или ручного добавления из каталога.',
            },
            {
                'name': 'Заказ-наряд',
                'role': 'Исполнение в цехе: создаётся из выбранных подтверждённых пакетов.',
                'when': 'После согласования пакета(ов) на подготовке.',
            },
        ],
        'rules_count': EstimationRule.objects.count(),
        'rules_published': EstimationRule.objects.filter(
            status=EstimationRule.STATUS_PUBLISHED,
            is_active=True,
        ).count(),
    }
    return render(request, 'estimation_engine/settings_hub.html', context)


@login_required
def work_packages_list(request):
    packages = (
        PreparationWorkPackage.objects
        .select_related('default_repair_zone', 'default_service_offering')
        .prefetch_related('lines')
        .order_by('sort_order', 'code', 'name')
    )
    return render(request, 'estimation_engine/work_packages_list.html', {
        'packages': packages,
    })


def _save_package_lines(package, request):
    """Сохраняет строки пакета из POST (line_type[], ref_id[], ...)."""
    package.lines.all().delete()
    line_types = request.POST.getlist('line_type[]')
    ref_ids = request.POST.getlist('ref_id[]')
    quantities = request.POST.getlist('quantity[]')
    norm_hours = request.POST.getlist('norm_hours[]')
    unit_costs = request.POST.getlist('unit_cost[]')
    coverage_keys = request.POST.getlist('coverage_key[]')
    parent_keys = request.POST.getlist('parent_coverage_key[]')
    required_flags = request.POST.getlist('is_required[]')
    required_idxs = set(request.POST.getlist('is_required_idx[]'))

    for idx, line_type in enumerate(line_types):
        line_type = (line_type or '').strip().upper()
        if line_type not in dict(PreparationWorkPackageLine.LINE_TYPE_CHOICES):
            continue
        try:
            ref_id = int(ref_ids[idx]) if idx < len(ref_ids) and ref_ids[idx] else None
        except (TypeError, ValueError):
            ref_id = None
        if not ref_id:
            continue

        if required_flags:
            is_required = (required_flags[idx] if idx < len(required_flags) else '1') in (
                '1', 'true', 'on', 'True',
            )
        else:
            is_required = str(idx) in required_idxs

        kwargs = {
            'package': package,
            'line_type': line_type,
            'quantity': _parse_decimal(quantities[idx] if idx < len(quantities) else 1, '1'),
            'norm_hours': _parse_decimal(norm_hours[idx] if idx < len(norm_hours) else 0),
            'unit_cost': _parse_decimal(unit_costs[idx] if idx < len(unit_costs) else 0),
            'coverage_key': (coverage_keys[idx] if idx < len(coverage_keys) else '') or '',
            'parent_coverage_key': (parent_keys[idx] if idx < len(parent_keys) else '') or '',
            'is_required': is_required,
            'sort_order': idx,
            'is_active': True,
        }
        if line_type == PreparationWorkPackageLine.LINE_WORK:
            kwargs['work_id'] = ref_id
        elif line_type == PreparationWorkPackageLine.LINE_MATERIAL:
            kwargs['material_id'] = ref_id
        elif line_type == PreparationWorkPackageLine.LINE_PART:
            kwargs['part_id'] = ref_id
        elif line_type == PreparationWorkPackageLine.LINE_SERVICE:
            # В UI выбирается только предложение подрядчика (offering).
            kwargs['service_offering_id'] = ref_id

        PreparationWorkPackageLine.objects.create(**kwargs)


def _package_form_context(package=None):
    works = (
        RefCarPreparationWork.objects.filter(is_active=True)
        .select_related('stage')
        .order_by('stage__sort_order', 'sort_order', 'name')
    )
    materials = RefPreparationMaterial.objects.filter(is_active=True).order_by('name')
    parts = PreparationPart.objects.filter(is_active=True).order_by('sort_order', 'name')
    services = PreparationService.objects.filter(is_active=True).order_by('sort_order', 'name')
    offerings = (
        PreparationServiceOffering.objects.filter(is_active=True)
        .select_related('service', 'provider')
        .order_by('sort_order', 'code')
    )
    zones = RefRepairZone.objects.filter(is_active=True).order_by('sort_order', 'name')
    lines = []
    if package:
        for line in package.lines.all().select_related(
            'work', 'material', 'part', 'service', 'service_offering',
        ):
            ref_id = (
                line.work_id or line.material_id or line.part_id
                or line.service_offering_id or line.service_id
            )
            ref_label = ''
            if line.work_id:
                ref_label = line.work.name
            elif line.material_id:
                ref_label = line.material.name
            elif line.part_id:
                ref_label = line.part.name
            elif line.service_offering_id:
                ref_label = str(line.service_offering)
            elif line.service_id:
                ref_label = line.service.name
            lines.append({
                'line_type': line.line_type,
                'ref_id': ref_id,
                'ref_label': ref_label,
                'quantity': line.quantity,
                'norm_hours': line.norm_hours,
                'unit_cost': line.unit_cost,
                'coverage_key': line.coverage_key,
                'parent_coverage_key': line.parent_coverage_key,
                'is_required': line.is_required,
            })
    return {
        'package': package,
        'section_choices': PreparationWorkPackage.SECTION_CHOICES,
        'status_choices': PreparationWorkPackage.STATUS_CHOICES,
        'route_choices': PreparationWorkPackage.ROUTE_CHOICES,
        'line_type_choices': PreparationWorkPackageLine.LINE_TYPE_CHOICES,
        'works': works,
        'materials': materials,
        'parts': parts,
        'services': services,
        'offerings': offerings,
        'zones': zones,
        'lines': lines,
    }


@login_required
@transaction.atomic
def work_package_create(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        if not code or not name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/work_package_form.html', _package_form_context())

        if PreparationWorkPackage.objects.filter(code=code).exists():
            messages.error(request, f'Пакет с кодом {code} уже существует.')
            return render(request, 'estimation_engine/work_package_form.html', _package_form_context())

        package = PreparationWorkPackage.objects.create(
            code=code,
            name=name,
            section=request.POST.get('section') or PreparationWorkPackage.SECTION_COMMON,
            status=request.POST.get('status') or PreparationWorkPackage.STATUS_PUBLISHED,
            route_type=request.POST.get('route_type') or PreparationWorkPackage.ROUTE_IN_HOUSE,
            description=request.POST.get('description', '').strip(),
            default_repair_zone_id=request.POST.get('default_repair_zone_id') or None,
            default_service_offering_id=request.POST.get('default_service_offering_id') or None,
            is_active=request.POST.get('is_active') == 'on',
            sort_order=int(request.POST.get('sort_order') or 0),
        )
        try:
            package.full_clean()
        except Exception as exc:
            package.delete()
            messages.error(request, str(exc))
            return render(request, 'estimation_engine/work_package_form.html', _package_form_context())

        _save_package_lines(package, request)
        messages.success(request, 'Пакет работ создан.')
        return redirect('estimation_engine:work_packages_list')

    return render(request, 'estimation_engine/work_package_form.html', _package_form_context())


@login_required
@transaction.atomic
def work_package_edit(request, package_id):
    package = get_object_or_404(
        PreparationWorkPackage.objects.prefetch_related('lines'),
        pk=package_id,
    )
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        if not code or not name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(
                request,
                'estimation_engine/work_package_form.html',
                _package_form_context(package),
            )
        if PreparationWorkPackage.objects.exclude(pk=package.pk).filter(code=code).exists():
            messages.error(request, f'Пакет с кодом {code} уже существует.')
            return render(
                request,
                'estimation_engine/work_package_form.html',
                _package_form_context(package),
            )

        package.code = code
        package.name = name
        package.section = request.POST.get('section') or package.section
        package.status = request.POST.get('status') or package.status
        package.route_type = request.POST.get('route_type') or package.route_type
        package.description = request.POST.get('description', '').strip()
        package.default_repair_zone_id = request.POST.get('default_repair_zone_id') or None
        package.default_service_offering_id = request.POST.get('default_service_offering_id') or None
        package.is_active = request.POST.get('is_active') == 'on'
        package.sort_order = int(request.POST.get('sort_order') or 0)
        try:
            package.full_clean()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(
                request,
                'estimation_engine/work_package_form.html',
                _package_form_context(package),
            )
        package.save()
        _save_package_lines(package, request)
        messages.success(request, 'Пакет работ сохранён.')
        return redirect('estimation_engine:work_packages_list')

    return render(
        request,
        'estimation_engine/work_package_form.html',
        _package_form_context(package),
    )


@login_required
def work_package_delete(request, package_id):
    package = get_object_or_404(PreparationWorkPackage, pk=package_id)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешён'}, status=405)
    if package.plan_packages.exists():
        return JsonResponse({
            'success': False,
            'error': 'Нельзя удалить: пакет уже использовался в планах оценки. Архивируйте его.',
        }, status=400)
    package.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Пакет удалён.')
    return redirect('estimation_engine:work_packages_list')


# ---------------------------------------------------------------------------
# Правила + preview
# ---------------------------------------------------------------------------


def _resolve_fact_catalog_codes(facts):
    """Подставляет element_code / damage_type из справочников по id."""
    from .models import SchemeElement, DamageType

    element_id = facts.get('element_id') or ''
    damage_type_id = facts.get('damage_type_id') or ''
    element_code = (facts.get('element_code') or '').strip()
    damage_type = (facts.get('damage_type') or '').strip()

    if element_id:
        el = SchemeElement.objects.filter(pk=element_id).first()
        if el:
            element_code = el.code
    if damage_type_id:
        dt = DamageType.objects.filter(pk=damage_type_id).first()
        if dt:
            damage_type = dt.code

    facts = dict(facts)
    facts['element_id'] = element_id
    facts['element_code'] = element_code
    facts['damage_type_id'] = damage_type_id
    facts['damage_type'] = damage_type
    return facts


def _facts_from_request(request):
    src = request.POST if request.method == 'POST' else request.GET
    return _resolve_fact_catalog_codes({
        'section': (src.get('section') or '').strip(),
        'element_id': src.get('element_id') or '',
        'element_code': (src.get('element_code') or '').strip(),
        'damage_type_id': src.get('damage_type_id') or '',
        'damage_type': (src.get('damage_type') or '').strip(),
        'damage_count': int(src.get('damage_count') or 1),
        'body_type': (src.get('body_type') or '').strip(),
        'price_group': (src.get('price_group') or '').strip(),
        'paint_type': (src.get('paint_type') or '').strip(),
        'under_instrument': src.get('under_instrument') in ('1', 'true', 'on', True),
    })


def _save_rule_packages(rule, request):
    rule.rule_packages.all().delete()
    package_ids = request.POST.getlist('package_id[]')
    fixed_costs = request.POST.getlist('fixed_cost[]')
    for idx, package_id in enumerate(package_ids):
        try:
            pid = int(package_id)
        except (TypeError, ValueError):
            continue
        if not PreparationWorkPackage.objects.filter(pk=pid).exists():
            continue
        fixed = None
        if idx < len(fixed_costs) and str(fixed_costs[idx]).strip():
            fixed = _parse_decimal(fixed_costs[idx])
        EstimationRulePackage.objects.create(
            rule=rule,
            package_id=pid,
            fixed_cost=fixed,
            sort_order=idx,
            is_active=True,
        )


def _rule_form_context(rule=None):
    packages = (
        PreparationWorkPackage.objects.filter(is_active=True)
        .exclude(status=PreparationWorkPackage.STATUS_ARCHIVED)
        .order_by('sort_order', 'code')
    )
    links = []
    if rule:
        links = list(
            rule.rule_packages.select_related('package').order_by('sort_order', 'id')
        )
    return {
        'rule': rule,
        'status_choices': EstimationRule.STATUS_CHOICES,
        'section_choices': EstimationRule.SECTION_CHOICES,
        'packages': packages,
        'links': links,
        'elements': SchemeElement.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'damage_types': DamageType.objects.filter(is_active=True).order_by('sort_order', 'name'),
    }


@login_required
def rules_list(request):
    rules = (
        EstimationRule.objects.prefetch_related('rule_packages__package')
        .order_by('-priority', 'code')
    )
    return render(request, 'estimation_engine/rules_list.html', {'rules': rules})


@login_required
@transaction.atomic
def rule_create(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        if not code or not name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context())
        if EstimationRule.objects.filter(code=code).exists():
            messages.error(request, f'Правило с кодом {code} уже есть.')
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context())

        rule = EstimationRule.objects.create(
            code=code,
            name=name,
            description=request.POST.get('description', '').strip(),
            status=request.POST.get('status') or EstimationRule.STATUS_DRAFT,
            priority=int(request.POST.get('priority') or 100),
            exclusive_group=request.POST.get('exclusive_group', '').strip(),
            section=request.POST.get('section') or '',
            element_id=request.POST.get('element_id') or None,
            damage_type_ref_id=request.POST.get('damage_type_id') or None,
            min_damage_count=max(1, int(request.POST.get('min_damage_count') or 1)),
            body_type=request.POST.get('body_type', '').strip(),
            price_group=request.POST.get('price_group', '').strip(),
            paint_type=request.POST.get('paint_type', '').strip(),
            under_instrument=request.POST.get('under_instrument') == 'on',
            hour_rate=_parse_decimal(request.POST.get('hour_rate'), '0'),
            is_active=request.POST.get('is_active') == 'on',
        )
        try:
            rule.full_clean()
        except Exception as exc:
            rule.delete()
            messages.error(request, str(exc))
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context())
        _save_rule_packages(rule, request)
        messages.success(request, 'Правило создано.')
        return redirect('estimation_engine:rules_list')

    return render(request, 'estimation_engine/rule_form.html', _rule_form_context())


@login_required
@transaction.atomic
def rule_edit(request, rule_id):
    rule = get_object_or_404(
        EstimationRule.objects.prefetch_related('rule_packages'),
        pk=rule_id,
    )
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        if not code or not name:
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context(rule))
        if EstimationRule.objects.exclude(pk=rule.pk).filter(code=code).exists():
            messages.error(request, f'Правило с кодом {code} уже есть.')
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context(rule))

        rule.code = code
        rule.name = name
        rule.description = request.POST.get('description', '').strip()
        rule.status = request.POST.get('status') or rule.status
        rule.priority = int(request.POST.get('priority') or 100)
        rule.exclusive_group = request.POST.get('exclusive_group', '').strip()
        rule.section = request.POST.get('section') or ''
        rule.element_id = request.POST.get('element_id') or None
        rule.damage_type_ref_id = request.POST.get('damage_type_id') or None
        rule.min_damage_count = max(1, int(request.POST.get('min_damage_count') or 1))
        rule.body_type = request.POST.get('body_type', '').strip()
        rule.price_group = request.POST.get('price_group', '').strip()
        rule.paint_type = request.POST.get('paint_type', '').strip()
        rule.under_instrument = request.POST.get('under_instrument') == 'on'
        rule.hour_rate = _parse_decimal(request.POST.get('hour_rate'), '0')
        rule.is_active = request.POST.get('is_active') == 'on'
        try:
            rule.full_clean()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context(rule))
        rule.save()
        _save_rule_packages(rule, request)
        messages.success(request, 'Правило сохранено.')
        return redirect('estimation_engine:rules_list')

    return render(request, 'estimation_engine/rule_form.html', _rule_form_context(rule))


@login_required
def rule_delete(request, rule_id):
    rule = get_object_or_404(EstimationRule, pk=rule_id)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешён'}, status=405)
    rule.delete()
    messages.success(request, 'Правило удалено.')
    return redirect('estimation_engine:rules_list')


@login_required
def rules_preview(request):
    """Симулятор: факты → сработавшие правила → состав и итог."""
    from .rules_engine import preview_from_facts

    facts = _facts_from_request(request)
    include_drafts = (
        request.POST.get('include_drafts') == 'on'
        if request.method == 'POST'
        else request.GET.get('include_drafts') == '1'
    )
    preview = None
    if request.method == 'POST' or request.GET.get('run') == '1':
        preview = preview_from_facts(facts, only_published=not include_drafts)

    return render(request, 'estimation_engine/rules_preview.html', {
        'facts': facts,
        'preview': preview,
        'include_drafts': include_drafts,
        'section_choices': EstimationRule.SECTION_CHOICES,
        'elements': SchemeElement.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'damage_types': DamageType.objects.filter(is_active=True).order_by('sort_order', 'name'),
    })


@login_required
def catalogs_hub(request):
    """Справочники элементов и типов повреждений."""
    return render(request, 'estimation_engine/catalogs_hub.html', {
        'elements_count': SchemeElement.objects.filter(is_active=True).count(),
        'damage_types_count': DamageType.objects.filter(is_active=True).count(),
        'polygon_links': SchemeElement.objects.filter(polygons__isnull=False).distinct().count(),
    })


@login_required
def elements_list(request):
    elements = (
        SchemeElement.objects.prefetch_related('polygons')
        .order_by('sort_order', 'name')
    )
    return render(request, 'estimation_engine/elements_list.html', {'elements': elements})


@login_required
def damage_types_list(request):
    items = DamageType.objects.order_by('sort_order', 'name')
    return render(request, 'estimation_engine/damage_types_list.html', {'items': items})


@login_required
@transaction.atomic
def sync_elements_from_polygons(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешён'}, status=405)
    from .catalog_sync import sync_scheme_elements_from_polygons
    stats = sync_scheme_elements_from_polygons()
    messages.success(
        request,
        f'Синхронизация: элементов создано {stats["elements_created"]}, '
        f'связей с полигонами +{stats["links_created"]}, всего элементов {stats["elements_total"]}.',
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, **stats})
    return redirect('estimation_engine:elements_list')


@login_required
def rules_preview_api(request):
    """JSON preview для AJAX."""
    from .rules_engine import preview_from_facts

    if request.method == 'POST' and request.content_type and 'json' in request.content_type:
        import json
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            data = {}
        facts = {
            'section': (data.get('section') or '').strip(),
            'element_id': data.get('element_id') or None,
            'element_code': (data.get('element_code') or '').strip(),
            'damage_type_id': data.get('damage_type_id') or None,
            'damage_type': (data.get('damage_type') or '').strip(),
            'damage_count': int(data.get('damage_count') or 1),
            'body_type': (data.get('body_type') or '').strip(),
            'price_group': (data.get('price_group') or '').strip(),
            'paint_type': (data.get('paint_type') or '').strip(),
            'under_instrument': bool(data.get('under_instrument')),
        }
        only_published = not data.get('include_drafts')
        facts = _resolve_fact_catalog_codes(facts)
    else:
        facts = _facts_from_request(request)
        only_published = request.GET.get('include_drafts') != '1'

    return JsonResponse(preview_from_facts(facts, only_published=only_published))
