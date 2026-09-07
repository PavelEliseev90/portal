# -*- coding: utf-8 -*-
"""Приём автомобиля по интерактивной оценке."""
from __future__ import annotations

import re
from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from register.models import (
    RegInteractivOcenkaReception,
    RegInteractivOcenkaRLK,
    RegRegInteractivOcenkaFiles,
)


def portal_absolute_url(relative_url, request=None):
    """Относительный путь → полный URL портала (https://host/media_dop/...)."""
    if not relative_url:
        return ''
    text = str(relative_url).strip()
    if text.startswith(('http://', 'https://')):
        return text
    if request is not None:
        return request.build_absolute_uri(text)
    base = (
        getattr(settings, 'MYKORS_PORTAL_PUBLIC_BASE_URL', None)
        or getattr(settings, 'PORTAL_PUBLIC_BASE_URL', None)
        or getattr(settings, 'SITE_URL', None)
        or 'https://ah.kors-group.com'
    ).rstrip('/')
    if not text.startswith('/'):
        text = '/' + text
    return base + text


# Фото / сканы страницы приёма (RegRegInteractivOcenkaFiles.type_file)
RECEPTION_FILE_SLOTS = (
    {
        'type_file': 'reception_passport_spread',
        'input_name': 'file_reception_passport_spread',
        'label': 'Скан паспорта — первый разворот',
        'hint': 'Разворот с фото и основными данными',
    },
    {
        'type_file': 'reception_passport_registration',
        'input_name': 'file_reception_passport_registration',
        'label': 'Скан паспорта — прописка',
        'hint': 'Страница с регистрацией / пропиской',
    },
    {
        'type_file': 'reception_snils',
        'input_name': 'file_reception_snils',
        'label': 'СНИЛС',
        'hint': '',
    },
    {
        'type_file': 'reception_pts',
        'input_name': 'file_reception_pts',
        'label': 'ПТС',
        'hint': 'Скан / фото ПТС',
    },
    {
        'type_file': 'reception_bankruptcy',
        'input_name': 'file_reception_bankruptcy',
        'label': 'Проверка банкротства',
        'hint': 'Скрин / PDF результата проверки',
    },
    {
        'type_file': 'reception_fines',
        'input_name': 'file_reception_fines',
        'label': 'Проверка штрафов',
        'hint': '',
    },
    {
        'type_file': 'reception_bailiffs',
        'input_name': 'file_reception_bailiffs',
        'label': 'Проверка приставов',
        'hint': '',
    },
)

RECEPTION_FILE_TYPES = tuple(slot['type_file'] for slot in RECEPTION_FILE_SLOTS)


def reception_allowed(interactiv_rlk: RegInteractivOcenkaRLK) -> bool:
    """Страница приёма доступна всегда (карточка создаётся по кнопке)."""
    return interactiv_rlk is not None


def status_is_am_accepted(interactiv_rlk: RegInteractivOcenkaRLK) -> bool:
    """Статус оценки — «АМ принят» (автомобиль уже принят)."""
    if interactiv_rlk is None:
        return False
    status = getattr(interactiv_rlk, 'status', None)
    name = (getattr(status, 'name', None) or '').strip().lower()
    return 'ам принят' in name


