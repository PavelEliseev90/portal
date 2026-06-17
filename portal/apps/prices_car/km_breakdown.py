"""Пошаговый разбор расчёта минимального КМ (cumulative_data) для UI."""
from datetime import datetime, timedelta

from django.db.models import Count, Sum

TYPE_KM_LABELS = {
    0: 'Не рассчитан',
    1: 'Авто',
    2: 'Авто+',
    3: 'Ручной КМ',
    4: 'Спец. условие ГК',
}


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


def _method_block(method_id, title, result_rub, steps, description, applicable, reason=''):
    return {
        'id': method_id,
        'title': title,
        'result_rub': result_rub,
        'result_display': _fmt_rub(result_rub),
        'steps': steps,
        'description': description,
        'applicable': applicable,
        'not_selected_reason': reason,
    }


def _winner_reason(type_km, km1, km2, has_discount, has_min_km):
    if type_km == 3:
        return 'На автомобиле задан ручной минимальный КМ — он имеет наивысший приоритет.'
    if type_km == 4:
        return 'Применено специальное условие ГК (дисконт к базе max(Авто, Авто+)).'
    if type_km == 2:
        return 'Метод «Авто+» ({}) выше метода «Авто» ({}).'.format(
            _fmt_rub(km2), _fmt_rub(km1),
        )
    if type_km == 1:
        if has_min_km:
            return 'Ручной КМ не задан или равен 0; спец. условие не найдено; «Авто+» не превысило «Авто».'
        return 'Использован расчёт по норме бренда и стоку марки (метод «Авто»).'
    return 'Недостаточно данных для расчёта (нет модификации Auto.ru).'


