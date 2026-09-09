# -*- coding: utf-8 -*-
"""Связанные документы и история статусов для карточки автомобиля на складе."""
from __future__ import annotations

from django.db.models import Q

from documents.models import DocCarAgreement, DocCarShipment


def _pick_label(value):
    if value is None:
        return ''
    if isinstance(value, dict):
        return (value.get('name') or value.get('Name') or '').strip()
    return str(value).strip()


def _fk_name(obj):
    if obj is None:
        return ''
    return (getattr(obj, 'name', None) or '').strip()


def _type_label(value, fallback=''):
    """Строка типа ремонта/затрат: FK, dict или уже строка."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, dict):
        return (value.get('name') or value.get('Name') or '').strip() or fallback
    name = getattr(value, 'name', None)
    if name is not None:
        return str(name).strip() or fallback
    text = str(value).strip()
    return text or fallback


def _dash(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return value


def parse_status_history_from_1c(data) -> list[dict]:
    """История статусов из ответа 1С /car/?uin_lo= (если блок есть в JSON)."""
    if not isinstance(data, dict):
        return []

    for key in (
        'Status_list', 'Statuses', 'Status_history', 'History_status',
        'StatusHistory', 'Status_history_list',
    ):
        block = data.get(key)
        if not block:
            continue
        if isinstance(block, list):
            rows = block
        elif isinstance(block, dict):
            rows = block.get('items') or block.get('Rows') or block.get('rows') or []
        else:
            continue

        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            result.append({
                'date': (
                    row.get('Date') or row.get('date') or row.get('Period')
                    or row.get('period') or ''
                ),
                'status': _pick_label(
                    row.get('Status') or row.get('status') or row.get('StatusName')
                ),
                'comment': (row.get('Comment') or row.get('comment') or '').strip(),
            })
        if result:
            return result
    return []


def get_car_interactiv_context(car):
    """Интерактивная оценка и ссылка на ECO."""
    from documents.rlk_estimation import (
        resolve_estimation_for_rlk,
        resolve_interactiv_rlk_for_rlk,
    )

    estimation = None
    interactiv_rlk = None
    eco_url = ''

    lo = getattr(car, 'lo', None)
    if lo is None:
        try:
            from documents.models import DocLO
            lo_uin = (getattr(car, 'lo_uin', None) or '').strip()
            if lo_uin:
                lo = DocLO.objects.filter(uin__icontains=lo_uin).select_related('rlk').order_by('-active', '-dataTime', '-id').first()
            if lo is None:
                nomer = (getattr(car, 'lo_link_number', None) or '').strip()
                if nomer:
                    lo = DocLO.objects.filter(nomer__iexact=nomer).select_related('rlk').order_by('-active', '-dataTime', '-id').first()
        except Exception:
            lo = None
    rlk = getattr(lo, 'rlk', None) if lo is not None else None
    if rlk is None:
        return {
            'estimation': None,
            'interactiv_rlk': None,
            'eco_url': '',
        }

    vin = (car.vin or '').strip()
    estimation = resolve_estimation_for_rlk(rlk, vin=vin)
    interactiv_rlk = resolve_interactiv_rlk_for_rlk(rlk, vin=vin)

    eco_rlk_id = None
    if interactiv_rlk is not None and interactiv_rlk.rlk_id:
        eco_rlk_id = interactiv_rlk.rlk_id
    elif estimation is not None and estimation.rlk_id:
        eco_rlk_id = estimation.rlk_id
    elif rlk.pk:
        eco_rlk_id = rlk.pk

    if eco_rlk_id:
        eco_url = '/eco/{}/'.format(eco_rlk_id)

    return {
        'estimation': estimation,
        'interactiv_rlk': interactiv_rlk,
        'eco_url': eco_url,
    }


def _client_label_from_reception(reception) -> str:
    ctype = (getattr(reception, 'customer_type', None) or '').strip()
    if ctype == 'fl':
        parts = [
            getattr(reception, 'customer_family', '') or '',
            getattr(reception, 'customer_name', '') or '',
            getattr(reception, 'customer_patronymic', '') or '',
        ]
        return ' '.join(p.strip() for p in parts if p and str(p).strip()).strip()
    if ctype in ('ul', 'ip'):
        return (getattr(reception, 'customer_company_name', None) or '').strip()
    parts = [
        getattr(reception, 'customer_family', '') or '',
        getattr(reception, 'customer_name', '') or '',
        getattr(reception, 'customer_patronymic', '') or '',
    ]
    name = ' '.join(p.strip() for p in parts if p and str(p).strip()).strip()
    if name:
        return name
    return (getattr(reception, 'customer_company_name', None) or '').strip()


def _pts_short_from_reception(reception) -> str:
    if getattr(reception, 'pts_electronic', None):
        base = 'ЭПТС'
    else:
        series = (getattr(reception, 'pts_series', None) or '').strip()
        number = (getattr(reception, 'pts_number', None) or '').strip()
        base = ' '.join(p for p in (series, number) if p).strip()
    pts_date = getattr(reception, 'pts_date', None)
    if pts_date:
        try:
            base = '{} от {}'.format(base, pts_date.strftime('%d.%m.%Y')).strip()
        except Exception:
            pass
    return base


def _sts_short_from_reception(reception) -> str:
    number = (getattr(reception, 'sts_number', None) or '').strip()
    sts_date = getattr(reception, 'sts_date', None)
    if not number and not sts_date:
        return ''
    if sts_date:
        try:
            return '{} от {}'.format(number or 'СТС', sts_date.strftime('%d.%m.%Y'))
        except Exception:
            return number
    return number


def _customer_type_label(reception) -> str:
    ctype = (getattr(reception, 'customer_type', None) or '').strip()
    mapping = {'fl': 'ФЛ', 'ul': 'ЮЛ', 'ip': 'ИП'}
    return mapping.get(ctype, '')


def _sklad_nomer(*, car=None, lo=None, rlk=None, vin='') -> str:
    """Складской номер = номер листа оценки (ЛО / lo_link_number)."""
    if lo is not None:
        n = (getattr(lo, 'nomer', None) or '').strip()
        if n:
            return n
    if car is not None:
        n = (getattr(car, 'lo_link_number', None) or '').strip()
        if n:
            return n
    try:
        from refs.models import RefCarsOrganization
        qs = RefCarsOrganization.objects.all()
        linked = None
        if lo is not None and getattr(lo, 'pk', None):
            linked = qs.filter(lo_id=lo.pk).order_by('-id').first()
        if linked is None and lo is not None and (getattr(lo, 'uin', None) or '').strip():
            linked = qs.filter(lo_uin=(lo.uin or '').strip()).order_by('-id').first()
        if linked is None and (vin or '').strip():
            linked = (
                qs.filter(vin=(vin or '').strip().upper())
                .exclude(lo_link_number='')
                .order_by('-id')
                .first()
            )
        if linked is not None:
            n = (linked.lo_link_number or '').strip()
            if n:
                return n
    except Exception:
        pass
    if rlk is not None:
        n = (getattr(rlk, 'nomer', None) or '').strip()
        if n:
            return n
    return ''


def get_car_intake_summary(car, interactiv_rlk=None, eco_url=''):
    """
    Сводка приёма / ЛО для карточки склада (без файлов).
    Приоритет: карточка приёма ECO → DocLO → поля автомобиля.
    """
    empty = {
        'has_data': False,
        'source': '',
        'source_label': '',
        'reception': None,
        'reception_url': '',
        'sklad_nomer': '',
        'rows': [],
    }

    reception = None
    if interactiv_rlk is not None:
        try:
            from register.models import RegInteractivOcenkaReception
            reception = (
                RegInteractivOcenkaReception.objects
                .select_related(
                    'organization', 'filial', 'unit', 'store',
                    'type_reception', 'staff',
                )
                .filter(interactiv_rlk=interactiv_rlk)
                .first()
            )
        except Exception:
            reception = None

    lo = getattr(car, 'lo', None)
    if lo is None:
        try:
            from documents.models import DocLO
            lo_uin = (getattr(car, 'lo_uin', None) or '').strip()
            if lo_uin:
                lo = (
                    DocLO.objects
                    .filter(uin__icontains=lo_uin)
                    .select_related('organization', 'unit', 'store', 'type_reception', 'staff')
                    .order_by('-active', '-dataTime', '-id')
                    .first()
                )
            if lo is None:
                nomer = (getattr(car, 'lo_link_number', None) or '').strip()
                if nomer:
                    lo = (
                        DocLO.objects
                        .filter(nomer__iexact=nomer)
                        .select_related('organization', 'unit', 'store', 'type_reception', 'staff')
                        .order_by('-active', '-dataTime', '-id')
                        .first()
                    )
        except Exception:
            lo = None
    rlk = None
    if interactiv_rlk is not None:
        rlk = getattr(interactiv_rlk, 'rlk', None)
    elif lo is not None:
        rlk = getattr(lo, 'rlk', None)
    sklad_nomer = _sklad_nomer(car=car, lo=lo, rlk=rlk)

    reception_url = ''
    if eco_url:
        reception_url = '{}?page=24'.format(eco_url.rstrip('/'))

    def _lo_extra_rows():
        if lo is None:
            return []
        extra = [
            {'label': 'Цвет (ЛО)', 'value': _dash(getattr(lo, 'color', ''))},
            {'label': 'Себестоимость (ЛО)', 'value': getattr(lo, 'cost_price', None) or ''},
            {'label': 'БЦП (ЛО)', 'value': getattr(lo, 'bcp', None) or ''},
            {
                'label': 'Аукцион (ЛО)',
                'value': 'да' if getattr(lo, 'auction', False) else '',
                'extra': _dash(getattr(lo, 'auction_comment', '')),
            },
            {
                'label': 'Комментарий подготовке (ЛО)',
                'value': _dash(getattr(lo, 'description_podgotovka', '')),
            },
            {
                'label': 'Комментарий ОП (ЛО)',
                'value': _dash(getattr(lo, 'description_op', '')),
            },
            {
                'label': 'Рекомендация / диагностика (ЛО)',
                'value': _dash(getattr(lo, 'recomendation', '')),
            },
        ]
        return [r for r in extra if r.get('value') not in (None, '', [])]

    if reception is not None:
        client = _client_label_from_reception(reception)
        phone = (getattr(reception, 'customer_phone', None) or '').strip()
        inn = (getattr(reception, 'customer_inn', None) or '').strip()
        client_extra = []
        ctype = _customer_type_label(reception)
        if ctype:
            client_extra.append(ctype)
        if phone:
            client_extra.append(phone)
        if inn:
            client_extra.append('ИНН {}'.format(inn))

        rows = [
            {'label': 'Складской №', 'value': sklad_nomer},
            {'label': 'Дата приёма', 'value': reception.actual_reception_at},
            {'label': 'Дата ЛО', 'value': getattr(lo, 'dataTime', None) if lo else None},
            {'label': 'Оценщик', 'value': _fk_name(reception.staff) or (_fk_name(getattr(lo, 'staff', None)) if lo else '')},
            {'label': 'Организация', 'value': _fk_name(reception.organization) or (_fk_name(getattr(lo, 'organization', None)) if lo else '')},
            {'label': 'Филиал', 'value': _fk_name(reception.filial)},
            {'label': 'Подразделение', 'value': _fk_name(reception.unit) or (_fk_name(getattr(lo, 'unit', None)) if lo else '')},
            {'label': 'Склад', 'value': _fk_name(reception.store) or (_fk_name(getattr(lo, 'store', None)) if lo else '')},
            {'label': 'Тип приёма', 'value': _fk_name(reception.type_reception) or (_fk_name(getattr(lo, 'type_reception', None)) if lo else '')},
            {
                'label': 'Клиент',
                'value': client or (_dash(getattr(lo, 'clientName', '')) if lo else ''),
                'extra': ' · '.join(client_extra),
            },
            {'label': 'Госномер', 'value': _dash(reception.plate_number) or (_dash(getattr(lo, 'carsGRZ', '')) if lo else '')},
            {'label': 'VIN', 'value': _dash(reception.vin) or _dash(getattr(car, 'vin', ''))},
            {'label': 'VIN 2 / кузов', 'value': _dash(reception.vin2) or _dash(reception.body_number)},
            {'label': 'Год', 'value': reception.year or (getattr(lo, 'year', None) if lo else '') or ''},
            {'label': 'Пробег', 'value': reception.mileage or (getattr(lo, 'run', None) if lo else '') or ''},
            {'label': 'Владельцев', 'value': reception.count_owners if reception.count_owners is not None else (getattr(lo, 'owners', None) if lo else None)},
            {'label': 'Ключей', 'value': reception.count_keys if reception.count_keys is not None else (getattr(lo, 'keys', None) if lo else None)},
            {'label': 'ПТС', 'value': _pts_short_from_reception(reception)},
            {'label': 'СТС', 'value': _sts_short_from_reception(reception)},
            {
                'label': 'Цвет кузова / салона',
                'value': ' / '.join(
                    p for p in (
                        (reception.body_color or '').strip(),
                        (reception.salon_color or '').strip(),
                    ) if p
                ) or (_dash(getattr(lo, 'color', '')) if lo else ''),
            },
            {
                'label': 'Взаимозачёт',
                'value': reception.amount_vzaimozachet or '',
            },
            {
                'label': 'Соглашение ОП',
                'value': _dash(reception.agreement_number_op),
            },
            {
                'label': 'В 1С',
                'value': reception.sent_to_1c_at,
                'extra': _dash(reception.sent_to_1c_status),
            },
        ]
        rows.extend(_lo_extra_rows())
        return {
            'has_data': True,
            'source': 'reception',
            'source_label': 'Карточка приёма + лист оценки',
            'reception': reception,
            'reception_url': reception_url,
            'sklad_nomer': sklad_nomer,
            'rows': [r for r in rows if r.get('value') not in (None, '', [])],
        }

    if lo is not None:
        rows = [
            {'label': 'Складской №', 'value': sklad_nomer or _dash(getattr(lo, 'nomer', ''))},
            {'label': 'Дата ЛО', 'value': getattr(lo, 'dataTime', None)},
            {'label': 'Оценщик', 'value': _fk_name(getattr(lo, 'staff', None))},
            {'label': 'Организация', 'value': _fk_name(getattr(lo, 'organization', None))},
            {'label': 'Подразделение', 'value': _fk_name(getattr(lo, 'unit', None))},
            {'label': 'Склад', 'value': _fk_name(getattr(lo, 'store', None))},
            {'label': 'Тип приёма', 'value': _fk_name(getattr(lo, 'type_reception', None))},
            {'label': 'Клиент', 'value': _dash(getattr(lo, 'clientName', ''))},
            {'label': 'Госномер', 'value': _dash(getattr(lo, 'carsGRZ', ''))},
            {'label': 'VIN', 'value': _dash(getattr(lo, 'vin', '')) or _dash(getattr(car, 'vin', ''))},
            {'label': 'VIN 2', 'value': _dash(getattr(lo, 'vin2', ''))},
            {'label': 'Год', 'value': getattr(lo, 'year', None) or ''},
            {'label': 'Пробег', 'value': getattr(lo, 'run', None) or ''},
            {'label': 'Владельцев', 'value': getattr(lo, 'owners', None)},
            {'label': 'Ключей', 'value': getattr(lo, 'keys', None)},
            {'label': 'Цвет', 'value': _dash(getattr(lo, 'color', ''))},
            {'label': 'Себестоимость', 'value': getattr(lo, 'cost_price', None) or ''},
            {'label': 'БЦП', 'value': getattr(lo, 'bcp', None) or ''},
            {
                'label': 'Аукцион',
                'value': 'да' if getattr(lo, 'auction', False) else '',
                'extra': _dash(getattr(lo, 'auction_comment', '')),
            },
            {
                'label': 'Комментарий подготовке',
                'value': _dash(getattr(lo, 'description_podgotovka', '')),
            },
            {
                'label': 'Комментарий ОП',
                'value': _dash(getattr(lo, 'description_op', '')),
            },
            {
                'label': 'Рекомендация / диагностика',
                'value': _dash(getattr(lo, 'recomendation', '')),
            },
        ]
        return {
            'has_data': True,
            'source': 'lo',
            'source_label': 'Лист оценки (карточка приёма ещё не создана)',
            'reception': None,
            'reception_url': reception_url,
            'sklad_nomer': sklad_nomer or _dash(getattr(lo, 'nomer', '')),
            'rows': [r for r in rows if r.get('value') not in (None, '', [])],
        }

    rows = [
        {'label': 'Складской №', 'value': sklad_nomer},
        {'label': 'Организация', 'value': _fk_name(getattr(car, 'organization', None))},
        {'label': 'Подразделение', 'value': _fk_name(getattr(car, 'unit', None))},
        {'label': 'Склад', 'value': _fk_name(getattr(car, 'store', None))},
        {'label': 'Тип приёма', 'value': _fk_name(getattr(car, 'type_reception', None))},
        {'label': 'Госномер', 'value': _dash(getattr(car, 'plate_number', ''))},
        {'label': 'VIN', 'value': _dash(getattr(car, 'vin', ''))},
        {'label': 'VIN 2', 'value': _dash(getattr(car, 'vin2', ''))},
        {'label': 'Владельцев', 'value': getattr(car, 'owners', None)},
        {'label': 'Ключей', 'value': getattr(car, 'keys', None)},
    ]
    filtered = [r for r in rows if r.get('value') not in (None, '', [])]
    if not filtered:
        return empty
    return {
        'has_data': True,
        'source': 'car',
        'source_label': 'Данные карточки склада',
        'reception': None,
        'reception_url': reception_url,
        'sklad_nomer': sklad_nomer,
        'rows': filtered,
    }


def _tyre_size_label(width, profil, radius) -> str:
    w = _fk_name(width)
    p = _fk_name(profil)
    r = _fk_name(radius)
    parts = []
    if w and p:
        parts.append('{}/{}'.format(w, p))
    elif w or p:
        parts.append(w or p)
    if r:
        parts.append('R{}'.format(r) if not str(r).upper().startswith('R') else str(r))
    return ' '.join(parts).strip()


def _wheels_rows_from_page_kolesa(page, *, second=False) -> list[dict]:
    """Строки для комплекта с страницы колёс оценки."""
    if page is None:
        return []
    s = '2' if second else ''
    mark = getattr(page, 'mark_tyre{}'.format(s) if second else 'mark_tyre', None)
    model = getattr(page, 'model_tyre{}'.format(s) if second else 'model_tyre', None) or ''
    width = getattr(page, 'width_tyre{}'.format(s) if second else 'width_tyre', None)
    profil = getattr(page, 'profil_tyre{}'.format(s) if second else 'profil_tyre', None)
    radius = getattr(page, 'radius{}'.format(s) if second else 'radius', None)
    sezon = getattr(page, 'sezon{}'.format(s) if second else 'sezon', None)
    disk_type = getattr(page, 'disk_type{}'.format(s) if second else 'disk_type', None)
    model_disk = getattr(page, 'model_disk{}'.format(s) if second else 'model_disk', None) or ''
    et_disk = getattr(page, 'et_disk{}'.format(s) if second else 'et_disk', None)
    dia_disk = getattr(page, 'dia_disk{}'.format(s) if second else 'dia_disk', None)
    psd_disk = getattr(page, 'psd_disk{}'.format(s) if second else 'psd_disk', None)

    rows = [
        {'label': 'Шины', 'value': ' '.join(
            p for p in (_fk_name(mark), (model or '').strip()) if p
        )},
        {'label': 'Размер', 'value': _tyre_size_label(width, profil, radius)},
        {'label': 'Сезон', 'value': _fk_name(sezon)},
        {'label': 'Диски', 'value': ' '.join(
            p for p in (_fk_name(disk_type), (model_disk or '').strip()) if p
        )},
        {
            'label': 'ET / DIA / PCD',
            'value': ' / '.join(
                p for p in (_fk_name(et_disk), _fk_name(dia_disk), _fk_name(psd_disk)) if p
            ),
        },
    ]
    if second:
        count_disk = getattr(page, 'count_disk2', None) or 0
        count_tyre = getattr(page, 'count_tyre2', None) or 0
        if count_disk or count_tyre:
            rows.append({
                'label': 'Кол-во дисков / шин',
                'value': '{} / {}'.format(count_disk, count_tyre),
            })
    return [r for r in rows if r.get('value') not in (None, '', [])]


def _wheels_rows_from_kolesa_reception(reception) -> list[dict]:
    if reception is None:
        return []
    rows = [
        {'label': 'Дата приёмки', 'value': getattr(reception, 'date', None)},
        {
            'label': 'Шины',
            'value': ' '.join(
                p for p in (
                    _fk_name(getattr(reception, 'mark_tyre', None)),
                    (getattr(reception, 'model_tyre', None) or '').strip(),
                ) if p
            ),
        },
        {
            'label': 'Размер',
            'value': _tyre_size_label(
                getattr(reception, 'width_tyre', None),
                getattr(reception, 'profil_tyre', None),
                getattr(reception, 'radius', None),
            ),
        },
        {'label': 'Сезон', 'value': _fk_name(getattr(reception, 'sezon', None))},
        {
            'label': 'Диски',
            'value': ' '.join(
                p for p in (
                    _fk_name(getattr(reception, 'disk_type', None)),
                    (getattr(reception, 'model_disk', None) or '').strip(),
                ) if p
            ),
        },
        {
            'label': 'ET / DIA / PCD',
            'value': ' / '.join(
                p for p in (
                    _fk_name(getattr(reception, 'et_disk', None)),
                    _fk_name(getattr(reception, 'dia_disk', None)),
                    _fk_name(getattr(reception, 'psd_disk', None)),
                ) if p
            ),
        },
        {
            'label': 'Кол-во дисков / шин',
            'value': (
                '{} / {}'.format(
                    getattr(reception, 'count_disk', None) or 0,
                    getattr(reception, 'count_tyre', None) or 0,
                )
                if (getattr(reception, 'count_disk', None) or getattr(reception, 'count_tyre', None))
                else ''
            ),
        },
        {
            'label': 'В базу БУ колёс',
            'value': (
                'Отправлено'
                if getattr(reception, 'send_wheels_ib', None)
                else 'Не отправлено'
            ),
            'extra': ' · '.join(
                p for p in (
                    (
                        reception.send_wheels_ib_date.strftime('%d.%m.%Y %H:%M')
                        if getattr(reception, 'send_wheels_ib_date', None)
                        else ''
                    ),
                    (getattr(reception, 'send_wheels_ib_number', None) or '').strip(),
                ) if p
            ),
        },
    ]
    return [r for r in rows if r.get('value') not in (None, '', [])]


def get_car_wheels_summary(car, estimation=None, eco_url=''):
    """
    Колёса на авто + второй комплект / приёмка 2КК.
    Источник: page_kolesa оценки и RegInteractivOcenkaKolesaReception.
    """
    from eco.reception import estimation_has_kolesa2, get_kolesa_reception_or_none

    page_kolesa = None
    if estimation is not None:
        page_kolesa = getattr(estimation, 'page_kolesa', None)
        if page_kolesa is None and getattr(estimation, 'page_kolesa_id', None):
            try:
                from register.models import RegInteractivOcenkaKolesa
                page_kolesa = (
                    RegInteractivOcenkaKolesa.objects
                    .select_related(
                        'mark_tyre', 'width_tyre', 'profil_tyre', 'radius', 'sezon',
                        'disk_type', 'et_disk', 'dia_disk', 'psd_disk',
                        'mark_tyre2', 'width_tyre2', 'profil_tyre2', 'radius2', 'sezon2',
                        'disk_type2', 'et_disk2', 'dia_disk2', 'psd_disk2',
                    )
                    .filter(pk=estimation.page_kolesa_id)
                    .first()
                )
            except Exception:
                page_kolesa = None
        elif page_kolesa is not None:
            # догрузим FK, если объект уже в памяти без select_related
            try:
                from register.models import RegInteractivOcenkaKolesa
                page_kolesa = (
                    RegInteractivOcenkaKolesa.objects
                    .select_related(
                        'mark_tyre', 'width_tyre', 'profil_tyre', 'radius', 'sezon',
                        'disk_type', 'et_disk', 'dia_disk', 'psd_disk',
                        'mark_tyre2', 'width_tyre2', 'profil_tyre2', 'radius2', 'sezon2',
                        'disk_type2', 'et_disk2', 'dia_disk2', 'psd_disk2',
                    )
                    .filter(pk=page_kolesa.pk)
                    .first()
                ) or page_kolesa
            except Exception:
                pass

    has_kolesa2 = estimation_has_kolesa2(estimation) if estimation else False
    # если page_kolesa подгрузили отдельно — пересчитаем
    if page_kolesa is not None and estimation is not None:
        try:
            if page_kolesa.kolesa2_estimation == 1 or bool(page_kolesa.kolesa2):
                has_kolesa2 = True
        except Exception:
            pass

    kolesa_reception = get_kolesa_reception_or_none(estimation) if estimation else None
    lo = getattr(car, 'lo', None)
    # fallback: по RLK автомобиля
    if kolesa_reception is None:
        rlk = getattr(lo, 'rlk', None) if lo is not None else None
        if rlk is not None:
            try:
                from register.models import RegInteractivOcenkaKolesaReception
                kolesa_reception = (
                    RegInteractivOcenkaKolesaReception.objects
                    .filter(rlk=rlk)
                    .select_related(
                        'mark_tyre', 'width_tyre', 'profil_tyre', 'radius', 'sezon',
                        'disk_type', 'et_disk', 'dia_disk', 'psd_disk', 'user', 'rlk',
                    )
                    .first()
                )
            except Exception:
                kolesa_reception = None

    lo_flag = bool(getattr(lo, 'kolesa2_reception', False)) if lo is not None else False

    primary_rows = _wheels_rows_from_page_kolesa(page_kolesa, second=False)
    estimated_2kk_rows = (
        _wheels_rows_from_page_kolesa(page_kolesa, second=True)
        if has_kolesa2 or (page_kolesa and getattr(page_kolesa, 'kolesa2', False))
        else []
    )
    reception_rows = _wheels_rows_from_kolesa_reception(kolesa_reception)

    kolesa_url = ''
    if eco_url:
        kolesa_url = '{}?page=5'.format(eco_url.rstrip('/'))
    reception_url = ''
    if kolesa_reception is not None:
        reception_url = '/estimations/kolesa-reception/{}/'.format(kolesa_reception.pk)

    has_data = bool(primary_rows or estimated_2kk_rows or reception_rows or has_kolesa2 or lo_flag)
    return {
        'has_data': has_data,
        'has_kolesa2': has_kolesa2 or bool(kolesa_reception) or lo_flag,
        'lo_kolesa2_reception': lo_flag,
        'kolesa_url': kolesa_url,
        'reception_url': reception_url,
        'primary': {
            'title': 'Комплект на автомобиле',
            'rows': primary_rows,
        },
        'estimated_2kk': {
            'title': 'Второй комплект (из оценки)',
            'rows': estimated_2kk_rows,
            'show': bool(estimated_2kk_rows) or has_kolesa2,
        },
        'reception_2kk': {
            'title': 'Приёмка второго комплекта',
            'rows': reception_rows,
            'show': bool(kolesa_reception) or lo_flag,
            'object': kolesa_reception,
        },
    }


def _money(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _list_expenses_for_lo(lo) -> list[dict]:
    """Фактические затраты по ЛО (как eco.views.list_expenses)."""
    from documents.models import (
        DocServiceItem,
        DocZNProductKA,
        DocZNServicesKA,
        DocZNWorkKA,
    )

    if lo is None:
        return []

    items = []
    for list_work in DocZNWorkKA.objects.filter(zn__lo=lo).select_related('zn', 'zn__typeRemont', 'work'):
        items.append({
            'type': _type_label(getattr(list_work.zn, 'typeRemont', None), 'Работы'),
            'date': getattr(list_work.zn, 'dataTime', None),
            'document': getattr(list_work.zn, 'nomer', None) or '',
            'name': getattr(getattr(list_work, 'work', None), 'name', None) or '',
            'quantity': _money(list_work.quantity),
            'price': _money(list_work.price),
            'amount': _money(list_work.amount),
            'description': '',
            'kind': 'work',
        })
    for list_product in DocZNProductKA.objects.filter(zn__lo=lo).select_related('zn', 'zn__typeRemont', 'product'):
        items.append({
            'type': _type_label(getattr(list_product.zn, 'typeRemont', None), 'Товары'),
            'date': getattr(list_product.zn, 'dataTime', None),
            'document': getattr(list_product.zn, 'nomer', None) or '',
            'name': getattr(getattr(list_product, 'product', None), 'name', None) or '',
            'quantity': _money(list_product.quantity),
            'price': _money(list_product.price),
            'amount': _money(list_product.amount),
            'description': '',
            'kind': 'product',
        })
    for list_service in DocZNServicesKA.objects.filter(zn__lo=lo).select_related('zn', 'zn__typeRemont', 'service'):
        items.append({
            'type': _type_label(getattr(list_service.zn, 'typeRemont', None), 'Услуги'),
            'date': getattr(list_service.zn, 'dataTime', None),
            'document': getattr(list_service.zn, 'nomer', None) or '',
            'name': getattr(getattr(list_service, 'service', None), 'name', None) or '',
            'quantity': _money(list_service.quantity),
            'price': _money(list_service.price),
            'amount': _money(list_service.amount),
            'description': '',
            'kind': 'service',
        })
    for row in (
        DocServiceItem.objects
        .filter(doc_service__lo=lo)
        .select_related('doc_service', 'service', 'type_service')
    ):
        items.append({
            'type': _fk_name(getattr(row, 'type_service', None)) or 'Подготовка',
            'date': getattr(getattr(row, 'doc_service', None), 'date_time', None),
            'document': getattr(getattr(row, 'doc_service', None), 'nomer', None) or '',
            'name': _fk_name(getattr(row, 'service', None)),
            'quantity': _money(row.quantity),
            'price': _money(row.price),
            'amount': _money(row.amount),
            'description': (getattr(row, 'description', None) or '').strip(),
            'kind': 'prep',
        })

    items.sort(
        key=lambda x: (x.get('date') is None, x.get('date') or 0),
        reverse=True,
    )
    return items


def get_car_expenses_summary(car, estimation=None, eco_url='', limit=40):
    """
    Фактические затраты (как блок «Затраты» на ECO ?page=20):
    работы/товары/услуги ЗН + позиции DocServiceItem по ЛО.
    """
    items = []
    lo = getattr(car, 'lo', None)

    if estimation is not None:
        try:
            from eco.views import list_expenses
            raw = list_expenses(estimation) or []
            for row in raw:
                items.append({
                    'type': _type_label(row.get('type'), 'Прочее'),
                    'date': row.get('date'),
                    'document': row.get('document') or '',
                    'name': row.get('name') or '',
                    'quantity': _money(row.get('qyantity') if 'qyantity' in row else row.get('quantity')),
                    'price': _money(row.get('price')),
                    'amount': _money(row.get('amount')),
                    'description': (row.get('description') or '').strip(),
                    'kind': 'eco',
                })
        except Exception:
            items = []

    if not items and lo is not None:
        items = _list_expenses_for_lo(lo)

    total_amount = sum(_money(i.get('amount')) for i in items)
    total_qty = sum(_money(i.get('quantity')) for i in items)

    by_type = {}
    for item in items:
        key = _type_label(item.get('type'), 'Прочее') or 'Прочее'
        bucket = by_type.setdefault(key, {'type': key, 'count': 0, 'amount': 0.0})
        bucket['count'] += 1
        bucket['amount'] += _money(item.get('amount'))
    type_totals = sorted(by_type.values(), key=lambda x: -x['amount'])

    expenses_url = ''
    if eco_url:
        expenses_url = '{}?page=20'.format(eco_url.rstrip('/'))

    car_outlay = _money(getattr(car, 'outlay', None))

    return {
        'has_data': bool(items) or car_outlay > 0,
        'count': len(items),
        'total_amount': total_amount,
        'total_quantity': total_qty,
        'car_outlay': car_outlay,
        'type_totals': type_totals,
        'items': items[:limit],
        'items_hidden': max(0, len(items) - limit),
        'expenses_url': expenses_url,
    }


def get_car_agreements(car):
    if not getattr(car, 'lo_id', None):
        return []
    return list(
        DocCarAgreement.objects
        .filter(lo=car.lo, active=True)
        .select_related('unit', 'staff', 'rlk')
        .order_by('-dataTime', '-id')
    )


def get_car_shipments(car, agreements=None):
    if agreements is None:
        agreements = get_car_agreements(car)

    qs = (
        DocCarShipment.objects
        .filter(active=True)
        .select_related('unit', 'staff', 'rlk', 'agreement')
    )
    filters = Q()
    if getattr(car, 'lo_id', None):
        filters |= Q(lo=car.lo)
        filters |= Q(agreement__lo=car.lo)
    agreement_ids = [item.pk for item in agreements]
    if agreement_ids:
        filters |= Q(agreement_id__in=agreement_ids)
    if not filters:
        return []

    return list(qs.filter(filters).order_by('-dataTime', '-id').distinct())


def build_car_related_context(car, base1c=None):
    interactiv_ctx = get_car_interactiv_context(car)
    agreements = get_car_agreements(car)
    shipments = get_car_shipments(car, agreements=agreements)
    status_history = parse_status_history_from_1c(base1c or {})
    eco_url = interactiv_ctx.get('eco_url') or ''
    intake = get_car_intake_summary(
        car,
        interactiv_rlk=interactiv_ctx.get('interactiv_rlk'),
        eco_url=eco_url,
    )
    wheels = get_car_wheels_summary(
        car,
        estimation=interactiv_ctx.get('estimation'),
        eco_url=eco_url,
    )
    expenses = get_car_expenses_summary(
        car,
        estimation=interactiv_ctx.get('estimation'),
        eco_url=eco_url,
    )

    return {
        **interactiv_ctx,
        'agreements': agreements,
        'shipments': shipments,
        'status_history': status_history,
        'status_history_from_1c': bool(status_history),
        'status_history_stored_in_portal': False,
        'intake': intake,
        'wheels': wheels,
        'expenses': expenses,
    }