def user_is_eco_staff(user) -> bool:
    """Сотрудник ЕЦО, которому разрешено править приём после «АМ принят»."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    profiles = getattr(user, 'profiles', None)
    return bool(getattr(profiles, 'eco', False))


def reception_fields_editable(interactiv_rlk: RegInteractivOcenkaRLK, user) -> bool:
    """
    Поля карточки приёма можно редактировать.
    После статуса «АМ принят» — только сотрудники ЕЦО (и суперпользователь).
    Кнопки печати / 1С / создание 2КК этим флагом не ограничиваются.
    """
    if not reception_allowed(interactiv_rlk):
        return False
    if not status_is_am_accepted(interactiv_rlk):
        return True
    return user_is_eco_staff(user)


def serialize_reception_file(file_obj: RegRegInteractivOcenkaFiles) -> dict:
    return {
        'id': file_obj.pk,
        'type_file': file_obj.type_file or '',
        'name': file_obj.name or '',
        'url': file_obj.get_absolute_url(),
        'thumb_url': file_obj.get_thumbnail_url(),
        'date': file_obj.date.strftime('%d.%m.%Y %H:%M') if file_obj.date else '',
        'is_video': bool(file_obj.is_video()) if file_obj.file else False,
    }


def get_reception_files_queryset(estimation):
    if estimation is None:
        return RegRegInteractivOcenkaFiles.objects.none()
    return (
        RegRegInteractivOcenkaFiles.objects
        .filter(estimation=estimation, type_file__in=RECEPTION_FILE_TYPES, blank=False)
        .exclude(file='')
        .order_by('type_file', '-date', '-id')
    )


def get_reception_files_by_type(estimation) -> dict:
    """Словарь type_file → list[serialized file]."""
    result = {slot['type_file']: [] for slot in RECEPTION_FILE_SLOTS}
    for file_obj in get_reception_files_queryset(estimation):
        key = file_obj.type_file or ''
        if key in result:
            result[key].append(serialize_reception_file(file_obj))
    return result


def get_reception_file_blocks(estimation) -> list:
    """Блоки для шаблона: слот + загруженные файлы."""
    by_type = get_reception_files_by_type(estimation)
    blocks = []
    for slot in RECEPTION_FILE_SLOTS:
        blocks.append({
            **slot,
            'files': by_type.get(slot['type_file'], []),
        })
    return blocks


def save_reception_files_from_request(estimation, files_dict, user=None) -> int:
    """Сохраняет загруженные файлы приёма. Возвращает число новых файлов."""
    if estimation is None or not files_dict:
        return 0
    created_count = 0
    for slot in RECEPTION_FILE_SLOTS:
        uploaded = files_dict.getlist(slot['input_name']) if hasattr(files_dict, 'getlist') else []
        if not uploaded:
            continue
        for uploaded_file in uploaded:
            if not uploaded_file:
                continue
            name = (uploaded_file.name or 'file').lower()
            file_row = RegRegInteractivOcenkaFiles(
                estimation=estimation,
                type_file=slot['type_file'],
                name=name,
                text='',
                type_point='',
                cor_x=0,
                cor_y=0,
                file_number=0,
                blank=False,
                date=datetime.now(),
                user=user if getattr(user, 'is_authenticated', False) else None,
            )
            file_row.file = uploaded_file
            file_row.save()
            try:
                file_row._generate_thumbnail()
            except Exception:
                pass
            created_count += 1
    return created_count


def delete_reception_file(estimation, file_id) -> bool:
    if estimation is None or not file_id:
        return False
    try:
        file_id = int(file_id)
    except (TypeError, ValueError):
        return False
    qs = RegRegInteractivOcenkaFiles.objects.filter(
        pk=file_id,
        estimation=estimation,
        type_file__in=RECEPTION_FILE_TYPES,
    )
    deleted, _ = qs.delete()
    return deleted > 0


def _as_date(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _as_datetime(value):
    """Парсинг даты и времени из datetime-local / строки формы."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip()
    if not text:
        return None
    text = text.replace('T', ' ')
    for fmt in (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d.%m.%Y %H:%M:%S',
        '%d.%m.%Y %H:%M',
        '%d/%m/%Y %H:%M',
    ):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    # Только дата — полночь
    only_date = _as_date(text)
    if only_date is not None:
        return datetime.combine(only_date, datetime.min.time())
    return None


def _as_int(value, default=0):
    if value is None or value == '':
        return default
    try:
        return int(float(str(value).replace(' ', '').replace(',', '.')))
    except (TypeError, ValueError):
        return default


def _default_reception_staff(interactiv_rlk: RegInteractivOcenkaRLK):
    """Оценщик для приёма в 1С: по умолчанию — кто начал оценку."""
    estimation = interactiv_rlk.estimation
    if estimation is not None and getattr(estimation, 'staff_id', None):
        return estimation.staff
    return getattr(interactiv_rlk, 'staff_rlk', None)


def _infer_pts_electronic(proverki, pts_number=''):
    """Определить вид ПТС: из проверок оценки или по формату номера."""
    if proverki is not None and proverki.epts is not None:
        return bool(proverki.epts)
    digits = re.sub(r'\D', '', (pts_number or '').strip())
    if len(digits) >= 15:
        return True
    if digits and len(digits) <= 8 and re.search(r'[A-Za-zА-Яа-я]', pts_number or ''):
        return False
    return None


def _mark_model(estimation):
    mark = (getattr(estimation, 'mark_name', None) or '').strip()
    model = (getattr(estimation, 'model_name', None) or '').strip()
    mod = getattr(estimation, 'modification', None)
    if mod is not None:
        try:
            if not mark and mod.model and mod.model.mark:
                mark = mod.model.mark.name or ''
            if not model and mod.model:
                model = mod.model.name or ''
        except Exception:
            pass
    return mark, model


