# -*- coding: utf-8 -*-
"""Сводка интерактивной оценки для разговора с клиентом (тестовый режим).

Факты осмотра, Автотеки, Автохаба, Avito, диагностики и наших продаж за 60 дней.
Без ценовых групп и внутренних коэффициентов. Этапы УС — только во внутреннем блоке.
"""
from __future__ import annotations

from typing import Any

from django.db.models import Sum

from estimations.brief_factors import (
    SALES_STAR_KEYS,
    build_objections,
    build_scale,
    load_factor_config,
)


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _rub(value) -> str:
    n = int(round(_num(value)))
    if n <= 0:
        return ''
    return '{:,} ₽'.format(n).replace(',', ' ')


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _car_title(estimation) -> str:
    if estimation.modification_id:
        try:
            mod = estimation.modification
            mark = mod.model.mark.name
            model = mod.model.name
            return '{} {}'.format(mark, model).strip()
        except Exception:
            pass
    parts = [
        (estimation.mark_name or '').strip(),
        (estimation.model_name or '').strip(),
    ]
    title = ' '.join(p for p in parts if p)
    return title or 'автомобиль'


def _mod_label(estimation) -> str:
    if estimation.modification_id:
        try:
            return estimation.modification.name or ''
        except Exception:
            pass
    return (estimation.modification_name or '').strip()


def _add(items: list, title: str, text: str, *, source: str, effect: str = '', factor: str = ''):
    items.append({
        'title': title,
        'text': text,
        'source': source,
        'effect': effect,
        'factor': factor,
    })


def _body_damage_count(estimation) -> int:
    from register.models import RegRegInteractivOcenkaFiles

    types = (
        'vnesh_car_osmotr_pered', 'vnesh_car_osmotr_vod', 'vnesh_car_osmotr_zad',
        'vnesh_car_osmotr_pass', 'vnesh_car_osmotr_up', 'vnesh_car_osmotr_down',
        'array_images_pered', 'array_images_vod', 'array_images_zad',
        'array_images_pass', 'array_images_up', 'array_images_down',
        'osmotr_salon',
    )
    return (
        RegRegInteractivOcenkaFiles.objects
        .filter(estimation=estimation, type_file__in=types, blank=False)
        .exclude(file='')
        .count()
    )


def _repair_works(estimation) -> dict:
    from register.models import RegEstimationMCU, RegEstimationSS

    mcu = list(
        RegEstimationMCU.objects.filter(estimation=estimation)
        .exclude(name='')
        .values('name', 'price_kors', 'price_podrad')[:12]
    )
    ss = list(
        RegEstimationSS.objects.filter(estimation=estimation)
        .exclude(name='')
        .values('name', 'price_kors', 'price_podrad')[:12]
    )
    mcu_sum = _num(
        RegEstimationMCU.objects.filter(estimation=estimation)
        .aggregate(s=Sum('price_kors'))['s']
    )
    ss_sum = _num(
        RegEstimationSS.objects.filter(estimation=estimation)
        .aggregate(s=Sum('price_kors'))['s']
    )
    names = []
    for row in mcu + ss:
        name = (row.get('name') or '').strip()
        if name:
            names.append(name)
    return {
        'mcu': mcu,
        'ss': ss,
        'mcu_sum': mcu_sum,
        'ss_sum': ss_sum,
        'total': mcu_sum + ss_sum,
        'names': names[:8],
    }


def _diag_items(estimation) -> list[dict]:
    td = estimation.page_test_drive
    if td is None:
        return []
    from register.models import DiagnosticReferenceSelection

    rows = []
    qs = (
        DiagnosticReferenceSelection.objects
        .filter(test_drive=td)
        .select_related('reference_item', 'reference_item__category')
    )
    for sel in qs:
        item = sel.reference_item
        if item is None:
            continue
        rows.append({
            'title': item.title or '',
            'category': getattr(item.category, 'name', '') or sel.category_code or '',
            'consequences': (item.consequences or '').strip(),
            'causes': (item.possible_causes or '').strip(),
        })
    return rows


def _autoteka_signal(vin: str) -> dict:
    if not vin:
        return {}
    try:
        from avtosalon.models import Autoteka_signal
    except Exception:
        return {}
    row = (
        Autoteka_signal.objects
        .filter(vin__iexact=vin.strip())
        .order_by('-date')
        .first()
    )
    if row is None:
        return {}
    return {
        'liquidity': (row.liquidity_rating or '').strip(),
        'estimate_sell': _num(row.estimate_sell_price),
        'crashes': bool(row.crashes_badge),
        'mileage_badge': bool(row.real_mileage_badge),
        'days_in_sale': _int(row.average_days_in_sale),
    }


