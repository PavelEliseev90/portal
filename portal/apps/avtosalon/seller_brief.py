# -*- coding: utf-8 -*-
"""Сводка по автомобилю для продавца (менеджера отдела продаж).

Анализ рыночных цен и метрик Автохаб, истории переоценок, положения на рынке,
выполненных ремонтов/подготовки и истории фотографий.
Генерация плюсов (с речевыми модулями презентации), минусов (с отработкой возражений)
и блока практических рекомендаций продавцу.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone


def _num(val) -> float:
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _int(val) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _format_money(val) -> str:
    n = int(round(_num(val)))
    if n == 0:
        return '0 ₽'
    return f"{n:,} ₽".replace(',', ' ')


def _days_ago(dt: datetime | None) -> int | None:
    if not dt:
        return None
    now = timezone.now() if timezone.is_aware(dt) else datetime.now()
    delta = now - dt
    return max(0, delta.days)


def _get_latest_avtohub(car) -> Any | None:
    """Возвращает последний наиболее информативный снимок Автохаб."""
    from avtosalon.models import Avtohub

    vin = (car.vin or '').strip()
    if not vin:
        return None

    qs = Avtohub.objects.filter(vin=vin).order_by('-date')
    records = list(qs[:10])
    if not records:
        return None

    for ah in records:
        if (
            (ah.avgMarketPrice or 0) > 0
            or (ah.numberOfCompetitors or 0) > 0
            or (ah.averageDaysInSale or 0) > 0
            or (ah.avitoViews or 0) + (ah.autoruViews or 0) + (ah.dromViews or 0) > 0
        ):
            return ah
    return records[0]


def _analyze_avtohub(car, ah) -> dict[str, Any]:
    car_price = _int(car.price)
    if not ah:
        return {
            'has_data': False,
            'cna': None,
            'imv': None,
            'pcp': None,
            'price_diff': None,
            'price_diff_pct': None,
            'position': None,
            'competitors': None,
            'rating_pct': None,
            'views_total': 0,
            'views_avito': 0,
            'views_autoru': 0,
            'views_drom': 0,
            'calls_total': 0,
            'chats_total': 0,
            'days_in_sale': 0,
            'avg_days_in_sale': 0,
            'marketing_cost': 0.0,
            'snapshot_date': None,
            'snapshot_days_ago': None,
        }

    cna = _int(ah.avgMarketPrice)
    imv = _int(ah.imv)
    pcp = _int(ah.maxposterSaleCost)

    price_diff = (car_price - cna) if cna > 0 else None
    price_diff_pct = round((price_diff / cna) * 100, 1) if (cna > 0 and price_diff is not None) else None

    pos = _int(ah.vRatingPosition)
    comp = _int(ah.numberOfCompetitors)
    rating_pct = round((pos / comp) * 100, 1) if comp > 0 else None

    views_avito = _int(ah.avitoViews)
    views_autoru = _int(ah.autoruViews)
    views_drom = _int(ah.dromViews)
    views_total = views_avito + views_autoru + views_drom

    calls_total = _int(ah.callsCounts_uniqueTotal)
    chats_total = _int(ah.chatsCounts_uniqueTotal)

    days_in_sale = _int(ah.daysInSale)
    avg_days = _int(ah.averageDaysInSale)
    marketing = round(_num(ah.totalAdvertisingCost), 0)

    snap_date = ah.date
    snap_days = _days_ago(snap_date)

    return {
        'has_data': True,
        'cna': cna if cna > 0 else None,
        'imv': imv if imv > 0 else None,
        'pcp': pcp if pcp > 0 else None,
        'price_diff': price_diff,
        'price_diff_pct': price_diff_pct,
        'position': pos if pos > 0 else None,
        'competitors': comp if comp > 0 else None,
        'rating_pct': rating_pct,
        'views_total': views_total,
        'views_avito': views_avito,
        'views_autoru': views_autoru,
        'views_drom': views_drom,
        'calls_total': calls_total,
        'chats_total': chats_total,
        'days_in_sale': days_in_sale,
        'avg_days_in_sale': avg_days,
        'marketing_cost': marketing,
        'snapshot_date': snap_date,
        'snapshot_days_ago': snap_days,
    }


def _analyze_price_revaluations(car) -> dict[str, Any]:
    from register.models import RegRefCarsOrganizationsPrice

    items = list(
        RegRefCarsOrganizationsPrice.objects
        .filter(car=car)
        .order_by('-date')
        .values('date', 'price')
    )
    count = len(items)
    car_price = _int(car.price)

    if not items:
        return {
            'count': 0,
            'items': [],
            'first_price': car_price,
            'total_delta': 0,
            'last_change_date': None,
            'days_since_change': car.days_in_stok or 0,
        }

    first_price = items[-1]['price']
    total_delta = car_price - first_price
    last_date = items[0]['date']
    days_since = _days_ago(last_date) or 0

    history = []
    prev_price = None
    for item in reversed(items):
        p = item['price']
        step_delta = (p - prev_price) if prev_price is not None else 0
        history.append({
            'date': item['date'],
            'price': p,
            'delta': step_delta,
        })
        prev_price = p

    history.reverse()

    return {
        'count': count,
        'items': history[:10],
        'first_price': first_price,
        'total_delta': total_delta,
        'last_change_date': last_date,
        'days_since_change': days_since,
    }


def _analyze_photos(car) -> dict[str, Any]:
    from refs.models import RefCarsOrganizationFiles

    photos = list(
        RefCarsOrganizationFiles.objects
        .filter(сars_organization=car)
        .order_by('-main', '-date')
    )
    count = len(photos)
    has_main = any(bool(p.main) for p in photos)

    latest_date = None
    oldest_date = None
    for p in photos:
        if p.date:
            if latest_date is None or p.date > latest_date:
                latest_date = p.date
            if oldest_date is None or p.date < oldest_date:
                oldest_date = p.date

    days_ago = _days_ago(latest_date)

    is_outdated = (days_ago is not None and days_ago > 35)
    is_few = count < 15

    return {
        'count': count,
        'has_main': has_main,
        'latest_date': latest_date,
        'days_ago': days_ago,
        'is_outdated': is_outdated,
        'is_few': is_few,
    }


def _analyze_repairs(car) -> dict[str, Any]:
    from documents.models import DocZN, DocZNWorkKA, DocZNProductKA

    vin = (car.vin or '').strip()
    zn_list = []
    if vin:
        zn_list = list(
            DocZN.objects
            .filter(cars__vin=vin)
            .select_related('typeRemont', 'readyStatus', 'unit')
            .order_by('-dataTime')[:50]
        )

    lo = getattr(car, 'lo', None)
    ka_works = []
    ka_products = []
    if lo:
        ka_works = list(
            DocZNWorkKA.objects
            .filter(zn__lo=lo)
            .select_related('work', 'zn', 'zn__typeRemont')
            .order_by('-id')[:50]
        )
        ka_products = list(
            DocZNProductKA.objects
            .filter(zn__lo=lo)
            .select_related('product', 'zn', 'zn__typeRemont')
            .order_by('-id')[:50]
        )

    outlay = _int(car.outlay)

    notable_works = []
    for w in ka_works:
        w_name = getattr(w.work, 'name', '') or ''
        if w_name and w_name not in notable_works:
            notable_works.append(w_name)

    for p in ka_products:
        p_name = getattr(p.product, 'name', '') or ''
        if p_name and p_name not in notable_works:
            notable_works.append(p_name)

    for zn in zn_list:
        t_name = getattr(zn.typeRemont, 'name', '') or ''
        num_str = f"ЗН №{zn.nomer or zn.id}"
        if t_name:
            num_str += f" ({t_name})"
        if num_str not in notable_works:
            notable_works.append(num_str)

    prep_comment = (car.description_podgotovka or '').strip()

    return {
        'count_zn': len(zn_list),
        'count_ka_works': len(ka_works),
        'count_ka_products': len(ka_products),
        'outlay': outlay,
        'notable_works': notable_works[:12],
        'prep_comment': prep_comment,
        'has_repairs': bool(zn_list or ka_works or ka_products or outlay > 0 or prep_comment),
    }


def _generate_strengths_and_weaknesses(car, hub: dict, reval: dict, photos: dict, repairs: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Генерирует списки:
    1. Плюсы (сильные стороны) с речевыми модулями для презентации
    2. Минусы (слабые стороны) со скриптами отработки возражений покупателя
    3. Практические рекомендации (Action items) для менеджера
    """
    strengths = []
    weaknesses = []
    actions = []

    car_price = _int(car.price)
    days_in_stok = _int(car.days_in_stok)
    run = _int(car.run)
    year = _int(car.year)
    owners = _int(car.owners)
    keys = _int(car.keys)

    # ==========================
    # ПЛЮСЫ (STRENGTHS)
    # ==========================

    # 1. Владельцы
    if owners in (1, 2):
        plural = 'Один аккуратный владелец' if owners == 1 else 'Всего 2 владельца'
        strengths.append({
            'tag': 'Документы',
            'title': f'{plural} по ПТС',
            'detail': 'Автомобиль с прозрачной историей владения, без частой смены хозяев.',
            'script': '«Обратите внимание: у автомобиля минимум записей в ПТС. Машина была в одних руках, эксплуатировалась бережно, история полностью прозрачна».',
        })

    # 2. Пробег
    if run > 0 and run <= 75000:
        strengths.append({
            'tag': 'Пробег',
            'title': f'Небольшой подтвержденный пробег ({run:,} км)'.replace(',', ' '),
            'detail': 'Ресурс ключевых агрегатов (ДВС, коробка, навесное) на высоком уровне.',
            'script': '«Пробег для этого года совсем небольшой — всего ' + f'{run:,} км'.replace(',', ' ') + '. Автомобиль только прошёл обкатку и имеет огромный запас надёжности до регламентных замен».',
        })
    elif run > 0 and year > 0 and (datetime.now().year - year) > 0:
        yearly_run = run / (datetime.now().year - year)
        if yearly_run < 15000:
            strengths.append({
                'tag': 'Пробег',
                'title': f'Умеренный среднегодовой пробег (~{int(yearly_run):,} км/год)'.replace(',', ' '),
                'detail': 'Машина не использовалась в коммерции, пробег в пределах комфортной городской эксплуатации.',
                'script': '«Средний пробег менее 15 000 км в год — признак частного домашнего использования без коммерческих нагрузок».',
            })

    # 3. Ключи
    if keys >= 2:
        strengths.append({
            'tag': 'Комплектность',
            'title': f'Полный комплект ключей ({keys} шт.)',
            'detail': 'Оба оригинальных ключа в наличии, никаких затрат на изготовление дубликата.',
            'script': '«Автомобиль передается с полным заводским комплектом ключей — вам не придется ничего дозаказывать и тратить время».',
        })

    # 4. Цена в рынке / ниже рынка
    diff = hub.get('price_diff')
    if diff is not None and diff < -10000:
        diff_abs = abs(diff)
        strengths.append({
            'tag': 'Цена',
            'title': f'Выгодная цена: ниже рынка на {_format_money(diff_abs)}',
            'detail': f'Среднерыночная цена (ЦНА) — {_format_money(hub.get("cna"))}, наша цена — {_format_money(car_price)}.',
            'script': '«Мы выставили честную рыночную цену даже ниже средней по региону — разница более ' + _format_money(diff_abs) + '. Это одно из самых привлекательных предложений на классифайдах».',
        })
    elif diff is not None and abs(diff) <= 10000:
        strengths.append({
            'tag': 'Цена',
            'title': 'Точное попадание в среднерыночную цену',
            'detail': f'Цена полностью соответствует аналитике Автохаб ({_format_money(hub.get("cna"))}).',
            'script': '«Цена сформирована на основе реальных сделок на рынке, без завышений и скрытых комиссий».',
        })

    # 5. Позиция по привлекательности
    pos = hub.get('position')
    comp = hub.get('competitors')
    if pos and comp and comp >= 5 and pos <= max(3, int(comp * 0.25)):
        strengths.append({
            'tag': 'Рынок',
            'title': f'В топе выдачи Автохаб: {pos}-е место из {comp}',
            'detail': f'Автомобиль входит в топ-{int(round(pos / comp * 100))}% самых привлекательных предложений.',
            'script': '«На классифайдах авто находится в самом топе выдачи. К машине проявляют высокий интерес, поэтому рекомендуем бронировать автомобиль уже сегодня».',
        })

    # 6. Ремонты и обслуживание дилера
    if repairs.get('has_repairs') and repairs.get('outlay', 0) > 0:
        strengths.append({
            'tag': 'Подготовка',
            'title': f'Проведена полная дилерская подготовка на {_format_money(repairs["outlay"])}',
            'detail': f'Выполнено работ и замен: {len(repairs.get("notable_works", []))} позиций в заказ-нарядах.',
            'script': '«Автомобиль прошёл предпродажную подготовку в нашем дилерском центре. Мы устранили недочеты, провели диагностику и вложили в подготовку ' + _format_money(repairs["outlay"]) + ' — вы забираете полностью обслуженную машину».',
        })
    elif repairs.get('count_zn', 0) > 0:
        strengths.append({
            'tag': 'Сервис',
            'title': f'Подтвержденная история обслуживания ({repairs["count_zn"]} заказ-нарядов)',
            'detail': 'Все заказ-наряды сохранены в нашей дилерской системе.',
            'script': '«Вся сервисная история прозрачна: есть официальные заказ-наряды с перечнем работ и запчастей, которые мы можем предоставить».',
        })

    # 7. Комплектация
    complect = getattr(car, 'complectation_autoru', None)
    if complect and complect.name:
        strengths.append({
            'tag': 'Комплектация',
            'title': f'Хорошая комплектация: {complect.name}',
            'detail': 'Повышенный комфорт и ликвидность при последующей перепродаже.',
            'script': f'«Автомобиль в богатой комплектации {complect.name}. Здесь есть всё необходимое для комфортной и безопасной езды».',
        })

    # ==========================
    # МИНУСЫ И ОТРАБОТКА ВОЗРАЖЕНИЙ
    # ==========================

    # 1. Цена выше рынка
    if diff is not None and diff > 15000:
        weaknesses.append({
            'tag': 'Цена',
            'title': f'Цена выше среднерыночной на {_format_money(diff)} (+{hub.get("price_diff_pct")}%)',
            'detail': f'ЦНА: {_format_money(hub.get("cna"))} | Наша цена: {_format_money(car_price)}',
            'objection': '«Почему у вас цена выше рынка? В объявлениях есть похожие машины дешевле».',
            'answer': '«В самых дешёвых объявлениях часто скрыты юридические проблемы, скрученный пробег, тяжелые ДТП или обязательные кредитные страховки на сотни тысяч рублей. У нас цена окончательная, за реальный проверенный автомобиль с юридической гарантией и диагностикой дилера».',
        })

    # 2. Срок на складе
    if days_in_stok >= 45:
        weaknesses.append({
            'tag': 'Склад',
            'title': f'Автомобиль на складе {days_in_stok} дней',
            'detail': f'При среднем сроке продажи на рынке {hub.get("avg_days_in_sale", 30)} дней.',
            'objection': '«Машина уже давно у вас стоит. С ней что-то не так, раз никто не купил?»',
            'answer': '«Автомобиль проходил тщательную предпродажную диагностику и комплексную подготовку на нашем сервисе. Мы не выпускаем авто на витрину в спешке. Сейчас машина полностью проверена, доведена до стандарта дилера и готова к любым проверкам».',
        })

    # 3. Владельцы > 3
    if owners > 3:
        weaknesses.append({
            'tag': 'Документы',
            'title': f'Больше 3 владельцев по ПТС ({owners} владельцев)',
            'detail': 'Может вызывать подозрения у консервативных покупателей.',
            'objection': '«Слишком много хозяев по ПТС. Наверное, проблемная машина?»',
            'answer': '«Нередко смена записей в ПТС связана с переоформлением внутри семьи, сменой номеров или лизингом. Главное — это реальное техническое состояние и юридическая чистота. Мы досконально проверили авто по базам ГИБДД, ФССП и залогов, а также провели 100-точечную диагностику».',
        })

    # 4. Один ключ
    if keys == 1:
        weaknesses.append({
            'tag': 'Комплектность',
            'title': 'Только один ключ зажигания',
            'detail': 'Потребуются затраты на дубликат или переговоры с клиентом.',
            'objection': '«Почему только один ключ? Опасаюсь, вдруг второй у кого-то остался».',
            'answer': '«Предыдущий собственник сдал автомобиль с одним ключом. При оформлении сделки мы можем прямо в нашем дилерском центре прописать новый оригинальный чип-ключ и стереть все старые ключи из памяти иммобилайзера».',
        })

    # 5. Пробег большой
    if run >= 150000:
        weaknesses.append({
            'tag': 'Пробег',
            'title': f'Большой пробег ({run:,} км)'.replace(',', ' '),
            'detail': 'Психологический барьер для многих покупателей.',
            'objection': '«Пробег уже солидный, скоро начнутся крупные поломки».',
            'answer': '«Честный трассовый пробег с регулярным обслуживанием всегда лучше скрученного городского. Этот двигатель и коробка известны своим ресурсом. Диагностика подтвердила отличную компрессию и отсутствие критических ошибок».',
        })

    # 6. Фото устарели или их мало
    if photos.get('is_outdated'):
        weaknesses.append({
            'tag': 'Маркетинг',
            'title': f'Фотосессия устарела ({photos.get("days_ago")} дней назад)',
            'detail': 'Покупатели в сети видят «застоявшееся» объявление.',
            'objection': '«Объявление висит уже больше месяца, фото старые».',
            'answer': '«Автомобиль сейчас на чистой площадке в отличной форме. Давайте осмотрим его вживую — он выглядит намного эффектнее, чем на фото в интернете».',
        })
    elif photos.get('is_few'):
        weaknesses.append({
            'tag': 'Маркетинг',
            'title': f'Мало фотографий в галерее ({photos.get("count")} шт.)',
            'detail': 'Не хватает детальных ракурсов салона, багажника и опций.',
            'objection': '«По фото в объявлении мало что понятно, не видно деталей».',
            'answer': '«Мы готовы прямо сейчас провести для вас видеообзор или показать автомобиль лично в шоуруме во всех ракурсах».',
        })

    # ==========================
    # РЕКОМЕНДАЦИИ ДЛЯ ПРОДАВЦА (ACTION ITEMS)
    # ==========================

    # Рекомендация 1: Фото
    if photos.get('is_few') or photos.get('is_outdated') or not photos.get('has_main'):
        desc_parts = []
        if photos.get('is_few'):
            desc_parts.append(f'загружено всего {photos.get("count")} фото (рекомендуется от 20)')
        if photos.get('is_outdated'):
            desc_parts.append(f'съёмка была {photos.get("days_ago")} дней назад')
        if not photos.get('has_main'):
            desc_parts.append('не назначена главная продающая фотография')

        actions.append({
            'priority': 'danger' if (photos.get('is_outdated') and days_in_stok > 30) else 'warning',
            'title': 'Обновить фотосессию автомобиля',
            'text': f'Сделать свежие качественные фотографии на чистой локации: {", ".join(desc_parts)}. Свежие фото резко поднимают CTR объявления.',
            'icon': 'icon-mbri-photo',
        })

    # Рекомендация 2: Переоценка
    if days_in_stok >= 45 and (diff is not None and diff > 0):
        actions.append({
            'priority': 'danger',
            'title': 'Инициировать переоценку / пересмотр цены',
            'text': f'Автомобиль на складе {days_in_stok} дней, а цена выше ЦНА на {_format_money(diff)}. Необходимо скорректировать цену или пересмотреть этап УС для ускорения оборачиваемости.',
            'icon': 'icon-mbri-cash',
        })
    elif reval.get('days_since_change', 0) >= 30 and days_in_stok >= 30:
        actions.append({
            'priority': 'warning',
            'title': 'Проверить актуальность цены',
            'text': f'Цена не менялась {reval.get("days_since_change")} дней. Проверьте количество звонков и просмотров — возможно, требуется точечная корректировка.',
            'icon': 'icon-mbri-growing-chart',
        })

    # Рекомендация 3: Продвижение на классифайдах
    views_total = hub.get('views_total', 0)
    calls_total = hub.get('calls_total', 0)
    if days_in_stok >= 15 and views_total < 500:
        actions.append({
            'priority': 'warning',
            'title': 'Усилить продвижение на классифайдах',
            'text': f'Низкий трафик: всего {views_total} просмотров и {calls_total} звонков. Рекомендуется подключить пакетное продвижение на Avito/Auto.ru или сменить главное фото.',
            'icon': 'icon-mbri-rocket',
        })

    # Рекомендация 4: Акцент на заказ-наряды
    if repairs.get('has_repairs'):
        actions.append({
            'priority': 'info',
            'title': 'Распечатать заказ-наряды на показ',
            'text': 'При презентации обязательно покажите клиенту перечень выполненных дилерских работ. Это снимает до 80% возражений по торгу.',
            'icon': 'icon-mbri-file',
        })

    # Рекомендация 5: Второй ключ
    if keys == 1:
        actions.append({
            'priority': 'info',
            'title': 'Предложить изготовление второго ключа',
            'text': 'Если клиент колеблется из-за одного ключа — предложите программирование дубликата как бонус при покупке без торга.',
            'icon': 'icon-mbri-key',
        })

    # Рекомендация по умолчанию, если действий мало
    if not actions:
        actions.append({
            'priority': 'success',
            'title': 'Автомобиль полностью готов к активной продаже',
            'text': 'Цена в рынке, фотографии актуальны, подготовка выполнена. Фокусируйтесь на быстром выводе клиента на тест-драйв.',
            'icon': 'icon-mbri-success',
        })

    return strengths, weaknesses, actions