def build_prefill(interactiv_rlk: RegInteractivOcenkaRLK) -> dict:
    estimation = interactiv_rlk.estimation
    docs = getattr(estimation, 'page_documents', None) if estimation else None
    salon = getattr(estimation, 'page_salon', None) if estimation else None
    vnesh = getattr(estimation, 'page_vnesh', None) if estimation else None
    proverki = getattr(estimation, 'page_proverki', None) if estimation else None
    mark, model = _mark_model(estimation) if estimation else ('', '')

    pts_date = None
    sts_date = None
    if docs is not None:
        pts_date = _as_date(docs.pts_date)
        sts_date = _as_date(docs.sts_date)

    body_color = ''
    if docs is not None and docs.pts_color:
        body_color = docs.pts_color
    elif vnesh is not None and getattr(vnesh, 'color', None):
        body_color = vnesh.color

    salon_color = ''

    mileage = 0
    if salon is not None and salon.run:
        mileage = _as_int(salon.run)

    pts_number = (docs.pts_number if docs else '') or ''
    pts_electronic = _infer_pts_electronic(proverki, pts_number)

    return {
        'type_reception': (
            getattr(interactiv_rlk, 'type_reception', None)
            or (docs.type_reception if docs else None)
        ),
        'organization': (
            getattr(interactiv_rlk, 'organization', None)
            or (docs.organization if docs else None)
        ),
        'filial': (
            getattr(interactiv_rlk, 'filial', None)
            or (docs.filial if docs else None)
        ),
        'unit': (
            getattr(interactiv_rlk, 'unit', None)
            or (docs.unit if docs else None)
        ),
        'store': (
            getattr(interactiv_rlk, 'store', None)
            or (docs.store if docs else None)
        ),
        'staff': _default_reception_staff(interactiv_rlk),
        'customer_family': (docs.customer_family if docs else '') or '',
        'customer_name': (docs.customer_name if docs else '') or '',
        'customer_patronymic': (docs.customer_patronymic if docs else '') or '',
        'customer_phone': (docs.customer_phone if docs else '') or '',
        'vin': (estimation.vin if estimation else '') or '',
        'vin2': (estimation.number_body if estimation else '') or '',
        'mark': mark or '',
        'model': model or '',
        'year': _as_int(estimation.year if estimation else 0),
        'mileage': mileage,
        'pts_mark_model': (docs.pts_mark_model if docs else '') or '',
        'plate_number': (docs.plate_number if docs else '') or '',
        'count_owners': _as_int(docs.count_owners if docs else 0),
        'count_keys': _as_int(docs.count_key if docs else 0),
        'chassis_number': '',
        'body_number': (estimation.number_body if estimation else '') or '',
        'pts_electronic': pts_electronic,
        'pts_series': '',
        'pts_number': pts_number,
        'pts_date': pts_date,
        'pts_org_address': '',
        'sts_number': (docs.sts_number if docs else '') or '',
        'sts_date': sts_date,
        'pts_original': bool(docs.pts_original) if docs else False,
        'pts_org_issuer': '',
        'salon_color': salon_color or '',
        'body_color': body_color or '',
        'engine_number': (docs.engine_number if docs else '') or '',
        'mass': 0,
        'max_mass': 0,
        'eco_class': '',
        'amount_vzaimozachet': 0,
        'agreement_number_op': '',
        'actual_reception_at': timezone.now(),
    }


@transaction.atomic
def create_reception(interactiv_rlk: RegInteractivOcenkaRLK, user=None) -> RegInteractivOcenkaReception:
    try:
        reception = interactiv_rlk.page_reception
    except RegInteractivOcenkaReception.DoesNotExist:
        data = build_prefill(interactiv_rlk)
        reception = RegInteractivOcenkaReception(
            interactiv_rlk=interactiv_rlk,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
            updated_by=user if getattr(user, 'is_authenticated', False) else None,
            **data,
        )
        reception.save()

    # Если оценка со 2-м комплектом — сразу создаём приёмку колёс.
    if estimation_has_kolesa2(interactiv_rlk.estimation):
        ensure_kolesa_reception(interactiv_rlk.estimation, user=user)

    return reception


def estimation_has_kolesa2(estimation) -> bool:
    """Оценка заявлена со вторым комплектом колёс."""
    if estimation is None:
        return False
    page_kolesa = getattr(estimation, 'page_kolesa', None)
    if page_kolesa is None:
        return False
    if page_kolesa.kolesa2_estimation == 1:
        return True
    return bool(page_kolesa.kolesa2)


def get_kolesa_reception_or_none(estimation):
    from register.models import RegInteractivOcenkaKolesaReception
    if estimation is None:
        return None
    return (
        RegInteractivOcenkaKolesaReception.objects
        .filter(estimation=estimation)
        .select_related(
            'mark_tyre', 'width_tyre', 'profil_tyre', 'radius', 'sezon',
            'disk_type', 'et_disk', 'dia_disk', 'psd_disk', 'user', 'rlk',
        )
        .first()
    )


