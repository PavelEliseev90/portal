# -*- coding: utf-8 -*-
"""
Сервисный слой для Центра управления ценообразованием и дисконтами новых автомобилей.
Включает:
- Аналитический радар (темп контрактования, run-rate, упущенные сделки).
- Мониторинг желтых авто и сроков бесплатной консигнации от импортера.
- Умный генератор рекомендаций правил дисконта (Smart Advisor).
- Импорт и экспорт планов ДЦ в Excel.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.utils import timezone

from prices_car.models import (
    BrandKM,
    DcCommandCenterShowcase,
    DcKeyModel,
    DcMonthlyPlan,
    PriceCarBrand,
    PriceCarKmDiscount,
)
from refs.models import (
    AutoruModel,
    RefCarsOrganization,
    RefCity,
    RefTypeSaleCarsOrganization,
    RefUnit,
)


def get_first_day_of_month(d: Optional[date] = None) -> date:
    """Возвращает дату первого дня месяца."""
    if d is None:
        d = timezone.now().date()
    return d.replace(day=1)


def get_month_days_info(month_start: date) -> dict:
    """Возвращает информацию о днях месяца: текущий день, всего дней, дней осталось."""
    today = timezone.now().date()
    _, days_in_month = calendar.monthrange(month_start.year, month_start.month)

    if today.year == month_start.year and today.month == month_start.month:
        day_now = today.day
    elif today > month_start:
        day_now = days_in_month
    else:
        day_now = 1

    days_remaining = max(days_in_month - day_now, 0)
    month_progress_pct = round((day_now / days_in_month) * 100, 1)

    return {
        'day_now': day_now,
        'days_in_month': days_in_month,
        'days_remaining': days_remaining,
        'month_progress_pct': month_progress_pct,
        'today': today,
    }


def get_contracts_count_for_unit(unit: RefUnit, month_start: date) -> int:
    """
    Получение количества контрактов ДЦ за указанный месяц.
    Источники (по приоритету):
    1. powerbi.models.Cumulative (по подразделению и дате контрактования / продажи)
    2. DocRLK / CarCalculations (согласованные сделки)
    """
    days_info = get_month_days_info(month_start)
    month_end = month_start.replace(day=days_info['days_in_month'])
    dt_start = datetime.combine(month_start, datetime.min.time())
    dt_end = datetime.combine(month_end, datetime.max.time())

    # Попытка извлечь из Cumulative
    try:
        from powerbi.models import Cumulative
        # Фильтруем по совпадению наименования ДЦ
        unit_name = (unit.name or '').strip()
        qs = Cumulative.objects.filter(
            PodrazdelenieDTs__icontains=unit_name,
            ListOtsenkiVIN=None,
        ).exclude(RRTS='0')

        # Контракты за месяц
        contracts = qs.filter(
            Q(DataKontraktovaniya__range=(dt_start, dt_end)) |
            Q(DataProdazhi__range=(dt_start, dt_end))
        ).count()
        if contracts > 0:
            return contracts
    except Exception:
        pass

    # Альтернатива: согласованные калькуляции КП с автомобилем в этом ДЦ
    try:
        from prices_car.models import CarCalculations
        calc_contracts = CarCalculations.objects.filter(
            unit=unit,
            car__is_new=True,
            date__range=(dt_start, dt_end),
            soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
                CarCalculations.SOGLASOVANIE_UK_APPROVED,
            ],
            active=True,
        ).count()
        if calc_contracts > 0:
            return calc_contracts
    except Exception:
        pass

    return 0


def format_rubles(val: int | float | None) -> str:
    """Форматирует сумму в рублях с пробелами (например 1 250 000 ₽)."""
    if val is None or val == 0:
        return '0 ₽'
    val_int = int(round(val))
    return f"{val_int:,} ₽".replace(',', ' ')


def get_dc_financial_fact(unit: RefUnit, month_start: date) -> dict:
    """
    Расчет фактических финансовых показателей ДЦ за указанный месяц:
    - Фактическая кумулятивная маржа (КМ в рублях):
      маржа авто + кредит + ОПФУ + ЗЧ + шины + работы + трейд-ин + госрег.
    - Фактический оборот (выручка в рублях).

    Источники:
    1. powerbi.models.Cumulative (по подразделению и дате контрактования / продажи)
    2. Резервный: CarCalculations (согласованные КП по новым авто)
    """
    days_info = get_month_days_info(month_start)
    month_end = month_start.replace(day=days_info['days_in_month'])
    dt_start = datetime.combine(month_start, datetime.min.time())
    dt_end = datetime.combine(month_end, datetime.max.time())

    # 1. Попытка расчета из Cumulative
    try:
        from powerbi.models import Cumulative
        unit_name = (unit.name or '').strip()
        qs = Cumulative.objects.filter(
            PodrazdelenieDTs__icontains=unit_name,
            ListOtsenkiVIN=None,
        ).exclude(RRTS='0').filter(
            Q(DataKontraktovaniya__range=(dt_start, dt_end)) |
            Q(DataProdazhi__range=(dt_start, dt_end))
        )

        res = qs.aggregate(
            marzha=Sum('SummaMarzhiBezNDS'),
            vp_kredit=Sum('VPKredit'),
            vp_opfu=Sum('VPOPFU'),
            vp_zch=Sum('ValovayaPribylZCh'),
            vp_shiny=Sum('ValovayaPribylZChShiny'),
            rabot=Sum('SummaRabot'),
            tradein=Sum('SummaTreydInPoPlanu'),
            gosreg=Sum('SummaGosreg'),
            vyruchka=Sum('VyruchkaZaAvto'),
        )

        total_km = sum(float(res.get(k) or 0.0) for k in (
            'marzha', 'vp_kredit', 'vp_opfu', 'vp_zch', 'vp_shiny',
            'rabot', 'tradein', 'gosreg'
        ))
        total_rev = float(res.get('vyruchka') or 0.0)

        if total_km != 0 or total_rev != 0:
            return {
                'fact_km': int(round(total_km)),
                'fact_revenue': int(round(total_rev)),
                'source': 'cumulative',
            }
    except Exception:
        pass

    # 2. Резервный источник: согласованные CarCalculations по новым авто
    try:
        from prices_car.models import CarCalculations
        calc_qs = CarCalculations.objects.filter(
            unit=unit,
            car__is_new=True,
            date__range=(dt_start, dt_end),
            soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
                CarCalculations.SOGLASOVANIE_UK_APPROVED,
            ],
            active=True,
        )
        calc_res = calc_qs.aggregate(
            total_kvp=Sum('kvp'),
            total_price=Sum('price'),
        )
        total_km = float(calc_res.get('total_kvp') or 0.0)
        total_rev = float(calc_res.get('total_price') or 0.0)
        if total_km != 0 or total_rev != 0:
            return {
                'fact_km': int(round(total_km)),
                'fact_revenue': int(round(total_rev)),
                'source': 'calculations',
            }
    except Exception:
        pass

    return {
        'fact_km': 0,
        'fact_revenue': 0,
        'source': 'none',
    }


def get_missed_deals_info(unit: RefUnit, month_start: date) -> dict:
    """
    Получение информации об упущенных сделках за месяц:
    - по DocRLK (is_missed=1)
    - по отказным калькуляциям КП (soglasovanie_status = rejected)
    """
    days_info = get_month_days_info(month_start)
    month_end = month_start.replace(day=days_info['days_in_month'])
    dt_start = datetime.combine(month_start, datetime.min.time())
    dt_end = datetime.combine(month_end, datetime.max.time())

    missed_count = 0
    rejected_calcs_count = 0
    top_missed_models = []

    try:
        from documents.models import DocRLK
        rlk_qs = DocRLK.objects.filter(
            staff__unit=unit,
            is_missed=1,
            dataTimeCreate__range=(dt_start, dt_end),
        )
        missed_count = rlk_qs.count()
    except Exception:
        pass

    try:
        from prices_car.models import CarCalculations
        rejected_qs = CarCalculations.objects.filter(
            unit=unit,
            car__is_new=True,
            date__range=(dt_start, dt_end),
            soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
                CarCalculations.SOGLASOVANIE_UK_REJECTED,
            ],
        )
        rejected_calcs_count = rejected_qs.count()

        # Топ моделей с отказами
        model_stats = rejected_qs.values('car__modification_autoru__model__name').annotate(
            cnt=Count('id')
        ).order_by('-cnt')[:3]
        for m in model_stats:
            m_name = m['car__modification_autoru__model__name']
            if m_name:
                top_missed_models.append({'name': m_name, 'count': m['cnt']})
    except Exception:
        pass

    return {
        'total_missed': missed_count + rejected_calcs_count,
        'missed_rlk': missed_count,
        'rejected_calcs': rejected_calcs_count,
        'top_models': top_missed_models,
    }


def get_brand_consignment_days_map() -> dict[int, int]:
    """Карта {brand_id: free_consignment_days}."""
    res = {}
    for pb in PriceCarBrand.objects.all():
        res[pb.id] = pb.free_consignment_days or 90
    return res


def get_dc_stock_analytics(unit: RefUnit, key_model_ids: set[int]) -> dict:
    """
    Анализ склада новых автомобилей ДЦ:
    - общее количество и сумма
    - желтые автомобили (is_yellow: сдан рапорт)
    - статус консигнации по брендам (просрочена, истекает, в норме)
    - остатки по ключевым моделям
    """
    cars_qs = RefCarsOrganization.objects.filter(
        unit=unit,
        is_new=True,
    ).exclude(quantity=0).select_related(
        'modification_autoru__model__mark',
        'type_sale',
        'stage_price',
    )

    total_count = 0
    total_rrc = 0
    total_cost = 0

    yellow_cars = []
    consignment_overdue_cars = []
    consignment_warning_cars = []
    key_models_stock: dict[int, dict] = {}
    models_stock: dict[int, dict] = {}

    brand_consignment = get_brand_consignment_days_map()

    for car in cars_qs:
        total_count += 1
        price = car.price or 0
        cost = car.cost_price or 0
        total_rrc += price
        total_cost += cost

        # 1. Проверка «желтого» статуса
        if car.is_yellow:
            yellow_cars.append(car)

        # 2. Проверка срока консигнации
        mark = None
        brand_free_days = 90
        if car.modification_autoru and car.modification_autoru.model and car.modification_autoru.model.mark:
            mark = car.modification_autoru.model.mark
            pb = PriceCarBrand.objects.filter(marks=mark).first()
            if pb:
                brand_free_days = pb.free_consignment_days or 90

        cons_status = car.get_consignment_status(free_days=brand_free_days)
        if cons_status['is_overdue']:
            consignment_overdue_cars.append({
                'car': car,
                'days_stock': cons_status['days_stock'],
                'free_days': brand_free_days,
                'days_overdue': abs(cons_status['days_left']),
            })
        elif cons_status['is_warning']:
            consignment_warning_cars.append({
                'car': car,
                'days_stock': cons_status['days_stock'],
                'free_days': brand_free_days,
                'days_left': cons_status['days_left'],
            })

        # 3. Учет остатков по моделям
        if car.modification_autoru and car.modification_autoru.model:
            m = car.modification_autoru.model
            if m.id not in models_stock:
                models_stock[m.id] = {
                    'model_id': m.id,
                    'name': m.name,
                    'mark_name': mark.name if mark else '',
                    'count': 0,
                    'is_key': m.id in key_model_ids,
                }
            models_stock[m.id]['count'] += 1

            if m.id in key_model_ids:
                if m.id not in key_models_stock:
                    key_models_stock[m.id] = {
                        'model_id': m.id,
                        'name': m.name,
                        'mark_name': mark.name if mark else '',
                        'count': 0,
                    }
                key_models_stock[m.id]['count'] += 1

    return {
        'total_count': total_count,
        'total_rrc': total_rrc,
        'total_cost': total_cost,
        'yellow_cars_count': len(yellow_cars),
        'yellow_cars': yellow_cars,
        'consignment_overdue_count': len(consignment_overdue_cars),
        'consignment_overdue_cars': consignment_overdue_cars,
        'consignment_warning_count': len(consignment_warning_cars),
        'consignment_warning_cars': consignment_warning_cars,
        'key_models_stock': list(key_models_stock.values()),
        'all_models_stock': sorted(models_stock.values(), key=lambda x: -x['count']),
    }


def generate_smart_recommendations(
    plan: DcMonthlyPlan,
    contracts_count: int,
    stock_data: dict,
    days_info: dict,
    missed_info: dict,
    financial_fact: Optional[dict] = None,
) -> list[dict]:
    """
    Генератор умных рекомендаций правил дисконта (Smart Advisor):
    Двухфакторный анализ: темп контрактования (штуки) vs финансовый результат (кумулятивная маржа КМ в рублях).
    Также анализирует желтые авто, риски консигнации и упущенные сделки.
    """
    recommendations = []
    day_now = days_info['day_now']
    days_in_month = days_info['days_in_month']
    days_remaining = days_info['days_remaining']

    plan_importer = plan.plan_importer_qty or 0
    plan_dc = plan.plan_dc_qty or 0
    target_plan = max(plan_importer, plan_dc)

    # Расчет темпа по штукам (run-rate)
    run_rate = (contracts_count / day_now * days_in_month) if day_now > 0 else 0
    pace_pct = (run_rate / target_plan * 100) if target_plan > 0 else 100
    gap = target_plan - contracts_count

    # Финансовый факт и темп по кумулятивной марже
    if financial_fact is None and getattr(plan, 'unit', None):
        financial_fact = get_dc_financial_fact(plan.unit, plan.month)

    fact_km = financial_fact.get('fact_km', 0) if financial_fact else 0
    plan_km = plan.plan_km_rub or 0
    km_run_rate = (fact_km / day_now * days_in_month) if day_now > 0 else 0
    km_pace_pct = (km_run_rate / plan_km * 100) if plan_km > 0 else 0

    # =========================================================================
    # ДВУХФАКТОРНЫЙ КОНТРОЛЬ: ШТУКИ vs ДЕНЬГИ (КМ В РУБЛЯХ)
    # =========================================================================
    if plan_km > 0:
        # Ситуация А: СЛИВ МАРЖИ (Штуки идут, но маржа отстает)
        if pace_pct >= 90 and km_pace_pct < 85:
            recommendations.append({
                'id': 'margin_drain_alert',
                'badge': 'Слив маржи',
                'badge_class': 'warning',
                'title': f'Слив маржи: темп КМ отстает ({int(km_pace_pct)}% от плана)',
                'text': (
                    f'План по штукам закрывается (прогноз {round(run_rate)} шт.), однако кумулятивная маржа ДЦ '
                    f'отстает от финансового плана ({fact_km:,} ₽ из {plan_km:,} ₽, прогноз: {round(km_run_rate):,} ₽). '
                    f'Скидки завышены! Рекомендуется ограничить дисконты и переключить ценообразование на защиту маржи.'
                ).replace(',', ' '),
                'action_label': 'Переключить тактику на «Максимальная маржа»',
                'action_type': 'set_tactic',
                'action_data': {
                    'tactic': DcMonthlyPlan.TACTIC_MAX_MARGIN,
                },
            })

        # Ситуация Б: ЗАПАС СКИДКИ (Маржа опережает план, но штуки отстают)
        elif pace_pct < 90 and km_pace_pct >= 105 and gap > 0:
            recommendations.append({
                'id': 'margin_safety_surplus',
                'badge': 'Запас скидки',
                'badge_class': 'info',
                'title': f'Запас по марже (+{int(km_pace_pct - 100)}%): есть резерв для дисконта',
                'text': (
                    f'Кумулятивная маржа ДЦ превышает финансовый график (прогноз: {round(km_run_rate):,} ₽ при плане {plan_km:,} ₽). '
                    f'При этом отставание по штукам составляет {gap} шт. Финансовая подушка позволяет предоставить '
                    f'точечные скидки для ускорения темпа контрактования.'
                ).replace(',', ' '),
                'action_label': 'Разрешить дисконт для объема («Макс. штуки»)',
                'action_type': 'set_tactic',
                'action_data': {
                    'tactic': DcMonthlyPlan.TACTIC_MAX_VOLUME,
                },
            })

        # Ситуация В: ЗОНА РИСКА (Оба показателя глубоко отстают)
        elif pace_pct < 85 and km_pace_pct < 85:
            recommendations.append({
                'id': 'critical_zone_alert',
                'badge': 'Зона риска',
                'badge_class': 'danger',
                'title': f'Зона риска: отставание по штукам ({int(pace_pct)}%) и по марже ({int(km_pace_pct)}%)',
                'text': (
                    f'ДЦ находится в зоне риска: прогноз контрактов {round(run_rate)} из {target_plan} шт., '
                    f'прогноз КМ: {round(km_run_rate):,} ₽ из {plan_km:,} ₽. Требуется аудит воронки трафика и складских остатков.'
                ).replace(',', ' '),
                'action_label': 'Переключить на сбалансированную тактику',
                'action_type': 'set_tactic',
                'action_data': {
                    'tactic': DcMonthlyPlan.TACTIC_BALANCED,
                },
            })

    # 1. Отставание от плана по штукам (Ускорение темпа)
    # Если зафиксирован слив маржи (km_pace_pct < 85), не создаем дополнительный дисконт на объем, чтобы не усугублять слив!
    if target_plan > 0 and pace_pct < 90 and gap > 0 and (plan_km == 0 or km_pace_pct >= 85):
        # Находим топ модель в стоке для стимулирования
        top_model = None
        if stock_data['key_models_stock']:
            top_model = max(stock_data['key_models_stock'], key=lambda x: x['count'])
        elif stock_data['all_models_stock']:
            top_model = stock_data['all_models_stock'][0]

        if top_model and top_model['count'] > 0:
            suggested_discount = -4.0 if plan.tactic == DcMonthlyPlan.TACTIC_MAX_VOLUME else -2.5
            recommendations.append({
                'id': 'pace_catchup',
                'badge': 'Нагнать темп продаж',
                'badge_class': 'danger',
                'title': f'Отставание от плана на {int(100 - pace_pct)}%: стимулировать «{top_model["name"]}»',
                'text': (
                    f'Текущий прогноз выполнения: {round(run_rate)} из {target_plan} шт. '
                    f'На складе {top_model["count"]} шт. модели {top_model["name"]}. '
                    f'Рекомендуется установить дисконт {suggested_discount}% на канал «Кредит / Розница» до конца месяца.'
                ),
                'action_label': f'Применить дисконт {suggested_discount}% на {top_model["name"]}',
                'action_type': 'create_discount',
                'action_data': {
                    'model_id': top_model['model_id'],
                    'discount_percent': suggested_discount,
                    'is_key_model': True,
                    'comment': f'Авто-рекомендация: ликвидация отставания темпа ДЦ ({gap} шт.)',
                },
            })

    # 2. Желтые автомобили со сданным рапортом
    if stock_data['yellow_cars_count'] > 0:
        yellow_cnt = stock_data['yellow_cars_count']
        recommendations.append({
            'id': 'yellow_cars',
            'badge': 'Желтые автомобили',
            'badge_class': 'warning',
            'title': f'{yellow_cnt} авто уже отчитаны перед импортером (сдан рапорт)',
            'text': (
                f'Автомобили со статусом «желтый» несут прямые издержки отвлечения капитала. '
                f'Рекомендуется включить специальный дисконт 50 000 ₽ (-5.0%) для ускорения розничной продажи этих машин.'
            ),
            'action_label': f'Включить дисконт 50 000 ₽ (-5.0%) для {yellow_cnt} желтых авто',
            'action_type': 'create_yellow_discount',
            'action_data': {
                'discount_percent': -5.0,
                'discount_rub': 50000,
                'is_yellow_car': True,
                'comment': f'Авто-рекомендация: ускорение выбытия отчитанных авто ({yellow_cnt} шт.)',
            },
        })

    # 3. Риск истечения бесплатного срока консигнации
    overdue_cnt = stock_data['consignment_overdue_count']
    warning_cnt = stock_data['consignment_warning_count']
    if overdue_cnt > 0 or warning_cnt > 0:
        total_risk_cnt = overdue_cnt + warning_cnt
        recommendations.append({
            'id': 'consignment_risk',
            'badge': 'Консигнация импортера',
            'badge_class': 'danger',
            'title': f'Риск платного хранения: {total_risk_cnt} авто на грани или просрочены',
            'text': (
                f'Просрочено: {overdue_cnt} шт., истекает срок (<= 15 дн): {warning_cnt} шт. '
                f'Каждый день просрочки консигнации увеличивает финансовые расходы ДЦ. '
                f'Рекомендуется запустить срочный дисконт 70 000 ₽ (порог консигнации <= 15 дн).'
            ),
            'action_label': 'Создать дисконт 70 000 ₽ для авто группы риска',
            'action_type': 'create_consignment_discount',
            'action_data': {
                'discount_percent': -3.0,
                'discount_rub': 70000,
                'days_consignment_left_lte': 15,
                'comment': f'Авто-рекомендация: защита от процентов платной консигнации ({total_risk_cnt} авто)',
            },
        })

    # 4. Упущенные сделки по отказам КП
    if missed_info['total_missed'] >= 3 and missed_info['top_models']:
        m_top = missed_info['top_models'][0]
        recommendations.append({
            'id': 'missed_deals',
            'badge': 'Упущенные сделки',
            'badge_class': 'info',
            'title': f'{missed_info["total_missed"]} упущенных клиентов: лидер отказов «{m_top["name"]}»',
            'text': (
                f'Клиенты уходят без сделки (по модели {m_top["name"]} зафиксировано {m_top["count"]} отказов). '
                f'Предоставление гибкого дисконта -2.0% поможет менеджерам закрывать сомневающихся покупателей в КП.'
            ),
            'action_label': f'Смягчить КМ на {m_top["name"]} (-2.0%)',
            'action_type': 'create_discount',
            'action_data': {
                'model_name': m_top['name'],
                'discount_percent': -2.0,
                'comment': f'Авто-рекомендация: предотвращение упущенных сделок по {m_top["name"]}',
            },
        })

    # 5. Опережение темпа (Максимизация маржи)
    if target_plan > 0 and pace_pct >= 115 and plan.tactic != DcMonthlyPlan.TACTIC_MAX_MARGIN:
        recommendations.append({
            'id': 'maximize_margin',
            'badge': 'Сверхмаржа',
            'badge_class': 'success',
            'title': f'Темп опережает план на +{int(pace_pct - 100)}%: переключить на «Макс. маржу»',
            'text': (
                f'Текущий прогноз ({round(run_rate)} шт.) с запасом перекрывает план импортера ({plan_importer} шт.). '
                f'Рекомендуется активировать тактику «Максимальная маржа», чтобы зафиксировать дополнительную валовую прибыль.'
            ),
            'action_label': 'Переключить тактику на «Максимальная маржа»',
            'action_type': 'set_tactic',
            'action_data': {
                'tactic': DcMonthlyPlan.TACTIC_MAX_MARGIN,
            },
        })

    return recommendations


def sync_autopilot_for_unit(
    unit: RefUnit,
    month_start: date,
    plan: Optional[DcMonthlyPlan] = None,
    recommendations: Optional[list] = None,
    financial_fact: Optional[dict] = None,
) -> list[str]:
    """
    Синхронизирует правила дисконта в режиме автопилота:
    Если plan.is_autopilot == True, система автоматически создает/обновляет правила дисконта по рекомендациям.
    Если ДЦ находится в режиме слива маржи (маржа отстает при выполненных штуках), автопилот блокирует
    создание агрессивных скидок на объем, отдавая приоритет защите маржи.
    """
    if plan is None:
        plan = DcMonthlyPlan.objects.filter(unit=unit, month=month_start).first()
    if not plan or not plan.is_autopilot:
        return []

    days_info = get_month_days_info(month_start)
    if financial_fact is None:
        financial_fact = get_dc_financial_fact(unit, month_start)

    if recommendations is None:
        contracts_count = get_contracts_count_for_unit(unit, month_start)
        missed_info = get_missed_deals_info(unit, month_start)
        key_model_ids = set(plan.key_models.values_list('model_id', flat=True))
        stock_data = get_dc_stock_analytics(unit, key_model_ids)
        recommendations = generate_smart_recommendations(
            plan=plan,
            contracts_count=contracts_count,
            stock_data=stock_data,
            days_info=days_info,
            missed_info=missed_info,
            financial_fact=financial_fact,
        )

    log_actions = []
    today = timezone.now().date()
    _, days_in_month = calendar.monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=days_in_month)

    # Проверка на слив маржи для защиты от избыточных скидок
    day_now = days_info['day_now']
    plan_km = plan.plan_km_rub or 0
    fact_km = financial_fact.get('fact_km', 0) if financial_fact else 0
    km_run_rate = (fact_km / day_now * days_in_month) if day_now > 0 else 0
    km_pace_pct = (km_run_rate / plan_km * 100) if plan_km > 0 else 100

    target_plan = max(plan.plan_importer_qty or 0, plan.plan_dc_qty or 0)
    contracts_cnt = get_contracts_count_for_unit(unit, month_start)
    run_rate = (contracts_cnt / day_now * days_in_month) if day_now > 0 else 0
    pace_pct = (run_rate / target_plan * 100) if target_plan > 0 else 100

    is_margin_drain = (plan_km > 0 and pace_pct >= 90 and km_pace_pct < 85)

    for rec in recommendations:
        a_type = rec.get('action_type')
        data = rec.get('action_data', {})
        if a_type in ('create_yellow_discount', 'create_consignment_discount', 'create_discount'):
            disc_pct = float(data.get('discount_percent') or 0.0)
            disc_rub = int(data.get('discount_rub') or 0)
            is_yellow = bool(data.get('is_yellow_car', False))
            is_key = bool(data.get('is_key_model', False))
            days_cons = data.get('days_consignment_left_lte')
            model_id = data.get('model_id')

            # Защита от слива маржи: если КМ отстает, не генерируем дисконты на объем
            if is_margin_drain and a_type == 'create_discount' and not is_yellow and days_cons is None:
                continue

            # Проверяем, есть ли уже активное правило автопилота для этого условия
            q_filter = Q(unit=unit, is_autopilot=True, date_to__gte=today)
            if is_yellow:
                q_filter &= Q(is_yellow_car=True)
            if days_cons is not None:
                q_filter &= Q(days_consignment_left_lte=days_cons)
            if model_id:
                q_filter &= Q(model_id=model_id)

            existing = PriceCarKmDiscount.objects.filter(q_filter).first()
            if not existing:
                brand = PriceCarBrand.objects.first()
                if model_id:
                    m_obj = AutoruModel.objects.filter(id=model_id).first()
                    if m_obj and m_obj.mark:
                        cand = PriceCarBrand.objects.filter(marks=m_obj.mark).first()
                        if cand:
                            brand = cand
                if brand:
                    PriceCarKmDiscount.objects.create(
                        brand=brand,
                        model_id=model_id,
                        unit=unit,
                        discount_percent=disc_pct,
                        discount_rub=disc_rub,
                        days_consignment_left_lte=days_cons,
                        is_yellow_car=is_yellow,
                        is_key_model=is_key,
                        is_autopilot=True,
                        comment=f"[Автопилот] {rec.get('title')}"[:512],
                        date_from=today,
                        date_to=month_end,
                    )
                    log_actions.append(f"Создано правило автопилота: {rec.get('title')}")

        elif a_type == 'set_tactic' and data.get('tactic'):
            new_tactic = data['tactic']
            if plan.tactic != new_tactic:
                plan.tactic = new_tactic
                plan.save(update_fields=['tactic'])
                log_actions.append(f"Тактика автоматически скорректирована на «{plan.get_tactic_display()}»")

    return log_actions


def get_command_center_full_context(unit: RefUnit, month_start: date) -> dict:
    """Собирает полный контекст для дашборда Центра управления."""
    # Получаем или создаем план ДЦ на месяц
    plan, _ = DcMonthlyPlan.objects.get_or_create(
        unit=unit,
        month=month_start,
        defaults={
            'plan_dc_qty': 0,
            'plan_importer_qty': 0,
            'tactic': DcMonthlyPlan.TACTIC_BALANCED,
            'is_autopilot': False,
        },
    )

    days_info = get_month_days_info(month_start)
    contracts_count = get_contracts_count_for_unit(unit, month_start)
    missed_info = get_missed_deals_info(unit, month_start)

    # Ключевые модели
    key_models_qs = plan.key_models.select_related('model').all()
    key_model_ids = {km.model_id for km in key_models_qs}

    # Анализ склада и желтых авто
    stock_data = get_dc_stock_analytics(unit, key_model_ids)

    # Расчет темпов и прогнозов
    day_now = days_info['day_now']
    days_in_month = days_info['days_in_month']
    days_remaining = days_info['days_remaining']

    speed_daily = round(contracts_count / max(day_now, 1), 2)
    run_rate_forecast = round(speed_daily * days_in_month)

    plan_importer = plan.plan_importer_qty or 0
    plan_dc = plan.plan_dc_qty or 0

    gap_importer = max(plan_importer - contracts_count, 0)
    gap_dc = max(plan_dc - contracts_count, 0)

    required_speed_importer = round(gap_importer / max(days_remaining, 1), 2) if days_remaining > 0 else 0
    required_speed_dc = round(gap_dc / max(days_remaining, 1), 2) if days_remaining > 0 else 0

    # Оценка состояния темпа
    if plan_importer > 0:
        pace_ratio = run_rate_forecast / plan_importer
        if pace_ratio < 0.85:
            pace_status = 'danger'
            pace_status_label = 'Критическое отставание'
        elif pace_ratio < 0.98:
            pace_status = 'warning'
            pace_status_label = 'Ниже плана импортера'
        elif pace_ratio < 1.15:
            pace_status = 'success'
            pace_status_label = 'В темпе плана'
        else:
            pace_status = 'primary'
            pace_status_label = 'Опережение плана'
    else:
        pace_status = 'info'
        pace_status_label = 'План не задан'

    # Финансовые показатели ДЦ за месяц (кумулятивная маржа и выручка)
    financial_fact = get_dc_financial_fact(unit, month_start)
    fact_km = financial_fact.get('fact_km', 0)
    fact_revenue = financial_fact.get('fact_revenue', 0)
    plan_km = plan.plan_km_rub or 0
    plan_revenue = plan.plan_revenue_rub or 0

    km_daily = round(fact_km / max(day_now, 1))
    km_run_rate = round(km_daily * days_in_month) if day_now > 0 else 0
    km_pace_pct = round(km_run_rate / plan_km * 100, 1) if plan_km > 0 else 0
    km_gap = max(plan_km - fact_km, 0)
    required_km_daily = round(km_gap / max(days_remaining, 1)) if days_remaining > 0 else 0

    # Квадрант двухфакторного анализа (Штуки vs Деньги)
    target_plan_qty = max(plan_importer, plan_dc)
    pace_pct_qty = (run_rate_forecast / target_plan_qty * 100) if target_plan_qty > 0 else 100

    if plan_km <= 0:
        quadrant_key = 'no_money_plan'
        quadrant_label = 'План КМ не задан'
        quadrant_badge_class = 'secondary'
        quadrant_desc = 'Контроль ведется только по штукам'
    elif (pace_pct_qty >= 90 or target_plan_qty == 0) and km_pace_pct >= 90:
        quadrant_key = 'both_ok'
        quadrant_label = 'В балансе'
        quadrant_badge_class = 'success'
        quadrant_desc = 'Штуки и маржа выполняются в графике'
    elif pace_pct_qty >= 90 and km_pace_pct < 90:
        quadrant_key = 'margin_drain'
        quadrant_label = 'Слив маржи'
        quadrant_badge_class = 'warning'
        quadrant_desc = 'Штуки идут, но маржа отстает от графика'
    elif pace_pct_qty < 90 and km_pace_pct >= 90:
        quadrant_key = 'money_ok_qty_lag'
        quadrant_label = 'Запас скидки'
        quadrant_badge_class = 'info'
        quadrant_desc = 'Маржа в норме, отставание по объему'
    else:
        quadrant_key = 'both_lag'
        quadrant_label = 'Зона риска'
        quadrant_badge_class = 'danger'
        quadrant_desc = 'Отставание и по штукам, и по марже'

    # Умные рекомендации
    recommendations = generate_smart_recommendations(
        plan=plan,
        contracts_count=contracts_count,
        stock_data=stock_data,
        days_info=days_info,
        missed_info=missed_info,
        financial_fact=financial_fact,
    )

    # Автопилот: автоматическая синхронизация при включенном режиме
    autopilot_logs = []
    if plan.is_autopilot:
        autopilot_logs = sync_autopilot_for_unit(
            unit,
            month_start,
            plan=plan,
            recommendations=recommendations,
            financial_fact=financial_fact,
        )

    # Активные правила дисконтов для этого ДЦ
    today = timezone.now().date()
    discounts_qs = PriceCarKmDiscount.objects.filter(
        Q(unit=unit) | Q(unit__isnull=True),
        date_from__lte=today,
        date_to__gte=today,
    ).select_related('brand', 'model', 'type_sale', 'unit').order_by('-date_from')

    # Каналы продаж
    sales_channels = RefTypeSaleCarsOrganization.objects.all().order_by('name')

    # Бренды для настройки сроков консигнации
    brands = PriceCarBrand.objects.all().order_by('name')

    return {
        'unit': unit,
        'month_start': month_start,
        'plan': plan,
        'days_info': days_info,
        'contracts_count': contracts_count,
        'speed_daily': speed_daily,
        'run_rate_forecast': run_rate_forecast,
        'gap_importer': gap_importer,
        'gap_dc': gap_dc,
        'required_speed_importer': required_speed_importer,
        'required_speed_dc': required_speed_dc,
        'pace_status': pace_status,
        'pace_status_label': pace_status_label,
        'financial_fact': financial_fact,
        'fact_km': fact_km,
        'fact_revenue': fact_revenue,
        'plan_km': plan_km,
        'plan_revenue': plan_revenue,
        'km_daily': km_daily,
        'km_run_rate': km_run_rate,
        'km_pace_pct': km_pace_pct,
        'km_gap': km_gap,
        'required_km_daily': required_km_daily,
        'quadrant_key': quadrant_key,
        'quadrant_label': quadrant_label,
        'quadrant_badge_class': quadrant_badge_class,
        'quadrant_desc': quadrant_desc,
        'fact_km_formatted': format_rubles(fact_km),
        'plan_km_formatted': format_rubles(plan_km),
        'km_run_rate_formatted': format_rubles(km_run_rate),
        'missed_info': missed_info,
        'stock_data': stock_data,
        'key_models': key_models_qs,
        'recommendations': recommendations,
        'autopilot_logs': autopilot_logs,
        'discounts': discounts_qs,
        'sales_channels': sales_channels,
        'brands': brands,
    }


# ==============================================================================
# Excel Импорт и Экспорт
# ==============================================================================

def export_plans_template_excel(month_start: date) -> BytesIO:
    """
    Генерирует Excel файл с шаблоном планов для всех ДЦ на указанный месяц.
    """
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Планы ДЦ {month_start:%m.%Y}"

    headers = [
        'ID ДЦ (не изменять)',
        'Код ДЦ / UIN',
        'Наименование ДЦ',
        'Год',
        'Месяц',
        'План ДЦ (шт.)',
        'План импортера (шт.)',
        'План КМ (руб.)',
        'План выручки (руб.)',
        'Тактика (max_margin / balanced / max_volume)',
    ]
    ws.append(headers)

    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center

    # Заполняем всеми ДЦ
    units = RefUnit.objects.filter(buauto=False).order_by('name')
    existing_plans = {
        p.unit_id: p for p in DcMonthlyPlan.objects.filter(month=month_start)
    }

    row_idx = 2
    for u in units:
        p = existing_plans.get(u.id)
        plan_dc = p.plan_dc_qty if p else 0
        plan_imp = p.plan_importer_qty if p else 0
        plan_km = p.plan_km_rub if p else 0
        plan_rev = p.plan_revenue_rub if p else 0
        tactic = p.tactic if p else 'balanced'

        ws.append([
            u.id,
            u.uin or '',
            u.name,
            month_start.year,
            month_start.month,
            plan_dc,
            plan_imp,
            plan_km,
            plan_rev,
            tactic,
        ])
        row_idx += 1

    # Автоподбор ширины колонок
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def import_plans_from_excel(file_obj, month_start: date, author: Optional[User] = None) -> tuple[int, int, list[str]]:
    """
    Импортирует планы ДЦ и импортера из загруженного Excel файла.
    Поддерживает как расширенный формат (с колонками КМ и выручки в рублях), так и базовый.
    Возвращает: (updated_count, created_count, errors_list).
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_obj, data_only=True)
    ws = wb.active

    updated = 0
    created = 0
    errors = []

    valid_tactics = {
        DcMonthlyPlan.TACTIC_MAX_MARGIN,
        DcMonthlyPlan.TACTIC_BALANCED,
        DcMonthlyPlan.TACTIC_MAX_VOLUME,
    }

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not any(row):
            continue

        unit_id = row[0]
        unit_name = row[2] if len(row) > 2 else ''
        plan_dc_raw = row[5] if len(row) > 5 else 0
        plan_imp_raw = row[6] if len(row) > 6 else 0

        # Распознавание формата колонок (10 колонок с деньгами или 8 старых)
        if len(row) >= 10:
            plan_km_raw = row[7] if len(row) > 7 else 0
            plan_rev_raw = row[8] if len(row) > 8 else 0
            tactic_raw = str(row[9]).strip() if len(row) > 9 and row[9] else 'balanced'
        else:
            plan_km_raw = 0
            plan_rev_raw = 0
            tactic_raw = str(row[7]).strip() if len(row) > 7 and row[7] else 'balanced'

        try:
            unit = None
            if unit_id:
                unit = RefUnit.objects.filter(id=int(unit_id)).first()
            if not unit and unit_name:
                unit = RefUnit.objects.filter(name__iexact=str(unit_name).strip()).first()

            if not unit:
                errors.append(f"Строка {row_idx}: ДЦ не найден (ID: {unit_id}, Имя: {unit_name})")
                continue

            plan_dc = max(int(float(plan_dc_raw or 0)), 0)
            plan_imp = max(int(float(plan_imp_raw or 0)), 0)
            plan_km_rub = max(int(float(plan_km_raw or 0)), 0)
            plan_revenue_rub = max(int(float(plan_rev_raw or 0)), 0)
            tactic = tactic_raw if tactic_raw in valid_tactics else DcMonthlyPlan.TACTIC_BALANCED

            plan_defaults = {
                'plan_dc_qty': plan_dc,
                'plan_importer_qty': plan_imp,
                'tactic': tactic,
                'author': author,
            }
            if len(row) >= 10:
                plan_defaults['plan_km_rub'] = plan_km_rub
                plan_defaults['plan_revenue_rub'] = plan_revenue_rub

            plan_obj, is_created = DcMonthlyPlan.objects.update_or_create(
                unit=unit,
                month=month_start,
                defaults=plan_defaults,
            )

            if is_created:
                created += 1
            else:
                updated += 1

        except Exception as ex:
            errors.append(f"Строка {row_idx}: ошибка обработки ({ex})")

    return updated, created, errors