OUR_SALES_DAYS = 60
# PK этапов УС, как в отчётах БУ: тест-прайс → РДО → коррекция → ТХТ
_STAGE_LABELS = (
    (4, 'Тест-прайс'),
    (2, 'РДО'),
    (3, 'Коррекция'),
    (1, 'ТХТ'),
)
_STAGE_EARLY = {4, 2}
_STAGE_LATE = {3, 1}


def _car_year(raw) -> int:
    text = str(raw or '').strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return _int(raw)


def _empty_sales(*, has_mod=False, reason=''):
    return {
        'days': OUR_SALES_DAYS,
        'total': 0,
        'total_any_year': 0,
        'year_match': True,
        'has_mod': has_mod,
        'reason': reason,
        'by_stage': [{'id': sid, 'name': name, 'count': 0} for sid, name in _STAGE_LABELS],
        'unknown_stage': 0,
        'avg_price': 0,
        'min_price': 0,
        'max_price': 0,
        'avg_days': None,
        'early_share': 0,
        'late_share': 0,
        'test_share': 0,
        'factor': '',
        'client_line': '',
        'rows': [],
    }


def _sales_factor(total: int, early_share: float, late_share: float) -> str:
    if total <= 0:
        return 'our_sales_none'
    if total < 2:
        return ''
    if early_share >= 0.5:
        return 'our_sales_hot'
    if late_share >= 0.5:
        return 'our_sales_slow'
    return ''


def _shipments_for_mod(mod_id, date_from, *, year=None, limit=40):
    from django.db.models import OuterRef, Q, Subquery

    from documents.models import DocCarShipment
    from refs.models import RefCarsOrganization

    car_sub = RefCarsOrganization.objects.filter(lo_id=OuterRef('lo_id')).order_by('-id')
    qs = (
        DocCarShipment.objects
        .filter(
            active=True,
            lo_id__isnull=False,
            dataTime__gte=date_from,
            unit__buauto=True,
            cars__modification_autoru_id=mod_id,
        )
        .select_related('cars', 'unit', 'lo')
        .annotate(
            stage_id=Subquery(car_sub.values('stage_price_id')[:1]),
            stage_name=Subquery(car_sub.values('stage_price__name')[:1]),
        )
    )
    if year:
        ys = str(year)
        qs = qs.filter(Q(cars__year=ys) | Q(cars__year__startswith=ys))
    return list(qs.order_by('-dataTime')[:limit])


def _our_sales_60d(estimation) -> dict[str, Any]:
    """Наши отгрузки той же модификации за 60 дней, с этапом УС через карточку склада."""
    mod_id = getattr(estimation, 'modification_id', None)
    if not mod_id:
        return _empty_sales(reason='Нет модификации Auto.ru — продажи не с чем сопоставить.')

    try:
        from datetime import timedelta

        from django.utils import timezone
    except Exception:
        return _empty_sales(has_mod=True, reason='Не удалось загрузить отгрузки.')

    date_from = timezone.now() - timedelta(days=OUR_SALES_DAYS)
    year = _int(estimation.year)
    try:
        docs = _shipments_for_mod(mod_id, date_from, year=year) if year else []
        year_match = bool(docs)
        if not docs:
            docs = _shipments_for_mod(mod_id, date_from, year=None)
            year_match = False
    except Exception:
        return _empty_sales(has_mod=True, reason='Ошибка выборки отгрузок.')

    if not docs:
        empty = _empty_sales(has_mod=True)
        empty['factor'] = 'our_sales_none'
        empty['client_line'] = (
            'За последние {} дней таких же (эта модификация) мы не продавали — '
            'покупателя придётся искать дольше.'.format(OUR_SALES_DAYS)
        )
        return empty

    rows = []
    for doc in docs:
        row_year = _car_year(getattr(doc.cars, 'year', '') if doc.cars_id else '')
        rows.append(_sale_row(doc, row_year))

    return _sales_summary(
        rows,
        total_any_year=len(rows),
        year_match=year_match or not year,
        year=year,
    )


