# -*- coding: utf-8 -*-
"""Приём автомобиля по интерактивной оценке."""
from __future__ import annotations

from datetime import date, datetime

from django.db import transaction
from django.utils import timezone

from register.models import (
    RegInteractivOcenkaReception,
    RegInteractivOcenkaRLK,
    RegRegInteractivOcenkaFiles,
)


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


def _as_int(value, default=0):
    if value is None or value == '':
        return default
    try:
        return int(float(str(value).replace(' ', '').replace(',', '.')))
    except (TypeError, ValueError):
        return default


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
        'pts_number': (docs.pts_number if docs else '') or '',
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


def build_kolesa2_1c_extras(estimation) -> dict:
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
                'url': f.get_absolute_url() if hasattr(f, 'get_absolute_url') else '',
                'thumb_url': f.get_thumbnail_url() if hasattr(f, 'get_thumbnail_url') else '',
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
        return interactiv_rlk.page_reception
    except RegInteractivOcenkaReception.DoesNotExist:
        return None


def reception_select_options():
    from refs.models import (
        RefFilial,
        RefOrganization,
        RefStore,
        RefTypeReceptionCarsOrganization,
        RefUnit,
    )
    return {
        'type_receptions': list(
            RefTypeReceptionCarsOrganization.objects.exclude(name='').order_by('name').values('id', 'name')
        ),
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


def apply_post_to_reception(reception: RegInteractivOcenkaReception, post, user=None) -> RegInteractivOcenkaReception:
    from refs.models import (
        RefFilial,
        RefOrganization,
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

    for field in (
        'customer_family', 'customer_name', 'customer_patronymic', 'customer_phone',
        'vin', 'vin2', 'mark', 'model', 'pts_mark_model', 'plate_number',
        'chassis_number', 'body_number', 'pts_number', 'pts_org_address', 'sts_number',
        'pts_org_issuer', 'salon_color', 'body_color', 'engine_number', 'eco_class',
    ):
        if field in post:
            setattr(reception, field, (post.get(field) or '').strip())

    for field in ('year', 'mileage', 'count_owners', 'count_keys', 'mass', 'max_mass'):
        if field in post:
            setattr(reception, field, _as_int(post.get(field), 0))

    if 'pts_date' in post:
        reception.pts_date = _as_date(post.get('pts_date'))
    if 'sts_date' in post:
        reception.sts_date = _as_date(post.get('sts_date'))

    reception.pts_original = str(post.get('pts_original', '')).lower() in ('1', 'true', 'on', 'yes')

    if user is not None and getattr(user, 'is_authenticated', False):
        reception.updated_by = user

    reception.save()
    return reception


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
        'Reception': RegInteractivOcenkaReceptionSerializer(reception, many=False).data,
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
