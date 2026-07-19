"""
UI настроек конструктора оценки и пакетов работ.

Не вызывает legacy-расчёт и не пишет в RegEstimation*.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from car_preparation.models import (
    RefCarPreparationWork,
    RefPreparationMaterial,
    RefRepairZone,
)
from refs.models import RefUnit

from register.models import RegInfoBody

from .models import (
    DamageType,
    EstimationRule,
    EstimationRuleCondition,
    EstimationRulePackage,
    PreparationPart,
    PreparationService,
    PreparationServiceOffering,
    PreparationServiceProvider,
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
    # Полные справочники на страницу не грузим — Select2 AJAX.
    zones = RefRepairZone.objects.filter(is_active=True).order_by('sort_order', 'name')
    lines = []
    default_offering = None
    if package:
        if package.default_service_offering_id:
            default_offering = (
                PreparationServiceOffering.objects
                .select_related('service', 'provider')
                .filter(pk=package.default_service_offering_id)
                .first()
            )
        for line in package.lines.all().select_related(
            'work', 'work__stage', 'material', 'part', 'service',
            'service_offering', 'service_offering__service', 'service_offering__provider',
        ):
            ref_id = (
                line.work_id or line.material_id or line.part_id
                or line.service_offering_id or line.service_id
            )
            ref_label = ''
            if line.work_id:
                stage = line.work.stage.name if line.work.stage_id else ''
                ref_label = f'{stage} — {line.work.name}' if stage else line.work.name
            elif line.material_id:
                ref_label = line.material.name
            elif line.part_id:
                ref_label = f'{line.part.code} / {line.part.name}'
            elif line.service_offering_id:
                o = line.service_offering
                ref_label = (
                    f'{o.code} — {o.service.name} / {o.provider.name}'
                    if o else str(line.service_offering_id)
                )
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
        'zones': zones,
        'default_offering': default_offering,
        'lines': lines,
        'search_urls': {
            'WORK': '/estimation-engine/api/catalog/works/',
            'MATERIAL': '/estimation-engine/api/catalog/materials/',
            'PART': '/estimation-engine/api/catalog/parts/',
            'SERVICE': '/estimation-engine/api/catalog/service-offerings/',
            'OFFERING': '/estimation-engine/api/catalog/service-offerings/',
            'PACKAGE': '/estimation-engine/api/catalog/packages/',
        },
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
            estimation_reduction_amount=_parse_decimal(
                request.POST.get('estimation_reduction_amount'),
            ),
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
        package.estimation_reduction_amount = _parse_decimal(
            request.POST.get('estimation_reduction_amount'),
        )
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
    """Подставляет element_code / damage_type / body_type из справочников по id."""
    from refs.models import RefTypeBody

    from .models import SchemeElement, DamageType

    element_id = facts.get('element_id') or ''
    damage_type_id = facts.get('damage_type_id') or ''
    body_type_id = facts.get('body_type_id') or ''
    element_code = (facts.get('element_code') or '').strip()
    damage_type = (facts.get('damage_type') or '').strip()
    body_type = (facts.get('body_type') or '').strip()

    if element_id:
        el = SchemeElement.objects.filter(pk=element_id).first()
        if el:
            element_code = el.code
    if damage_type_id:
        dt = DamageType.objects.filter(pk=damage_type_id).first()
        if dt:
            damage_type = dt.code
    if body_type_id:
        bt = RefTypeBody.objects.filter(pk=body_type_id).first()
        if bt:
            body_type = bt.name

    facts = dict(facts)
    facts['element_id'] = element_id
    facts['element_code'] = element_code
    facts['damage_type_id'] = damage_type_id
    facts['damage_type'] = damage_type
    facts['body_type_id'] = body_type_id
    facts['body_type'] = body_type
    return facts


def _parse_flag_choice(value):
    """'' | yes | no для условий правила."""
    v = (value or '').strip().lower()
    if v in (EstimationRule.FLAG_YES, EstimationRule.FLAG_NO):
        return v
    return EstimationRule.FLAG_ANY


def _parse_cleaning_level(value):
    allowed = {c for c, _ in EstimationRule.CLEANING_CHOICES}
    v = str(value or '').strip()
    return v if v in allowed else EstimationRule.CLEANING_ANY


def _parse_salon_type(value):
    allowed = {c for c, _ in EstimationRule.SALON_TYPE_CHOICES}
    v = str(value or '').strip()
    return v if v in allowed else EstimationRule.SALON_ANY


def _parse_diagnostic_system(value):
    allowed = {c for c, _ in EstimationRule.DIAG_SYSTEM_CHOICES}
    v = str(value or '').strip()
    return v if v in allowed else EstimationRule.DIAG_SYSTEM_ANY


def _parse_diagnostic_status(value):
    allowed = {c for c, _ in EstimationRule.DIAG_STATUS_CHOICES}
    v = str(value or '').strip()
    return v if v in allowed else EstimationRule.DIAG_STATUS_ANY


def _facts_from_request(request):
    src = request.POST if request.method == 'POST' else request.GET
    count_type_ids = src.getlist('damage_count_type_id[]') if hasattr(src, 'getlist') else []
    count_values = src.getlist('damage_count_n[]') if hasattr(src, 'getlist') else []
    damage_counts = {}
    for idx, raw_id in enumerate(count_type_ids):
        if not raw_id:
            continue
        try:
            dt = DamageType.objects.filter(pk=int(raw_id)).first()
        except (TypeError, ValueError):
            dt = None
        if not dt:
            continue
        try:
            n = int(count_values[idx]) if idx < len(count_values) else 0
        except (TypeError, ValueError):
            n = 0
        damage_counts[dt.code] = damage_counts.get(dt.code, 0) + n

    damage_count_raw = src.get('damage_count')
    facts = {
        'section': (src.get('section') or '').strip(),
        'element_id': src.get('element_id') or '',
        'element_code': (src.get('element_code') or '').strip(),
        'damage_type_id': src.get('damage_type_id') or '',
        'damage_type': (src.get('damage_type') or '').strip(),
        'damage_count': damage_count_raw if damage_count_raw not in (None, '') else None,
        'damage_counts': damage_counts,
        'body_type_id': src.get('body_type_id') or '',
        'body_type': (src.get('body_type') or '').strip(),
        'price_group': (src.get('price_group') or '').strip(),
        'paint_type': (src.get('paint_type') or '').strip(),
        'under_instrument': src.get('under_instrument') in ('1', 'true', 'on', True),
        'windshield_heat': src.get('windshield_heat') in ('1', 'true', 'on', 'yes', True),
        'windshield_projection': src.get('windshield_projection') in ('1', 'true', 'on', 'yes', True),
        'cleaning_level': (src.get('cleaning_level') or src.get('cleaning_int') or '').strip(),
        'salon_type': (src.get('salon_type') or src.get('type_salon_int') or '').strip(),
        'diagnostic_system': (src.get('diagnostic_system') or '').strip(),
        'diagnostic_status': (src.get('diagnostic_status') or '').strip(),
    }
    # карта систем из формы preview: diag_engine, diag_system_og, ...
    diag_map = {}
    for key in ('engine', 'system_og', 'gear', 'suspension', 'conditioner'):
        raw = src.get(f'diag_{key}') or src.get(key)
        if raw not in (None, '', '10'):
            diag_map[key] = str(raw).strip()
    if diag_map:
        facts['diagnostic_statuses'] = diag_map
    # для повторного отображения формы preview
    facts['damage_count_rows'] = [
        {
            'type_id': count_type_ids[i] if i < len(count_type_ids) else '',
            'n': count_values[i] if i < len(count_values) else '0',
        }
        for i in range(max(len(count_type_ids), len(count_values)))
        if (count_type_ids[i] if i < len(count_type_ids) else '')
    ]
    return _resolve_fact_catalog_codes(facts)


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


def _save_rule_body_types(rule, request):
    from refs.models import RefTypeBody

    raw_ids = request.POST.getlist('body_type_ids[]')
    ids = []
    for raw in raw_ids:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    valid_ids = list(
        RefTypeBody.objects.filter(pk__in=ids).values_list('id', flat=True)
    )
    rule.body_types.set(valid_ids)
    rule.sync_body_type_cache()


def _save_rule_conditions(rule, request):
    rule.conditions.all().delete()
    join_ops = request.POST.getlist('cond_join_op[]')
    fields = request.POST.getlist('cond_field[]')
    damage_type_ids = request.POST.getlist('cond_damage_type_id[]')
    operators = request.POST.getlist('cond_operator[]')
    values = request.POST.getlist('cond_value[]')
    n = max(len(fields), len(operators), len(values), len(damage_type_ids), len(join_ops))
    for idx in range(n):
        field = (fields[idx] if idx < len(fields) else '').strip()
        if not field:
            continue
        operator = (operators[idx] if idx < len(operators) else EstimationRuleCondition.OP_GTE).strip()
        value = (values[idx] if idx < len(values) else '').strip()
        join_op = (join_ops[idx] if idx < len(join_ops) else EstimationRuleCondition.JOIN_AND).strip()
        if join_op not in (EstimationRuleCondition.JOIN_AND, EstimationRuleCondition.JOIN_OR):
            join_op = EstimationRuleCondition.JOIN_AND
        dt_id = damage_type_ids[idx] if idx < len(damage_type_ids) else ''
        try:
            dt_id = int(dt_id) if dt_id else None
        except (TypeError, ValueError):
            dt_id = None
        if field == EstimationRuleCondition.FIELD_DAMAGE_TYPE_COUNT and not dt_id:
            continue
        EstimationRuleCondition.objects.create(
            rule=rule,
            sort_order=idx,
            join_op=join_op or EstimationRuleCondition.JOIN_AND,
            field=field,
            damage_type_ref_id=dt_id,
            operator=operator or EstimationRuleCondition.OP_GTE,
            value=value,
            is_active=True,
        )


def _rule_form_context(rule=None):
    from refs.models import RefTypeBody

    links = []
    conditions = []
    selected_body_type_ids = set()
    if rule:
        links = list(
            rule.rule_packages.select_related('package').order_by('sort_order', 'id')
        )
        conditions = list(
            rule.conditions.select_related('damage_type_ref').order_by('sort_order', 'id')
        )
        selected_body_type_ids = set(rule.body_types.values_list('id', flat=True))
    return {
        'rule': rule,
        'status_choices': EstimationRule.STATUS_CHOICES,
        'section_choices': EstimationRule.SECTION_CHOICES,
        'flag_choices': EstimationRule.FLAG_CHOICES,
        'cleaning_choices': EstimationRule.CLEANING_CHOICES,
        'salon_type_choices': EstimationRule.SALON_TYPE_CHOICES,
        'diagnostic_system_choices': EstimationRule.DIAG_SYSTEM_CHOICES,
        'diagnostic_status_choices': EstimationRule.DIAG_STATUS_CHOICES,
        'condition_field_choices': EstimationRuleCondition.FIELD_CHOICES,
        'condition_operator_choices': EstimationRuleCondition.OPERATOR_CHOICES,
        'condition_join_choices': EstimationRuleCondition.JOIN_CHOICES,
        'links': links,
        'conditions': conditions,
        'elements': SchemeElement.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'damage_types': DamageType.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'body_type_choices': RefTypeBody.objects.all().order_by('name'),
        'selected_body_type_ids': selected_body_type_ids,
        'package_search_url': '/estimation-engine/api/catalog/packages/',
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
            min_damage_count=max(0, int(request.POST.get('min_damage_count') or 0)),
            price_group=request.POST.get('price_group', '').strip(),
            paint_type=request.POST.get('paint_type', '').strip(),
            under_instrument=request.POST.get('under_instrument') == 'on',
            windshield_heat=_parse_flag_choice(request.POST.get('windshield_heat')),
            windshield_projection=_parse_flag_choice(request.POST.get('windshield_projection')),
            cleaning_level=_parse_cleaning_level(request.POST.get('cleaning_level')),
            salon_type=_parse_salon_type(request.POST.get('salon_type')),
            diagnostic_system=_parse_diagnostic_system(request.POST.get('diagnostic_system')),
            diagnostic_status=_parse_diagnostic_status(request.POST.get('diagnostic_status')),
            hour_rate=_parse_decimal(request.POST.get('hour_rate'), '0'),
            is_active=request.POST.get('is_active') == 'on',
        )
        try:
            rule.full_clean()
        except Exception as exc:
            rule.delete()
            messages.error(request, str(exc))
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context())
        _save_rule_body_types(rule, request)
        _save_rule_packages(rule, request)
        _save_rule_conditions(rule, request)
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
        rule.min_damage_count = max(0, int(request.POST.get('min_damage_count') or 0))
        rule.price_group = request.POST.get('price_group', '').strip()
        rule.paint_type = request.POST.get('paint_type', '').strip()
        rule.under_instrument = request.POST.get('under_instrument') == 'on'
        rule.windshield_heat = _parse_flag_choice(request.POST.get('windshield_heat'))
        rule.windshield_projection = _parse_flag_choice(request.POST.get('windshield_projection'))
        rule.cleaning_level = _parse_cleaning_level(request.POST.get('cleaning_level'))
        rule.salon_type = _parse_salon_type(request.POST.get('salon_type'))
        rule.diagnostic_system = _parse_diagnostic_system(request.POST.get('diagnostic_system'))
        rule.diagnostic_status = _parse_diagnostic_status(request.POST.get('diagnostic_status'))
        rule.hour_rate = _parse_decimal(request.POST.get('hour_rate'), '0')
        rule.is_active = request.POST.get('is_active') == 'on'
        try:
            rule.full_clean()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, 'estimation_engine/rule_form.html', _rule_form_context(rule))
        rule.save()
        _save_rule_body_types(rule, request)
        _save_rule_packages(rule, request)
        _save_rule_conditions(rule, request)
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

    from refs.models import RefTypeBody

    return render(request, 'estimation_engine/rules_preview.html', {
        'facts': facts,
        'preview': preview,
        'include_drafts': include_drafts,
        'section_choices': EstimationRule.SECTION_CHOICES,
        'cleaning_choices': EstimationRule.CLEANING_CHOICES,
        'salon_type_choices': EstimationRule.SALON_TYPE_CHOICES,
        'diagnostic_system_choices': EstimationRule.DIAG_SYSTEM_CHOICES,
        'diagnostic_status_choices': EstimationRule.DIAG_STATUS_CHOICES,
        'elements': SchemeElement.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'damage_types': DamageType.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'body_type_choices': RefTypeBody.objects.all().order_by('name'),
    })


@login_required
def catalogs_hub(request):
    """Справочники осмотра и подготовки."""
    from car_preparation.models import RefCarPreparationWork, RefPreparationMaterial

    return render(request, 'estimation_engine/catalogs_hub.html', {
        'elements_count': SchemeElement.objects.filter(is_active=True).count(),
        'damage_types_count': DamageType.objects.filter(is_active=True).count(),
        'polygon_links': SchemeElement.objects.filter(polygons__isnull=False).distinct().count(),
        'info_body_count': RegInfoBody.objects.count(),
        'info_body_sides': (
            RegInfoBody.objects.exclude(side='')
            .values_list('side', flat=True)
            .distinct()
            .count()
        ),
        'works_count': RefCarPreparationWork.objects.filter(is_active=True).count(),
        'materials_count': RefPreparationMaterial.objects.filter(is_active=True).count(),
        'parts_count': PreparationPart.objects.filter(is_active=True).count(),
        'services_count': PreparationService.objects.filter(is_active=True).count(),
        'providers_count': PreparationServiceProvider.objects.filter(is_active=True).count(),
        'offerings_count': PreparationServiceOffering.objects.filter(is_active=True).count(),
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


def _damage_type_form_context(item=None):
    return {
        'item': item,
        'section_choices': DamageType.SECTION_CHOICES,
    }


def _apply_damage_type_from_post(item, request):
    code = (request.POST.get('code') or '').strip().lower().replace(' ', '_')
    name = (request.POST.get('name') or '').strip()
    if not code or not name:
        raise ValueError('Код и наименование обязательны.')
    section = request.POST.get('section') or DamageType.SECTION_EXTERIOR
    if section not in dict(DamageType.SECTION_CHOICES):
        section = DamageType.SECTION_EXTERIOR
    try:
        severity = max(1, int(request.POST.get('severity') or 1))
    except (TypeError, ValueError):
        severity = 1
    try:
        sort_order = max(0, int(request.POST.get('sort_order') or 0))
    except (TypeError, ValueError):
        sort_order = 0

    item.code = code[:64]
    item.name = name[:128]
    item.section = section
    item.legacy_label = (request.POST.get('legacy_label') or '').strip()[:128]
    item.severity = severity
    item.requires_photo = request.POST.get('requires_photo') in ('1', 'on', 'true')
    item.is_active = request.POST.get('is_active') in ('1', 'on', 'true')
    item.sort_order = sort_order
    return item


@login_required
def damage_type_create(request):
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip().lower().replace(' ', '_')
        if not code or not (request.POST.get('name') or '').strip():
            messages.error(request, 'Код и наименование обязательны.')
            return render(request, 'estimation_engine/damage_type_form.html', _damage_type_form_context())
        if DamageType.objects.filter(code=code).exists():
            messages.error(request, f'Тип с кодом «{code}» уже существует.')
            return render(request, 'estimation_engine/damage_type_form.html', _damage_type_form_context())
        try:
            item = _apply_damage_type_from_post(DamageType(), request)
            item.save()
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, 'estimation_engine/damage_type_form.html', _damage_type_form_context())
        messages.success(request, 'Тип повреждения создан.')
        return redirect('estimation_engine:damage_types_list')
    return render(request, 'estimation_engine/damage_type_form.html', _damage_type_form_context())


@login_required
def damage_type_edit(request, item_id):
    item = get_object_or_404(DamageType, pk=item_id)
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip().lower().replace(' ', '_')
        if not code or not (request.POST.get('name') or '').strip():
            messages.error(request, 'Код и наименование обязательны.')
            return render(
                request,
                'estimation_engine/damage_type_form.html',
                _damage_type_form_context(item),
            )
        if DamageType.objects.filter(code=code).exclude(pk=item.pk).exists():
            messages.error(request, f'Тип с кодом «{code}» уже существует.')
            return render(
                request,
                'estimation_engine/damage_type_form.html',
                _damage_type_form_context(item),
            )
        try:
            old_code = item.code
            _apply_damage_type_from_post(item, request)
            item.save()
            if item.code != old_code:
                EstimationRule.objects.filter(damage_type_ref=item).update(damage_type=item.code)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(
                request,
                'estimation_engine/damage_type_form.html',
                _damage_type_form_context(item),
            )
        messages.success(request, 'Тип повреждения сохранён.')
        return redirect('estimation_engine:damage_types_list')
    return render(request, 'estimation_engine/damage_type_form.html', _damage_type_form_context(item))


@login_required
def damage_type_delete(request, item_id):
    item = get_object_or_404(DamageType, pk=item_id)
    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'Тип «{name}» удалён.')
        return redirect('estimation_engine:damage_types_list')
    return render(request, 'estimation_engine/damage_type_confirm_delete.html', {'item': item})


def _normalize_polygon(value):
    """Проверка и нормализация строки полигона: x1,y1,x2,y2,..."""
    raw = (value or '').strip().replace(';', ',')
    if not raw:
        return ''
    parts = [p.strip() for p in raw.split(',') if p.strip() != '']
    if len(parts) < 6:
        raise ValueError('Полигон: нужно минимум 3 точки (6 чисел).')
    if len(parts) % 2 != 0:
        raise ValueError('Полигон: число координат должно быть чётным (пары x,y).')
    nums = []
    for p in parts:
        try:
            nums.append(str(int(float(p))))
        except (TypeError, ValueError):
            raise ValueError(f'Полигон: «{p}» не число.')
    return ','.join(nums)


def _info_body_form_context(item=None):
    type_bodies = list(
        RegInfoBody.objects.exclude(type_body='')
        .values_list('type_body', flat=True)
        .distinct()
        .order_by('type_body')
    )
    sides = list(
        RegInfoBody.objects.exclude(side='')
        .values_list('side', flat=True)
        .distinct()
        .order_by('side')
    )
    return {
        'item': item,
        'type_bodies': type_bodies,
        'sides': sides,
    }


def _apply_info_body_from_post(item, request):
    type_body = (request.POST.get('type_body') or '').strip()
    side = (request.POST.get('side') or '').strip()
    body_element = (request.POST.get('body_element') or '').strip()
    body_elem_name = (request.POST.get('body_elem_name') or '').strip()
    if not type_body or not side or not body_element:
        raise ValueError('Тип кузова, сторона и код элемента обязательны.')
    item.type_body = type_body[:512]
    item.side = side[:512]
    item.body_element = body_element[:512]
    item.body_elem_name = (body_elem_name or body_element)[:512]
    item.polygon = _normalize_polygon(request.POST.get('polygon'))[:5120]
    return item


@login_required
def info_body_list(request):
    """Справочник полигонов RegInfoBody."""
    qs = RegInfoBody.objects.all().order_by('type_body', 'side', 'body_elem_name', 'id')
    type_body = (request.GET.get('type_body') or '').strip()
    side = (request.GET.get('side') or '').strip()
    q = (request.GET.get('q') or '').strip()
    if type_body:
        qs = qs.filter(type_body=type_body)
    if side:
        qs = qs.filter(side=side)
    if q:
        qs = qs.filter(
            Q(body_element__icontains=q)
            | Q(body_elem_name__icontains=q)
            | Q(polygon__icontains=q)
        )

    items_total = qs.count()
    items = list(qs[:500])
    for row in items:
        parts = [p for p in (row.polygon or '').split(',') if p.strip()]
        row.point_count = len(parts) // 2

    type_bodies = (
        RegInfoBody.objects.exclude(type_body='')
        .values_list('type_body', flat=True)
        .distinct()
        .order_by('type_body')
    )
    sides = (
        RegInfoBody.objects.exclude(side='')
        .values_list('side', flat=True)
        .distinct()
        .order_by('side')
    )
    return render(request, 'estimation_engine/info_body_list.html', {
        'items': items,
        'items_total': items_total,
        'type_bodies': type_bodies,
        'sides': sides,
        'filter_type_body': type_body,
        'filter_side': side,
        'filter_q': q,
    })


@login_required
def info_body_create(request):
    if request.method == 'POST':
        try:
            item = _apply_info_body_from_post(RegInfoBody(), request)
            item.save()
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(
                request,
                'estimation_engine/info_body_form.html',
                _info_body_form_context(),
            )
        messages.success(request, 'Полигон создан. При необходимости синхронизируйте элементы схемы.')
        return redirect('estimation_engine:info_body_edit', item_id=item.pk)
    return render(request, 'estimation_engine/info_body_form.html', _info_body_form_context())


@login_required
def info_body_edit(request, item_id):
    item = get_object_or_404(RegInfoBody, pk=item_id)
    if request.method == 'POST':
        try:
            _apply_info_body_from_post(item, request)
            item.save()
        except ValueError as exc:
            messages.error(request, str(exc))
            ctx = _info_body_form_context(item)
            ctx['linked_elements'] = list(
                SchemeElement.objects.filter(polygons__info_body=item).distinct()
            )
            return render(request, 'estimation_engine/info_body_form.html', ctx)
        messages.success(request, 'Полигон сохранён.')
        return redirect('estimation_engine:info_body_edit', item_id=item.pk)

    ctx = _info_body_form_context(item)
    ctx['linked_elements'] = list(
        SchemeElement.objects.filter(polygons__info_body=item).distinct()
    )
    return render(request, 'estimation_engine/info_body_form.html', ctx)


@login_required
def info_body_delete(request, item_id):
    item = get_object_or_404(RegInfoBody, pk=item_id)
    if request.method == 'POST':
        label = f'{item.type_body} / {item.side} / {item.body_elem_name or item.body_element}'
        item.delete()
        messages.success(request, f'Полигон «{label}» удалён.')
        return redirect('estimation_engine:info_body_list')
    return render(request, 'estimation_engine/info_body_confirm_delete.html', {'item': item})


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
            'damage_count': data.get('damage_count'),
            'damage_counts': data.get('damage_counts') or {},
            'body_type_id': data.get('body_type_id') or '',
            'body_type': (data.get('body_type') or '').strip(),
            'price_group': (data.get('price_group') or '').strip(),
            'paint_type': (data.get('paint_type') or '').strip(),
            'under_instrument': bool(data.get('under_instrument')),
            'windshield_heat': bool(data.get('windshield_heat')),
            'windshield_projection': bool(data.get('windshield_projection')),
        }
        only_published = not data.get('include_drafts')
        facts = _resolve_fact_catalog_codes(facts)
    else:
        facts = _facts_from_request(request)
        only_published = request.GET.get('include_drafts') != '1'

    return JsonResponse(preview_from_facts(facts, only_published=only_published))