def _sale_row(doc, row_year: int) -> dict[str, Any]:
    stage_id = getattr(doc, 'stage_id', None)
    days = None
    try:
        if doc.lo_id and doc.lo and doc.lo.dataTime and doc.dataTime:
            days = (doc.dataTime - doc.lo.dataTime).days
            if days < 0:
                days = None
    except Exception:
        days = None
    unit = ''
    try:
        if doc.unit_id:
            unit = (doc.unit.name_dop or doc.unit.name or '').strip()
    except Exception:
        unit = ''
    price = _num(doc.amount)
    return {
        'id': doc.pk,
        'date': doc.dataTime,
        'year': row_year or None,
        'run': _int(doc.run),
        'price': price,
        'stage_id': stage_id,
        'stage': (getattr(doc, 'stage_name', None) or '').strip() or 'не указан',
        'days': days,
        'unit': unit,
        'vin': ((doc.cars.vin or '') if doc.cars_id else '')[-6:],
    }


def _sales_summary(rows: list, *, total_any_year: int, year_match: bool, year: int) -> dict[str, Any]:
    counts = {sid: 0 for sid, _name in _STAGE_LABELS}
    unknown = 0
    prices = []
    days_list = []
    for row in rows:
        sid = row.get('stage_id')
        if sid in counts:
            counts[sid] += 1
        else:
            unknown += 1
        if row.get('price'):
            prices.append(row['price'])
        if row.get('days') is not None:
            days_list.append(row['days'])

    total = len(rows)
    early = sum(counts[sid] for sid in _STAGE_EARLY)
    late = sum(counts[sid] for sid in _STAGE_LATE)
    test_n = counts.get(4, 0)
    early_share = (early / total) if total else 0
    late_share = (late / total) if total else 0
    test_share = (test_n / total) if total else 0
    factor = _sales_factor(total, early_share, late_share)

    if factor == 'our_sales_hot':
        client_line = (
            'За последние {} дней такие же мы продали {} — обычно быстро находят покупателя.'.format(
                OUR_SALES_DAYS, total
            )
        )
    elif factor == 'our_sales_slow':
        client_line = (
            'За последние {} дней такие же мы продали {}, но они дольше стоят на площадке, '
            'покупатель торгуется.'.format(OUR_SALES_DAYS, total)
        )
    elif total:
        client_line = (
            'За последние {} дней такие же мы продали {}.'.format(OUR_SALES_DAYS, total)
        )
    else:
        client_line = ''

    avg_days = int(round(sum(days_list) / len(days_list))) if days_list else None
    return {
        'days': OUR_SALES_DAYS,
        'total': total,
        'total_any_year': total_any_year,
        'year_match': year_match,
        'year': year,
        'has_mod': True,
        'reason': '' if year_match else 'За этот год продаж нет — ниже та же модификация, другие годы.',
        'by_stage': [{'id': sid, 'name': name, 'count': counts[sid]} for sid, name in _STAGE_LABELS],
        'unknown_stage': unknown,
        'avg_price': int(round(sum(prices) / len(prices))) if prices else 0,
        'min_price': int(round(min(prices))) if prices else 0,
        'max_price': int(round(max(prices))) if prices else 0,
        'avg_days': avg_days,
        'early_share': round(early_share * 100),
        'late_share': round(late_share * 100),
        'test_share': round(test_share * 100),
        'factor': factor,
        'client_line': client_line,
        'rows': rows[:12],
    }