def build_kolesa2_1c_extras(estimation, request=None) -> dict:
    """
    Блок 2КК для выгрузки в 1С (и в Type=estimation, и в Type=reception).
    Возвращает HasKolesa2 / KolesaReception / Kolesa2 / KolesaReceptionFiles.
    """
    from register.models import RegRegInteractivOcenkaFilesKolesaReception
    from register.serializers import RegInteractivOcenkaKolesaReceptionSerializer

    has_kolesa2 = estimation_has_kolesa2(estimation)
    kolesa_reception = get_kolesa_reception_or_none(estimation)

    kolesa2_from_estimation = None
    page_kolesa = getattr(estimation, 'page_kolesa', None) if estimation else None
    if page_kolesa is not None and has_kolesa2:
        def _ref_name(obj):
            return getattr(obj, 'name', None) if obj is not None else None

        kolesa2_from_estimation = {
            'kolesa2': bool(page_kolesa.kolesa2),
            'kolesa2_estimation': page_kolesa.kolesa2_estimation,
            'mark_tyre2': _ref_name(page_kolesa.mark_tyre2),
            'mark_tyre2_id': page_kolesa.mark_tyre2_id,
            'model_tyre2': page_kolesa.model_tyre2 or '',
            'width_tyre2': _ref_name(page_kolesa.width_tyre2),
            'width_tyre2_id': page_kolesa.width_tyre2_id,
            'profil_tyre2': _ref_name(page_kolesa.profil_tyre2),
            'profil_tyre2_id': page_kolesa.profil_tyre2_id,
            'radius2': _ref_name(page_kolesa.radius2),
            'radius2_id': page_kolesa.radius2_id,
            'sezon2': _ref_name(page_kolesa.sezon2),
            'sezon2_id': page_kolesa.sezon2_id,
            'disk_type2': _ref_name(page_kolesa.disk_type2),
            'disk_type2_id': page_kolesa.disk_type2_id,
            'model_disk2': page_kolesa.model_disk2 or '',
            'et_disk2': _ref_name(page_kolesa.et_disk2),
            'et_disk2_id': page_kolesa.et_disk2_id,
            'dia_disk2': _ref_name(page_kolesa.dia_disk2),
            'dia_disk2_id': page_kolesa.dia_disk2_id,
            'psd_disk2': _ref_name(page_kolesa.psd_disk2),
            'psd_disk2_id': page_kolesa.psd_disk2_id,
            'count_disk2': page_kolesa.count_disk2 or 0,
            'count_tyre2': page_kolesa.count_tyre2 or 0,
        }

    kolesa_files = []
    if kolesa_reception is not None:
        for f in (
            RegRegInteractivOcenkaFilesKolesaReception.objects
            .filter(kolesa_reception=kolesa_reception, blank=False)
            .exclude(file='')
            .order_by('file_number', 'id')
        ):
            kolesa_files.append({
                'id': f.pk,
                'name': f.name or '',
                'type_file': f.type_file or '',
                'url': portal_absolute_url(
                    f.get_absolute_url() if hasattr(f, 'get_absolute_url') else '',
                    request,
                ),
                'thumb_url': portal_absolute_url(
                    f.get_thumbnail_url() if hasattr(f, 'get_thumbnail_url') else '',
                    request,
                ),
                'file_number': f.file_number or 0,
            })

    return {
        'HasKolesa2': has_kolesa2,
        'KolesaReception': (
            RegInteractivOcenkaKolesaReceptionSerializer(kolesa_reception, many=False).data
            if kolesa_reception is not None
            else None
        ),
        'Kolesa2': kolesa2_from_estimation,
        'KolesaReceptionFiles': kolesa_files,
        'KolesaReceptionId': kolesa_reception.pk if kolesa_reception is not None else None,
    }


def _strip_unit_price_groups(payload):
    """Убрать поля ценовых групп из unit/unit_dc/agreement_unit во всём JSON."""
    from refs.serializers import ref_unit_price_group_field_names

    drop = set(ref_unit_price_group_field_names())
    unit_keys = frozenset(('unit', 'unit_dc', 'agreement_unit'))

    def _walk(obj):
        if isinstance(obj, dict):
            for key in unit_keys:
                unit = obj.get(key)
                if isinstance(unit, dict):
                    for fname in drop:
                        unit.pop(fname, None)
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(payload)
    return payload


def build_kolesa_reception_send_payload(reception, request=None) -> dict:
    """JSON для выгрузки 2КК: РЛК, листы оценки (DocLO), приёмка."""
    from documents.models import DocLO
    from documents.serializers import DocLOKolesaExportSerializer, DocRLKKolesaExportSerializer
    from register.serializers import RegInteractivOcenkaKolesaReceptionExportSerializer

    if reception is None:
        return {}

    rlk = reception.rlk
    estimation = reception.estimation

    if rlk is not None:
        los = (
            DocLO.objects.filter(rlk=rlk)
            .select_related(
                'organization', 'filial', 'unit', 'store', 'type_reception',
                'staff', 'customer', 'cars', 'modification_autoru',
                'complectation_autoru', 'agreement_unit',
            )
            .order_by('-dataTime', '-id')
        )
    else:
        los = DocLO.objects.none()

    kolesa_extras = build_kolesa2_1c_extras(estimation, request=request) if estimation else {}

    payload = {
        'Rlk': DocRLKKolesaExportSerializer(rlk, many=False).data if rlk else None,
        'Lo': DocLOKolesaExportSerializer(los, many=True).data,
        'KolesaReception': RegInteractivOcenkaKolesaReceptionExportSerializer(
            reception, many=False,
        ).data,
        'KolesaReceptionFiles': kolesa_extras.get('KolesaReceptionFiles') or [],
        'Kolesa2': kolesa_extras.get('Kolesa2'),
        'HasKolesa2': kolesa_extras.get('HasKolesa2'),
        'EstimationId': estimation.pk if estimation else None,
        'KolesaReceptionId': reception.pk,
    }
    return _strip_unit_price_groups(payload)


