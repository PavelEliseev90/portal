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
    EstimationRuleCondition,
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


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in ('1', 'true', 'on', 'yes', 'да')


def _as_int(value, default=0) -> int:
    try:
        return int(float(str(value).replace(',', '.')))
    except (TypeError, ValueError):
        return default


def _flag_matches(required: str, fact_value) -> bool:
    """
    required: '' | 'yes' | 'no'
    '' = любое; yes = факт должен быть true; no = факт должен быть false.
    """
    req = _norm(required)
    if not req:
        return True
    fact = _as_bool(fact_value)
    if req == EstimationRule.FLAG_YES:
        return fact
    if req == EstimationRule.FLAG_NO:
        return not fact
    return True


def normalize_facts(facts: dict[str, Any]) -> dict[str, Any]:
    """
    Приводит факты к единому виду:
    - damage_counts: {code: int}
    - damage_count: итог (если не задан явно — сумма счётчиков / одиночный тип)
    """
    out = dict(facts or {})
    counts: dict[str, int] = {}

    raw_counts = out.get('damage_counts') or {}
    if isinstance(raw_counts, dict):
        for key, val in raw_counts.items():
            code = _norm(key)
            if code:
                counts[code] = _as_int(val, 0)

    # пары из формы preview: damage_count_type[] + damage_count_n[]
    types = out.get('damage_count_type') or out.get('damage_count_types') or []
    nums = out.get('damage_count_n') or out.get('damage_count_values') or []
    if isinstance(types, (list, tuple)) and isinstance(nums, (list, tuple)):
        for idx, code in enumerate(types):
            c = _norm(code)
            if not c:
                continue
            n = _as_int(nums[idx] if idx < len(nums) else 0, 0)
            counts[c] = counts.get(c, 0) + n

    single_type = _norm(out.get('damage_type'))
    if single_type and single_type not in counts:
        counts[single_type] = _as_int(out.get('damage_count'), 0)

    out['damage_counts'] = counts

    if out.get('damage_count') in (None, ''):
        out['damage_count'] = sum(counts.values())
    else:
        out['damage_count'] = _as_int(out.get('damage_count'), 0)

    return out


def _fact_damage_type_count(facts: dict[str, Any], damage_code: str) -> int:
    code = _norm(damage_code)
    counts = facts.get('damage_counts') or {}
    if code in counts:
        return _as_int(counts.get(code), 0)
    if code and code == _norm(facts.get('damage_type')):
        return _as_int(facts.get('damage_count'), 0)
    return 0


def _condition_left_value(cond: EstimationRuleCondition, facts: dict[str, Any]):
    field = cond.field
    if field == EstimationRuleCondition.FIELD_DAMAGE_TYPE_COUNT:
        code = cond.damage_type or (
            cond.damage_type_ref.code if getattr(cond, 'damage_type_ref', None) else ''
        )
        return _fact_damage_type_count(facts, code)
    if field == EstimationRuleCondition.FIELD_DAMAGE_COUNT:
        return _as_int(facts.get('damage_count'), 0)
    if field in (
        EstimationRuleCondition.FIELD_UNDER_INSTRUMENT,
        EstimationRuleCondition.FIELD_WINDSHIELD_HEAT,
        EstimationRuleCondition.FIELD_WINDSHIELD_PROJECTION,
    ):
        return _as_bool(facts.get(field))
    return facts.get(field)


