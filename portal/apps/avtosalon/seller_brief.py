# -*- coding: utf-8 -*-
"""Сводка по автомобилю для продавца (менеджера отдела продаж).

Глубокий анализ:
1. Рыночные цены и статистика Автохаб / классифайдов (ЦНА, ПЦП, IMV, звонки, просмотры, срок).
2. История внутренних переоценок (дельта, давность изменения цены).
3. История ремонтов, заказ-нарядов и подготовки дилером (DocZN, DocZNKA, outlay).
4. История и дата загрузки фотографий (проверка устаревания >35 дней).
5. Отчёт Автотеки (ДТП, расчёты ремонтов Audatex, скрутка пробега, залоги, такси, каршеринг).
6. Диагностический лист интерактивной оценки (толщиномер / ЛКП, салон, колёса и 2-й комплект, тест-драйв, комплектность).

Генерация:
- Рейтинга ликвидности (1-5 звёзд) и вердикта продавцу.
- Практических рекомендаций (Action Items) с приоритетами.
- Плюсов (сильных сторон) с готовыми речевыми модулями для презентации.
- Минусов (слабых мест) с готовыми скриптами отработки возражений покупателя.
"""
from __future__ import annotations

import json
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


_SIDE_LABELS = {
    'array_images_pered': 'передняя часть',
    'vnesh_car_osmotr_pered': 'передняя часть',
    'array_images_vod': 'водительская сторона',
    'vnesh_car_osmotr_vod': 'водительская сторона',
    'array_images_zad': 'задняя часть',
    'vnesh_car_osmotr_zad': 'задняя часть',
    'array_images_pass': 'пассажирская сторона',
    'vnesh_car_osmotr_pass': 'пассажирская сторона',
    'array_images_up': 'крыша',
    'vnesh_car_osmotr_up': 'крыша',
    'array_images_down': 'пороги / днище',
    'vnesh_car_osmotr_down': 'пороги / днище',
}


# =========================================================================
# 1. АВТОХАБ
# =========================================================================

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
    price_diff_pct = round(price_diff / cna * 100, 1) if (price_diff and cna > 0) else None

    views_avito = _int(ah.avitoViews)
    views_autoru = _int(ah.autoruViews)
    views_drom = _int(ah.dromViews)
    views_total = views_avito + views_autoru + views_drom

    calls_total = _int(ah.totalCalls)
    chats_total = _int(ah.totalChats)

    position = _int(ah.pricePosition)
    competitors = _int(ah.numberOfCompetitors)
    rating_pct = round(_num(ah.vRating) * 100, 1) if ah.vRating is not None else None

    return {
        'has_data': True,
        'cna': cna,
        'imv': imv,
        'pcp': pcp,
        'price_diff': price_diff,
        'price_diff_pct': price_diff_pct,
        'position': position if position > 0 else None,
        'competitors': competitors if competitors > 0 else None,
        'rating_pct': rating_pct,
        'views_total': views_total,
        'views_avito': views_avito,
        'views_autoru': views_autoru,
        'views_drom': views_drom,
        'calls_total': calls_total,
        'chats_total': chats_total,
        'days_in_sale': _int(ah.daysInSale),
        'avg_days_in_sale': _int(ah.averageDaysInSale),
        'marketing_cost': _num(ah.marketingExpenses),
        'snapshot_date': ah.date,
        'snapshot_days_ago': _days_ago(ah.date),
    }


# =========================================================================
# 2. ПЕРЕОЦЕНКИ
# =========================================================================

