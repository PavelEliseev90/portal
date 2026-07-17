"""
MVP rule engine: факты → правила → пакеты → preview состава и суммы.

Не пишет в legacy-расчёт. Не создаёт snapshot/передачу — только симуляция.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Prefetch

from .models import (
    EstimationRule,
    EstimationRulePackage,
    PreparationWorkPackage,
    PreparationWorkPackageLine,
)


def _dec(value, default='0') -> Decimal:
    try:
        return Decimal(str(value if value is not None else default).replace(',', '.'))
    except Exception:
        return Decimal(default)


def _norm(value) -> str:
    return (str(value or '')).strip().lower()


def rule_matches(rule: EstimationRule, facts: dict[str, Any]) -> tuple[bool, str]:
    """Проверка AND-условий. Пустые поля правила = «любое»."""
    if rule.section and _norm(rule.section) != _norm(facts.get('section')):
        return False, f'раздел: нужно «{rule.section}», факт «{facts.get("section") or "—"}»'
    if rule.element_code and _norm(rule.element_code) != _norm(facts.get('element_code')):
        return False, f'элемент: нужно «{rule.element_code}»'
    if rule.damage_type and _norm(rule.damage_type) != _norm(facts.get('damage_type')):
        return False, f'повреждение: нужно «{rule.damage_type}»'
    fact_count = int(facts.get('damage_count') or 0)
    if fact_count < (rule.min_damage_count or 1):
        return False, f'кол-во повреждений {fact_count} < {rule.min_damage_count}'
    if rule.body_type and _norm(rule.body_type) != _norm(facts.get('body_type')):
        return False, f'кузов: нужно «{rule.body_type}»'
    if rule.price_group and _norm(rule.price_group) != _norm(facts.get('price_group')):
        return False, f'ЦГ: нужно «{rule.price_group}»'
    if rule.paint_type and _norm(rule.paint_type) != _norm(facts.get('paint_type')):
        return False, f'краска: нужно «{rule.paint_type}»'
    if rule.under_instrument and not facts.get('under_instrument'):
        return False, 'требуется «под прибор»'
    return True, 'ok'


def select_rules(facts: dict[str, Any], *, only_published: bool = True) -> dict:
    """
    Возвращает сработавшие и отклонённые правила с учётом exclusive_group.
    """
    qs = EstimationRule.objects.filter(is_active=True)
    if only_published:
        qs = qs.filter(status=EstimationRule.STATUS_PUBLISHED)
    else:
        qs = qs.exclude(status=EstimationRule.STATUS_ARCHIVED)

    qs = qs.prefetch_related(
        Prefetch(
            'rule_packages',
            queryset=EstimationRulePackage.objects.filter(is_active=True)
            .select_related('package')
            .order_by('sort_order', 'id'),
        ),
    ).order_by('-priority', 'id')

    matched = []
    rejected = []
    for rule in qs:
        ok, reason = rule_matches(rule, facts)
        if ok:
            matched.append(rule)
        else:
            rejected.append({
                'rule_id': rule.id,
                'code': rule.code,
                'name': rule.name,
                'priority': rule.priority,
                'reason': reason,
            })

    # exclusive_group: оставляем только max priority в группе
    winners = []
    suppressed = []
    seen_groups: dict[str, EstimationRule] = {}
    for rule in matched:
        group = (rule.exclusive_group or '').strip()
        if not group:
            winners.append(rule)
            continue
        prev = seen_groups.get(group)
        if prev is None:
            seen_groups[group] = rule
            winners.append(rule)
        else:
            # уже есть победитель с >= priority (список отсортирован)
            suppressed.append({
                'rule_id': rule.id,
                'code': rule.code,
                'name': rule.name,
                'priority': rule.priority,
                'reason': f'подавлено exclusive_group «{group}» правилом {prev.code}',
                'winner_code': prev.code,
            })

    return {
        'matched': winners,
        'rejected': rejected,
        'suppressed': suppressed,
    }


def _line_cost(line: PreparationWorkPackageLine, hour_rate: Decimal) -> Decimal:
    if line.line_type == PreparationWorkPackageLine.LINE_WORK:
        return _dec(line.norm_hours) * _dec(hour_rate)
    return _dec(line.quantity) * _dec(line.unit_cost)


def _line_label(line: PreparationWorkPackageLine) -> str:
    if line.work_id:
        return line.work.name
    if line.material_id:
        return line.material.name
    if line.part_id:
        return line.part.name
    if line.service_offering_id:
        return str(line.service_offering)
    if line.service_id:
        return line.service.name
    return line.notes or line.line_type


def expand_preview(rules: list[EstimationRule]) -> dict:
    """
    Раскрывает пакеты сработавших правил, дедуп по coverage_key, считает суммы.
    """
    packages_out = []
    lines_out = []
    seen_coverage: set[str] = set()
    total = Decimal('0')
    total_hours = Decimal('0')
    skipped_dupes = []

    for rule in rules:
        hour_rate = _dec(rule.hour_rate)
        for link in rule.rule_packages.all():
            if not link.is_active:
                continue
            package = link.package
            if not package or not package.is_active:
                continue
            if package.status == PreparationWorkPackage.STATUS_ARCHIVED:
                continue

            pkg_lines = list(
                package.lines.filter(is_active=True)
                .select_related('work', 'material', 'part', 'service', 'service_offering')
                .order_by('sort_order', 'id')
            )
            line_rows = []
            pkg_sum = Decimal('0')
            pkg_hours = Decimal('0')

            for line in pkg_lines:
                key = (line.coverage_key or '').strip()
                if key and key in seen_coverage:
                    skipped_dupes.append({
                        'coverage_key': key,
                        'line_type': line.line_type,
                        'name': _line_label(line),
                        'from_package': package.code,
                        'from_rule': rule.code,
                    })
                    continue
                if key:
                    seen_coverage.add(key)

                cost = _line_cost(line, hour_rate)
                hours = _dec(line.norm_hours) if line.line_type == PreparationWorkPackageLine.LINE_WORK else Decimal('0')
                row = {
                    'rule_id': rule.id,
                    'rule_code': rule.code,
                    'package_id': package.id,
                    'package_code': package.code,
                    'package_name': package.name,
                    'line_id': line.id,
                    'line_type': line.line_type,
                    'name': _line_label(line),
                    'quantity': str(_dec(line.quantity)),
                    'norm_hours': str(hours),
                    'unit_cost': str(_dec(line.unit_cost)),
                    'hour_rate': str(hour_rate),
                    'cost': str(cost),
                    'coverage_key': key,
                    'route_type': package.route_type,
                }
                line_rows.append(row)
                lines_out.append(row)
                pkg_sum += cost
                pkg_hours += hours

            if link.fixed_cost is not None:
                # Фикс на пакете заменяет построчную сумму
                pkg_sum = _dec(link.fixed_cost)
                for row in line_rows:
                    row['cost'] = '0'
                    row['cost_note'] = 'входит в фикс. стоимость пакета'

            packages_out.append({
                'rule_id': rule.id,
                'rule_code': rule.code,
                'rule_name': rule.name,
                'package_id': package.id,
                'package_code': package.code,
                'package_name': package.name,
                'route_type': package.route_type,
                'route_display': package.get_route_type_display(),
                'fixed_cost': str(link.fixed_cost) if link.fixed_cost is not None else None,
                'lines_count': len(line_rows),
                'norm_hours': str(pkg_hours),
                'cost': str(pkg_sum),
                'hour_rate': str(hour_rate),
            })
            total += pkg_sum
            total_hours += pkg_hours

    return {
        'packages': packages_out,
        'lines': lines_out,
        'skipped_duplicates': skipped_dupes,
        'total_cost': str(total),
        'total_norm_hours': str(total_hours),
    }


def preview_from_facts(facts: dict[str, Any], *, only_published: bool = True) -> dict:
    """Полный preview: отбор правил + состав + итог."""
    selection = select_rules(facts, only_published=only_published)
    matched = selection['matched']
    expansion = expand_preview(matched)
    return {
        'facts': facts,
        'matched_rules': [
            {
                'id': r.id,
                'code': r.code,
                'name': r.name,
                'priority': r.priority,
                'exclusive_group': r.exclusive_group,
                'hour_rate': str(r.hour_rate),
                'packages': [
                    {'id': lp.package_id, 'code': lp.package.code, 'name': lp.package.name}
                    for lp in r.rule_packages.all() if lp.is_active
                ],
            }
            for r in matched
        ],
        'rejected_rules': selection['rejected'],
        'suppressed_rules': selection['suppressed'],
        **expansion,
        'explanation': _build_explanation(matched, expansion),
    }


def _build_explanation(rules: list[EstimationRule], expansion: dict) -> list[str]:
    lines = []
    for rule in rules:
        pkg_names = [
            p['package_name'] for p in expansion['packages'] if p['rule_id'] == rule.id
        ]
        cost = sum(
            (_dec(p['cost']) for p in expansion['packages'] if p['rule_id'] == rule.id),
            Decimal('0'),
        )
        lines.append(
            f'«{rule.code}» (приоритет {rule.priority}) → '
            f'{", ".join(pkg_names) or "без пакетов"} → {cost} ₽'
        )
    if expansion['total_cost']:
        lines.append(f'Итого: {expansion["total_cost"]} ₽ / {expansion["total_norm_hours"]} н/ч')
    return lines