# ==============================================================================
# Тестовый стенд расчета сделки (Deal Simulator / Test Bench)
# ==============================================================================

def simulate_deal_calculation(
    car_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    type_sale_id: Optional[int] = None,
    tactic_override: Optional[str] = None,
    is_yellow_override: Optional[bool] = None,
    is_key_model_override: Optional[bool] = None,
    sale_price: Optional[int] = None,
    discount_amount: int = 0,
    with_trade_in: bool = False,
    tradein_margin: int = 0,
    with_credit: bool = False,
    opfu_amount: int = 0,
    dop_margin: int = 0,
    work_margin: int = 0,
    insurance_margin: int = 0,
) -> dict:
    """
    Симулятор расчета сделки для тестирования правил ценообразования, дисконтов и тактик.
    Возвращает детальный протокол расчета, КВП, расчетный КМ и статус автосогласования.
    """
    from prices_car.target_cum import calculate_target_cum

    car = None
    if car_id:
        car = RefCarsOrganization.objects.filter(id=int(car_id)).select_related(
            'modification_autoru__model__mark',
            'complectation_autoru',
            'unit',
            'type_sale',
        ).first()

    if not car:
        return {
            'success': False,
            'error': 'Автомобиль не найден. Выберите автомобиль со склада.',
        }

    # Определение ДЦ и канала продаж
    unit = None
    if unit_id:
        unit = RefUnit.objects.filter(id=int(unit_id)).first()
    if not unit:
        unit = car.unit

    type_sale = None
    if type_sale_id:
        type_sale = RefTypeSaleCarsOrganization.objects.filter(id=int(type_sale_id)).first()
    if not type_sale:
        type_sale = car.type_sale

    # Определение тактики
    effective_tactic = tactic_override
    if not effective_tactic and unit:
        month_start = timezone.now().date().replace(day=1)
        plan = DcMonthlyPlan.objects.filter(unit=unit, month=month_start).first()
        if plan:
            effective_tactic = plan.tactic
    if not effective_tactic:
        effective_tactic = DcMonthlyPlan.TACTIC_BALANCED

    tactic_label_map = {
        'max_margin': 'Максимальная маржа (×1.10)',
        'balanced': 'Умеренный / Баланс (×1.00)',
        'max_volume': 'Максимальные штуки (×0.85)',
    }
    tactic_label = tactic_label_map.get(effective_tactic, 'Баланс')

    # Определение признака «желтый»
    is_yellow = is_yellow_override if is_yellow_override is not None else car.is_yellow

    # Определение ключевой модели
    is_key_model = False
    car_model = car.modification_autoru.model if car.modification_autoru else None
    if is_key_model_override is not None:
        is_key_model = bool(is_key_model_override)
    elif unit and car_model:
        month_start = timezone.now().date().replace(day=1)
        is_key_model = DcKeyModel.objects.filter(
            plan__unit=unit,
            plan__month=month_start,
            model=car_model,
        ).exists()

    # Финансовые показатели автомобиля
    rrc_price = int(car.price or 0)
    cost_price = int(car.cost_price or 0)

    if sale_price is not None and int(sale_price) > 0:
        actual_sale_price = int(sale_price)
        actual_discount = max(rrc_price - actual_sale_price, 0)
    else:
        actual_discount = int(discount_amount or 0)
        actual_sale_price = max(rrc_price - actual_discount, 0)

    car_margin = actual_sale_price - cost_price

    # Доходные составляющие сделки
    effective_tradein_margin = int(tradein_margin or 0) if with_trade_in else 0
    effective_opfu = int(opfu_amount or 0) if with_credit else 0
    effective_dop = int(dop_margin or 0)
    effective_work = int(work_margin or 0)
    effective_ins = int(insurance_margin or 0)

    # Итоговый фактический КВП сделки
    total_deal_kvp = (
        car_margin
        + effective_tradein_margin
        + effective_opfu
        + effective_dop
        + effective_work
        + effective_ins
    )

    # 1. Расчет базового АвтоК (Вариант 3)
    target_cum_result = calculate_target_cum(
        car,
        with_trade_in=with_trade_in,
        dc_tactic=effective_tactic,
    )

    base_km = 0
    cum_description = ''
    analog_count = 0
    median_margin_pct = 0.0
    liquidity_mult = 1.0
    tactic_mult = 1.0

    if target_cum_result:
        base_km = int(round(target_cum_result.get('km_min_automatic', 0)))
        cum_description = target_cum_result.get('km_description', '')
        analog_count = target_cum_result.get('analog_count', 0)
        median_margin_pct = target_cum_result.get('median_margin_pct', 0.0)
        liquidity_mult = target_cum_result.get('liquidity_multiplier', 1.0)
        tactic_mult = target_cum_result.get('tactic_multiplier', 1.0)

    # 2. Подбор активного правила дисконта (PriceCarKmDiscount)
    # Временно подставляем тестовые значения в объект автомобиля для поиска
    saved_unit = car.unit
    saved_type_sale = car.type_sale
    car.unit = unit
    car.type_sale = type_sale

    mark = car_model.mark if car_model else None
    brand_car = PriceCarBrand.objects.filter(marks=mark).first() if mark else None

    matched_discount = None
    discount_pct = 0.0
    discount_rub = 0
    discount_comment = ''

    if brand_car:
        matched_discount = car._find_applicable_km_discount(brand_car)
        if matched_discount:
            discount_pct = float(matched_discount.discount_percent or 0.0)
            discount_rub = int(matched_discount.discount_rub or 0)
            discount_comment = matched_discount.comment or ''

    # Восстанавливаем исходные значения объекта
    car.unit = saved_unit
    car.type_sale = saved_type_sale

    # 3. Применение дисконта к базовому КМ (процент + рубли)
    km_after_pct = base_km * (1 + discount_pct / 100) if discount_pct != 0 else base_km
    final_km_rule = int(round(max(km_after_pct - discount_rub, 0)))
    discount_rub_impact = final_km_rule - base_km

    # 4. Проверка условий автосогласования (Вердикт)
    diff = total_deal_kvp - final_km_rule

    if diff >= 0:
        verdict_status = 'approved'
        verdict_badge = 'Согласовано автоматически'
        verdict_class = 'success'
        verdict_msg = (
            f'КВП сделки ({total_deal_kvp:,} ₽) превышает расчетное правило КМ ({final_km_rule:,} ₽) '
            f'на +{diff:,} ₽. Сделка проходит без согласований.'
        ).replace(',', ' ')
    elif diff >= -50000:
        verdict_status = 'director_required'
        verdict_badge = 'Требуется директор ДЦ'
        verdict_class = 'warning'
        verdict_msg = (
            f'КВП сделки ({total_deal_kvp:,} ₽) ниже расчетного правила КМ ({final_km_rule:,} ₽) '
            f'на {abs(diff):,} ₽ (в пределах лимита директора). Требуется подтверждение директора ДЦ.'
        ).replace(',', ' ')
    else:
        verdict_status = 'uk_required'
        verdict_badge = 'Требуется согласование УК'
        verdict_class = 'danger'
        verdict_msg = (
            f'Существенное отклонение КВП ({diff:,} ₽ от правила {final_km_rule:,} ₽). '
            f'Сделка блокируется и требует прямого согласования Управляющей Компании.'
        ).replace(',', ' ')

    # 5. Пошаговый протокол расчета («Рентген»)
    disc_val_parts = []
    if discount_pct:
        disc_val_parts.append(f'{discount_pct}%')
    if discount_rub:
        disc_val_parts.append(f'-{discount_rub:,} ₽'.replace(',', ' '))
    disc_val_str = ' и '.join(disc_val_parts) if disc_val_parts else '0%'

    steps = [
        {
            'step': 1,
            'title': 'Целевой КМ аналогов (АвтоК)',
            'value': f'{base_km:,} ₽'.replace(',', ' '),
            'formula': f'Себестоимость ({cost_price:,} ₽) × Медиана ({median_margin_pct}%) × Ликвидность (×{liquidity_mult}) × Тактика {tactic_label} (×{tactic_mult})'.replace(',', ' '),
            'comment': cum_description,
        },
        {
            'step': 2,
            'title': 'Правило дисконта ДЦ (Вариант 6)',
            'value': disc_val_str,
            'formula': f'Специфичность: ДЦ={unit.name if unit else "Все"}, Канал={type_sale.name if type_sale else "Любой"}, Желтый={"Да" if is_yellow else "Нет"}, Ключевая={"Да" if is_key_model else "Нет"}',
            'comment': f'Найдено правило ID {matched_discount.id}: {discount_comment}' if matched_discount else 'Индивидуальные правила дисконта не найдены (дисконт 0%)',
        },
        {
            'step': 3,
            'title': 'Итоговый расчетный КМ (Правило сделки)',
            'value': f'{final_km_rule:,} ₽'.replace(',', ' '),
            'formula': f'Базовый КМ ({base_km:,} ₽) ' + (f'× (1 + {discount_pct}%) ' if discount_pct else '') + (f'- {discount_rub:,} ₽ ' if discount_rub else '') + f'= {final_km_rule:,} ₽'.replace(',', ' '),
            'comment': f'Влияние дисконта: {discount_rub_impact:,} ₽'.replace(',', ' ') if discount_rub_impact else 'Без изменения',
        },
        {
            'step': 4,
            'title': 'Фактический КВП сделки',
            'value': f'{total_deal_kvp:,} ₽'.replace(',', ' '),
            'formula': f'Маржа авто ({car_margin:,} ₽) + Trade-in ({effective_tradein_margin:,} ₽) + ОПФУ ({effective_opfu:,} ₽) + Допы ({effective_dop:,} ₽) + З/Ч ({effective_work + effective_ins:,} ₽)'.replace(',', ' '),
            'comment': f'Цена продажи: {actual_sale_price:,} ₽ (скидка {actual_discount:,} ₽ от РРЦ)'.replace(',', ' '),
        },
    ]

    return {
        'success': True,
        'car': {
            'id': car.id,
            'vin': car.vin,
            'name': f'{car.mark} {car.model} {car.modification}',
            'rrc_price': rrc_price,
            'cost_price': cost_price,
            'days_in_stok': car.days_in_stok,
            'is_yellow': is_yellow,
        },
        'parameters': {
            'unit_name': unit.name if unit else '—',
            'type_sale_name': type_sale.name if type_sale else '—',
            'tactic': effective_tactic,
            'tactic_label': tactic_label,
            'is_yellow': is_yellow,
            'is_key_model': is_key_model,
            'with_trade_in': with_trade_in,
            'with_credit': with_credit,
            'actual_sale_price': actual_sale_price,
            'actual_discount': actual_discount,
        },
        'breakdown': {
            'car_margin': car_margin,
            'tradein_margin': effective_tradein_margin,
            'opfu_amount': effective_opfu,
            'dop_margin': effective_dop,
            'other_margin': effective_work + effective_ins,
            'total_deal_kvp': total_deal_kvp,
            'base_km': base_km,
            'discount_percent': discount_pct,
            'discount_rub_impact': discount_rub_impact,
            'final_km_rule': final_km_rule,
            'diff': diff,
        },
        'verdict': {
            'status': verdict_status,
            'badge': verdict_badge,
            'class': verdict_class,
            'message': verdict_msg,
        },
        'steps': steps,
    }