def queue_estimation_for_1c(estimation, comment=''):
    """Поставить РЛК/оценку в очередь выгрузки в 1С (RegSwapKors, status_code=60)."""
    from register.models import RegSwapKors

    if estimation is None:
        return False
    rlk = getattr(estimation, 'rlk', None)
    if rlk is None:
        return False
    if RegSwapKors.objects.filter(rlk=rlk, estimation=estimation, status_code=60).exists():
        return False
    swap = RegSwapKors()
    swap.rlk = rlk
    swap.estimation = estimation
    if comment:
        swap.comment = (comment or '')[:250]
    swap.save()
    return True


def ensure_kolesa_reception(estimation, user=None):
    """Создать приёмку 2КК, если оценка со вторым комплектом."""
    if not estimation_has_kolesa2(estimation):
        return get_kolesa_reception_or_none(estimation)
    from estimations.views_kolesa_reception import create_kolesa_reception
    return create_kolesa_reception(estimation, user)


def get_reception_or_none(interactiv_rlk: RegInteractivOcenkaRLK):
    try:
        return (
            RegInteractivOcenkaReception.objects
            .select_related('staff')
            .get(interactiv_rlk=interactiv_rlk)
        )
    except RegInteractivOcenkaReception.DoesNotExist:
        return None


def search_reception_staff(query='', staff_id=None, limit=30):
    """Поиск оценщиков для вкладки приёма (RefStaff по ФИО)."""
    from refs.models import RefStaff

    try:
        limit = max(1, min(int(limit or 30), 50))
    except (TypeError, ValueError):
        limit = 30

    qs = RefStaff.objects.exclude(name='')
    if staff_id:
        try:
            qs = qs.filter(pk=int(staff_id))
        except (TypeError, ValueError):
            return []
    elif query:
        qs = qs.filter(name__icontains=query.strip())
    else:
        return []

    return [
        {
            'id': staff.pk,
            'text': staff.get_reception_display_name(),
            'buauto': staff.buauto,
        }
        for staff in qs.order_by('name')[:limit]
    ]


def is_commission_reception(reception: RegInteractivOcenkaReception) -> bool:
    """Приём на комиссию — по названию типа или известному id=3."""
    type_reception = reception.type_reception
    if type_reception is None:
        return False
    name = (type_reception.name or '').lower()
    if 'комисс' in name:
        return True
    return type_reception.id == 3


def _normalize_digits(value, max_len=None):
    digits = re.sub(r'\D', '', value or '')
    if max_len:
        return digits[:max_len]
    return digits


def _vat_rate_label(reception: RegInteractivOcenkaReception) -> str:
    raw = (reception.customer_vat_rate or '').strip()
    if not raw:
        return ''
    for value, label in RegInteractivOcenkaReception.VAT_RATE_CHOICES:
        if value == raw:
            return label
    return raw


def _tax_system_label(reception: RegInteractivOcenkaReception) -> str:
    raw = (reception.customer_tax_system or '').strip()
    if not raw:
        return ''
    for value, label in RegInteractivOcenkaReception.TAX_SYSTEM_CHOICES:
        if value == raw:
            return label
    return raw


def _is_valid_email(value: str) -> bool:
    text = (value or '').strip()
    if not text:
        return False
    return '@' in text and '.' in text.split('@')[-1]


def _validate_business_customer(reception: RegInteractivOcenkaReception, errors: list[str]) -> None:
    """Общие проверки для юрлица и ИП."""
    if not (reception.customer_tax_system or '').strip():
        errors.append('Укажите систему налогообложения.')
    if not (reception.customer_vat_rate or '').strip():
        errors.append('Укажите ставку НДС.')
    if not _is_valid_email(reception.customer_email):
        errors.append('Укажите корректный email.')
    if not (reception.customer_bank_name or '').strip():
        errors.append('Укажите наименование банка.')
    bik = _normalize_digits(reception.customer_bank_bik)
    if not bik:
        errors.append('Укажите БИК банка.')
    elif len(bik) != 9:
        errors.append('БИК должен содержать 9 цифр.')
    account = _normalize_digits(reception.customer_bank_account)
    if not account:
        errors.append('Укажите расчётный счёт.')
    elif len(account) != 20:
        errors.append('Расчётный счёт должен содержать 20 цифр.')
    corr_account = _normalize_digits(reception.customer_bank_corr_account)
    if not corr_account:
        errors.append('Укажите корреспондентский счёт.')
    elif len(corr_account) != 20:
        errors.append('Корреспондентский счёт должен содержать 20 цифр.')