def _compare(operator: str, left, right_raw: str) -> bool:
    op = _norm(operator)
    if op == EstimationRuleCondition.OP_ABSENT:
        if isinstance(left, bool):
            return not left
        if isinstance(left, (int, float)):
            return _as_int(left, 0) == 0
        return not _norm(left)
    if op == EstimationRuleCondition.OP_PRESENT:
        if isinstance(left, bool):
            return left
        if isinstance(left, (int, float)):
            return _as_int(left, 0) > 0
        return bool(_norm(left))

    if isinstance(left, bool) or _norm(right_raw) in ('1', '0', 'true', 'false', 'yes', 'no', 'да', 'нет'):
        left_b = _as_bool(left)
        right_b = _as_bool(right_raw)
        if op == EstimationRuleCondition.OP_EQ:
            return left_b == right_b
        if op == EstimationRuleCondition.OP_NE:
            return left_b != right_b
        return False

    # числа, если оба похожи на числа
    try:
        left_n = float(str(left).replace(',', '.'))
        right_n = float(str(right_raw).replace(',', '.'))
        numeric = True
    except (TypeError, ValueError):
        numeric = False

    if numeric and op in (
        EstimationRuleCondition.OP_GT,
        EstimationRuleCondition.OP_GTE,
        EstimationRuleCondition.OP_LT,
        EstimationRuleCondition.OP_LTE,
        EstimationRuleCondition.OP_EQ,
        EstimationRuleCondition.OP_NE,
    ):
        if op == EstimationRuleCondition.OP_GT:
            return left_n > right_n
        if op == EstimationRuleCondition.OP_GTE:
            return left_n >= right_n
        if op == EstimationRuleCondition.OP_LT:
            return left_n < right_n
        if op == EstimationRuleCondition.OP_LTE:
            return left_n <= right_n
        if op == EstimationRuleCondition.OP_EQ:
            return left_n == right_n
        return left_n != right_n

    left_s = _norm(left)
    right_s = _norm(right_raw)
    if op == EstimationRuleCondition.OP_EQ:
        return left_s == right_s
    if op == EstimationRuleCondition.OP_NE:
        return left_s != right_s
    return False


def evaluate_condition(cond: EstimationRuleCondition, facts: dict[str, Any]) -> tuple[bool, str]:
    left = _condition_left_value(cond, facts)
    ok = _compare(cond.operator, left, cond.value)
    label = dict(EstimationRuleCondition.FIELD_CHOICES).get(cond.field, cond.field)
    op_label = dict(EstimationRuleCondition.OPERATOR_CHOICES).get(cond.operator, cond.operator)
    dtype = ''
    if cond.field == EstimationRuleCondition.FIELD_DAMAGE_TYPE_COUNT:
        dtype = cond.damage_type or ''
        if not dtype and getattr(cond, 'damage_type_ref', None):
            dtype = cond.damage_type_ref.code
        dtype = f' «{dtype}»' if dtype else ''
    detail = f'{label}{dtype} {op_label}'
    if cond.operator not in (
        EstimationRuleCondition.OP_ABSENT,
        EstimationRuleCondition.OP_PRESENT,
    ):
        detail += f' {cond.value}'
    detail += f' (факт: {left})'
    return ok, detail


def evaluate_condition_chain(
    conditions: list[EstimationRuleCondition],
    facts: dict[str, Any],
) -> tuple[bool, str]:
    """Левоассоциативно: A И B ИЛИ C = (A И B) ИЛИ C."""
    active = [c for c in conditions if getattr(c, 'is_active', True)]
    if not active:
        return True, 'ok'

    result = None
    parts = []
    for idx, cond in enumerate(active):
        ok, detail = evaluate_condition(cond, facts)
        if idx == 0:
            result = ok
            parts.append(detail)
            continue
        join = _norm(cond.join_op) or EstimationRuleCondition.JOIN_AND
        join_label = 'И' if join == EstimationRuleCondition.JOIN_AND else 'ИЛИ'
        parts.append(f'{join_label} {detail}')
        if join == EstimationRuleCondition.JOIN_OR:
            result = bool(result) or ok
        else:
            result = bool(result) and ok

    if result:
        return True, 'ok'
    return False, 'условия: ' + ' '.join(parts)


def _rule_conditions(rule: EstimationRule) -> list[EstimationRuleCondition]:
    preset = getattr(rule, '_prefetched_conditions', None)
    if preset is not None:
        return list(preset)
    if getattr(rule, 'pk', None):
        try:
            return list(rule.conditions.filter(is_active=True).order_by('sort_order', 'id'))
        except Exception:
            return []
    return list(getattr(rule, '_conditions', []) or [])