def compute_single_dc_showcase_data(
    unit: RefUnit,
    month_start: date,
    plan: Optional[DcMonthlyPlan] = None,
    days_info: Optional[dict] = None,
    key_models: Optional[set[int]] = None,
    autopilot_rules_count: Optional[int] = None,
) -> dict:
    """
    Рассчитывает полный набор аналитических метрик дилерского центра за указанный месяц
    для записи в витрину данных DcCommandCenterShowcase.
    """
    if days_info is None:
        days_info = get_month_days_info(month_start)
    day_now = days_info['day_now']
    days_in_month = days_info['days_in_month']

    if plan is None:
        plan = DcMonthlyPlan.objects.filter(unit=unit, month=month_start).first()

    if key_models is None:
        key_models = set(
            DcKeyModel.objects.filter(plan__unit=unit, plan__month=month_start)
            .values_list('model_id', flat=True)
        )

    if autopilot_rules_count is None:
        autopilot_rules_count = PriceCarKmDiscount.objects.filter(
            unit=unit,
            is_autopilot=True,
            date_to__gte=days_info['today'],
        ).count()

    plan_dc = plan.plan_dc_qty if plan else 0
    plan_importer = plan.plan_importer_qty if plan else 0
    target_plan = max(plan_dc, plan_importer)

    is_autopilot = bool(plan and plan.is_autopilot)
    tactic = plan.tactic if plan else DcMonthlyPlan.TACTIC_BALANCED
    tactic_label = dict(DcMonthlyPlan.TACTIC_CHOICES).get(tactic, 'Сбалансированная')

    contracts_count = get_contracts_count_for_unit(unit, month_start)
    run_rate = round(contracts_count / day_now * days_in_month, 1) if day_now > 0 else 0.0
    pace_pct = round(run_rate / target_plan * 100, 1) if target_plan > 0 else 0.0
    gap = max(target_plan - contracts_count, 0)

    if target_plan == 0:
        pace_status = 'no_plan'
        pace_label = 'План не задан'
        pace_class = 'secondary'
        pace_delta_label = 'нет плана'
    elif pace_pct < 90:
        pace_status = 'lagging'
        pace_label = 'Отстает'
        pace_class = 'danger'
        pace_delta_label = f'-{int(100 - pace_pct)}%'
    elif pace_pct <= 110:
        pace_status = 'on_track'
        pace_label = 'В графике'
        pace_class = 'success'
        pace_delta_label = 'в норме'
    else:
        pace_status = 'ahead'
        pace_label = 'Опережает'
        pace_class = 'info'
        pace_delta_label = f'+{int(pace_pct - 100)}%'

    # 2. Финансовый факт и темп кумулятивной маржи (КМ в рублях)
    financial_fact = get_dc_financial_fact(unit, month_start)
    fact_km = financial_fact.get('fact_km', 0)
    fact_revenue = financial_fact.get('fact_revenue', 0)
    plan_km_rub = plan.plan_km_rub if plan else 0
    plan_revenue_rub = plan.plan_revenue_rub if plan else 0

    km_run_rate = round(fact_km / day_now * days_in_month) if day_now > 0 else 0
    km_pace_pct = round(km_run_rate / plan_km_rub * 100, 1) if plan_km_rub > 0 else 0.0

    # Квадрант двухфакторного баланса (Штуки vs Деньги)
    if plan_km_rub <= 0:
        quadrant_key = 'no_money_plan'
        quadrant_label = 'План КМ не задан'
        quadrant_badge_class = 'secondary'
        quadrant_desc = 'Контроль ведется только по штукам'
    elif (pace_pct >= 90 or target_plan == 0) and km_pace_pct >= 90:
        quadrant_key = 'both_ok'
        quadrant_label = 'В балансе'
        quadrant_badge_class = 'success'
        quadrant_desc = 'Штуки и маржа выполняются в графике'
    elif pace_pct >= 90 and km_pace_pct < 90:
        quadrant_key = 'margin_drain'
        quadrant_label = 'Слив маржи'
        quadrant_badge_class = 'warning'
        quadrant_desc = 'Штуки идут, но маржа отстает от графика'
    elif pace_pct < 90 and km_pace_pct >= 90:
        quadrant_key = 'money_ok_qty_lag'
        quadrant_label = 'Запас скидки'
        quadrant_badge_class = 'info'
        quadrant_desc = 'Маржа в норме, отставание по объему'
    else:
        quadrant_key = 'both_lag'
        quadrant_label = 'Зона риска'
        quadrant_badge_class = 'danger'
        quadrant_desc = 'Отставание и по штукам, и по марже'

    # Склад и риски
    stock_data = get_dc_stock_analytics(unit, key_models)
    missed_info = get_missed_deals_info(unit, month_start)

    # Рекомендации Smart Advisor
    recs = []
    if plan:
        recs = generate_smart_recommendations(
            plan=plan,
            contracts_count=contracts_count,
            stock_data=stock_data,
            days_info=days_info,
            missed_info=missed_info,
            financial_fact=financial_fact,
        )
    recs_count = len(recs)
    has_recs = recs_count > 0

    needs_attention = (
        pace_status == 'lagging'
        or quadrant_key in ('margin_drain', 'both_lag')
        or has_recs
        or stock_data['consignment_overdue_count'] > 0
        or stock_data['yellow_cars_count'] >= 5
    )

    top_rec = recs[0] if recs else {}
    top_rec_title = top_rec.get('title', '')
    top_rec_badge = top_rec.get('badge', '')
    top_rec_badge_class = top_rec.get('badge_class', '')

    return {
        'plan_dc_qty': plan_dc,
        'plan_importer_qty': plan_importer,
        'target_plan': target_plan,
        'contracts_count': contracts_count,
        'run_rate': run_rate,
        'pace_pct': pace_pct,
        'pace_status': pace_status,
        'pace_label': pace_label,
        'pace_class': pace_class,
        'pace_delta_label': pace_delta_label,
        'gap': gap,
        'plan_km_rub': plan_km_rub,
        'plan_revenue_rub': plan_revenue_rub,
        'fact_km': fact_km,
        'fact_revenue': fact_revenue,
        'km_run_rate': km_run_rate,
        'km_pace_pct': km_pace_pct,
        'quadrant_key': quadrant_key,
        'quadrant_label': quadrant_label,
        'quadrant_badge_class': quadrant_badge_class,
        'quadrant_desc': quadrant_desc,
        'stock_total': stock_data['total_count'],
        'yellow_count': stock_data['yellow_cars_count'],
        'consignment_overdue': stock_data['consignment_overdue_count'],
        'consignment_warning': stock_data['consignment_warning_count'],
        'missed_count': missed_info['total_missed'],
        'is_autopilot': is_autopilot,
        'autopilot_rules_count': autopilot_rules_count,
        'tactic': tactic,
        'tactic_label': tactic_label,
        'recs_count': recs_count,
        'has_recs': has_recs,
        'needs_attention': needs_attention,
        'top_rec_title': top_rec_title,
        'top_rec_badge': top_rec_badge,
        'top_rec_badge_class': top_rec_badge_class,
        'recommendations_json': recs,
    }