def validate_reception_client(reception: RegInteractivOcenkaReception) -> list[str]:
    """Проверка блока «Клиент» перед сохранением приёма."""
    errors = []

    if not reception.actual_reception_at:
        errors.append('Укажите фактическую дату и время приёма автомобиля.')

    customer_type = (reception.customer_type or '').strip()
    commission = is_commission_reception(reception)

    if not customer_type:
        errors.append('Укажите тип клиента: физическое лицо, юридическое лицо или ИП.')
        return errors

    inn = _normalize_digits(reception.customer_inn)

    if customer_type == RegInteractivOcenkaReception.CUSTOMER_TYPE_FL:
        if reception.registration_owner_fl is None:
            errors.append('Для физического лица укажите «Регистрация собственником ФЛ».')
        if commission:
            if not inn:
                errors.append('Для приёма на комиссию укажите ИНН клиента.')
            elif len(inn) != 12:
                errors.append('ИНН физического лица должен содержать 12 цифр.')

    elif customer_type == RegInteractivOcenkaReception.CUSTOMER_TYPE_UL:
        if not (reception.customer_company_name or '').strip():
            errors.append('Укажите наименование организации.')
        if not inn:
            errors.append('Укажите ИНН организации.')
        elif len(inn) != 10:
            errors.append('ИНН юридического лица должен содержать 10 цифр.')
        kpp = _normalize_digits(reception.customer_kpp)
        if not kpp:
            errors.append('Укажите КПП организации.')
        elif len(kpp) != 9:
            errors.append('КПП должен содержать 9 цифр.')
        ogrn = _normalize_digits(reception.customer_ogrn)
        if not ogrn:
            errors.append('Укажите ОГРН организации.')
        elif len(ogrn) != 13:
            errors.append('ОГРН должен содержать 13 цифр.')
        if not (reception.customer_legal_address or '').strip():
            errors.append('Укажите юридический адрес организации.')
        _validate_business_customer(reception, errors)

    elif customer_type == RegInteractivOcenkaReception.CUSTOMER_TYPE_IP:
        if not (reception.customer_company_name or '').strip():
            errors.append('Укажите ФИО индивидуального предпринимателя.')
        if not inn:
            errors.append('Укажите ИНН ИП.')
        elif len(inn) != 12:
            errors.append('ИНН ИП должен содержать 12 цифр.')
        ogrn = _normalize_digits(reception.customer_ogrn)
        if not ogrn:
            errors.append('Укажите ОГРНИП.')
        elif len(ogrn) != 15:
            errors.append('ОГРНИП должен содержать 15 цифр.')
        _validate_business_customer(reception, errors)

    return errors


def reception_select_options():
    from refs.models import (
        RefFilial,
        RefOrganization,
        RefStore,
        RefTypeReceptionCarsOrganization,
        RefUnit,
    )
    return {
        'type_receptions': [
            {
                'id': item['id'],
                'name': item['name'],
                'is_commission': 'комисс' in (item['name'] or '').lower() or item['id'] == 3,
            }
            for item in RefTypeReceptionCarsOrganization.objects.exclude(name='').order_by('name').values('id', 'name')
        ],
        'customer_types': [
            {'value': value, 'label': label}
            for value, label in RegInteractivOcenkaReception.CUSTOMER_TYPE_CHOICES
        ],
        'vat_rates': [
            {'value': value, 'label': label}
            for value, label in RegInteractivOcenkaReception.VAT_RATE_CHOICES
            if value
        ],
        'tax_systems': [
            {'value': value, 'label': label}
            for value, label in RegInteractivOcenkaReception.TAX_SYSTEM_CHOICES
            if value
        ],
        'organizations': list(
            RefOrganization.objects.exclude(name='').order_by('name').values('id', 'name')
        ),
        'filials': list(
            RefFilial.objects.exclude(name='').order_by('name').values('id', 'name')
        ),
        'stores': list(
            RefStore.objects.exclude(name='').order_by('name').values('id', 'name')
        ),
        'units': list(
            RefUnit.objects.exclude(name='').order_by('name').values('id', 'name')
        ),
    }


