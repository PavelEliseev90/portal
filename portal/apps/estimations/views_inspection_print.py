# -*- coding: utf-8 -*-
"""Печать «Лист осмотра и оценки автомобиля»."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from estimations.views_kolesa_reception import (
    _complect_label,
    _estimation_car_label,
    _money,
)


def build_inspection_sheet(*, estimation, rlk=None, back_url=''):
    """Данные для печати листа осмотра и оценки (одна страница A4)."""
    if rlk is None and estimation is not None:
        rlk = estimation.rlk

    docs = estimation.page_documents if estimation and estimation.page_documents_id else None
    salon = estimation.page_salon if estimation and estimation.page_salon_id else None
    vnesh = estimation.page_vnesh if estimation and estimation.page_vnesh_id else None
    comp = estimation.page_complectnost if estimation and estimation.page_complectnost_id else None
    proverki = estimation.page_proverki if estimation and estimation.page_proverki_id else None
    sogl = estimation.page_soglasovanie if estimation and estimation.page_soglasovanie_id else None

    lo = None
    if rlk is not None:
        from documents.models import DocLO
        lo = (
            DocLO.objects
            .filter(rlk=rlk)
            .select_related('organization', 'staff')
            .order_by('-active', '-dataTime', '-id')
            .first()
        )

    # Клиент
    customer_fio = ''
    if docs:
        customer_fio = ' '.join(
            p for p in [
                (docs.customer_family or '').strip(),
                (docs.customer_name or '').strip(),
                (docs.customer_patronymic or '').strip(),
            ] if p
        )
    if not customer_fio and rlk and (rlk.clientName or '').strip():
        customer_fio = rlk.clientName.strip()
    elif not customer_fio and lo and (lo.clientName or '').strip():
        customer_fio = lo.clientName.strip()

    customer_phone = ''
    if docs and (docs.customer_phone or '').strip():
        customer_phone = docs.customer_phone.strip()
    elif rlk and (rlk.phone or '').strip():
        customer_phone = rlk.phone.strip()

    manager_name = ''
    if docs and (docs.new_staff_name or '').strip():
        manager_name = docs.new_staff_name.strip()
    elif rlk and (rlk.manager_trade_in or '').strip():
        manager_name = rlk.manager_trade_in.strip()
    elif rlk and rlk.staff_id and rlk.staff:
        manager_name = rlk.staff.name or str(rlk.staff)

    new_car = ''
    if docs and (docs.new_car or '').strip():
        new_car = docs.new_car.strip()
    elif lo and (lo.name_new_auto or '').strip():
        new_car = lo.name_new_auto.strip()

    # Авто
    vin = ((estimation.vin or estimation.number_body or '') if estimation else '').strip()
    car_label = _estimation_car_label(estimation) if estimation else '—'

    mark = ''
    model = ''
    modification = ''
    if estimation and estimation.modification_id and estimation.modification:
        mod = estimation.modification
        if mod.model_id and mod.model:
            mark = mod.model.mark.name if mod.model.mark_id else ''
            model = mod.model.name or ''
        modification = mod.name or ''
    if not mark:
        mark = (estimation.mark_name or '').strip() if estimation else ''
    if not model:
        model = (estimation.model_name or '').strip() if estimation else ''
    if not modification:
        modification = (estimation.modification_name or '').strip() if estimation else ''

    year = str(estimation.year) if estimation and estimation.year else ''

    mileage = ''
    mileage_val = salon.run if salon and salon.run else (lo.run if lo and lo.run else None)
    if mileage_val:
        try:
            mileage = '{:,}'.format(int(mileage_val)).replace(',', ' ')
        except (TypeError, ValueError):
            mileage = str(mileage_val)

    plate_number = ''
    if docs and (docs.plate_number or '').strip():
        plate_number = docs.plate_number.strip()
    elif lo and (lo.carsGRZ or '').strip():
        plate_number = lo.carsGRZ.strip()

    engine_number = (docs.engine_number or '').strip() if docs else ''

    gearbox = ''
    if estimation and estimation.type_gear_id and estimation.type_gear:
        gearbox = estimation.type_gear.name or str(estimation.type_gear)

    body = ''
    if estimation and estimation.type_body_id and estimation.type_body:
        body = estimation.type_body.name or str(estimation.type_body)

    color = ''
    if vnesh and (vnesh.color or '').strip():
        color = vnesh.color.strip()
    elif docs and (docs.pts_color or '').strip():
        color = docs.pts_color.strip()

    drive = (estimation.type_drive or '').strip() if estimation else ''

    owners = ''
    if docs and docs.count_owners:
        owners = str(docs.count_owners)
    elif lo and lo.owners:
        owners = str(lo.owners)

    keys_count = ''
    if docs and docs.count_key:
        keys_count = str(docs.count_key)
    elif lo and lo.keys:
        keys_count = str(lo.keys)

    # Комплектность
    complect_defs = [
        ('Аптечка', 'aptechka_int', 'aptechka'),
        ('Балонник', 'ball_key_int', 'ball_key'),
        ('Домкрат', 'domkrat_int', 'domkrat'),
        ('Прикуриватель', 'prikur_int', 'prikur'),
        ('Трос', 'tros_int', 'tros'),
        ('Запаска', 'zapas_int', 'zapas'),
        ('Коврики', 'kovrik_int', 'kovrik'),
        ('Огнетушитель', 'ognet_int', 'ognet'),
        ('Знак аварийной остановки', 'znak_av_int', 'znak_av'),
    ]
    complect_items = []
    for label, int_attr, bool_attr in complect_defs:
        if comp is not None:
            complect_items.append((
                label,
                _complect_label(getattr(comp, int_attr, None), getattr(comp, bool_attr, None)),
            ))
        else:
            complect_items.append((label, ''))

    # Проверки
    car_credit = False
    if proverki and proverki.car_credit:
        car_credit = True
    elif docs and docs.car_credit:
        car_credit = True

    epts = bool(proverki and proverki.epts)
    epts_ok = bool(proverki and proverki.epts_success)
    count_dtp = proverki.count_dtp if proverki and proverki.count_dtp else 0

    checks = [
        ('ЭПТС', epts),
        ('ЭПТС действующий', epts_ok),
        ('В залоге / кредите', car_credit),
        ('Ключи, кол-во', keys_count),
        ('ДТП, кол-во', str(count_dtp) if count_dtp else ''),
    ]

    # Схемы кузова (скриншоты осмотра)
    body_sides = []
    if estimation is not None:
        body_sides = [
            ('Слева', estimation.fotos_vnesh_vod()),
            ('Спереди', estimation.fotos_vnesh_pered()),
            ('Сзади', estimation.fotos_vnesh_zad()),
            ('Справа', estimation.fotos_vnesh_pass()),
        ]

    # Цена
    price = ''
    price_label = 'Оценочная стоимость'
    if sogl:
        if sogl.price_after_kd:
            price = _money(sogl.price_after_kd)
            price_label = 'Согласовано после диагностики'
        elif sogl.price_before_kd:
            price = _money(sogl.price_before_kd)
            price_label = 'Согласовано до диагностики'
        elif sogl.price_reception:
            price = _money(sogl.price_reception)
            price_label = 'Цена приёма оценщика'

    comment = ''
    if sogl and (sogl.comment or '').strip():
        comment = sogl.comment.strip()
    elif vnesh and (vnesh.comment_vnesh or '').strip():
        comment = vnesh.comment_vnesh.strip()

    valid_until = None
    if estimation and estimation.end_estimation:
        valid_until = estimation.end_estimation
    elif rlk and rlk.dataTime:
        valid_until = rlk.dataTime

    appraiser = ''
    if estimation and estimation.staff_id and estimation.staff:
        appraiser = estimation.staff.name or str(estimation.staff)
    elif lo and lo.staff_id and lo.staff:
        appraiser = lo.staff.name or str(lo.staff)

    unit_name = ''
    if rlk and rlk.unit_id and rlk.unit:
        unit_name = rlk.unit.name or ''

    doc_date = None
    if estimation and estimation.end_estimation:
        doc_date = estimation.end_estimation
    elif estimation and estimation.start_estimation:
        doc_date = estimation.start_estimation
    elif rlk and rlk.dataTime:
        doc_date = rlk.dataTime

    if not back_url and rlk is not None:
        back_url = '/eco/{}/'.format(rlk.pk)

    return {
        'estimation': estimation,
        'rlk': rlk,
        'back_url': back_url,
        'doc_date': doc_date,
        'unit_name': unit_name,
        'rlk_nomer': (rlk.nomer if rlk else '') or '',
        'customer_fio': customer_fio,
        'customer_phone': customer_phone,
        'manager_name': manager_name,
        'new_car': new_car,
        'vin': vin,
        'car_label': car_label,
        'mark': mark,
        'model': model,
        'modification': modification,
        'year': year,
        'mileage': mileage,
        'plate_number': plate_number,
        'engine_number': engine_number,
        'gearbox': gearbox,
        'body': body,
        'color': color,
        'drive': drive,
        'owners': owners,
        'complect_items': complect_items,
        'checks': checks,
        'body_sides': body_sides,
        'price': price,
        'price_label': price_label,
        'comment': comment,
        'valid_until': valid_until,
        'appraiser': appraiser,
    }


@login_required
def estimation_inspection_sheet_print(request, rlk_id):
    """Печать листа осмотра и оценки по РЛК."""
    from documents.models import DocRLK
    from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK

    rlk = get_object_or_404(DocRLK.objects.select_related('unit', 'staff'), pk=rlk_id)

    related = (
        'page_documents',
        'page_salon',
        'page_vnesh',
        'page_complectnost',
        'page_proverki',
        'page_soglasovanie',
        'staff',
        'modification',
        'modification__model',
        'modification__model__mark',
        'type_gear',
        'type_body',
        'complectation',
        'rlk',
        'rlk__unit',
    )

    estimation = None
    try:
        link = RegInteractivOcenkaRLK.objects.select_related(
            'estimation',
            *['estimation__' + p for p in related],
        ).get(rlk=rlk)
        estimation = link.estimation
    except RegInteractivOcenkaRLK.DoesNotExist:
        try:
            estimation = RegInteractivOcenka.objects.select_related(*related).get(rlk=rlk)
        except RegInteractivOcenka.DoesNotExist:
            raise Http404('Интерактивная оценка для рабочего листа не найдена')

    if estimation is None:
        raise Http404('Интерактивная оценка не найдена')

    sheet = build_inspection_sheet(
        estimation=estimation,
        rlk=rlk,
        back_url='/eco/{}/'.format(rlk.pk),
    )
    return render(
        request,
        'estimations/inspection_sheet_print.html',
        {'params': sheet},
    )