def rebuild_dc_command_center_showcase(
    unit: Optional[RefUnit] = None,
    month_start: Optional[date] = None,
) -> int:
    """
    Пересчитывает и сохраняет аналитическую витрину DcCommandCenterShowcase
    для одного ДЦ или всей сети дилерских центров за месяц.
    Возвращает количество обновленных записей витрины.
    """
    if month_start is None:
        month_start = get_first_day_of_month()

    days_info = get_month_days_info(month_start)

    if unit is not None:
        data = compute_single_dc_showcase_data(
            unit=unit,
            month_start=month_start,
            days_info=days_info,
        )
        DcCommandCenterShowcase.objects.update_or_create(
            unit=unit,
            month=month_start,
            defaults=data,
        )
        return 1

    all_units = list(
        RefUnit.objects.filter(buauto=False)
        .select_related('city')
        .order_by('city__name', 'name')
    )

    plans_by_unit = {
        p.unit_id: p
        for p in DcMonthlyPlan.objects.filter(month=month_start).select_related('unit')
    }

    key_models_by_unit: dict[int, set[int]] = {}
    for km in DcKeyModel.objects.filter(plan__month=month_start):
        key_models_by_unit.setdefault(km.plan.unit_id, set()).add(km.model_id)

    autopilot_active_rules_map = dict(
        PriceCarKmDiscount.objects.filter(
            is_autopilot=True,
            date_to__gte=days_info['today'],
        ).values('unit_id').annotate(cnt=Count('id')).values_list('unit_id', 'cnt')
    )

    updated_count = 0
    for u in all_units:
        data = compute_single_dc_showcase_data(
            unit=u,
            month_start=month_start,
            plan=plans_by_unit.get(u.id),
            days_info=days_info,
            key_models=key_models_by_unit.get(u.id, set()),
            autopilot_rules_count=autopilot_active_rules_map.get(u.id, 0),
        )
        DcCommandCenterShowcase.objects.update_or_create(
            unit=u,
            month=month_start,
            defaults=data,
        )
        updated_count += 1

    return updated_count