def apply_post_to_reception(
    reception: RegInteractivOcenkaReception,
    post,
    user=None,
    save=True,
) -> RegInteractivOcenkaReception:
    from refs.models import (
        RefFilial,
        RefOrganization,
        RefStaff,
        RefStore,
        RefTypeReceptionCarsOrganization,
        RefUnit,
    )

    def _fk(model, key):
        raw = post.get(key, '')
        if raw in (None, '', '0', 'None'):
            return None
        try:
            return model.objects.filter(pk=int(raw)).first()
        except (TypeError, ValueError):
            return None

    reception.type_reception = _fk(RefTypeReceptionCarsOrganization, 'type_reception')
    reception.organization = _fk(RefOrganization, 'organization')
    reception.filial = _fk(RefFilial, 'filial')
    reception.unit = _fk(RefUnit, 'unit')
    reception.store = _fk(RefStore, 'store')
    reception.staff = _fk(RefStaff, 'staff')

    if 'actual_reception_at' in post:
        reception.actual_reception_at = _as_datetime(post.get('actual_reception_at'))

    for field in (
        'customer_family', 'customer_name', 'customer_patronymic', 'customer_phone',
        'customer_type', 'customer_inn', 'customer_kpp', 'customer_ogrn',
        'customer_company_name', 'customer_legal_address', 'customer_vat_rate',
        'customer_tax_system', 'customer_email', 'customer_contact_person',
        'customer_actual_address', 'customer_bank_name', 'customer_bank_bik',
        'customer_bank_account', 'customer_bank_corr_account',
        'vin', 'vin2', 'mark', 'model', 'pts_mark_model', 'plate_number',
        'chassis_number', 'body_number', 'pts_series', 'pts_number', 'pts_org_address', 'sts_number',
        'pts_org_issuer', 'salon_color', 'body_color', 'engine_number', 'eco_class',
        'agreement_number_op',
    ):
        if field in post:
            setattr(reception, field, (post.get(field) or '').strip())

    if 'customer_inn' in post:
        reception.customer_inn = _normalize_digits(post.get('customer_inn'), 12)
    if 'customer_kpp' in post:
        reception.customer_kpp = _normalize_digits(post.get('customer_kpp'), 9)
    if 'customer_ogrn' in post:
        reception.customer_ogrn = _normalize_digits(post.get('customer_ogrn'), 15)
    if 'customer_bank_bik' in post:
        reception.customer_bank_bik = _normalize_digits(post.get('customer_bank_bik'), 9)
    if 'customer_bank_account' in post:
        reception.customer_bank_account = _normalize_digits(post.get('customer_bank_account'), 20)
    if 'customer_bank_corr_account' in post:
        reception.customer_bank_corr_account = _normalize_digits(post.get('customer_bank_corr_account'), 20)

    for field in ('year', 'mileage', 'count_owners', 'count_keys', 'mass', 'max_mass', 'amount_vzaimozachet'):
        if field in post:
            setattr(reception, field, _as_int(post.get(field), 0))

    if 'pts_date' in post:
        reception.pts_date = _as_date(post.get('pts_date'))
    if 'sts_date' in post:
        reception.sts_date = _as_date(post.get('sts_date'))

    reception.pts_original = str(post.get('pts_original', '')).lower() in ('1', 'true', 'on', 'yes')

    if 'pts_electronic' in post:
        raw = post.get('pts_electronic', '')
        if raw in (None, '', 'None'):
            reception.pts_electronic = None
        elif str(raw).lower() in ('1', 'true', 'yes', 'on'):
            reception.pts_electronic = True
        else:
            reception.pts_electronic = False

    if reception.pts_electronic is True:
        reception.pts_series = ''

    if 'registration_owner_fl' in post:
        raw = post.get('registration_owner_fl', '')
        if raw in (None, '', 'None'):
            reception.registration_owner_fl = None
        elif str(raw).lower() in ('1', 'true', 'yes', 'on'):
            reception.registration_owner_fl = True
        else:
            reception.registration_owner_fl = False

    if user is not None and getattr(user, 'is_authenticated', False):
        reception.updated_by = user

    if save:
        reception.save()
    return reception