def build_km_calculation_breakdown(car):
    """
    Структурированный разбор cumulative_data для отображения пользователю.
    Формулы совпадают с RefCarsOrganization.cumulative_data().
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
        }

    from prices_car.brand_resolve import resolve_price_car_brand_for_car
    from prices_car.models import PriceCarStageKM
    from refs.models import RefCarsOrganization

    cumulative = car.cumulative_data()
    type_km = cumulative.get('type_km', 0)

    brand_car = resolve_price_car_brand_for_car(car)
    brand_km_obj = cumulative.get('brand_km')
    stage_km = PriceCarStageKM.objects.filter(stage=car.stage_price).last()
    irc = cumulative.get('irc')
    if irc is None and stage_km:
        irc = stage_km.km_index

    mark_name = car.modification_autoru.model.mark.name
    price = car.price or 0
    methods = []

    # --- Method 1: Авто ---
    km1 = 0
    desc1 = ''
    steps1 = []
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

        steps1.append(_step('Норма КМ бренда на месяц', _fmt_rub(brand_km_val), source='BrandKM'))
        steps1.append(_step(
            'Период нормы',
            brand_km_obj.month.strftime('%m.%Y') if brand_km_obj.month else '—',
            source='BrandKM',
        ))
        steps1.append(_step('ИРЦ этапа УС', str(irc), source='PriceCarStageKM'))
        steps1.append(_step('РРЦ автомобиля', _fmt_rub(price), source='Карточка АМ'))

        if stock_sum and stock_count > 0:
            avg_price = stock_sum / stock_count
            km_pct = brand_km_val / avg_price * 100
            km_stage_pct = round(km_pct, 2) * float(irc)
            km1 = price * km_stage_pct / 100
            steps1.append(_step(
                'Сток марки (новые АМ с ценой)',
                '{} шт.'.format(stock_count),
                source='RefCarsOrganization',
            ))
            steps1.append(_step('Сумма РРЦ стока', _fmt_rub(stock_sum)))
            steps1.append(_step('Средняя РРЦ стока', _fmt_rub(avg_price)))
            steps1.append(_step(
                'КМ % от средней цены',
                _fmt_pct(km_pct),
                formula='{brand_km} / {avg} × 100'.format(
                    brand_km=brand_km_val, avg=int(avg_price),
                ),
            ))
            steps1.append(_step(
                'КМ % с учётом ИРЦ',
                _fmt_pct(km_stage_pct),
                formula='{km_pct} × {irc}'.format(km_pct=round(km_pct, 2), irc=irc),
            ))
            desc1 = (
                'Автоматический минимальный КМ {mark} — {cnt} шт. на сумму РРЦ {sum} руб.'
            ).format(mark=mark_name, cnt=stock_count, sum=_fmt_rub(stock_sum).replace(' ₽', ''))
        else:
            km_pct = brand_km_val
            km_stage_pct = round(km_pct, 2) * float(irc)
            km1 = price * km_stage_pct / 100
            if km1 == 0:
                km1 = brand_km_val
            steps1.append(_step('Сток марки', 'нет данных', source='RefCarsOrganization'))
            steps1.append(_step(
                'КМ (fallback без стока)',
                _fmt_rub(brand_km_val),
                formula='используется норма бренда в руб.',
            ))
            steps1.append(_step(
                'КМ % с учётом ИРЦ',
                _fmt_pct(km_stage_pct),
            ))
            desc1 = 'Автоматический минимальный КМ {mark} {sum} руб. (без стока марки)'.format(
                mark=mark_name, sum=_fmt_rub(km1).replace(' ₽', ''),
            )

        steps1.append(_step('Итого мин. КМ (метод «Авто»)', _fmt_rub(km1), highlight=True))
    else:
        steps1.append(_step(
            'Расчёт недоступен',
            'Нет BrandKM или индекса этапа УС',
            source='Справочники',
        ))
        desc1 = cumulative.get('automatic', {}).get('km_description', '')

    auto_data = cumulative.get('automatic', {})
    if auto_data:
        km1 = auto_data.get('km_min_automatic', km1)
        desc1 = auto_data.get('km_description', desc1)

    methods.append(_method_block(
        1, 'Авто (норма бренда × сток марки)', km1, steps1, desc1,
        applicable=type_km == 1,
        reason='' if type_km == 1 else 'Не выбран как итоговый метод',
    ))

    # --- Method 2: Авто+ ---
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

    steps2.append(_step(
        'Период анализа продаж',
        '{} — {}'.format(dt_start.strftime('%d.%m.%Y'), datetime.now().strftime('%d.%m.%Y')),
        source='Cumulative',
    ))
    steps2.append(_step('Марка', mark_name, source='Cumulative'))
    steps2.append(_step('Количество продаж', str(cum_count), source='Cumulative'))
    steps2.append(_step('ИРЦ этапа УС', str(irc), source='PriceCarStageKM'))
    steps2.append(_step('РРЦ автомобиля', _fmt_rub(price)))

    if cum_count > 0 and stage_km is not None:
        cum_sum = 0
        cum_aggregate = 0
        for cum_info in cum_qs:
            SummaRabot = float(cum_info.SummaRabot or 0)
            ValovayaPribylZChShiny = float(cum_info.ValovayaPribylZChShiny or 0)
            ValovayaPribylZCh = float(cum_info.ValovayaPribylZCh or 0)
            SummaTreydInPoPlanu = float(cum_info.SummaTreydInPoPlanu or 0)
            VPOPFU = float(cum_info.VPOPFU or 0)
            SummaMarzhiBezNDS = float(cum_info.SummaMarzhiBezNDS or 0)
            SummaGosreg = float(cum_info.SummaGosreg or 0)
            cum_data = (
                SummaRabot + ValovayaPribylZChShiny + ValovayaPribylZCh
                + SummaTreydInPoPlanu + VPOPFU + SummaMarzhiBezNDS + SummaGosreg
            )
            cum_sum += cum_data
            cum_aggregate += float(cum_info.RRTS or 0)

        km_sale = round(cum_sum, 2) / cum_count
        avg_rrc = cum_aggregate / cum_count
        km_pct2 = km_sale / avg_rrc * 100 if avg_rrc else 0
        km_stage_pct2 = round(km_pct2, 2) * float(irc)
        km2 = price * km_stage_pct2 / 100
        if km2 == 0:
            km2 = km_sale

        steps2.append(_step(
            'Сумма маржи по продажам',
            _fmt_rub(cum_sum),
            formula='работы + ЗЧ + trade-in + ОПФУ + маржа + госрег.',
        ))
        steps2.append(_step('Средняя маржа на сделку', _fmt_rub(km_sale)))
        steps2.append(_step('Сумма РРЦ продаж', _fmt_rub(cum_aggregate)))
        steps2.append(_step('Средняя РРЦ продаж', _fmt_rub(avg_rrc)))
        steps2.append(_step('КМ % от РРЦ продаж', _fmt_pct(km_pct2)))
        steps2.append(_step('КМ % с учётом ИРЦ', _fmt_pct(km_stage_pct2)))
        steps2.append(_step('Итого мин. КМ (метод «Авто+»)', _fmt_rub(km2), highlight=True))
        desc2 = (
            'Проанализированы продажи склада новых АМ по бренду {mark} — {cnt} шт. '
            'на сумму РРЦ {sum} руб.'
        ).format(mark=mark_name, cnt=cum_count, sum=_fmt_rub(cum_aggregate).replace(' ₽', ''))
    else:
        steps2.append(_step('Итого', 'Нет продаж за период или нет ИРЦ', highlight=True))
        desc2 = 'Нет данных по продажам за текущий месяц для метода «Авто+».'

    auto2 = cumulative.get('automatic_2', {})
    if auto2:
        km2 = auto2.get('km_min_automatic', km2)
        desc2 = auto2.get('km_description', desc2)

    reason2 = ''
    if type_km != 2:
        if type_km == 3:
            reason2 = 'Перебит ручным КМ'
        elif type_km == 4:
            reason2 = 'Применено спец. условие ГК'
        elif km2 <= km1:
            reason2 = 'Не превышает метод «Авто» ({})'.format(_fmt_rub(km1))
        else:
            reason2 = 'Не выбран как итоговый метод'

    methods.append(_method_block(
        2, 'Авто+ (факт продаж за месяц)', km2, steps2, desc2,
        applicable=type_km == 2,
        reason=reason2,
    ))

    # --- Method 4: Спец. условие ---
    km4 = 0
    desc4 = ''
    steps4 = []
    auto3 = cumulative.get('automatic_3')
    km_base = max(km1 or 0, km2 or 0)

    steps4.append(_step('База для дисконта', _fmt_rub(km_base), formula='max(Авто, Авто+)'))

    if auto3:
        km4 = auto3.get('km_min_automatic', 0)
        disc_pct = auto3.get('discount_percent', 0)
        steps4.append(_step('Процент спец. условия ГК', _fmt_pct(disc_pct, 0)))
        steps4.append(_step(
            'Расчёт',
            _fmt_rub(km4),
            formula='{base} × (1 + {p}/100)'.format(base=int(km_base), p=disc_pct),
        ))
        steps4.append(_step('Итого мин. КМ (спец. условие)', _fmt_rub(km4), highlight=True))
        desc4 = auto3.get('km_description', '')
        reason4 = '' if type_km == 4 else (
            'Перебит ручным КМ' if type_km == 3 else 'Не выбран как итоговый метод'
        )
    else:
        steps4.append(_step('Спец. условие', 'не найдено для этого автомобиля', source='PriceCarKmDiscount'))
        desc4 = 'Активный дисконт КМ по бренду/модели не применяется.'
        reason4 = 'Дисконт не найден или не активен'

    methods.append(_method_block(
        4, 'Спец. условие ГК', km4, steps4, desc4,
        applicable=type_km == 4,
        reason=reason4,
    ))

    # --- Method 3: Ручной ---
    min_km = car.min_km or 0
    steps3 = []
    if min_km:
        km_pct3 = min_km / price * 100 if price else 0
        steps3.append(_step('Ручной мин. КМ на карточке', _fmt_rub(min_km), source='RefCarsOrganization.min_km'))
        steps3.append(_step('РРЦ автомобиля', _fmt_rub(price)))
        steps3.append(_step('Доля от цены', _fmt_pct(km_pct3)))
        steps3.append(_step('Итого мин. КМ (ручной)', _fmt_rub(min_km), highlight=True))
        desc3 = cumulative.get('custom', {}).get('km_description', '')
    else:
        steps3.append(_step('Ручной КМ', 'не задан', source='Карточка АМ'))
        desc3 = 'На автомобиле не установлен ручной минимальный КМ.'

    methods.append(_method_block(
        3, 'Ручной КМ на автомобиле', min_km if min_km else None, steps3, desc3,
        applicable=type_km == 3,
        reason='' if type_km == 3 else 'Не задан или не выбран',
    ))

    winner_amount = None
    if type_km == 1:
        winner_amount = km1
    elif type_km == 2:
        winner_amount = km2
    elif type_km == 3:
        winner_amount = min_km
    elif type_km == 4:
        winner_amount = km4

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

    return {
        'available': True,
        'type_km': type_km,
        'type_km_label': TYPE_KM_LABELS.get(type_km, str(type_km)),
        'winner': {
            'type_km': type_km,
            'label': TYPE_KM_LABELS.get(type_km, ''),
            'amount': winner_amount,
            'amount_display': _fmt_rub(winner_amount),
        },
        'priority_note': _winner_reason(
            type_km, km1, km2, bool(auto3), bool(min_km),
        ),
        'methods': methods,
        'irc': irc,
        'brand_km': brand_km_info,
        'stage_price': str(car.stage_price) if car.stage_price else None,
        'car_price': _fmt_rub(price),
        'car_price_raw': price,
    }