def get_all_units_command_center_overview(
    month_start: date,
    filters: Optional[dict] = None,
) -> dict:
    """
    Формирует структурированные аналитические данные по всем дилерским центрам
    из материализованной витрины данных DcCommandCenterShowcase.
    Обеспечивает мгновенную отдачу страницы (<20 мс) без повторного расчёта.
    Группировка по городам, расчет темпа (идут/отстают), статуса автопилота,
    рекомендаций Smart Advisor, складских рисков и глобальных KPI сети.
    """
    filters = filters or {}
    days_info = get_month_days_info(month_start)
    all_cities = RefCity.objects.all().order_by('name')

    showcase_qs = (
        DcCommandCenterShowcase.objects.filter(month=month_start)
        .select_related('unit__city')
        .order_by('unit__city__name', 'unit__name')
    )

    # Если витрина за этот месяц ещё не была собрана — собираем на лету
    if not showcase_qs.exists():
        rebuild_dc_command_center_showcase(month_start=month_start)
        showcase_qs = (
            DcCommandCenterShowcase.objects.filter(month=month_start)
            .select_related('unit__city')
            .order_by('unit__city__name', 'unit__name')
        )

    showcase_list = list(showcase_qs)
    last_updated_at = max((s.updated_at for s in showcase_list), default=None)

    raw_units_data = []
    for s in showcase_list:
        unit = s.unit
        city_id = unit.city_id or 0
        city_name = unit.city.name if unit.city else 'Без города'
        recs = s.recommendations_json or []

        raw_units_data.append({
            'unit': unit,
            'unit_id': unit.id,
            'unit_name': unit.name,
            'city_id': city_id,
            'city_name': city_name,
            'plan': None,
            'plan_dc': s.plan_dc_qty,
            'plan_importer': s.plan_importer_qty,
            'target_plan': s.target_plan,
            'plan_km_rub': s.plan_km_rub,
            'plan_revenue_rub': s.plan_revenue_rub,
            'fact_km': s.fact_km,
            'fact_revenue': s.fact_revenue,
            'km_run_rate': s.km_run_rate,
            'km_pace_pct': s.km_pace_pct,
            'fact_km_formatted': format_rubles(s.fact_km),
            'plan_km_formatted': format_rubles(s.plan_km_rub),
            'km_run_rate_formatted': format_rubles(s.km_run_rate),
            'fact_revenue_formatted': format_rubles(s.fact_revenue),
            'plan_revenue_formatted': format_rubles(s.plan_revenue_rub),
            'quadrant_key': s.quadrant_key,
            'quadrant_label': s.quadrant_label,
            'quadrant_badge_class': s.quadrant_badge_class,
            'quadrant_desc': s.quadrant_desc,
            'is_autopilot': s.is_autopilot,
            'autopilot_rules_count': s.autopilot_rules_count,
            'tactic': s.tactic,
            'tactic_label': s.tactic_label,
            'contracts_count': s.contracts_count,
            'run_rate': round(s.run_rate),
            'pace_pct': s.pace_pct,
            'pace_status': s.pace_status,
            'pace_label': s.pace_label,
            'pace_class': s.pace_class,
            'pace_delta_label': s.pace_delta_label,
            'gap': s.gap,
            'stock_total': s.stock_total,
            'yellow_count': s.yellow_count,
            'consignment_overdue': s.consignment_overdue,
            'consignment_warning': s.consignment_warning,
            'recs': recs,
            'recs_count': s.recs_count,
            'has_recs': s.has_recs,
            'top_rec': recs[0] if recs else None,
            'needs_attention': s.needs_attention,
            'missed_count': s.missed_count,
            'updated_at': s.updated_at,
        })

    # 3. Глобальные счетчики сети (до применения фильтров отображения)
    total_fact_km = sum(u['fact_km'] for u in raw_units_data)
    total_plan_km = sum(u['plan_km_rub'] for u in raw_units_data)
    total_km_run_rate = sum(u['km_run_rate'] for u in raw_units_data)
    total_km_pace = round(total_km_run_rate / total_plan_km * 100, 1) if total_plan_km > 0 else 0

    network_stats = {
        'total_units': len(raw_units_data),
        'autopilot_enabled_count': sum(1 for u in raw_units_data if u['is_autopilot']),
        'autopilot_disabled_count': sum(1 for u in raw_units_data if not u['is_autopilot']),
        'lagging_count': sum(1 for u in raw_units_data if u['pace_status'] == 'lagging'),
        'on_track_count': sum(1 for u in raw_units_data if u['pace_status'] == 'on_track'),
        'ahead_count': sum(1 for u in raw_units_data if u['pace_status'] == 'ahead'),
        'both_ok_count': sum(1 for u in raw_units_data if u['quadrant_key'] == 'both_ok'),
        'margin_drain_count': sum(1 for u in raw_units_data if u['quadrant_key'] == 'margin_drain'),
        'money_ok_qty_lag_count': sum(1 for u in raw_units_data if u['quadrant_key'] == 'money_ok_qty_lag'),
        'both_lag_count': sum(1 for u in raw_units_data if u['quadrant_key'] == 'both_lag'),
        'no_money_plan_count': sum(1 for u in raw_units_data if u['quadrant_key'] == 'no_money_plan'),
        'total_fact_km': total_fact_km,
        'total_plan_km': total_plan_km,
        'total_km_run_rate': total_km_run_rate,
        'total_km_pace': total_km_pace,
        'total_fact_km_formatted': format_rubles(total_fact_km),
        'total_plan_km_formatted': format_rubles(total_plan_km),
        'total_km_run_rate_formatted': format_rubles(total_km_run_rate),
        'has_recs_count': sum(1 for u in raw_units_data if u['has_recs']),
        'needs_attention_count': sum(1 for u in raw_units_data if u['needs_attention']),
        'total_stock': sum(u['stock_total'] for u in raw_units_data),
        'total_contracts': sum(u['contracts_count'] for u in raw_units_data),
        'total_yellow': sum(u['yellow_count'] for u in raw_units_data),
        'total_consignment_overdue': sum(u['consignment_overdue'] for u in raw_units_data),
    }

    # 4. Применение пользовательских фильтров
    filtered_units = raw_units_data

    # Фильтр по квадранту баланса (Штуки vs Деньги)
    req_quadrant = filters.get('quadrant')
    if req_quadrant and req_quadrant != 'all':
        filtered_units = [u for u in filtered_units if u['quadrant_key'] == req_quadrant]

    # Фильтр по городу
    req_city = filters.get('city_id')
    if req_city and req_city != 'all':
        try:
            req_city_int = int(req_city)
            filtered_units = [u for u in filtered_units if u['city_id'] == req_city_int]
        except ValueError:
            pass

    # Фильтр по автопилоту
    req_autopilot = filters.get('autopilot')
    if req_autopilot == 'enabled':
        filtered_units = [u for u in filtered_units if u['is_autopilot']]
    elif req_autopilot == 'disabled':
        filtered_units = [u for u in filtered_units if not u['is_autopilot']]

    # Фильтр по рекомендациям
    req_recs = filters.get('recommendations')
    if req_recs == 'has_recs':
        filtered_units = [u for u in filtered_units if u['has_recs']]
    elif req_recs == 'no_recs':
        filtered_units = [u for u in filtered_units if not u['has_recs']]
    elif req_recs == 'attention':
        filtered_units = [u for u in filtered_units if u['needs_attention']]

    # Фильтр по темпу
    req_pace = filters.get('pace')
    if req_pace and req_pace != 'all':
        filtered_units = [u for u in filtered_units if u['pace_status'] == req_pace]

    # Текстовый поиск
    req_search = (filters.get('search') or '').strip().lower()
    if req_search:
        filtered_units = [
            u for u in filtered_units
            if req_search in u['unit_name'].lower() or req_search in u['city_name'].lower()
        ]

    # 5. Группировка отфильтрованных ДЦ по городам
    cities_dict: dict[int, dict] = {}
    for item in filtered_units:
        c_id = item['city_id']
        c_name = item['city_name']
        if c_id not in cities_dict:
            cities_dict[c_id] = {
                'city_id': c_id,
                'city_name': c_name,
                'units': [],
                'total_units': 0,
                'autopilot_count': 0,
                'lagging_count': 0,
                'on_track_count': 0,
                'has_recs_count': 0,
                'total_stock': 0,
                'total_contracts': 0,
            }
        c_data = cities_dict[c_id]
        c_data['units'].append(item)
        c_data['total_units'] += 1
        if item['is_autopilot']:
            c_data['autopilot_count'] += 1
        if item['pace_status'] == 'lagging':
            c_data['lagging_count'] += 1
        elif item['pace_status'] in ('on_track', 'ahead'):
            c_data['on_track_count'] += 1
        if item['has_recs']:
            c_data['has_recs_count'] += 1
        c_data['total_stock'] += item['stock_total']
        c_data['total_contracts'] += item['contracts_count']

    # Сортируем города по названию (города с ДЦ идут в начале)
    grouped_cities = sorted(cities_dict.values(), key=lambda x: x['city_name'])

    return {
        'grouped_cities': grouped_cities,
        'filtered_units_count': len(filtered_units),
        'network_stats': network_stats,
        'all_cities': all_cities,
        'days_info': days_info,
        'filters': filters,
        'last_updated_at': last_updated_at,
    }