def _rule_body_types(rule: EstimationRule) -> dict:
    """
    Допустимые типы кузова правила.
    Пустой результат = любой кузов.
    """
    preset = getattr(rule, '_body_types', None)
    if preset is not None:
        names = {_norm(x.get('name') if isinstance(x, dict) else x) for x in preset}
        ids = set()
        labels = set()
        for x in preset:
            if isinstance(x, dict):
                if x.get('id') is not None:
                    ids.add(int(x['id']))
                labels.add(str(x.get('name') or x.get('id') or ''))
            else:
                labels.add(str(x))
        names.discard('')
        labels.discard('')
        return {'names': names, 'ids': ids, 'labels': labels}

    if getattr(rule, 'pk', None):
        try:
            rows = list(rule.body_types.values_list('id', 'name'))
            if rows:
                return {
                    'ids': {int(i) for i, _ in rows},
                    'names': {_norm(n) for _, n in rows},
                    'labels': {str(n) for _, n in rows},
                }
        except Exception:
            pass

    # legacy: "седан, хэтчбек" в кэш-поле
    raw = (getattr(rule, 'body_type', None) or '').strip()
    if raw:
        parts = [p.strip() for p in raw.replace(';', ',').split(',') if p.strip()]
        names = {_norm(p) for p in parts}
        return {'ids': set(), 'names': names, 'labels': set(parts)}
    return {'ids': set(), 'names': set(), 'labels': set()}


def rule_matches(rule: EstimationRule, facts: dict[str, Any]) -> tuple[bool, str]:
    """Базовые поля (И) + цепочка доп. условий (И/ИЛИ)."""
    facts = normalize_facts(facts)

    if rule.section and _norm(rule.section) != _norm(facts.get('section')):
        return False, f'раздел: нужно «{rule.section}», факт «{facts.get("section") or "—"}»'
    if rule.element_code and _norm(rule.element_code) != _norm(facts.get('element_code')):
        return False, f'элемент: нужно «{rule.element_code}»'
    if rule.damage_type:
        code = _norm(rule.damage_type)
        counts = facts.get('damage_counts') or {}
        if counts:
            if _fact_damage_type_count(facts, code) <= 0:
                return False, f'повреждение: нужно «{rule.damage_type}»'
        elif code != _norm(facts.get('damage_type')):
            return False, f'повреждение: нужно «{rule.damage_type}»'
    min_count = rule.min_damage_count or 0
    fact_count = _as_int(facts.get('damage_count'), 0)
    if min_count > 0 and fact_count < min_count:
        return False, f'кол-во повреждений {fact_count} < {min_count}'
    allowed_bodies = _rule_body_types(rule)
    if allowed_bodies:
        fact_body = _norm(facts.get('body_type'))
        fact_body_id = facts.get('body_type_id')
        matched = False
        if fact_body and fact_body in allowed_bodies['names']:
            matched = True
        else:
            try:
                bid = int(fact_body_id) if fact_body_id not in (None, '') else None
            except (TypeError, ValueError):
                bid = None
            if bid is not None and bid in allowed_bodies['ids']:
                matched = True
        if not matched:
            need = ', '.join(sorted(allowed_bodies['labels'])) or '—'
            return False, f'кузов: нужно один из «{need}», факт «{facts.get("body_type") or "—"}»'
    if rule.price_group and _norm(rule.price_group) != _norm(facts.get('price_group')):
        return False, f'ЦГ: нужно «{rule.price_group}»'
    if rule.paint_type and _norm(rule.paint_type) != _norm(facts.get('paint_type')):
        return False, f'краска: нужно «{rule.paint_type}»'
    if rule.under_instrument and not facts.get('under_instrument'):
        return False, 'требуется «под прибор»'

    heat_req = getattr(rule, 'windshield_heat', '') or ''
    if not _flag_matches(heat_req, facts.get('windshield_heat')):
        need = 'да' if _norm(heat_req) == EstimationRule.FLAG_YES else 'нет'
        return False, f'подогрев лобового: нужно «{need}»'

    proj_req = getattr(rule, 'windshield_projection', '') or ''
    if not _flag_matches(proj_req, facts.get('windshield_projection')):
        need = 'да' if _norm(proj_req) == EstimationRule.FLAG_YES else 'нет'
        return False, f'проекция на лобовое: нужно «{need}»'

    conditions = _rule_conditions(rule)
    if conditions:
        return evaluate_condition_chain(conditions, facts)
    return True, 'ok'


def select_rules(facts: dict[str, Any], *, only_published: bool = True) -> dict:
    """
    Возвращает сработавшие и отклонённые правила с учётом exclusive_group.
    """
    facts = normalize_facts(facts)
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
        Prefetch(
            'conditions',
            queryset=EstimationRuleCondition.objects.filter(is_active=True)
            .select_related('damage_type_ref')
            .order_by('sort_order', 'id'),
            to_attr='_prefetched_conditions',
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