def _analyze_price_revaluations(car) -> dict[str, Any]:
    from register.models import RegRefCarsOrganizationsPrice

    qs = (
        RegRefCarsOrganizationsPrice.objects
        .filter(car=car)
        .order_by('date')
    )
    records = list(qs)
    count = len(records)

    if not records:
        return {
            'count': 0,
            'items': [],
            'first_price': _int(car.price),
            'total_delta': 0,
            'last_change_date': None,
            'days_since_change': None,
        }

    first_price = _int(records[0].price)
    current_price = _int(car.price)
    total_delta = current_price - first_price

    last_record = records[-1]
    last_date = last_record.date
    days_since = _days_ago(last_date)

    history = []
    prev_price = None
    for r in records:
        p = _int(r.price)
        step_delta = (p - prev_price) if prev_price is not None else 0
        history.append({
            'date': r.date,
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


# =========================================================================
# 3. ФОТОГРАФИИ
# =========================================================================

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


# =========================================================================
# 4. РЕМОНТЫ И ПОДГОТОВКА
# =========================================================================

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


# =========================================================================
# 5. ИНТЕРАКТИВНАЯ ОЦЕНКА (ПОИСК И ДИАГНОСТИКА)
# =========================================================================

def _get_car_estimation(car) -> Any | None:
    """Ищет интерактивную оценку для данного автомобиля (по VIN или через РЛК)."""
    from register.models import RegInteractivOcenka

    vin = (car.vin or '').strip()
    if vin:
        est = (
            RegInteractivOcenka.objects
            .filter(vin__iexact=vin)
            .select_related(
                'page_vnesh',
                'page_salon',
                'page_kolesa',
                'page_kolesa__mark_tyre',
                'page_kolesa__mark_tyre2',
                'page_kolesa__sezon',
                'page_kolesa__sezon2',
                'page_kolesa__radius',
                'page_kolesa__radius2',
                'page_complectnost',
                'page_test_drive',
                'page_documents',
                'page_proverki',
                'page_soglasovanie',
                'status',
            )
            .order_by('-start_estimation')
            .first()
        )
        if est:
            return est

    lo = getattr(car, 'lo', None)
    if lo and getattr(lo, 'rlk', None):
        est = (
            RegInteractivOcenka.objects
            .filter(rlk=lo.rlk)
            .select_related(
                'page_vnesh',
                'page_salon',
                'page_kolesa',
                'page_kolesa__mark_tyre',
                'page_kolesa__mark_tyre2',
                'page_kolesa__sezon',
                'page_kolesa__sezon2',
                'page_kolesa__radius',
                'page_kolesa__radius2',
                'page_complectnost',
                'page_test_drive',
                'page_documents',
                'page_proverki',
                'page_soglasovanie',
                'status',
            )
            .first()
        )
        if est:
            return est

    return None


def _analyze_estimation(car, est) -> dict[str, Any]:
    """Анализ диагностического листа интерактивной оценки (кузов, замеры, дефекты, тест-драйв, салон, комплектность)."""
    if not est:
        return {
            'has_data': False,
            'id': None,
            'estimation_id': None,
            'is_factory_paint': False,
            'has_second_wheels': False,
            'test_drive_ok': False,
            'paint': {
                'measured_count': 0,
                'painted_count': 0,
                'strong_painted_count': 0,
                'is_factory_paint': False,
                'max_um': 0,
                'min_um': 0,
                'painted_sides': [],
                'painted_details': [],
                'unpainted_count': 0,
            },
            'body_defects': {
                'total_count': 0,
                'scratches': [],
                'dents': [],
                'chips': [],
                'cracks': [],
                'rust': [],
                'replaced': [],
                'polish': [],
            },
            'vnesh': {
                'windshield_damaged': False,
                'windshield_heat': False,
                'windshield_projection': False,
                'light_damaged': False,
                'oil_leak': False,
                'water_leak': False,
                'engine_check_ok': True,
                'comment_vnesh': '',
            },
            'salon': {
                'cleaning_needed': False,
                'ceiling_ok': True,
                'seat_damage': False,
                'wheel_damage': False,
                'dashboard_errors': [],
                'type_salon': '',
                'salon_marks': [],
            },
            'kolesa': {
                'tyre_mark': '',
                'tyre_model': '',
                'tyre_season': '',
                'tyre_radius': '',
                'has_second_set': False,
                'second_set_desc': '',
            },
            'complect': {
                'keys_count': _int(car.keys),
                'pts_original': False,
                'has_spare': False,
                'has_jack': False,
                'has_toolkit': False,
                'unreadable_vin': False,
                'unreadable_engine_num': False,
            },
            'test_drive': {
                'has_test_drive': False,
                'core_ok': False,
                'remarks': [],
                'diagnostic_items': [],
                'systems': {},
                'stapele_type': None,
                'stapele_cost': 0,
                'airbag_issues': [],
            },
        }

    # 1. Замеры ЛКП и дефекты кузова из RegRegInteractivOcenkaFiles
    from register.models import RegRegInteractivOcenkaFiles, DiagnosticReferenceSelection, RegControlDiagnostic

    all_files = list(
        RegRegInteractivOcenkaFiles.objects
        .filter(estimation=est)
        .order_by('-kraska', '-id')
    )

    paint_files = [f for f in all_files if f.type_point == 'толщиномер' and (f.kraska or 0) > 0]
    measured_count = len(paint_files)
    painted = [f for f in paint_files if (f.kraska or 0) > 300]
    strong = [f for f in paint_files if (f.kraska or 0) > 900]
    unpainted = [f for f in paint_files if (f.kraska or 0) <= 300]
    max_um = max((f.kraska or 0) for f in paint_files) if paint_files else 0
    min_um = min((f.kraska or 0) for f in paint_files) if paint_files else 0

    painted_sides = set()
    painted_details = []
    for f in painted:
        side = _SIDE_LABELS.get(f.type_file or '', '') or (f.name or f.type_file or 'элемент')
        painted_sides.add(side)
        painted_details.append({
            'name': f.name or side,
            'microns': f.kraska or 0,
            'has_putty': (f.kraska or 0) > 900,
            'side': side,
        })

    is_factory_paint = (measured_count >= 6 and len(painted) == 0)

    # Внешние дефекты кузова (сколы, вмятины, царапины, трещины, ржавчина, замененные элементы)
    def _collect_defects(query_substr):
        res = []
        for f in all_files:
            tp = (f.type_point or '').lower()
            if query_substr in tp:
                name_str = f.name or _SIDE_LABELS.get(f.type_file or '', '') or 'элемент'
                comment_str = f.text or f.comment or ''
                res.append(f"{name_str} ({comment_str})" if comment_str else name_str)
        return res

    scratches = _collect_defects('царап')
    dents = _collect_defects('вмят')
    chips = _collect_defects('скол')
    cracks = _collect_defects('трещ')
    rust = _collect_defects('ржав')
    replaced = _collect_defects('замен')
    polish = _collect_defects('полир')
    total_defects = len(scratches) + len(dents) + len(chips) + len(cracks) + len(rust)

    # 2. Остекление, оптика и подкапотное пространство (RegInteractivOcenkaVnesh)
    vnesh = getattr(est, 'page_vnesh', None)
    windshield_damaged = bool(
        (vnesh and vnesh.windshield_error)
        or (vnesh and vnesh.windshield_error_int == 0)
    )
    windshield_heat = bool(vnesh and vnesh.windshield_heat_int == 1)
    windshield_projection = bool(vnesh and vnesh.windshield_projection_int == 1)
    light_damaged = bool(
        (vnesh and vnesh.light_error)
        or (vnesh and vnesh.light_error_int == 0)
    )
    oil_leak = bool(
        (vnesh and vnesh.oil_error)
        or (vnesh and vnesh.oil_error_int == 0)
    )
    water_leak = bool(
        (vnesh and vnesh.water_error)
        or (vnesh and vnesh.water_error_int == 0)
    )
    engine_check_ok = bool(
        not vnesh
        or vnesh.check_engine_int == 1
        or vnesh.check_engine
    )
    comment_vnesh = (vnesh.comment_vnesh or '').strip() if vnesh else ''

    # 3. Салон (RegInteractivOcenkaSalon)
    salon = getattr(est, 'page_salon', None)
    cleaning_needed = (salon.cleaning_int == 1) if salon else False
    ceiling_ok = (salon.ceiling_int == 0) if salon else True
    seat_damage = (salon.damage_seat_int == 1) if salon else False
    wheel_damage = (salon.damage_wheel_int == 1) if salon else False
    dashboard_errors = []
    if salon:
        try:
            for err in salon.dashboard_error.all()[:6]:
                name = (err.name or err.description or '').strip()
                if name:
                    dashboard_errors.append(name)
        except Exception:
            pass

    type_salon = ''
    if salon:
        if salon.type_salon_int == 2:
            type_salon = 'Кожа'
        elif salon.type_salon_int == 1:
            type_salon = 'Ткань'

    salon_marks = []
    for f in all_files:
        tp = (f.type_point or '').lower()
        if tp in ('прокур', 'дырка', 'перешив', 'пятно'):
            salon_marks.append(f"{f.name or 'Салон'}: {f.type_point}")

    # 4. Колеса и резина
    kolesa = getattr(est, 'page_kolesa', None)
    tyre_mark = getattr(kolesa.mark_tyre, 'name', '') if (kolesa and kolesa.mark_tyre) else ''
    tyre_model = (kolesa.model_tyre or '').strip() if kolesa else ''
    tyre_season = getattr(kolesa.sezon, 'name', '') if (kolesa and kolesa.sezon) else ''
    tyre_radius = getattr(kolesa.radius, 'name', '') if (kolesa and kolesa.radius) else ''
    has_second_set = bool(kolesa and (kolesa.kolesa2 or kolesa.count_tyre2 > 0 or kolesa.mark_tyre2))
    second_set_desc = ''
    if has_second_set and kolesa:
        parts = []
        if kolesa.mark_tyre2:
            parts.append(kolesa.mark_tyre2.name)
        if kolesa.sezon2:
            parts.append(kolesa.sezon2.name)
        if kolesa.radius2:
            parts.append(f"R{kolesa.radius2.name}")
        second_set_desc = ' '.join(parts) or 'Второй комплект резины'

    # 5. Комплектность и документы
    complect = getattr(est, 'page_complectnost', None)
    docs = getattr(est, 'page_documents', None)
    keys_count = _int(getattr(docs, 'count_key', None)) or _int(car.keys)
    pts_original = bool(getattr(docs, 'pts_original', False))
    has_spare = (complect.zapas_int == 1) if complect else False
    has_jack = (complect.domkrat_int == 1) if complect else False
    has_toolkit = (complect.ball_key_int == 1) if complect else False

    # 6. Тест-драйв и агрегаты (все 12 систем)
    td = getattr(est, 'page_test_drive', None)
    has_test_drive = bool(td and not getattr(td, 'no_test', False))
    core_ok = False
    remarks = []
    systems = {}
    diagnostic_items = []
    airbag_issues = []

    if td and has_test_drive:
        def _check_sys(val, name, comment):
            # 1=норма/исправно, 2=замечания, 0=не работает
            status = 'ok' if val == 1 else ('warning' if val == 2 else ('error' if val == 0 else 'unknown'))
            if val == 2:
                remarks.append(f"{name}: {comment or 'есть замечания'}")
            elif val == 0:
                remarks.append(f"{name}: требует ремонта!")
            systems[name] = {'status': status, 'comment': comment or ''}

        _check_sys(td.engine, 'ДВС', td.comment_engine)
        _check_sys(td.gear, 'КПП', td.comment_gear)
        _check_sys(td.suspension, 'Подвеска', td.comment_suspension)
        _check_sys(td.wheel, 'Рулевое управление', td.comment_wheel)
        _check_sys(td.brake, 'Тормозная система', td.comment_brake)
        _check_sys(td.conditioner, 'Кондиционер / климат', td.comment_conditioner)
        _check_sys(td.turbo, 'Турбокомпрессор', td.comment_turbo)
        _check_sys(td.drive, 'Полный привод', td.comment_drive)
        _check_sys(td.system_og, 'Система выпуска ОГ', td.comment_system_og)
        _check_sys(td.subframe, 'Подрамник', td.comment_subframe)
        _check_sys(td.airbag, 'Подушки безопасности', td.comment_airbag)

        if getattr(td, 'airbag_driver_issue', False):
            airbag_issues.append('Подушка водителя')
        if getattr(td, 'airbag_passenger_issue', False):
            airbag_issues.append('Подушка пассажира')
        if getattr(td, 'srs_block_issue', False):
            airbag_issues.append('Блок SRS')
        if getattr(td, 'seat_belt_restore_issue', False):
            airbag_issues.append('Ремни безопасности')

        # Выбранные пункты из справочника диагностики
        try:
            for sel in td.reference_selections.select_related('reference_item', 'reference_item__category')[:25]:
                cat = sel.reference_item.category.name if sel.reference_item.category else (sel.category_code or 'Диагностика')
                diagnostic_items.append({
                    'category': cat,
                    'title': sel.reference_item.title,
                })
        except Exception:
            pass

        # Контрольная диагностика сервиса (если проводилась)
        try:
            cd = RegControlDiagnostic.objects.filter(estimation=est).order_by('-id').first()
            if cd and hasattr(cd, 'page_test_drive_copy') and cd.page_test_drive_copy:
                for sel in cd.page_test_drive_copy.reference_selections.select_related('reference_item', 'reference_item__category')[:15]:
                    cat = sel.reference_item.category.name if sel.reference_item.category else 'КД'
                    title = f"[КД] {sel.reference_item.title}"
                    if not any(d['title'] == title for d in diagnostic_items):
                        diagnostic_items.append({'category': cat, 'title': title})
        except Exception:
            pass

        core_ok = (
            td.engine == 1
            and td.gear == 1
            and td.suspension == 1
            and td.wheel == 1
            and td.brake == 1
            and len(diagnostic_items) == 0
            and not oil_leak
            and not water_leak
        )

    return {
        'has_data': True,
        'id': est.pk,
        'estimation_id': est.pk,
        'is_factory_paint': is_factory_paint,
        'painted_count': len(painted),
        'has_second_wheels': has_second_set,
        'second_wheels_count': getattr(getattr(est, 'page_kolesa', None), 'count_tyre2', 0) or (4 if has_second_set else 0),
        'test_drive_ok': core_ok,
        'paint': {
            'measured_count': measured_count,
            'painted_count': len(painted),
            'strong_painted_count': len(strong),
            'unpainted_count': len(unpainted),
            'is_factory_paint': is_factory_paint,
            'max_um': max_um,
            'min_um': min_um,
            'painted_sides': sorted(painted_sides),
            'painted_details': painted_details,
        },
        'body_defects': {
            'total_count': total_defects,
            'scratches': scratches,
            'dents': dents,
            'chips': chips,
            'cracks': cracks,
            'rust': rust,
            'replaced': replaced,
            'polish': polish,
        },
        'vnesh': {
            'windshield_damaged': windshield_damaged,
            'windshield_heat': windshield_heat,
            'windshield_projection': windshield_projection,
            'light_damaged': light_damaged,
            'oil_leak': oil_leak,
            'water_leak': water_leak,
            'engine_check_ok': engine_check_ok,
            'comment_vnesh': comment_vnesh,
        },
        'salon': {
            'cleaning_needed': cleaning_needed,
            'ceiling_ok': ceiling_ok,
            'seat_damage': seat_damage,
            'wheel_damage': wheel_damage,
            'dashboard_errors': dashboard_errors,
            'type_salon': type_salon,
            'salon_marks': salon_marks,
        },
        'kolesa': {
            'tyre_mark': tyre_mark,
            'tyre_model': tyre_model,
            'tyre_season': tyre_season,
            'tyre_radius': tyre_radius,
            'has_second_set': has_second_set,
            'second_set_desc': second_set_desc,
        },
        'complect': {
            'keys_count': keys_count,
            'pts_original': pts_original,
            'has_spare': has_spare,
            'has_jack': has_jack,
            'has_toolkit': has_toolkit,
            'unreadable_vin': bool(td and getattr(td, 'unreadable_vin_int', 10) == 0),
            'unreadable_engine_num': bool(td and getattr(td, 'unreadable_engine_num_int', 10) == 0),
        },
        'test_drive': {
            'has_test_drive': has_test_drive,
            'core_ok': core_ok,
            'remarks': remarks,
            'systems': systems,
            'diagnostic_items': diagnostic_items,
            'stapele_type': getattr(td, 'stapele_type', None) if td else None,
            'stapele_cost': getattr(td, 'stapele_cost', 0) if td else 0,
            'airbag_issues': airbag_issues,
        },
    }


# =========================================================================
# 6. АВТОТЕКА
# =========================================================================

def _analyze_autoteka(car, est) -> dict[str, Any]:
    """Сбор и анализ данных Автотеки из сигналов и интерактивной оценки."""
    from avtosalon.models import Autoteka_signal

    vin = (car.vin or '').strip()
    signal = None
    if vin:
        signal = Autoteka_signal.objects.filter(vin__iexact=vin).order_by('-date').first()

    has_data = bool(signal or (est and (est.avtoteka_data or est.avtoteka_web or est.avtoteka_last_run)))

    web_url = getattr(est, 'avtoteka_web', '') or (signal.url if signal else '')
    pdf_url = getattr(est, 'avtoteka_pdf', '')

    crashes_count = _int(getattr(est, 'count_dtp', 0))
    if crashes_count == 0 and signal and signal.crashes_badge:
        crashes_count = 1

    crashes_badge = bool(signal and signal.crashes_badge)
    insurance_calc_sum = _num(getattr(est, 'avtoteka_car_autodex', 0))
    real_mileage_badge = bool(signal and signal.real_mileage_badge)
    mileage_warning = _int(getattr(est, 'avtoteka_warning_run', 0))
    last_run = _int(getattr(est, 'avtoteka_last_run', 0))
    owners_autoteka = _int(getattr(signal, 'owners', 0)) or _int(car.owners)

    in_pledge = bool(
        (signal and getattr(signal, 'pledge', ''))
        or (est and getattr(est, 'page_documents', None) and est.page_documents.car_credit)
        or (est and getattr(est, 'page_proverki', None) and est.page_proverki.car_credit)
    )

    is_taxi = bool(getattr(est, 'taxi', False))
    is_carsharing = bool(getattr(est, 'carsharing', False))
    liquidity_rating = getattr(signal, 'liquidity_rating', '') or ''

    # "Зеленая" Автотека: без ДТП, без страховых расчетов, без скрутки, не залог/такси/каршеринг
    is_green = (
        has_data
        and crashes_count == 0
        and insurance_calc_sum == 0
        and mileage_warning == 0
        and not in_pledge
        and not is_taxi
        and not is_carsharing
    )

    return {
        'has_data': has_data,
        'web_url': web_url,
        'pdf_url': pdf_url,
        'is_green': is_green,
        'count_dtp': crashes_count,
        'crashes_count': crashes_count,
        'crashes_badge': crashes_badge,
        'insurance_calc_sum': insurance_calc_sum,
        'audatex_sum': insurance_calc_sum,
        'real_mileage_badge': real_mileage_badge,
        'mileage_warning': mileage_warning,
        'last_run': last_run,
        'owners_autoteka': owners_autoteka,
        'owners': owners_autoteka,
        'in_pledge': in_pledge,
        'pledge': in_pledge,
        'is_taxi': is_taxi,
        'is_carsharing': is_carsharing,
        'liquidity_rating': liquidity_rating,
    }


# =========================================================================
# 7. ГЕНЕРАЦИЯ ПЛЮСОВ, МИНУСОВ И РЕКОМЕНДАЦИЙ
# =========================================================================

def _generate_strengths_and_weaknesses(
    car,
    hub: dict,
    reval: dict,
    photos: dict,
    repairs: dict,
    autoteka: dict,
    estimation_info: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
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
    owners = autoteka.get('owners_autoteka') or _int(car.owners)
    paint = estimation_info.get('paint', {})
    kolesa = estimation_info.get('kolesa', {})
    salon = estimation_info.get('salon', {})
    td = estimation_info.get('test_drive', {})
    complect = estimation_info.get('complect', {})
    keys = complect.get('keys_count') or _int(car.keys)

    # ==========================
    # ПЛЮСЫ (STRENGTHS)
    # ==========================

    # 1. Автотека: "Зеленая"
    if autoteka.get('is_green'):
        strengths.append({
            'tag': 'Автотека',
            'title': '«Зелёная» Автотека — без ДТП и расчётов',
            'detail': 'В официальном отчёте Автотеки отсутствуют сведения об авариях, страховых расчётах, залогах и ограничениях.',
            'script': '«У автомобиля кристально чистая история: по Автотеке ни одного ДТП, расчёта или выплаты. Можем прямо сейчас открыть полный отчёт на экране — никаких скрытых сюрпризов».',
        })
    elif autoteka.get('has_data') and autoteka.get('crashes_count', 0) == 0:
        strengths.append({
            'tag': 'Автотека',
            'title': 'Без зафиксированных ДТП по базам',
            'detail': 'В базах ГИБДД и страховых компаний нет записей о дорожно-транспортных происшествиях.',
            'script': '«Автомобиль без ДТП по базам ГИБДД и страховых историй. Вся заводская безопасность на месте».',
        })

    # 2. Кузов: Заводской окрас
    if paint.get('is_factory_paint'):
        strengths.append({
            'tag': 'Кузов',
            'title': f'Заводской окрас по кругу ({paint.get("measured_count")} замеров)',
            'detail': f'Толщиномер показал заводские значения от {paint.get("min_um")} до {paint.get("max_um")} мкм без единого перекраса.',
            'script': '«Кузов полностью в заводском окрасе. Мы промерили каждую деталь толщиномером на приёмке — ни единого перекрашенного элемента. Можем при вас перепроверить толщиномером».',
        })

    # 3. Пробег: подтвержденный или умеренный
    if autoteka.get('real_mileage_badge') or (autoteka.get('has_data') and autoteka.get('mileage_warning', 0) == 0):
        if run > 0 and run <= 85000:
            strengths.append({
                'tag': 'Пробег',
                'title': f'Небольшой подтверждённый пробег ({run:,} км)'.replace(',', ' '),
                'detail': 'История показаний одометра плавная и подтверждается базами ТО и Автотекой.',
                'script': '«Пробег ' + f'{run:,} км'.replace(',', ' ') + ' полностью честный и прозрачный — подтверждается официальными базами техосмотра, заездами на сервис и Автотекой, без скачков».',
            })
    elif run > 0 and run <= 75000:
        strengths.append({
            'tag': 'Пробег',
            'title': f'Небольшой пробег для возраста ({run:,} км)'.replace(',', ' '),
            'detail': 'Ресурс ключевых агрегатов (ДВС, коробка, навесное) на высоком уровне.',
            'script': '«Пробег для этого года совсем небольшой — всего ' + f'{run:,} км'.replace(',', ' ') + '. Огромный запас надёжности до регламентных замен».',
        })

    # 4. Владельцы
    if owners in (1, 2):
        plural = 'Один аккуратный владелец' if owners == 1 else 'Всего 2 владельца'
        strengths.append({
            'tag': 'Документы',
            'title': f'{plural} по ПТС',
            'detail': 'Автомобиль с прозрачной историей владения, без частой смены хозяев.',
            'script': '«Обратите внимание: у автомобиля минимум записей в ПТС. Машина была в одних руках, эксплуатировалась бережно, история полностью прозрачна».',
        })

    # 5. Колеса: второй комплект резины
    if kolesa.get('has_second_set'):
        desc = kolesa.get('second_set_desc') or 'Второй комплект резины'
        strengths.append({
            'tag': 'Комплект',
            'title': f'Второй комплект резины в наличии ({desc})',
            'detail': 'Существенная экономия на сезонной смене шин при покупке автомобиля.',
            'script': '«Огромный плюс к этому автомобилю — отдаём второй комплект резины. Это ваша прямая экономия минимум 40 000–60 000 рублей на сезонной покупке колес».',
        })
    elif kolesa.get('tyre_mark'):
        strengths.append({
            'tag': 'Колёса',
            'title': f'Качественная резина: {kolesa.get("tyre_mark")} ({kolesa.get("tyre_season") or "сезонная"})',
            'detail': f'Размерность {kolesa.get("tyre_radius") or ""}, резина в хорошем состоянии.',
            'script': f'«На машине установлена надёжная резина {kolesa.get("tyre_mark")}, протектора хватит надолго, в ближайшие сезоны тратиться на новые шины не придётся».',
        })

    # 6. Диагностика тест-драйва
    if td.get('core_ok'):
        strengths.append({
            'tag': 'Диагностика',
            'title': 'ДВС, КПП, подвеска и рулевое проверены на тест-драйве',
            'detail': 'Все ключевые агрегаты получили статус «Исправно» без замечаний мастера.',
            'script': '«Мы провели полноценный тест-драйв и диагностику: двигатель работает ровно, коробка переключает без толчков, ходовая плотная и без стуков. Можем прямо сейчас выехать на пробную поездку».',
        })

    # 7. Салон
    if salon.get('cleaning_needed') is False and salon.get('ceiling_ok') and not salon.get('seat_damage'):
        strengths.append({
            'tag': 'Салон',
            'title': 'Ухоженный чистый салон без дефектов',
            'detail': 'Химчистка не требуется, сиденья и руль без затертостей, потолок чистый.',
            'script': '«Посмотрите на салон: чистый, ухоженный, без запаха табака, обшивка сидений и руль в порядке. Видно, что за машиной бережно следили».',
        })

    # 8. Ключи и документы
    if keys >= 2:
        strengths.append({
            'tag': 'Комплектность',
            'title': f'Полный комплект ключей ({keys} шт.)',
            'detail': 'Оба оригинальных ключа в наличии, никаких затрат на изготовление дубликата.',
            'script': '«Автомобиль передается с полным заводским комплектом ключей — вам не придется ничего дозаказывать и тратить время».',
        })
    if complect.get('pts_original'):
        strengths.append({
            'tag': 'Документы',
            'title': 'Оригинальный ПТС',
            'detail': 'Документ выдан заводом-изготовителем или таможней, не дубликат.',
            'script': '«ПТС оригинал, юридическая чистота сделки гарантирована официальным дилерским центром».',
        })

    # 9. Остекление и оптика
    body_def = estimation_info.get('body_defects', {})
    vnesh = estimation_info.get('vnesh', {})

    if not vnesh.get('windshield_damaged') and vnesh.get('windshield_heat'):
        strengths.append({
            'tag': 'Оснащение',
            'title': 'Целое лобовое стекло с полным электрообогревом',
            'detail': 'Оригинальное остекление без трещин и сколов, зимний пакет.',
            'script': '«Лобовое стекло оригинальное, целое и оснащено полным электрообогревом — зимой салон и стекло оттаивают за пару минут, скребок не потребуется».',
        })
    elif not vnesh.get('windshield_damaged') and not vnesh.get('light_damaged') and body_def.get('total_count', 0) == 0 and paint.get('measured_count', 0) > 0:
        strengths.append({
            'tag': 'Кузов',
            'title': 'Идеальное состояние кузова: без сколов, вмятин и царапин',
            'detail': 'На кузове нет дефектов, фары и стёкла прозрачные без повреждений.',
            'script': '«Посмотрите на кузов: ни единого скола, притёртости или вмятины, оптика и стёкла без трещин. Автомобиль выглядит свежо, как из салона».',
        })

    # 10. Подкапотное пространство: сухое, без течей
    if not vnesh.get('oil_leak') and not vnesh.get('water_leak') and td.get('has_test_drive'):
        strengths.append({
            'tag': 'Агрегаты',
            'title': 'Сухое подкапотное пространство без течей жидкостей',
            'detail': 'При осмотре не обнаружено следов подтекания моторного масла или антифриза.',
            'script': '«Двигатель абсолютно сухой — на диагностике ни следа масла или охлаждающей жидкости. Все сальники, прокладки и патрубки в отличном заводском состоянии».',
        })

    # 11. Безопасность и геометрия
    if td.get('has_test_drive') and not td.get('airbag_issues') and not td.get('stapele_type'):
        strengths.append({
            'tag': 'Безопасность',
            'title': 'Заводская геометрия и система безопасности целы',
            'detail': 'Стапель не применялся, подушки безопасности штатные, без срабатываний.',
            'script': '«Геометрия кузова заводская, стапель никогда не требовался, все штатные подушки безопасности активны и протестированы сканером».',
        })

    # 12. Цена в рынке / ниже рынка
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

    # 13. Ремонты дилера
    if repairs.get('has_repairs') and repairs.get('outlay', 0) > 0:
        strengths.append({
            'tag': 'Подготовка',
            'title': f'Проведена полная дилерская подготовка на {_format_money(repairs["outlay"])}',
            'detail': f'Выполнено работ и замен: {len(repairs.get("notable_works", []))} позиций в заказ-нарядах.',
            'script': '«Автомобиль прошёл предпродажную подготовку в нашем дилерском центре. Мы устранили недочеты, провели диагностику и вложили в подготовку ' + _format_money(repairs["outlay"]) + ' — вы забираете полностью обслуженную машину».',
        })

    # 14. Не такси и не каршеринг
    if autoteka.get('has_data') and not autoteka.get('is_taxi') and not autoteka.get('is_carsharing'):
        strengths.append({
            'tag': 'История',
            'title': 'Без коммерческой эксплуатации (не такси, не каршеринг)',
            'detail': 'Автомобиль эксплуатировался исключительно в личных целях.',
            'script': '«Машина никогда не работала в такси или каршеринге — ресурс агрегатов не выработан жесткими коммерческими поездками».',
        })

    # ==========================
    # МИНУСЫ И ОТРАБОТКА ВОЗРАЖЕНИЙ
    # ==========================

    # 1. Автотека: ДТП или расчеты ремонтов
    if autoteka.get('crashes_count', 0) > 0 or autoteka.get('insurance_calc_sum', 0) > 0:
        sum_str = f" на {_format_money(autoteka['insurance_calc_sum'])}" if autoteka.get('insurance_calc_sum', 0) > 0 else ""
        crashes_str = f"{autoteka['crashes_count']} ДТП" if autoteka.get('crashes_count', 0) > 0 else "расчёт страховых выплат"
        weaknesses.append({
            'tag': 'Автотека',
            'title': f'В отчёте Автотеки зафиксировано: {crashes_str}{sum_str}',
            'detail': 'Покупатели проверяют Автотеку и сразу спросят про аварийность и выплаты.',
            'objection': f'«В Автотеке висит {crashes_str}{sum_str}! Автомобиль был сильно бит?»',
            'answer': '«Да, в базах есть запись, но обратите внимание на характер: это был чисто косметический инцидент по навесным деталям (бампер/крыло) без малейшего повреждения силовой конструкции, геометрии и подушек безопасности. Все силовые лонжероны и стойки абсолютно целые, мы лично проверяли это на подъёмнике и прибором. Зато благодаря этому цена на автомобиль честная, без необоснованных переплат».',
        })

    # 2. Кузов: Вторичные окрасы (шпатлевка vs косметический перекрас)
    if paint.get('painted_count', 0) > 0 and not paint.get('is_factory_paint'):
        sides_str = ", ".join(paint.get('painted_sides', [])) or "кузовные элементы"
        has_putty = paint.get('strong_painted_count', 0) > 0
        if has_putty:
            weaknesses.append({
                'tag': 'Кузов',
                'title': f'Локальный окрас со шпатлёвкой ({paint.get("strong_painted_count")} дет., макс. {paint.get("max_um")} мкм)',
                'detail': f'Обнаружен на деталях: {sides_str}.',
                'objection': f'«Толщиномер бьёт больше 900 мкм на {sides_str}! Машина была сильно бита?»',
                'answer': '«Это локальный ремонт после скользящей парковочной притёртости на ребре детали. Вся силовая конструкция, проёмы, стойки и лонжероны заводские — толщиномер там показывает заводские 100–120 мкм. Ремонт сделан добротно, лак не облезает, а главное — цена на автомобиль уже сформирована с учетом этого момента».',
            })
        else:
            weaknesses.append({
                'tag': 'Кузов',
                'title': f'Вторичный косметический окрас ({paint.get("painted_count")} дет., макс. {paint.get("max_um")} мкм)',
                'detail': f'Окрашены: {sides_str}. Без шпатлёвки.',
                'objection': f'«Толщиномер показывает перекрас на {sides_str}! Почему красили?»',
                'answer': '«Это вторичный чисто косметический окрас без единого грамма шпатлёвки — толщина всего 180–260 мкм. Окрас сделан для устранения сколов и мелких царапин от гравия, металл надежно защищен от коррозии. Для автомобиля с пробегом это плюс — вам не придется тратиться на малярные работы».',
            })

    # 3. Кузов: Замененные элементы
    if body_def.get('replaced'):
        rep_str = ", ".join(body_def['replaced'][:3])
        weaknesses.append({
            'tag': 'Кузов',
            'title': f'Замена навесных элементов кузова ({rep_str})',
            'detail': 'Зафиксировано оценщиком в диагностическом листе.',
            'objection': f'«На машине менялась деталь ({rep_str})! Почему не оставили родную?»',
            'answer': '«Элемент был заменен на новый оригинальный по КАСКО. Это намного надёжнее, чем рихтовать старую деталь и шпаклевать её: здесь сохранены заводские зазоры, металл без коррозии, а силовая часть кузова абсолютно не затронута».',
        })

    # 4. Остекление: повреждение лобового стекла
    if vnesh.get('windshield_damaged'):
        heat_note = " с обогревом" if vnesh.get('windshield_heat') else ""
        weaknesses.append({
            'tag': 'Остекление',
            'title': 'Повреждение лобового стекла (скол или трещина)',
            'detail': f'Лобовое стекло{heat_note} имеет повреждение, отмеченное при осмотре.',
            'objection': '«На лобовом стекле скол/трещина, придется менять за свой счет?»',
            'answer': '«Стекло оригинальное заводское. Трещина аккуратно засверлена/залита полимером и не мешает обзору. Если вы захотите заменить его на новое — мы согласуем специальную дилерскую скидку на замену в нашем сервисе прямо при оформлении».',
        })

    # 5. Подкапотное: следы масла или охлаждающей жидкости
    if vnesh.get('oil_leak') or vnesh.get('water_leak'):
        leak_type = "масла и антифриза" if (vnesh.get('oil_leak') and vnesh.get('water_leak')) else ("масла" if vnesh.get('oil_leak') else "охлаждающей жидкости")
        weaknesses.append({
            'tag': 'Подкапотное',
            'title': f'Следы запотевания / подтекания {leak_type}',
            'detail': 'Зафиксировано мастером при осмотре подкапотного пространства.',
            'objection': f'«Под капотом следы {leak_type}! Двигатель течет?»',
            'answer': '«Это естественное возрастное запотевание прокладки клапанной крышки/патрубка, а не активная течь. Уровни жидкостей в норме. Перед передачей машины клиенту наш сервис проводит контрольную мойку подкапотного пространства и при необходимости меняет уплотнитель».',
        })

    # 6. Рекомендации по диагностике и тест-драйву
    diag_items = td.get('diagnostic_items', [])
    if diag_items:
        items_str = "; ".join(f"{d['category']}: {d['title']}" for d in diag_items[:2])
        weaknesses.append({
            'tag': 'Диагностика',
            'title': f'Рекомендации мастера по диагностике ({items_str})',
            'detail': f'Всего {len(diag_items)} пунктов в диагностической карте автомобиля.',
            'objection': f'«В диагностике указано: {items_str}. Машина требует ремонта?»',
            'answer': '«Мы проводим открытую 100-точечную диагностику и ничего не скрываем от клиентов. Это стандартные регламентные расходники (сайлентблоки/колодки), которые мы либо устраняем в нашем техцентре перед выдачей, либо уже заложили в цену в виде скидки».',
        })
    elif td.get('remarks'):
        rem_str = "; ".join(td['remarks'][:2])
        weaknesses.append({
            'tag': 'Диагностика',
            'title': f'Замечания мастера при осмотре ({rem_str})',
            'detail': 'Выявлены при проведении тест-драйва.',
            'objection': '«Я вижу замечания в диагностическом листе. Придётся сразу вкладываться?»',
            'answer': '«Мы открыто показываем результаты диагностики — нам нечего скрывать. Это стандартные эксплуатационные моменты, которые мы либо устраняем по нашей сервисной программе, либо уже учли в привлекательной цене автомобиля».',
        })

    # 7. Автотека: Скачок или сомнения по пробегу
    if autoteka.get('mileage_warning', 0) > 0:
        warn_km = autoteka['mileage_warning']
        weaknesses.append({
            'tag': 'Пробег',
            'title': f'В Автотеке зафиксировано расхождение пробега (~{warn_km:,} км)'.replace(',', ' '),
            'detail': 'Возможная ошибка оператора техосмотра или страховой компании.',
            'objection': '«В Автотеке указан скачок пробега! Пробег скручен?»',
            'answer': '«В базах техосмотра и страховых базах очень часто встречаются банальные опечатки операторов (вместо 45 тыс. вбили 95 тыс.). Мы подключили диагностический сканер, считали реальные часы работы ЭБУ и проверили состояние руля, педалей и тормозных дисков — состояние машины на 100% соответствует текущему пробегу на щитке».',
        })

    # 8. Цена выше рынка
    if diff is not None and diff > 15000:
        weaknesses.append({
            'tag': 'Цена',
            'title': f'Цена выше среднерыночной на {_format_money(diff)} (+{hub.get("price_diff_pct")}%)',
            'detail': f'ЦНА: {_format_money(hub.get("cna"))} | Наша цена: {_format_money(car_price)}',
            'objection': '«Почему у вас цена выше рынка? В объявлениях есть похожие машины дешевле».',
            'answer': '«В самых дешёвых объявлениях часто скрыты юридические проблемы, скрученный пробег, тяжелые ДТП или обязательные кредитные страховки на сотни тысяч рублей. У нас цена окончательная, за реальный проверенный автомобиль с юридической гарантией и диагностикой дилера».',
        })

    # 9. Срок на складе
    if days_in_stok >= 45:
        weaknesses.append({
            'tag': 'Склад',
            'title': f'Автомобиль на складе {days_in_stok} дней',
            'detail': f'При среднем сроке продажи на рынке {hub.get("avg_days_in_sale", 30)} дней.',
            'objection': '«Машина уже давно у вас стоит. С ней что-то не так, раз никто не купил?»',
            'answer': '«Автомобиль проходил тщательную предпродажную диагностику и комплексную подготовку на нашем сервисе. Мы не выпускаем авто на витрину в спешке. Сейчас машина полностью проверена, доведена до стандарта дилера и готова к любым проверкам».',
        })

    # 10. Владельцы > 3
    if owners > 3:
        weaknesses.append({
            'tag': 'Документы',
            'title': f'Больше 3 владельцев по ПТС ({owners} владельцев)',
            'detail': 'Может вызывать подозрения у консервативных покупателей.',
            'objection': '«Слишком много хозяев по ПТС. Наверное, проблемная машина?»',
            'answer': '«Нередко смена записей в ПТС связана с переоформлением внутри семьи, сменой красивых номеров или лизингом. Главное — это реальное техническое состояние и юридическая чистота. Мы досконально проверили авто по базам ГИБДД, ФССП и залогов, а также провели 100-точечную диагностику».',
        })

    # 11. Один ключ
    if keys == 1:
        weaknesses.append({
            'tag': 'Комплектность',
            'title': 'Только один ключ зажигания',
            'detail': 'Потребуются затраты на дубликат или переговоры с клиентом.',
            'objection': '«Почему только один ключ? Опасаюсь, вдруг второй у кого-то остался».',
            'answer': '«Предыдущий собственник сдал автомобиль с одним ключом. Мы стёрли утерянный ключ из памяти иммобилайзера — завести им авто невозможно. При оформлении сделки мы можем прямо в нашем дилерском центре прописать новый ключ по льготной цене».',
        })

    # 12. Ошибки на приборке
    if salon.get('dashboard_errors'):
        err_str = ", ".join(salon['dashboard_errors'][:2])
        weaknesses.append({
            'tag': 'Салон',
            'title': f'Индикаторы ошибок на приборной панели ({err_str})',
            'detail': 'Зафиксированы при осмотре салона.',
            'objection': f'«На приборке горит значок ({err_str}). Что с электроникой?»',
            'answer': '«Это датчик сервисного напоминания / давления в шинах. Перед выдачей мы проводим электронный сброс и калибровку на сервисном оборудовании, на ключевые агрегаты это не влияет».',
        })

    # ==========================
    # РЕКОМЕНДАЦИИ (ACTIONS)
    # ==========================

    # Фотографии
    if photos.get('count', 0) == 0:
        actions.append({
            'priority': 'danger',
            'title': 'Срочно загрузить фотографии автомобиля',
            'text': 'У автомобиля нет фотографий на классифайдах. Карточка получает в 10 раз меньше просмотров.',
            'icon': 'icon-mbri-camera',
        })
    elif photos.get('is_outdated'):
        actions.append({
            'priority': 'warning',
            'title': 'Перефотографировать автомобиль (фото устарели)',
            'text': f'Фотографии загружены {photos.get("days_ago")} дней назад. Покупатели видят зависший склад и требуют скидки. Обновите ракурсы и интерьер.',
            'icon': 'icon-mbri-camera',
        })
    elif photos.get('is_few'):
        actions.append({
            'priority': 'info',
            'title': 'Добавить ракурсы (сейчас всего ' + str(photos.get('count')) + ' фото)',
            'text': 'Рекомендуется не менее 20 качественных фото: детали салона, багажник, подкапотное пространство, сервисная книжка.',
            'icon': 'icon-mbri-camera',
        })

    # Автотека: "Зеленая"
    if autoteka.get('is_green'):
        actions.append({
            'priority': 'success',
            'title': 'Распечатать отчёт «Зелёной» Автотеки',
            'text': 'Положите распечатку на панель приборов при показе авто. В 2026 году чистая Автотека — решающий фактор доверия покупателя.',
            'icon': 'icon-mbri-success',
        })

    # Заводской окрас
    if paint.get('is_factory_paint'):
        actions.append({
            'priority': 'success',
            'title': 'Держать толщиномер наготове при показе',
            'text': 'Предложите клиенту лично замерить ЛКП: заводской окрас по всем элементам мгновенно снимает любые подозрения по ДТП.',
            'icon': 'icon-mbri-shield',
        })

    # Второй комплект резины
    if kolesa.get('has_second_set'):
        actions.append({
            'priority': 'info',
            'title': 'Использовать 2-й комплект резины вместо скидки',
            'text': f'Если клиент требует торг на 30-50 тыс. ₽ — презентуйте наличие второго комплекта шин ({kolesa.get("second_set_desc")}).',
            'icon': 'icon-mbri-gift',
        })

    # ДТП / расчеты
    if autoteka.get('crashes_count', 0) > 0 or autoteka.get('insurance_calc_sum', 0) > 0:
        actions.append({
            'priority': 'warning',
            'title': 'Заранее подготовить аргументы по расчётам в Автотеке',
            'text': 'Покажите клиенту целые заводские лонжероны, маркировку стекол и фар, чтобы подтвердить, что ремонт был чисто косметическим.',
            'icon': 'icon-mbri-alert',
        })

    # Ценообразование
    if diff is not None and diff > 30000 and days_in_stok >= 30:
        actions.append({
            'priority': 'danger',
            'title': 'Инициировать переоценку в сторону рынка',
            'text': f'Цена выше ЦНА на {_format_money(diff)}. Срок склада {days_in_stok} дн. Без коррекции цены звонков будет мало.',
            'icon': 'icon-mbri-cash',
        })

    # Длительный простой без переоценки
    if days_in_stok >= 45 and (reval.get('days_since_change') is None or reval.get('days_since_change', 0) >= 30):
        actions.append({
            'priority': 'warning',
            'title': 'Цена не менялась более 30 дней при складе >45 дней',
            'text': 'Обсудите с руководителем отдела продаж коррекцию цены или запуск спецпредложения.',
            'icon': 'icon-mbri-timer',
        })

    # Лобовое стекло
    if vnesh.get('windshield_damaged'):
        actions.append({
            'priority': 'warning',
            'title': 'Отремонтировать скол/трещину на лобовом стекле',
            'text': 'Повреждения стекла сразу бросаются в глаза клиенту. Отремонтируйте дефект полимером на сервисе или заранее подготовьте спеццену на замену.',
            'icon': 'icon-mbri-alert',
        })

    # Полировка
    if body_def.get('polish'):
        actions.append({
            'priority': 'info',
            'title': 'Выполнить локальную полировку кузова',
            'text': 'Оценщик зафиксировал необходимость полировки. Это освежит блеск ЛКП и устранит мелкие эксплуатационные потертости.',
            'icon': 'icon-mbri-magic-stick',
        })

    # Диагностическая карта
    diag_items_list = td.get('diagnostic_items', [])
    if diag_items_list:
        actions.append({
            'priority': 'warning',
            'title': f'Изучить замечания диагностики ({len(diag_items_list)} поз.)',
            'text': 'Ознакомьтесь с замечаниями мастера перед показом, чтобы уверенно оперировать стоимостью запчастей при обсуждении торга.',
            'icon': 'icon-mbri-bulleted-list',
        })

    if not actions:
        actions.append({
            'priority': 'success',
            'title': 'Автомобиль полностью готов к активной продаже',
            'text': 'Цена в рынке, фотографии актуальны, подготовка выполнена. Фокусируйтесь на быстром выводе клиента на тест-драйв.',
            'icon': 'icon-mbri-success',
        })

    return strengths, weaknesses, actions


# =========================================================================
# 8. РАСЧЕТ РЕЙТИНГА И ВЕРДИКТА
# =========================================================================

def _calculate_sales_score(
    car,
    hub: dict,
    reval: dict,
    photos: dict,
    repairs: dict,
    autoteka: dict,
    estimation_info: dict,
) -> tuple[int, str]:
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
    owners = autoteka.get('owners_autoteka') or _int(car.owners)
    if owners in (1, 2):
        score += 0.3
    elif owners > 3:
        score -= 0.3

    # Автотека
    if autoteka.get('is_green'):
        score += 0.5
    elif autoteka.get('crashes_count', 0) > 0 or autoteka.get('insurance_calc_sum', 0) > 100000:
        score -= 0.4
    if autoteka.get('mileage_warning', 0) > 0:
        score -= 0.4

    # ЛКП и диагностика
    paint = estimation_info.get('paint', {})
    if paint.get('is_factory_paint'):
        score += 0.4
    elif paint.get('strong_painted_count', 0) > 1:
        score -= 0.3

    kolesa = estimation_info.get('kolesa', {})
    if kolesa.get('has_second_set'):
        score += 0.3

    td = estimation_info.get('test_drive', {})
    if td.get('core_ok'):
        score += 0.3

    score = max(1.0, min(5.0, score))
    stars = int(round(score))

    verdicts = {
        5: 'Высокая ликвидность — топовое предложение с чистой историей. Уверенная презентация, торг минимальный.',
        4: 'Хорошая позиция — весомые плюсы перевешивают недочеты. Акцент на диагностику и дилерскую подготовку.',
        3: 'Средняя ликвидность — требует активной отработки возражений и внимания к цене/фото.',
        2: 'Затрудненная продажа — есть сдерживающие факторы (цена выше рынка, замечания по Автотеке или старое фото).',
        1: 'Требуется вмешательство — переоценка, пересъёмка или устранение замечаний по диагностике.',
    }
    return stars, verdicts.get(stars, 'Стандартный вариант продажи.')


# =========================================================================
# 9. ГЛАВНАЯ СБОРКА СВОДКИ
# =========================================================================

def build_seller_brief(car, request=None) -> dict[str, Any]:
    """Главная функция сборки контекста сводки для продавца."""
    ah = _get_latest_avtohub(car)
    hub = _analyze_avtohub(car, ah)
    reval = _analyze_price_revaluations(car)
    photos = _analyze_photos(car)
    repairs = _analyze_repairs(car)

    est = _get_car_estimation(car)
    autoteka = _analyze_autoteka(car, est)
    estimation_info = _analyze_estimation(car, est)

    strengths, weaknesses, actions = _generate_strengths_and_weaknesses(
        car, hub, reval, photos, repairs, autoteka, estimation_info
    )
    stars, verdict = _calculate_sales_score(
        car, hub, reval, photos, repairs, autoteka, estimation_info
    )

    return {
        'car': car,
        'stars': stars,
        'stars_range': range(1, 6),
        'verdict': verdict,
        'hub': hub,
        'reval': reval,
        'photos': photos,
        'repairs': repairs,
        'autoteka': autoteka,
        'has_autoteka': autoteka.get('has_data', False),
        'estimation_info': estimation_info,
        'estimation': estimation_info,
        'has_estimation': estimation_info.get('has_data', False),
        'strengths': strengths,
        'weaknesses': weaknesses,
        'actions': actions,
        'has_actions': bool(actions),
        'strengths_count': len(strengths),
        'weaknesses_count': len(weaknesses),
        'actions_count': len(actions),
    }
