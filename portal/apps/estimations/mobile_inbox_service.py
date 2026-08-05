from datetime import datetime

from django.core.files.base import ContentFile
from django.db import transaction

from register.models import RegInteractivOcenka, RegRegInteractivOcenkaFiles

from .mobile_gallery_utils import MOBILE_INBOX_TYPE_FILE

MAX_INBOX_FILES = 120
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'image/heic',
    'image/heif',
}

# Соответствие name у <input type="file"> и параметров привязки (как в views.py).
FILE_INPUT_TARGETS = {
    'image_sts': {'type_file': 'sts', 'label': 'СТС'},
    'image_pts': {'type_file': 'pts', 'label': 'ПТС'},
    'image_run': {'type_file': 'run', 'label': 'Пробег'},
    'image_salon': {'type_file': 'salon_all', 'label': 'Салон (общий)'},
    'image_damage_salon': {'type_file': 'salon_error', 'label': 'Повреждения салона'},
    'photo_a1': {'type_file': 'vnesh_car_all', 'file_number': 1, 'single_slot': True, 'label': 'Внешний осмотр 1'},
    'photo_a2': {'type_file': 'vnesh_car_all', 'file_number': 2, 'single_slot': True, 'label': 'Внешний осмотр 2'},
    'photo_a3': {'type_file': 'vnesh_car_all', 'file_number': 3, 'single_slot': True, 'label': 'Внешний осмотр 3'},
    'photo_a4': {'type_file': 'vnesh_car_all', 'file_number': 4, 'single_slot': True, 'label': 'Внешний осмотр 4'},
    'photo_a5': {'type_file': 'vnesh_car_all', 'file_number': 5, 'single_slot': True, 'label': 'Внешний осмотр 5'},
    'photo_a6': {'type_file': 'vnesh_car_all', 'file_number': 6, 'single_slot': True, 'label': 'Внешний осмотр 6'},
    'photo_a7': {'type_file': 'vnesh_car_all', 'file_number': 7, 'single_slot': True, 'label': 'Внешний осмотр 7'},
    'photo_a8': {'type_file': 'vnesh_car_all', 'file_number': 8, 'single_slot': True, 'label': 'Внешний осмотр 8'},
    'file_light_error': {'type_file': 'light_error', 'single_slot': True, 'label': 'Неисправность фар'},
    'file_windshield_error': {'type_file': 'windshield_error', 'single_slot': True, 'label': 'Неисправность лобового стекла'},
    'file_vin': {'type_file': 'vin', 'label': 'VIN'},
    'file_podcapot': {'type_file': 'pod_capot', 'label': 'Подкапотное пространство'},
    'file_kolesa_1': {'type_file': 'kolesa', 'label': 'Колёса (комплект 1)'},
    'file_kolesa_2': {'type_file': 'kolesa2', 'label': 'Колёса (комплект 2)'},
    'file_gibdd': {'type_file': 'gibdd', 'label': 'ГИБДД'},
    'file_reestr': {'type_file': 'reestr', 'label': 'Реестр залогов'},
    'file_market': {'type_file': 'market', 'label': 'Рынок'},
    'file_epts': {'type_file': 'epts', 'label': 'ЭПТС'},
    'images_remote': {'type_file': 'images_remote', 'label': 'Удалённая оценка'},
}

OSMOTR_SIDE_TARGETS = {
    'pered': {'type_file': 'array_images_pered', 'label': 'Осмотр кузова — перед'},
    'pol': {'type_file': 'array_images_pol', 'label': 'Осмотр кузова — днище'},
    'vod': {'type_file': 'array_images_vod', 'label': 'Осмотр кузова — водительская'},
    'pass': {'type_file': 'array_images_pass', 'label': 'Осмотр кузова — пассажирская'},
    'zad': {'type_file': 'array_images_zad', 'label': 'Осмотр кузова — зад'},
    'up': {'type_file': 'array_images_up', 'label': 'Осмотр кузова — крыша'},
}


def normalize_input_name(name):
    return (name or '').strip()


def get_target_for_input(input_name):
    return FILE_INPUT_TARGETS.get(normalize_input_name(input_name))


def get_estimation_inbox_queryset(estimation):
    return (
        RegRegInteractivOcenkaFiles.objects
        .filter(estimation=estimation, type_file=MOBILE_INBOX_TYPE_FILE, blank=False)
        .exclude(file='')
        .order_by('-date', '-id')
    )


def inbox_count(estimation):
    return get_estimation_inbox_queryset(estimation).count()


def serialize_inbox_file(file_obj):
    return {
        'id': file_obj.pk,
        'name': file_obj.name or '',
        'url': file_obj.get_absolute_url(),
        'thumb_url': file_obj.get_thumbnail_url(),
        'date': file_obj.date.strftime('%d.%m.%Y %H:%M') if file_obj.date else '',
    }


def _validate_upload_file(uploaded_file):
    if not uploaded_file:
        return 'Файл не передан'
    size = getattr(uploaded_file, 'size', 0) or 0
    if size > MAX_UPLOAD_SIZE_BYTES:
        return 'Файл слишком большой (макс. 15 МБ)'
    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        return 'Допустимы только изображения (JPEG, PNG, WEBP, HEIC)'
    return None