def _calculate_sales_score(car, hub: dict, reval: dict, photos: dict, repairs: dict) -> tuple[int, str]:
    """Рассчитывает оценку ликвидности / привлекательности (1-5 звёзд) и вердикт."""
    score = 3.5

    # Цена
    diff = hub.get('price_diff')
    if diff is not None:
        if diff < -20000:
            score += 0.8
        elif diff < 0:
            score += 0.4
        elif diff > 50000:
            score -= 0.8
        elif diff > 15000:
            score -= 0.4

    # Дни на складе
    days = _int(car.days_in_stok)
    if days <= 20:
        score += 0.4
    elif days >= 60:
        score -= 0.7
    elif days >= 40:
        score -= 0.3

    # Фото
    if photos.get('is_outdated'):
        score -= 0.3
    if photos.get('is_few'):
        score -= 0.2
    if not photos.get('is_few') and not photos.get('is_outdated'):
        score += 0.3

    # Ремонты
    if repairs.get('has_repairs'):
        score += 0.3

    # Владельцы
    owners = _int(car.owners)
    if owners in (1, 2):
        score += 0.3
    elif owners > 3:
        score -= 0.3

    score = max(1.0, min(5.0, score))
    stars = int(round(score))

    verdicts = {
        5: 'Высокая ликвидность — топовое рыночное предложение. Уверенная презентация, торг минимальный.',
        4: 'Хорошая позиция — понятные плюсы перевешивают недочеты. Акцент на дилерскую подготовку.',
        3: 'Средняя ликвидность — требует активной отработки возражений и внимания к цене/фото.',
        2: 'Затрудненная продажа — есть сдерживающие факторы (цена выше рынка или старый фотосет).',
        1: 'Требуется срочное вмешательство — переоценка, пересъёмка или маркетинговая поддержка.',
    }
    return stars, verdicts.get(stars, 'Стандартный вариант продажи.')


def build_seller_brief(car, request=None) -> dict[str, Any]:
    """Главная функция сборки контекста сводки для продавца."""
    ah = _get_latest_avtohub(car)
    hub = _analyze_avtohub(car, ah)
    reval = _analyze_price_revaluations(car)
    photos = _analyze_photos(car)
    repairs = _analyze_repairs(car)

    strengths, weaknesses, actions = _generate_strengths_and_weaknesses(
        car, hub, reval, photos, repairs
    )
    stars, verdict = _calculate_sales_score(car, hub, reval, photos, repairs)

    return {
        'car': car,
        'stars': stars,
        'stars_range': range(1, 6),
        'verdict': verdict,
        'hub': hub,
        'reval': reval,
        'photos': photos,
        'repairs': repairs,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'actions': actions,
        'has_actions': bool(actions),
        'strengths_count': len(strengths),
        'weaknesses_count': len(weaknesses),
        'actions_count': len(actions),
    }
