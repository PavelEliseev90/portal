"""Пошаговый разбор расчёта минимального КМ (cumulative_data) для UI."""
from datetime import datetime, timedelta

from django.db.models import Count, Sum

from prices_car.km_car import TYPE_KM_LABELS, resolve_km_from_cumulative


def _fmt_rub(value):
    if value is None:
        return '—'
    try:
        return '{:,}'.format(int(round(float(value)))).replace(',', ' ') + ' ₽'
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value, digits=2):
    if value is None:
        return '—'
    try:
        return ('{:.' + str(digits) + 'f}').format(float(value)).replace('.', ',') + '%'
    except (TypeError, ValueError):
        return str(value)


def _step(label, value='', formula='', source='', highlight=False):
    return {
        'label': label,
        'value': value,
        'formula': formula,
        'source': source,
        'highlight': highlight,
    }


def _method_block(
    method_id, title, result_rub, steps, description,
    applicable, reason='', reference_only=False,
):
    return {
        'id': method_id,
        'title': title,
        'result_rub': result_rub,
        'result_display': _fmt_rub(result_rub),
        'steps': steps,
        'description': description,
        'applicable': applicable,
        'not_selected_reason': reason,
        'reference_only': reference_only,
    }


def _winner_reason(type_km, with_trade_in=False):
    if type_km == 3:
        return 'На автомобиле задан ручной минимальный КМ — он имеет наивысший приоритет.'
    if type_km == 4:
        return 'Применено специальное условие ГК.'
    if type_km == 5:
        if with_trade_in:
            return 'Метод «АвтоК с trade-in» — по детальному расчёту КП применён показатель trade-in.'
        return 'Метод «АвтоК» (целевая кумулятивная маржа по аналогам).'
    if type_km == 1:
        return 'АвтоК и спец. условия не применены — используется план на месяц (норма бренда).'
    return 'Недостаточно данных для расчёта (нет модификации Auto.ru).'


def get_km_rule_total(cumulative_data, car=None, calc=None, with_trade_in=None):
    """Итог по правилу с учётом приоритетов и trade-in из детального расчёта КП."""
    if not cumulative_data:
        return None
    if with_trade_in is None and calc is not None:
        from prices_car.km_raschet import calculation_has_applied_trade_in
        with_trade_in = calculation_has_applied_trade_in(calc)

    total, _ = resolve_km_from_cumulative(cumulative_data, car, with_trade_in=with_trade_in)
    return int(total) if total else None