@transaction.atomic
def upload_to_inbox(estimation, uploaded_file, user=None):
    error = _validate_upload_file(uploaded_file)
    if error:
        raise ValueError(error)

    current_count = inbox_count(estimation)
    if current_count >= MAX_INBOX_FILES:
        raise ValueError(f'Достигнут лимит галереи ({MAX_INBOX_FILES} фото). Привяжите или удалите старые.')

    name = (uploaded_file.name or 'photo.jpg').lower()
    inbox_file = RegRegInteractivOcenkaFiles(
        estimation=estimation,
        type_file=MOBILE_INBOX_TYPE_FILE,
        name=name,
        text='',
        type_point='',
        cor_x=0,
        cor_y=0,
        file_number=0,
        blank=False,
        date=datetime.now(),
        user=user,
    )
    inbox_file.file = uploaded_file
    inbox_file.save()
    try:
        inbox_file._generate_thumbnail()
    except Exception:
        pass
    return inbox_file


def _delete_slot_files(estimation, type_file, file_number=None, exclude_pk=None):
    qs = RegRegInteractivOcenkaFiles.objects.filter(
        estimation=estimation,
        type_file=type_file,
        blank=False,
    )
    if file_number:
        qs = qs.filter(file_number=file_number)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    for old_file in qs:
        old_file.delete()


def _build_lookup(estimation, target):
    lookup = {
        'estimation': estimation,
        'type_file': target['type_file'],
        'type_point': target.get('type_point', '') or '',
        'text': target.get('text', '') or '',
        'cor_x': int(target.get('cor_x', 0) or 0),
        'cor_y': int(target.get('cor_y', 0) or 0),
        'name': (target.get('name') or '').lower(),
    }
    file_number = target.get('file_number')
    if file_number:
        lookup['file_number'] = int(file_number)
    return lookup


@transaction.atomic
def assign_inbox_file(inbox_file_id, target, user=None, estimation=None):
    inbox_file = (
        RegRegInteractivOcenkaFiles.objects
        .select_for_update()
        .get(pk=inbox_file_id)
    )
    if inbox_file.type_file != MOBILE_INBOX_TYPE_FILE or inbox_file.blank:
        raise ValueError('Файл не найден в галерее оценки')
    if estimation is not None and inbox_file.estimation_id != estimation.pk:
        raise ValueError('Файл не принадлежит этой оценке')

    if estimation is None:
        if inbox_file.estimation_id is None:
            raise ValueError('Файл не привязан к оценке')
        # Не используем select_related + select_for_update на nullable FK (это ломает Postgres)
        estimation = RegInteractivOcenka.objects.get(pk=inbox_file.estimation_id)
    if not target.get('name'):
        target = dict(target)
        target['name'] = (inbox_file.name or 'photo.jpg').lower()

    if target.get('single_slot'):
        _delete_slot_files(
            estimation,
            target['type_file'],
            file_number=target.get('file_number'),
            exclude_pk=inbox_file.pk,
        )

    lookup = _build_lookup(estimation, target)
    existing = (
        RegRegInteractivOcenkaFiles.objects
        .filter(**lookup)
        .exclude(pk=inbox_file.pk)
        .first()
    )

    if existing:
        if inbox_file.file:
            existing.file = inbox_file.file
        if inbox_file.file_mini:
            existing.file_mini = inbox_file.file_mini
        existing.blank = False
        existing.user = user or inbox_file.user
        existing.date = datetime.now()
        if target.get('file_number'):
            existing.file_number = int(target['file_number'])
        existing.kraska = int(target.get('kraska', 0) or 0)
        existing.save()
        inbox_file.delete()
        result = existing
    else:
        inbox_file.type_file = target['type_file']
        inbox_file.name = lookup['name']
        inbox_file.text = lookup['text']
        inbox_file.type_point = lookup['type_point']
        inbox_file.cor_x = lookup['cor_x']
        inbox_file.cor_y = lookup['cor_y']
        if target.get('file_number'):
            inbox_file.file_number = int(target['file_number'])
        inbox_file.kraska = int(target.get('kraska', 0) or 0)
        inbox_file.blank = False
        inbox_file.user = user or inbox_file.user
        inbox_file.date = datetime.now()
        inbox_file.save()
        result = inbox_file

    try:
        result._generate_thumbnail()
    except Exception:
        pass
    return result


@transaction.atomic
def assign_inbox_to_osmotr_point(inbox_file_id, side, type_point, text, cor_x, cor_y, kraska=0, user=None, estimation=None):
    if side not in OSMOTR_SIDE_TARGETS:
        raise ValueError('Неизвестная сторона осмотра')
    target = dict(OSMOTR_SIDE_TARGETS[side])
    target.update({
        'type_point': type_point or '',
        'text': text or '',
        'cor_x': int(cor_x or 0),
        'cor_y': int(cor_y or 0),
        'kraska': int(kraska or 0),
        'name': f'{type_point or "point"}_{cor_x}_{cor_y}.jpg'.lower(),
    })
    return assign_inbox_file(inbox_file_id, target, user=user, estimation=estimation)


@transaction.atomic
def delete_inbox_file(inbox_file_id, estimation):
    file_obj = RegRegInteractivOcenkaFiles.objects.get(
        pk=inbox_file_id,
        estimation=estimation,
        type_file=MOBILE_INBOX_TYPE_FILE,
    )
    file_obj.delete()


def get_estimation_or_none(estimation_id):
    return RegInteractivOcenka.objects.filter(pk=estimation_id).first()