def build_client_brief(estimation) -> dict[str, Any]:
    docs = estimation.page_documents
    salon = estimation.page_salon
    vnesh = estimation.page_vnesh
    proverki = estimation.page_proverki
    sog = estimation.page_soglasovanie
    kolesa = estimation.page_kolesa
    complect = estimation.page_complectnost
    td = estimation.page_test_drive

    run = _int(salon.run) if salon else 0
    if not run and getattr(estimation, 'page_remote', None):
        run = _int(estimation.page_remote.run)
    owners = _int(docs.count_owners) if docs else 0
    keys = _int(docs.count_key) if docs else 0
    year = _int(estimation.year)
    title = _car_title(estimation)
    vin = (estimation.vin or '').strip()
    plate = (docs.plate_number or '').strip() if docs else ''

    offer_reception = 0
    offer_sale = 0
    offer_before = 0
    offer_after = 0
    repairs_prep = 0
    if sog:
        offer_reception = _int(sog.price_reception)
        offer_sale = _int(sog.price_sale)
        offer_before = _int(sog.price_before_kd)
        offer_after = _int(sog.price_after_kd)
        repairs_prep = _num(sog.amount_recovery) or _num(sog.price_recovery)
        if not repairs_prep:
            repairs_prep = _num(sog.amount_podgotovka) + _num(sog.amount_ss) + _num(sog.amount_mcu)

    client_price = offer_after or offer_before or offer_reception
    works = _repair_works(estimation)
    if not repairs_prep and works['total']:
        repairs_prep = works['total']

    diag = _diag_items(estimation)
    damage_n = _body_damage_count(estimation)
    signal = _autoteka_signal(vin)
    sales = _our_sales_60d(estimation)

    hub_min = _num(estimation.hub_price_min)
    hub_max = _num(estimation.hub_price_max)
    hub_avg = _num(estimation.hub_avg) or _num(estimation.hub_price)
    avito_min = _num(estimation.avito_price_min) or _num(estimation.avito_price_market_min)
    avito_max = _num(estimation.avito_price_max) or _num(estimation.avito_price_market_max)
    avito_avg = _num(estimation.avito_price_avg_market_price)

    market_low = min(x for x in (hub_min, avito_min) if x > 0) if (hub_min or avito_min) else 0
    market_high = max(x for x in (hub_max, avito_max, hub_avg, avito_avg) if x > 0) if (
        hub_max or avito_max or hub_avg or avito_avg
    ) else 0

    pros: list[dict] = []
    cons: list[dict] = []
    sources: list[str] = ['Осмотр на площадке']

    if year and year >= 2018:
        _add(pros, 'Относительно свежий год', '{} год выпуска.'.format(year), source='Документы', factor='year_fresh')
    if 0 < owners <= 2:
        _add(pros, 'Немного владельцев', 'В ПТС / СТС — {}.'.format(owners), source='Документы', factor='owners_few')
    elif owners == 3:
        _add(cons, 'Три владельца', 'В документах три владельца.', source='Документы',
             effect='На рынке слабее, чем 1–2 хозяина, но ещё не «много хозяев».', factor='owners_3')
    if keys >= 2:
        _add(pros, 'Полный комплект ключей', 'Ключей: {}.'.format(keys), source='Документы', factor='keys_full')
    if docs and docs.pts_original:
        _add(pros, 'Оригинал ПТС', 'Документ на руках в оригинале.', source='Документы', factor='pts_original')
    if proverki and proverki.epts_success:
        _add(pros, 'Электронный ПТС в порядке', 'ЭПТС действующий.', source='Проверки', factor='epts_ok')
    if salon and salon.run_respond == 1:
        _add(pros, 'Пробег выглядит честно', 'Состояние салона соответствует заявленному пробегу.', source='Салон', factor='run_matches')
    if vnesh and vnesh.check_vin_int == 1:
        _add(pros, 'VIN совпадает', 'Номер на кузове проверен, расхождений нет.', source='Внешний осмотр', factor='vin_ok')
    if vnesh and vnesh.check_engine_int == 1:
        _add(pros, 'Двигатель и коробка на месте', 'При осмотре агрегатов замечаний нет.', source='Внешний осмотр', factor='engine_place_ok')
    dtp = _int(estimation.count_dtp) or (_int(proverki.count_dtp) if proverki else 0)
    if dtp == 0 and (proverki is not None or estimation.avtoteka_data):
        _add(pros, 'Без зафиксированных ДТП', 'В доступных проверках аварий нет.', source='Автотека / проверки', factor='no_dtp')
    if (proverki is not None or estimation.avtoteka_data) and not estimation.taxi and not estimation.carsharing:
        _add(pros, 'Не такси и не каршеринг', 'По данным проверок коммерческой эксплуатации нет.', source='Автотека', factor='no_taxi_share')
    if kolesa and kolesa.kolesa2:
        _add(pros, 'Второй комплект колёс', 'Есть зимний/летний комплект — это плюс при продаже.', source='Колёса', factor='kolesa2')
    if complect and complect.zapas_int == 1:
        _add(pros, 'Есть запаска', 'Запасное колесо на месте.', source='Комплектность', factor='spare_ok')
    if _num(estimation.hub_sale_total) >= 5:
        _add(
            pros,
            'Модель хорошо продаётся',
            'По рынку похожих авто достаточно сделок — машину проще выставить и продать.',
            source='Автохаб',
            factor='market_liquid',
        )
    if signal.get('liquidity') and 'низк' not in (signal.get('liquidity') or '').lower():
        _add(
            pros,
            'Ликвидность на рынке',
            'Оценка ликвидности Автотеки: {}.'.format(signal['liquidity']),
            source='Автотека',
            factor='autoteka_liquid',
        )
    if sales.get('factor') == 'our_sales_hot':
        _add(
            pros,
            'Такие авто у нас быстро продаются',
            sales.get('client_line') or 'За 60 дней модификация уходила с ранних этапов цены.',
            source='Наши продажи',
            factor='our_sales_hot',
        )

    if dtp > 0:
        _add(
            cons, 'История ДТП',
            'В проверках указано ДТП: {}.'.format(dtp)
            + (' Есть сильные повреждения.' if estimation.dtp_red else ''),
            source='Автотека / проверки',
            effect='Покупатель будет торговаться, страховка и перепродажа сложнее. Это обычно снижает цену приёма.',
            factor='dtp',
        )
    if estimation.taxi:
        _add(
            cons, 'Работа в такси',
            'Автотека / проверки фиксируют использование в такси.',
            source='Автотека',
            effect='Выше износ, сложнее продать в розницу. Цена приёма ниже рыночных объявлений.',
            factor='taxi',
        )
    if estimation.carsharing:
        _add(
            cons, 'Каршеринг',
            'Фиксировалось использование в каршеринге.',
            source='Автотека',
            effect='Много водителей и износ. Для клиента это аргумент снизить оценку.',
            factor='carsharing',
        )
    if estimation.iznos:
        _add(
            cons, 'Повышенный износ',
            'По осмотру состояние хуже типичного для года и пробега.',
            source='Осмотр',
            effect='Нужны вложения в подготовку, цена приёма ниже «красивых» объявлений.',
            factor='iznos',
        )
    if _int(estimation.avtoteka_warning_run) > 0:
        _add(
            cons, 'Вопрос по пробегу',
            'Автотека показывает возможное расхождение пробега (ориентир {} км).'.format(
                _int(estimation.avtoteka_warning_run)
            ),
            source='Автотека',
            effect='Риск претензий покупателя. Оценка консервативнее, пока история не закрыта документами.',
            factor='mileage_warning',
        )
    last_avt = _int(estimation.avtoteka_last_run)
    if last_avt and run and last_avt > run + 3000:
        _add(
            cons, 'Пробег меньше, чем в Автотеке',
            'На панели {} км, в Автотеке ранее фиксировали {} км.'.format(run, last_avt),
            source='Автотека',
            effect='Нужно объяснить историю. Пока есть сомнение — цена ниже.',
            factor='mileage_avtoteka_higher',
        )
    if salon and salon.run_respond == 0:
        _add(
            cons, 'Пробег не бьётся с состоянием',
            'Салон выглядит иначе, чем типично для заявленных километров.',
            source='Салон',
            effect='Покупатель увидит износ. Это торг и скидка при приёме.',
            factor='run_not_match',
        )
    if owners >= 4:
        _add(
            cons, 'Много владельцев',
            'В документах владельцев: {}.'.format(owners),
            source='Документы',
            effect='На рынке такие авто продаются дольше и дешевле одно-двуххозяйских.',
            factor='owners_many',
        )
    if keys == 1:
        _add(
            cons, 'Один ключ',
            'В комплекте один ключ.',
            source='Документы',
            effect='Дубликат — расход. Небольшой минус к цене и к доверию покупателя.',
            factor='keys_one',
        )
    if (docs and docs.car_credit) or (proverki and proverki.car_credit):
        _add(
            cons, 'Залог / кредит',
            'Автомобиль в залоге или кредите.',
            source='Документы',
            effect='Сделку нельзя закрыть, пока не снят залог. Срок и риски закладываются в предложение.',
            factor='credit',
        )
    if vnesh and vnesh.windshield_error_int == 0:
        _add(
            cons, 'Лобовое стекло',
            'Есть повреждения лобового.',
            source='Внешний осмотр',
            effect='Замена стекла — ощутимая сумма, её вычитают из цены приёма.',
            factor='windshield',
        )
    if vnesh and vnesh.light_error_int == 0:
        _add(
            cons, 'Свет',
            'Проблемы со световыми приборами.',
            source='Внешний осмотр',
            effect='Ремонт/замена фар. Влияет на безопасность и на оценку.',
            factor='lights',
        )
    if vnesh and vnesh.oil_error_int == 0:
        _add(
            cons, 'Подтекание масла',
            'На осмотре видны следы масла.',
            source='Внешний осмотр',
            effect='Нужна диагностика двигателя. Пока причина не ясна — консервативная цена.',
            factor='oil_leak',
        )
    if vnesh and vnesh.water_error_int == 0:
        _add(
            cons, 'Антифриз',
            'Следы подтекания охлаждающей жидкости.',
            source='Внешний осмотр',
            effect='Риск ремонта системы охлаждения. Это минус к предложению.',
            factor='coolant',
        )
    if vnesh and vnesh.check_vin_int == 0:
        _add(
            cons, 'Вопрос по VIN',
            'При сверке VIN есть замечания.',
            source='Внешний осмотр',
            effect='Юридический риск. Пока не закрыт — оценку не поднимаем.',
            factor='vin_problem',
        )
    if salon and salon.cleaning_int == 1:
        _add(
            cons, 'Нужна химчистка',
            'Салон требует химчистки.',
            source='Салон',
            effect='Расход на подготовку перед продажей.',
            factor='cleaning',
        )
    if salon and salon.ceiling_int == 1:
        _add(
            cons, 'Потолок',
            'Нужна перетяжка потолка.',
            source='Салон',
            effect='Заметная сумма подготовки, снижает цену приёма.',
            factor='ceiling',
        )
    for attr, label in (
        ('damage_seat_int', 'сиденья'),
        ('damage_wheel_int', 'руль'),
        ('damage_door_int', 'карты дверей'),
        ('damage_kpp_int', 'рычаг КПП'),
        ('damage_pedal_int', 'педали'),
    ):
        if salon and getattr(salon, attr, 10) == 1:
            _add(
                cons, 'Износ салона: {}'.format(label),
                'На осмотре отмечены повреждения / затёртости ({}).'.format(label),
                source='Салон',
                effect='Либо ремонт салона, либо скидка покупателю.',
                factor='salon_wear',
            )
            break
    if salon:
        try:
            if salon.dashboard_error.exists():
                names = list(salon.dashboard_error.values_list('name', flat=True)[:6])
                _add(
                    cons, 'Ошибки на панели',
                    'Горят индикаторы: {}.'.format(', '.join(n for n in names if n) or 'есть ошибки'),
                    source='Салон',
                    effect='Нужна диагностика электроники. Пока лампы горят — цена ниже.',
                    factor='dashboard',
                )
        except Exception:
            pass
    if damage_n >= 3:
        _add(
            cons, 'Повреждения кузова',
            'На схемах осмотра отмечено дефектов: {}.'.format(damage_n),
            source='Внешний осмотр',
            effect='Кузовной ремонт перед продажей. Чем больше точек — тем ниже приём.',
            factor='body_many',
        )
    elif damage_n > 0:
        _add(
            cons, 'Есть следы на кузове',
            'На схемах отмечено дефектов: {}.'.format(damage_n),
            source='Внешний осмотр',
            effect='Локальный ремонт или скидка на торге.',
            factor='body_few',
        )
    if td:
        for attr, label in (
            ('engine', 'двигатель'),
            ('gear', 'коробка передач'),
            ('suspension', 'подвеска'),
            ('brake', 'тормоза'),
            ('wheel', 'рулевое'),
            ('airbag', 'подушки безопасности'),
        ):
            val = getattr(td, attr, 10)
            comment = (getattr(td, 'comment_' + attr, None) or '').strip()
            if val == 0:
                _add(
                    cons, 'Диагностика: {}'.format(label),
                    (comment or 'По диагностике узел не в порядке.').strip(),
                    source='Диагностика',
                    effect='Ремонт до продажи. Сумма работ вычитается из рыночной цены.',
                    factor='diag_fail',
                )
            elif val == 2:
                _add(
                    cons, 'Замечания: {}'.format(label),
                    (comment or 'Есть замечания по диагностике.').strip(),
                    source='Диагностика',
                    effect='Либо устраняем, либо закладываем риск в цену.',
                    factor='diag_remarks',
                )
    for item in diag[:8]:
        _add(
            cons, item['title'] or 'Замечание диагностики',
            item['consequences'] or item['causes'] or (item['category'] or 'Диагностика'),
            source='Диагностика',
            effect=item['consequences'] or 'Может потребовать ремонта и влияет на цену приёма.',
            factor='diag_item',
        )
    if repairs_prep >= 10000:
        names = ', '.join(works['names'][:4])
        extra = ' В том числе: {}.'.format(names) if names else ''
        _add(
            cons, 'Предстоят работы',
            'Ориентир затрат на подготовку и ремонт: {}.'.format(_rub(repairs_prep)) + extra,
            source='Осмотр / диагностика',
            effect='Эти работы дилер делает до продажи. Их стоимость — основная причина, почему приём ниже объявлений.',
            factor='repairs_high',
        )
    autodex = _num(estimation.avtoteka_car_autodex)
    if autodex >= 30000:
        _add(
            cons, 'История ремонтов в Автотеке',
            'Сумма известных расчётов ремонтов: {}.'.format(_rub(autodex)),
            source='Автотека',
            effect='Покупатель увидит историю. Крупные ремонты давят на цену.',
            factor='autodex_high',
        )
    if signal.get('crashes'):
        _add(
            cons, 'Метка аварийности Автотеки',
            'В мониторинге Автотеки стоит признак аварийности.',
            source='Автотека',
            effect='Сложнее продать «как новую». Оценка ниже верхнего рынка.',
            factor='crashes_badge',
        )
    if sales.get('factor') == 'our_sales_slow':
        _add(
            cons,
            'Такие авто у нас дольше стоят',
            sales.get('client_line') or 'За 60 дней продажи шли с поздних этапов цены.',
            source='Наши продажи',
            effect='Покупатель торгуется. Приём ближе к нижней полке объявлений, иначе риск зависнуть на складе.',
            factor='our_sales_slow',
        )
    elif sales.get('factor') == 'our_sales_none' and sales.get('has_mod'):
        _add(
            cons,
            'Свежих продаж этой модификации нет',
            sales.get('client_line') or 'За 60 дней таких отгрузок не было.',
            source='Наши продажи',
            effect='Сложнее спрогнозировать срок продажи. В цене есть запас на экспозицию.',
            factor='our_sales_none',
        )

    if estimation.avtoteka_web or estimation.avtoteka_data or last_avt or dtp:
        sources.append('Автотека')
    if hub_avg or hub_min or _num(estimation.hub_sale_total):
        sources.append('Автохаб (рынок)')
    if avito_avg or avito_min:
        sources.append('Объявления Avito')
    if diag or (td and any(getattr(td, a, 10) in (0, 2) for a in ('engine', 'gear', 'suspension', 'brake'))):
        sources.append('Диагностика')
    if sog and sog.no_diagnostica:
        sources.append('Без диагностики (решение по осмотру)')
    if sales.get('total') or sales.get('factor') == 'our_sales_none':
        sources.append('Наши продажи за {} дней'.format(OUR_SALES_DAYS))

    price_story = []
    if market_low and market_high:
        price_story.append(
            'Похожие автомобили на рынке сейчас в диапазоне {} — {}{}.'.format(
                _rub(market_low),
                _rub(market_high),
                (' среднее около ' + _rub(hub_avg or avito_avg)) if (hub_avg or avito_avg) else '',
            )
        )
    elif hub_avg:
        price_story.append(
            'Ориентир рынка по Автохабу: около {}.'.format(_rub(hub_avg))
        )
    elif avito_avg:
        price_story.append(
            'По объявлениям похожих авто ориентир около {}.'.format(_rub(avito_avg))
        )
    else:
        price_story.append(
            'Рыночный коридор по Автохабу/объявлениям в оценке ещё не заполнен — опираемся на осмотр и проверки.'
        )

    if client_price:
        price_story.append(
            'Предложение по приёму / зачёту: {}.'.format(_rub(client_price))
            + (' После диагностики: {}.'.format(_rub(offer_after)) if offer_after and offer_after != client_price else '')
            + (' До диагностики: {}.'.format(_rub(offer_before)) if offer_before and not offer_after else '')
        )
    if offer_sale:
        price_story.append(
            'Ориентир, по которому авто потом выставляют в продажу: {}.'.format(_rub(offer_sale))
        )
    if repairs_prep >= 5000:
        price_story.append(
            'Чтобы подготовить машину к продаже (кузов, слесарка, химчистка и т.п.), нужны работы примерно на {}. '
            'Их нельзя «спрятать» в красивую цену объявления — поэтому приём ниже верхнего рынка.'.format(
                _rub(repairs_prep)
            )
        )
    if cons:
        price_story.append(
            'На цену также влияют факты осмотра и проверок: {}.'.format(
                '; '.join(c['title'].lower() for c in cons[:5])
            )
        )
    else:
        price_story.append(
            'Серьёзных замечаний по осмотру и проверкам нет — предложение ближе к рынку, с запасом на подготовку и гарантию сделки.'
        )
    if sales.get('client_line'):
        price_story.append(sales['client_line'])
    price_story.append(
        'Цифры внутренних настроек дилера клиенту не называем: говорим про рынок, состояние, историю и необходимые работы. Этапы УС (тест-прайс, РДО, ТХТ) — только для нас.'
    )

    talk_lines = [
        '{} {}{}, VIN {}{}.'.format(
            year or '',
            title,
            (', ' + _mod_label(estimation)) if _mod_label(estimation) else '',
            vin or '—',
            (', гос. номер ' + plate) if plate else '',
        ).strip(),
    ]
    if run:
        talk_lines.append('Пробег по панели: {} км.'.format(run))
    talk_lines.extend(price_story[:-1])
    if cons:
        talk_lines.append('Минусы, которые стоит проговорить: ' + '; '.join(c['title'] for c in cons[:6]) + '.')
    if pros:
        talk_lines.append('Плюсы: ' + '; '.join(p['title'] for p in pros[:6]) + '.')

    fired = [item.get('factor') for item in (pros + cons) if item.get('factor')]
    factor_cfg = load_factor_config()
    scale = build_scale(fired, factor_cfg)
    objections = build_objections(
        fired,
        client_price=client_price,
        market_high=market_high,
        market_low=market_low,
        repairs=repairs_prep,
        cfg=factor_cfg,
    )
    sales['stars_enabled'] = any(k in factor_cfg for k in SALES_STAR_KEYS)
    sales['stars_on'] = bool(sales.get('factor') and sales['factor'] in factor_cfg)
    talk_lines.append(
        'Оценка состояния: {} из 5 — {}.'.format(scale['stars'], scale['label'])
    )

    missing = []
    if not vin:
        missing.append('Нет VIN')
    if not run:
        missing.append('Нет пробега')
    if not client_price:
        missing.append('Ещё нет согласованной цены приёма')
    if not (hub_avg or avito_avg or market_low):
        missing.append('Нет данных Автохаб / объявлений — обновите рыночные данные в оценке')
    if vnesh is None:
        missing.append('Не заполнен внешний осмотр')
    if salon is None:
        missing.append('Не заполнен салон')

    preview_url = ''
    try:
        from register.models import RegRegInteractivOcenkaFiles
        prev = (
            RegRegInteractivOcenkaFiles.objects
            .filter(estimation=estimation, type_file='vnesh_car_all')
            .exclude(file='')
            .exclude(blank=True)
            .order_by('file_number', 'id')
            .first()
        )
        if prev is None:
            prev = estimation.fotos_prev()
        if prev is not None and getattr(prev, 'file', None) and prev.file.name:
            preview_url = prev.get_thumbnail_url() or prev.get_absolute_url()
    except Exception:
        preview_url = ''

    price_eco = 0
    remote = getattr(estimation, 'page_remote', None)
    if remote is not None:
        price_eco = _int(remote.price_eco)

    return {
        'title': title,
        'year': year,
        'vin': vin,
        'plate': plate,
        'modification': _mod_label(estimation),
        'run': run,
        'owners': owners,
        'keys': keys,
        'color': ((vnesh.color if vnesh else '') or (docs.pts_color if docs else '') or '').strip(),
        'drive': (estimation.type_drive or '').strip(),
        'engine': getattr(estimation.type_engine, 'name', '') or '',
        'gear': getattr(estimation.type_gear, 'name', '') or '',
        'body': getattr(estimation.type_body, 'name', '') or '',
        'status': getattr(estimation.status, 'name', '') or '',
        'preview_url': preview_url,
        'pros_count': len(pros),
        'cons_count': len(cons),
        'offer_reception': offer_reception,
        'offer_sale': offer_sale,
        'offer_before': offer_before,
        'offer_after': offer_after,
        'price_eco': price_eco,
        'client_price': client_price,
        'repairs': repairs_prep,
        'market_low': market_low,
        'market_high': market_high,
        'hub_avg': hub_avg,
        'avito_avg': avito_avg,
        'hub_sales': _num(estimation.hub_sale_total),
        'avtoteka_url': (estimation.avtoteka_web or '').strip(),
        'pros': pros,
        'cons': cons,
        'price_story': price_story,
        'talk_text': '\n'.join(talk_lines),
        'scale': scale,
        'objections': objections,
        'our_sales': sales,
        'sources': sources,
        'missing': missing,
        'works_names': works['names'],
        'diag_count': len(diag),
        'damage_n': damage_n,
        'no_diagnostica': bool(sog.no_diagnostica) if sog else False,
        'eco_comment': ((sog.comment or '') if sog else '').strip(),
        'eco_comment_kd': ((sog.price_after_kd_comment or sog.price_before_kd_comment or '') if sog else '').strip(),
    }