def build_km_calculation_breakdown(car, calc=None, show_reference_methods=False):
    """
    Разбор cumulative_data для UI.
    calc — КП (для определения trade-in по детальному расчёту).
    show_reference_methods — показывать «Авто» и «Авто+» (директор новых всех ДЦ).
    """
    if car is None or car.modification_autoru is None:
        return {
            'available': False,
            'type_km': 0,
            'type_km_label': TYPE_KM_LABELS[0],
            'winner': None,
            'priority_note': 'Нет привязки к модификации Auto.ru — расчёт КМ недоступен.',
            'methods': [],
            'irc': None,
            'brand_km': None,
            'stage_price': None,
            'car_price': None,
            'with_trade_in': False,
        }

    from prices_car.brand_resolve import resolve_price_car_brand_for_car
    from prices_car.km_raschet import calculation_has_applied_trade_in
    from prices_car.models import PriceCarStageKM
    from refs.models import RefCarsOrganization

    cumulative = car.cumulative_data()
    with_trade_in = calculation_has_applied_trade_in(calc) if calc else False
    winner_amount, type_km = resolve_km_from_cumulative(
        cumulative, car, with_trade_in=with_trade_in,
    )

    brand_car = resolve_price_car_brand_for_car(car)
    brand_km_obj = cumulative.get('brand_km')
    stage_km = PriceCarStageKM.objects.filter(stage=car.stage_price).last()
    irc = cumulative.get('irc')
    if irc is None and stage_km:
        irc = stage_km.km_index

    mark_name = car.modification_autoru.model.mark.name
    price = car.price or 0
    methods = []

    # --- План на месяц (fallback) ---
    km_plan = 0
    desc_plan = ''
    steps_plan = []
    if brand_km_obj is not None and stage_km is not None:
        stock = RefCarsOrganization.objects.filter(
            modification_autoru__model__mark=car.modification_autoru.model.mark,
            is_new=True,
        ).exclude(quantity=0).exclude(price=0).aggregate(
            Sum('price'), Count('id'),
        )
        stock_sum = stock['price__sum']
        stock_count = stock['id__count'] or 0
        brand_km_val = brand_km_obj.km

        steps_plan.append(_step('Норма КМ бренда на месяц', _fmt_rub(brand_km_val), source='BrandKM'))
        steps_plan.append(_step(
            'Период нормы',
            brand_km_obj.month.strftime('%m.%Y') if brand_km_obj.month else '—',
            source='BrandKM',
        ))
        steps_plan.append(_step('ИРЦ этапа УС', str(irc), source='PriceCarStageKM'))
        steps_plan.append(_step('РРЦ автомобиля', _fmt_rub(price), source='Карточка АМ'))

        if stock_sum and stock_count > 0:
            avg_price = stock_sum / stock_count
            km_pct = brand_km_val / avg_price * 100
            km_stage_pct = round(km_pct, 2) * float(irc)
            km_plan = price * km_stage_pct / 100
            steps_plan.append(_step('Сток марки (новые АМ с ценой)', '{} шт.'.format(stock_count)))
            steps_plan.append(_step('Сумма РРЦ стока', _fmt_rub(stock_sum)))
            steps_plan.append(_step('Средняя РРЦ стока', _fmt_rub(avg_price)))
            steps_plan.append(_step('КМ % от средней цены', _fmt_pct(km_pct)))
            steps_plan.append(_step('КМ % с учётом ИРЦ', _fmt_pct(km_stage_pct)))
            desc_plan = (
                'План на месяц {mark} — норма бренда и сток марки ({cnt} шт.).'
            ).format(mark=mark_name, cnt=stock_count)
        else:
            km_stage_pct = round(float(brand_km_val), 2) * float(irc)
            km_plan = price * km_stage_pct / 100 if price else brand_km_val
            if km_plan == 0:
                km_plan = brand_km_val
            steps_plan.append(_step('Сток марки', 'нет данных'))
            steps_plan.append(_step('КМ (без стока)', _fmt_rub(brand_km_val)))
            desc_plan = 'План на месяц {mark} (без стока марки).'.format(mark=mark_name)

        steps_plan.append(_step('Итого план на месяц', _fmt_rub(km_plan), highlight=True))

    auto_data = cumulative.get('automatic', {})
    if auto_data:
        km_plan = auto_data.get('km_min_automatic', km_plan)
        desc_plan = auto_data.get('km_description', desc_plan)

    methods.append(_method_block(
        1, 'План на месяц', km_plan, steps_plan, desc_plan,
        applicable=type_km == 1,
        reason='' if type_km == 1 else 'Не выбран — есть метод с более высоким приоритетом',
    ))

    # --- Справочно: Авто / Авто+ (только для УК всех ДЦ) ---
    if show_reference_methods:
        km1 = km_plan
        steps1 = list(steps_plan)
        methods.append(_method_block(
            101, 'Авто (справочно: норма бренда × сток)', km1, steps1,
            cumulative.get('automatic', {}).get('km_description', ''),
            applicable=False,
            reason='Справочный метод, не участвует в итоге',
            reference_only=True,
        ))

        km2 = 0
        desc2 = ''
        steps2 = []
        from powerbi.models import Cumulative

        dt_start = datetime.now().replace(day=1, hour=0, second=1) - timedelta(days=1)
        dt_start = dt_start.replace(day=1, hour=0, second=1)
        cum_qs = Cumulative.objects.filter(
            TipProdazhi='Розница',
            DataProdazhi__gte=dt_start,
            DataProdazhi__lte=datetime.now(),
            Marka=mark_name.upper(),
            ListOtsenkiVIN=None,
        ).exclude(RRTS='0')
        cum_count = cum_qs.count()
        steps2.append(_step('Период', '{} — {}'.format(
            dt_start.strftime('%d.%m.%Y'), datetime.now().strftime('%d.%m.%Y'),
        )))
        steps2.append(_step('Продаж за период', str(cum_count)))

        if cum_count > 0 and stage_km is not None:
            cum_sum = cum_aggregate = 0
            for cum_info in cum_qs:
                cum_data = sum(float(getattr(cum_info, f, None) or 0) for f in (
                    'SummaRabot', 'ValovayaPribylZChShiny', 'ValovayaPribylZCh',
                    'SummaTreydInPoPlanu', 'VPOPFU', 'SummaMarzhiBezNDS', 'SummaGosreg',
                ))
                cum_sum += cum_data
                cum_aggregate += float(cum_info.RRTS or 0)
            km_sale = cum_sum / cum_count
            avg_rrc = cum_aggregate / cum_count
            km_pct2 = km_sale / avg_rrc * 100 if avg_rrc else 0
            km_stage_pct2 = round(km_pct2, 2) * float(irc)
            km2 = price * km_stage_pct2 / 100 or km_sale
            steps2.append(_step('Средняя маржа на сделку', _fmt_rub(km_sale)))
            steps2.append(_step('Итого (справочно)', _fmt_rub(km2), highlight=True))
            desc2 = 'Факт продаж за месяц по бренду {mark}.'.format(mark=mark_name)

        auto2 = cumulative.get('automatic_2', {})
        if auto2:
            km2 = auto2.get('km_min_automatic', km2)
            desc2 = auto2.get('km_description', desc2)

        methods.append(_method_block(
            102, 'Авто+ (справочно: факт продаж)', km2, steps2, desc2,
            applicable=False,
            reason='Справочный метод, не участвует в итоге',
            reference_only=True,
        ))

    # --- АвтоК ---
    def _build_target_cum_steps(auto_k_block, title_suffix):
        steps_local = []
        km_val = 0
        desc_local = ''
        if auto_k_block:
            km_val = auto_k_block.get('km_min_automatic', 0)
            steps_local.append(_step('Сегмент сделок', title_suffix, source='Cumulative'))
            steps_local.append(_step('Себестоимость', _fmt_rub(auto_k_block.get('car_cost'))))
            steps_local.append(_step('Период анализа', '60 дней'))
            steps_local.append(_step('Сегмент поиска', auto_k_block.get('search_label') or '—'))
            steps_local.append(_step('Сделок после очистки', str(auto_k_block.get('analog_count') or 0)))
            if auto_k_block.get('median_margin_pct') is not None:
                steps_local.append(_step('Медианная маржа', _fmt_pct(auto_k_block.get('median_margin_pct'))))
            steps_local.append(_step('Дней на складе', str(auto_k_block.get('days_in_stock') or 0)))
            if auto_k_block.get('liquidity_ratio') is not None:
                steps_local.append(_step('Коэфф. ликвидности', str(auto_k_block.get('liquidity_ratio'))))
            steps_local.append(_step(
                'Корректировка ликвидности',
                auto_k_block.get('liquidity_label') or '—',
            ))
            steps_local.append(_step('Итого мин. КМ', _fmt_rub(km_val), highlight=True))
            desc_local = auto_k_block.get('km_description', '')
            if auto_k_block.get('fallback'):
                steps_local.insert(2, _step('Источник', 'План на месяц (fallback внутри АвтоК)', source='BrandKM'))
        else:
            steps_local.append(_step('АвтоК', 'не рассчитан'))
            desc_local = 'Недостаточно данных для АвтоК.'
        return km_val, steps_local, desc_local

    auto_k = cumulative.get('automatic_k') or {}
    auto_k_ti = cumulative.get('automatic_k_tradein') or {}
    km_k, steps_k, desc_k = _build_target_cum_steps(auto_k, 'без trade-in')
    km_k_ti, steps_k_ti, desc_k_ti = _build_target_cum_steps(auto_k_ti, 'с trade-in')

    autok_applicable = type_km == 5 and not with_trade_in
    autok_ti_applicable = type_km == 5 and with_trade_in

    methods.append(_method_block(
        5, 'АвтоК без trade-in', km_k, steps_k, desc_k,
        applicable=autok_applicable,
        reason='' if autok_applicable else (
            'В КП применён trade-in — используется вариант с trade-in'
            if with_trade_in and type_km == 5 else 'Не выбран как итоговый метод'
        ),
    ))
    methods.append(_method_block(
        51, 'АвтоК с trade-in', km_k_ti, steps_k_ti, desc_k_ti,
        applicable=autok_ti_applicable,
        reason='' if autok_ti_applicable else (
            'В КП нет применённого показателя trade-in'
            if not with_trade_in else 'Не выбран как итоговый метод'
        ),
    ))

    # --- Спец. условие ---
    km4 = 0
    desc4 = ''
    steps4 = []
    auto3 = cumulative.get('automatic_3')
    km_base = max(km_plan or 0, km_k or 0, km_k_ti or 0)
    steps4.append(_step('База для дисконта', _fmt_rub(km_base), formula='max(план, АвтоК)'))

    if auto3:
        km4 = auto3.get('km_min_automatic', 0)
        steps4.append(_step('Процент спец. условия', _fmt_pct(auto3.get('discount_percent', 0), 0)))
        steps4.append(_step('Итого', _fmt_rub(km4), highlight=True))
        desc4 = auto3.get('km_description', '')
        reason4 = '' if type_km == 4 else 'Не выбран как итоговый метод'
    else:
        steps4.append(_step('Спец. условие', 'не найдено'))
        desc4 = 'Дисконт КМ по бренду/модели не применяется.'
        reason4 = 'Дисконт не найден'

    methods.append(_method_block(
        4, 'Спец. условие ГК', km4, steps4, desc4,
        applicable=type_km == 4,
        reason=reason4,
    ))

    # --- Ручной ---
    min_km = car.min_km or 0
    steps3 = []
    if min_km:
        steps3.append(_step('Ручной мин. КМ', _fmt_rub(min_km), source='min_km'))
        steps3.append(_step('Итого', _fmt_rub(min_km), highlight=True))
        desc3 = cumulative.get('custom', {}).get('km_description', '')
    else:
        steps3.append(_step('Ручной КМ', 'не задан'))
        desc3 = 'На автомобиле не установлен ручной минимальный КМ.'

    methods.append(_method_block(
        3, 'Ручной КМ на автомобиле', min_km if min_km else None, steps3, desc3,
        applicable=type_km == 3,
        reason='' if type_km == 3 else 'Не задан или не выбран',
    ))

    # Порядок отображения: ручной → спец → АвтоК → план → справочные
    order = {3: 0, 4: 1, 5: 2, 51: 3, 1: 4, 101: 5, 102: 6}
    methods.sort(key=lambda m: order.get(m['id'], 99))

    brand_km_info = None
    if brand_km_obj:
        brand_km_info = {
            'brand': str(brand_km_obj.brand),
            'km': brand_km_obj.km,
            'km_min_dc': brand_km_obj.km_min_dc,
            'month': brand_km_obj.month.strftime('%m.%Y') if brand_km_obj.month else '',
            'km_display': _fmt_rub(brand_km_obj.km),
            'km_min_dc_display': _fmt_rub(brand_km_obj.km_min_dc),
        }

    winner_label = TYPE_KM_LABELS.get(type_km, '')
    if type_km == 5 and with_trade_in:
        winner_label = 'АвтоК с trade-in'

    return {
        'available': True,
        'type_km': type_km,
        'type_km_label': winner_label,
        'with_trade_in': with_trade_in,
        'winner': {
            'type_km': type_km,
            'label': winner_label,
            'amount': winner_amount,
            'amount_display': _fmt_rub(winner_amount),
        },
        'priority_note': _winner_reason(type_km, with_trade_in),
        'methods': methods,
        'irc': irc,
        'brand_km': brand_km_info,
        'stage_price': str(car.stage_price) if car.stage_price else None,
        'car_price': _fmt_rub(price),
        'car_price_raw': price,
    }