def enrich_reception_export(reception_data: dict, reception: RegInteractivOcenkaReception) -> dict:
    """Явные поля приёма для выгрузки в 1С (ПТС, оценщик)."""
    if reception.pts_electronic is True:
        pts_type = 'electronic'
        pts_type_label = 'Электронный'
        pts_number_full = (reception.pts_number or '').strip()
    elif reception.pts_electronic is False:
        pts_type = 'paper'
        pts_type_label = 'Бумажный'
        series = (reception.pts_series or '').strip()
        number = (reception.pts_number or '').strip()
        pts_number_full = ' '.join(part for part in (series, number) if part)
    else:
        pts_type = None
        pts_type_label = None
        pts_number_full = (reception.pts_number or '').strip()

    staff = reception.staff
    staff_id = reception.staff_id
    staff_name = (staff.name if staff else '') or ''
    staff_uin = (staff.uin if staff else '') or ''
    staff_domain_login = (staff.domain_login if staff else '') or ''

    reception_data = dict(reception_data)
    reception_data.update({
        'actual_reception_at': reception.actual_reception_at,
        'actual_reception_at_str': (
            reception.actual_reception_at.strftime('%d.%m.%Y %H:%M')
            if reception.actual_reception_at
            else ''
        ),
        'pts_electronic': reception.pts_electronic,
        'pts_series': (reception.pts_series or '').strip(),
        'pts_number': (reception.pts_number or '').strip(),
        'pts_type': pts_type,
        'pts_type_label': pts_type_label,
        'pts_number_full': pts_number_full,
        'staff_id': staff_id,
        'staff_name': staff_name,
        'staff_uin': staff_uin,
        'staff_domain_login': staff_domain_login,
        'customer_type': (reception.customer_type or '').strip(),
        'customer_type_label': reception.get_customer_type_display() if reception.customer_type else '',
        'customer_inn': (reception.customer_inn or '').strip(),
        'customer_kpp': (reception.customer_kpp or '').strip(),
        'customer_ogrn': (reception.customer_ogrn or '').strip(),
        'customer_company_name': (reception.customer_company_name or '').strip(),
        'customer_legal_address': (reception.customer_legal_address or '').strip(),
        'customer_vat_rate': (reception.customer_vat_rate or '').strip(),
        'customer_vat_rate_label': _vat_rate_label(reception),
        'customer_tax_system': (reception.customer_tax_system or '').strip(),
        'customer_tax_system_label': _tax_system_label(reception),
        'customer_email': (reception.customer_email or '').strip(),
        'customer_contact_person': (reception.customer_contact_person or '').strip(),
        'customer_actual_address': (reception.customer_actual_address or '').strip(),
        'customer_bank_name': (reception.customer_bank_name or '').strip(),
        'customer_bank_bik': (reception.customer_bank_bik or '').strip(),
        'customer_bank_account': (reception.customer_bank_account or '').strip(),
        'customer_bank_corr_account': (reception.customer_bank_corr_account or '').strip(),
        'registration_owner_fl': reception.registration_owner_fl,
        'is_commission_reception': is_commission_reception(reception),
    })
    return reception_data


def build_reception_1c_payload(interactiv_rlk: RegInteractivOcenkaRLK, reception: RegInteractivOcenkaReception) -> dict:
    from documents.serializers import DocRLKSerializer
    from register.serializers import (
        RegInteractivOcenkaReceptionSerializer,
        RegInteractivOcenkaRLKSerializer,
        RegInteractivOcenkaSerializer,
        RegInteractivOcenkaSoglasovanieSerializer,
    )

    estimation = interactiv_rlk.estimation
    rlk = interactiv_rlk.rlk
    payload = {
        'Type': 'reception',
        'Rlk': DocRLKSerializer(rlk, many=False).data if rlk else None,
        'Estimation': RegInteractivOcenkaSerializer(estimation, many=False).data if estimation else None,
        'Soglasovanie': (
            RegInteractivOcenkaSoglasovanieSerializer(interactiv_rlk.page_soglasovanie, many=False).data
            if interactiv_rlk.page_soglasovanie_id
            else None
        ),
        'Info': RegInteractivOcenkaRLKSerializer(interactiv_rlk, many=False).data,
        'Reception': enrich_reception_export(
            RegInteractivOcenkaReceptionSerializer(reception, many=False).data,
            reception,
        ),
        'ReceptionFiles': [
            serialize_reception_file(f)
            for f in get_reception_files_queryset(estimation)
        ],
    }
    payload.update(build_kolesa2_1c_extras(estimation))
    return payload


def send_reception_1c(interactiv_rlk: RegInteractivOcenkaRLK, reception: RegInteractivOcenkaReception | None = None):
    """Отправка приёма в 1С. Возвращает (ok: bool, status_code|None, text)."""
    import requests
    from task_manager.views import url_hs_alfa_auto, url_hs_kors_auto

    reception = reception or get_reception_or_none(interactiv_rlk)
    if reception is None:
        return False, None, 'Приём не создан'

    rlk = interactiv_rlk.rlk
    js_data = build_reception_1c_payload(interactiv_rlk, reception)
    try:
        if rlk is None or rlk.unit is None:
            response = requests.post(url_hs_kors_auto, json=js_data)
        elif rlk.unit.ib and rlk.unit.ib.alfa:
            response = requests.post(url_hs_alfa_auto, json=js_data)
        else:
            response = requests.post(url_hs_kors_auto, json=js_data)
    except Exception as exc:
        reception.sent_to_1c_status = str(exc)[:250]
        reception.save(update_fields=['sent_to_1c_status', 'updated_at'])
        return False, None, str(exc)

    text = ''
    try:
        text = (response.text or '')[:2000]
    except Exception:
        text = ''

    ok = response.status_code == 200
    reception.sent_to_1c_at = timezone.now()
    reception.sent_to_1c_status = ('OK' if ok else f'HTTP {response.status_code}')[:250]
    if text and not ok:
        reception.sent_to_1c_status = (reception.sent_to_1c_status + ': ' + text)[:250]
    reception.save(update_fields=['sent_to_1c_at', 'sent_to_1c_status', 'updated_at'])
    return ok, response.status_code, text
