# -*- coding: utf-8 -*-
"""Печать «Передача автомобиля из подготовки в отдел продаж»."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

# Чеклист передачи: (код, текст). Пустые клетки Да/Нет для подписи на бланке.
TRANSFER_CHECKS = [
    ('salon_clean', 'Салон чистый (химчистка / мойка выполнены)'),
    ('exterior_clean', 'Кузов чистый, полировка / мойка выполнены'),
    ('fake_plates', 'Фальшномера сняты / установлены согласно регламенту'),
    ('plates_ok', 'Регистрационные знаки на месте, читаемы'),
    ('keys', 'Ключи переданы (комплект, пульты, метки)'),
    ('docs', 'Документы переданы (ПТС/ЭПТС, СТС, сервисная книжка)'),
    ('complect', 'Комплектность на месте (аптечка, огнетушитель, знак, инструмент)'),
    ('spare', 'Запасное колесо / докатка, домкрат, баллонный ключ'),
    ('fuel', 'Уровень топлива достаточен для показа / тест-драйва'),
    ('no_faults', 'Нет видимых неисправностей, влияющих на показ'),
    ('media_ok', 'Мультимедиа / камера / парктроники проверены'),
    ('prep_done', 'Работы по подготовке завершены, авто готово к продаже'),
]


def _txt(*parts) -> str:
    return ' '.join(str(p).strip() for p in parts if p not in (None, '')).strip()


def _staff_name(obj) -> str:
    if obj is None:
        return ''
    name = getattr(obj, 'name', None)
    if name:
        return str(name).strip()
    return str(obj).strip()


def _cleaning_label(page_salon) -> str:
    if page_salon is None:
        return ''
    cleaning_map = {
        0: 'не требуется',
        3: 'лёгкая',
        2: 'средняя',
        1: 'сложная',
    }
    label = cleaning_map.get(getattr(page_salon, 'cleaning_int', None), '')
    if not label and getattr(page_salon, 'cleaning', None):
        label = 'требуется'
    return label


def build_transfer_sales_sheet(*, estimation=None, rlk=None, page_reception=None, back_url=''):
    """Данные бланка передачи из подготовки в ОП."""
    from documents.models import DocLO
    from register.models import RegEstimationPodgotovka, RegEstimationSS, RegEstimationMCU

    if rlk is None and estimation is not None:
        rlk = estimation.rlk

    lo = None
    if rlk is not None:
        lo = (
            DocLO.objects
            .filter(rlk=rlk)
            .select_related('organization', 'staff', 'store')
            .order_by('-active', '-dataTime', '-id')
            .first()
        )

    page_docs = None
    page_salon = None
    page_sogl = None
    page_complect = None
    if estimation is not None:
        page_docs = estimation.page_documents if estimation.page_documents_id else None
        page_salon = estimation.page_salon if estimation.page_salon_id else None
        page_sogl = estimation.page_soglasovanie if estimation.page_soglasovanie_id else None
        page_complect = estimation.page_complectnost if estimation.page_complectnost_id else None

    lo_nomer = ''
    if lo and lo.nomer:
        lo_nomer = lo.nomer
    elif rlk and rlk.nomer:
        lo_nomer = rlk.nomer

    car_label = ''
    if page_reception and (page_reception.mark or page_reception.model):
        car_label = _txt(page_reception.mark, page_reception.model)
    elif estimation is not None:
        try:
            from estimations.views_kolesa_reception import _estimation_car_label
            car_label = _estimation_car_label(estimation)
        except Exception:
            car_label = ''

    year = ''
    if estimation and estimation.year:
        year = str(estimation.year)
    elif page_reception and page_reception.year:
        year = str(page_reception.year)

    vin = ''
    if estimation:
        vin = (estimation.vin or estimation.number_body or '').strip()
    if not vin and page_reception:
        vin = (getattr(page_reception, 'vin', None) or '').strip()

    plate = ''
    if page_reception and (getattr(page_reception, 'plate_number', None) or ''):
        plate = page_reception.plate_number.strip()
    elif lo and (getattr(lo, 'carsGRZ', None) or ''):
        plate = (lo.carsGRZ or '').strip()

    mileage = ''
    mileage_val = None
    if page_reception and page_reception.mileage:
        mileage_val = page_reception.mileage
    elif page_salon and page_salon.run:
        mileage_val = page_salon.run
    elif lo and lo.run:
        mileage_val = lo.run
    if mileage_val:
        try:
            mileage = '{:,}'.format(int(mileage_val)).replace(',', ' ')
        except (TypeError, ValueError):
            mileage = str(mileage_val)

    color = ''
    if page_reception and (getattr(page_reception, 'body_color', None) or ''):
        color = page_reception.body_color.strip()
    if not color and page_docs and (page_docs.pts_color or '').strip():
        color = page_docs.pts_color.strip()

    org_name = ''
    store_name = ''
    if lo and lo.organization_id and lo.organization:
        org_name = lo.organization.name or ''
    if lo and getattr(lo, 'store_id', None) and lo.store:
        store_name = lo.store.name or ''
    if not store_name and page_reception and getattr(page_reception, 'store', None):
        store_name = getattr(page_reception.store, 'name', '') or ''

    unit_name = ''
    if rlk and rlk.unit_id and rlk.unit:
        unit_name = rlk.unit.name or ''

    appraiser = ''
    if page_reception and page_reception.staff_id and page_reception.staff:
        appraiser = _staff_name(page_reception.staff)
    elif estimation and estimation.staff_id and estimation.staff:
        appraiser = _staff_name(estimation.staff)

    comment_podgotovka = ''
    if lo and (lo.description_podgotovka or '').strip():
        comment_podgotovka = lo.description_podgotovka.strip()
    elif page_sogl and (page_sogl.comment or '').strip():
        comment_podgotovka = page_sogl.comment.strip()

    himchistka = _cleaning_label(page_salon)
    salon_color = ''
    if page_salon and getattr(page_salon, 'type_salon_int', None) is not None:
        salon_map = {0: '', 1: 'ткань', 2: 'кожа', 3: 'комбинированный'}
        salon_color = salon_map.get(page_salon.type_salon_int, '') or (
            getattr(page_salon, 'type_salon', None) or ''
        )
    if page_reception and (getattr(page_reception, 'salon_color', None) or ''):
        salon_color = salon_color or page_reception.salon_color.strip()

    works = []
    if estimation is not None:
        for row in RegEstimationPodgotovka.objects.filter(estimation=estimation).order_by('id'):
            works.append({
                'kind': 'Подготовка',
                'name': row.name or '',
                'status': row.status,
                'done': bool(row.status and int(row.status) > 0),
            })
        for row in RegEstimationSS.objects.filter(estimation=estimation).order_by('id')[:40]:
            works.append({
                'kind': 'СС',
                'name': getattr(row, 'name', None) or str(row),
                'status': getattr(row, 'status', 0),
                'done': bool(getattr(row, 'status', 0)),
            })
        for row in RegEstimationMCU.objects.filter(estimation=estimation).order_by('id')[:40]:
            works.append({
                'kind': 'МКУ',
                'name': getattr(row, 'name', None) or str(row),
                'status': getattr(row, 'status', 0),
                'done': bool(getattr(row, 'status', 0)),
            })

    complect_notes = []
    if page_complect is not None:
        mapping = (
            ('prikur_int', 'прикуриватель'),
            ('ognet_int', 'огнетушитель'),
            ('kovrik_int', 'коврики'),
            ('tros_int', 'трос'),
            ('domkrat_int', 'домкрат'),
            ('znak_av_int', 'знак аварийной остановки'),
            ('ball_key_int', 'баллонный ключ'),
            ('zapas_int', 'запаска'),
            ('aptechka_int', 'аптечка'),
        )
        for attr, label in mapping:
            val = getattr(page_complect, attr, None)
            if val in (None, 0, ''):
                continue
            complect_notes.append('{}: {}'.format(label, val))

    amount_parts = []
    if page_sogl is not None:
        for attr, label in (
            ('amount_podgotovka', 'подготовка'),
            ('amount_ss', 'СС'),
            ('amount_mcu', 'МКУ'),
            ('amount_recovery', 'восстановление'),
        ):
            val = getattr(page_sogl, attr, None)
            if val not in (None, '', 0, 0.0):
                try:
                    amount_parts.append('{} {}'.format(label, int(val)))
                except (TypeError, ValueError):
                    amount_parts.append('{} {}'.format(label, val))
    amount_prep = ', '.join(amount_parts)

    if not back_url and rlk is not None:
        back_url = '/eco/{}/?page=24'.format(rlk.pk)

    return {
        'rlk': rlk,
        'estimation': estimation,
        'back_url': back_url,
        'lo_nomer': lo_nomer,
        'car_label': car_label,
        'year': year,
        'vin': vin,
        'plate_number': plate,
        'mileage': mileage,
        'color': color,
        'org_name': org_name,
        'store_name': store_name,
        'unit_name': unit_name,
        'appraiser': appraiser,
        'comment_podgotovka': comment_podgotovka,
        'himchistka': himchistka,
        'salon_color': salon_color,
        'works': works,
        'complect_notes': complect_notes,
        'amount_prep': amount_prep,
        'checks': TRANSFER_CHECKS,
    }


@login_required
def estimation_transfer_sales_sheet_print(request, id):
    """Печать акта передачи из подготовки в отдел продаж."""
    from documents.models import DocRLK
    from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK

    rlk = get_object_or_404(DocRLK.objects.select_related('unit'), pk=id)

    estimation = None
    page_reception = None
    try:
        link = RegInteractivOcenkaRLK.objects.select_related(
            'estimation',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
            'estimation__staff',
            'estimation__page_documents',
            'estimation__page_salon',
            'estimation__page_soglasovanie',
            'estimation__page_complectnost',
            'page_reception',
            'page_reception__staff',
            'page_reception__store',
        ).get(rlk=rlk)
        estimation = link.estimation
        page_reception = getattr(link, 'page_reception', None)
    except RegInteractivOcenkaRLK.DoesNotExist:
        try:
            estimation = (
                RegInteractivOcenka.objects
                .select_related(
                    'modification',
                    'modification__model',
                    'modification__model__mark',
                    'staff',
                    'page_documents',
                    'page_salon',
                    'page_soglasovanie',
                    'page_complectnost',
                )
                .get(rlk=rlk)
            )
        except RegInteractivOcenka.DoesNotExist:
            raise Http404('Интерактивная оценка для рабочего листа не найдена')

    sheet = build_transfer_sales_sheet(
        estimation=estimation,
        rlk=rlk,
        page_reception=page_reception,
        back_url='/eco/{}/?page=24'.format(rlk.pk),
    )
    return render(request, 'estimations/transfer_sales_sheet_print.html', {'params': sheet})
