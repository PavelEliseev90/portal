"""Список и приёмка второго комплекта колес (RegInteractivOcenkaKolesaReception)."""
import io
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Q, Subquery
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from refs.models import RefStatusEstimation, RefUnit
from register.models import (
    RegInteractivOcenka,
    RegInteractivOcenkaRLK,
    RegInteractivOcenkaKolesaReception,
    RegInteractivOcenkaKolesaReceptionEvent,
    RegRegInteractivOcenkaFilesKolesaReception,
)
from estimations.kolesa_reception_events import log_kolesa_reception_event, user_display


def _parse_date(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            from datetime import datetime
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _resolve_reception_unit_name(reception, estimation=None):
    """Подразделение: РЛ приёмки → РЛ оценки → РЛК-обёртка → лист оценки (DocLO)."""
    estimation = estimation or getattr(reception, 'estimation', None)

    if reception.rlk_id and reception.rlk and reception.rlk.unit_id and reception.rlk.unit:
        return reception.rlk.unit.name

    if estimation and estimation.rlk_id and estimation.rlk and estimation.rlk.unit_id and estimation.rlk.unit:
        return estimation.rlk.unit.name

    try:
        from register.models import RegInteractivOcenkaRLK
        rlk_id = reception.rlk_id or (estimation.rlk_id if estimation else None)
        qs = RegInteractivOcenkaRLK.objects.select_related('unit')
        if estimation and estimation.pk:
            row = qs.filter(estimation_id=estimation.pk).first()
            if row and row.unit_id and row.unit:
                return row.unit.name
        if rlk_id:
            row = qs.filter(rlk_id=rlk_id).first()
            if row and row.unit_id and row.unit:
                return row.unit.name
    except Exception:
        pass

    try:
        from documents.models import DocLO
        rlk_id = reception.rlk_id or (estimation.rlk_id if estimation else None)
        if rlk_id:
            lo = (
                DocLO.objects
                .filter(rlk_id=rlk_id)
                .select_related('unit')
                .order_by('-dataTime')
                .first()
            )
            if lo and lo.unit_id and lo.unit:
                return lo.unit.name
    except Exception:
        pass

    return '—'


def _estimation_car_label(estimation):
    if estimation.modification_id and estimation.modification:
        mod = estimation.modification
        if mod.model_id and mod.model:
            mark = mod.model.mark.name if mod.model.mark_id else ''
            return f'{mark} {mod.model.name} {mod.name}'.strip()
    parts = [estimation.mark_name, estimation.model_name, estimation.modification_name]
    label = ' '.join(p for p in parts if p)
    return label or estimation.vin or estimation.number_body or '—'


def _copy_kolesa_to_reception(reception, page_kolesa):
    """Перенос данных 2-го комплекта из оценки в приёмку."""
    reception.mark_tyre = page_kolesa.mark_tyre2
    reception.model_tyre = page_kolesa.model_tyre2 or ''
    reception.width_tyre = page_kolesa.width_tyre2
    reception.profil_tyre = page_kolesa.profil_tyre2
    reception.radius = page_kolesa.radius2
    reception.sezon = page_kolesa.sezon2
    reception.disk_type = page_kolesa.disk_type2
    reception.model_disk = page_kolesa.model_disk2 or ''
    reception.et_disk = page_kolesa.et_disk2
    reception.dia_disk = page_kolesa.dia_disk2
    reception.psd_disk = page_kolesa.psd_disk2
    reception.count_disk = page_kolesa.count_disk2 or 0
    reception.count_tyre = page_kolesa.count_tyre2 or 0
    reception.kolesa_estimation = page_kolesa.kolesa2_estimation


def create_kolesa_reception(estimation, user):
    """Создать приёмку для оценки (идемпотентно по estimation)."""
    existing = RegInteractivOcenkaKolesaReception.objects.filter(
        estimation=estimation,
    ).first()
    if existing:
        return existing

    reception = RegInteractivOcenkaKolesaReception(
        rlk=estimation.rlk,
        estimation=estimation,
        date=timezone.now(),
        user=user,
    )
    if estimation.page_kolesa_id:
        _copy_kolesa_to_reception(reception, estimation.page_kolesa)
    else:
        reception.kolesa_estimation = 1
    reception.save()
    log_kolesa_reception_event(
        reception,
        RegInteractivOcenkaKolesaReceptionEvent.EVENT_CREATED,
        user=user,
        message='Создана приёмка второго комплекта колёс',
    )
    try:
        from eco.reception import queue_estimation_for_1c
        queue_estimation_for_1c(estimation, comment='kolesa_reception_create')
    except Exception:
        pass
    return reception


def _save_file_thumbnail(file_obj):
    if not file_obj.file or not file_obj.file.name:
        return
    if file_obj.is_video():
        return
    try:
        from PIL import Image
        from django.core.files.base import ContentFile

        path = getattr(file_obj.file, 'path', None)
        if path and os.path.isfile(path):
            img = Image.open(path)
        else:
            file_obj.file.open('rb')
            img = Image.open(io.BytesIO(file_obj.file.read()))
            file_obj.file.close()

        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA' and len(img.split()) >= 4:
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        img.thumbnail((400, 300), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        base, _ext = os.path.splitext(file_obj.file.name)
        thumb_name = base + '_mini.jpg'
        img.save(buf, format='JPEG', quality=85, optimize=True)
        buf.seek(0)
        file_obj.file_mini.save(thumb_name, ContentFile(buf.read()), save=False)
        file_obj.save(update_fields=['file_mini'])
    except Exception:
        pass


def handle_kolesa_reception_files_post(request, reception):
    action = request.POST.get('action', '')
    if action not in ('delete', 'upload'):
        return False

    sent = bool(reception.send_wheels_ib)

    if action == 'delete':
        if sent:
            messages.error(request, 'Нельзя удалить фото: приёмка уже отправлена в базу БУ колёс')
            return True
        photo_id = request.POST.get('photo_id', '')
        try:
            photo = RegRegInteractivOcenkaFilesKolesaReception.objects.get(
                id=photo_id,
                kolesa_reception=reception,
            )
            photo_name = photo.name or str(photo.pk)
            photo.delete()
            log_kolesa_reception_event(
                reception,
                RegInteractivOcenkaKolesaReceptionEvent.EVENT_PHOTO_DELETE,
                user=request.user,
                message='Удалено фото: {}'.format(photo_name),
                extra={'photo_name': photo_name},
            )
            messages.success(request, 'Файл удалён')
        except RegRegInteractivOcenkaFilesKolesaReception.DoesNotExist:
            messages.error(request, 'Файл не найден')

    elif action == 'upload':
        uploaded_files = request.FILES.getlist('photos')
        if not uploaded_files:
            messages.warning(request, 'Не выбраны файлы')
            return True

        uploaded_count = 0
        for uploaded_file in uploaded_files:
            if not uploaded_file.content_type.startswith('image/'):
                continue
            file_obj = RegRegInteractivOcenkaFilesKolesaReception(
                kolesa_reception=reception,
                name=uploaded_file.name,
                file=uploaded_file,
                user=request.user,
                date=timezone.now(),
            )
            file_obj.save()
            _save_file_thumbnail(file_obj)
            uploaded_count += 1

        if uploaded_count:
            log_kolesa_reception_event(
                reception,
                RegInteractivOcenkaKolesaReceptionEvent.EVENT_PHOTO_ADD,
                user=request.user,
                message='Добавлено фото: {}'.format(uploaded_count),
                extra={'count': uploaded_count},
            )
            messages.success(request, f'Загружено файлов: {uploaded_count}')
        else:
            messages.warning(request, 'Не удалось загрузить изображения')

    return True


_TRACKED_RECEPTION_FIELDS = (
    'mark_tyre_id', 'model_tyre', 'width_tyre_id', 'profil_tyre_id', 'radius_id',
    'sezon_id', 'disk_type_id', 'model_disk', 'et_disk_id', 'dia_disk_id',
    'psd_disk_id', 'count_disk', 'count_tyre', 'kolesa_estimation',
)

_TRACKED_FIELD_LABELS = {
    'mark_tyre_id': 'Марка шин',
    'model_tyre': 'Модель шин',
    'width_tyre_id': 'Ширина',
    'profil_tyre_id': 'Профиль',
    'radius_id': 'Радиус',
    'sezon_id': 'Сезон',
    'disk_type_id': 'Тип диска',
    'model_disk': 'Модель дисков',
    'et_disk_id': 'ET',
    'dia_disk_id': 'DIA',
    'psd_disk_id': 'PSD',
    'count_disk': 'Дисков',
    'count_tyre': 'Шин',
    'kolesa_estimation': 'Признак 2КК',
}

_KOLESA_ESTIMATION_LABELS = {
    0: 'Нет второго комплекта колес',
    1: 'Оценка со вторым комплектом колес',
}


def _ref_display_name(obj):
    if obj is None:
        return '—'
    for attr in ('name', 'value'):
        val = getattr(obj, attr, None)
        if val not in (None, ''):
            return str(val)
    return str(obj)


_CHANGELOG_FIELD_LABELS = {
    'kolesa_estimation': 'Признак второго комплекта колёс',
    'count_disk': 'Количество дисков 2',
    'count_tyre': 'Количество резины 2',
    'mark_tyre': 'Марка резины 2',
    'model_tyre': 'Модель резины 2',
    'width_tyre': 'Ширина резины 2',
    'profil_tyre': 'Профиль резины 2',
    'radius': 'Радиус колес 2',
    'sezon': 'Сезон колес 2',
    'disk_type': 'Тип диска 2',
    'model_disk': 'Модель дисков 2',
    'et_disk': 'ET дисков 2',
    'dia_disk': 'DIA дисков 2',
    'psd_disk': 'PSD дисков 2',
    'send_wheels_ib': 'Отправлена информация в базу БУ колёс',
    'send_wheels_ib_date': 'Дата документа приёмки в базе БУ колёс',
    'send_wheels_ib_number': 'Номер документа приёмки в базе БУ колёс',
    'send_wheels_ib_uin': 'УИН документа приёмки в базе БУ колёс',
    'route_sheet_attached': 'Маршрутный лист прикреплён',
    'route_sheet_attached_at': 'Дата прикрепления маршрутного листа',
    'route_sheet_attached_by': 'Кто прикрепил маршрутный лист',
    'route_sheet_file': 'Подписанный маршрутный лист',
    'user': 'Автор приёмки',
    'date': 'Дата приёмки',
    'rlk': 'Рабочий лист',
    'estimation': 'Оценка',
}


def _format_reception_field_value(field_name, value, cache=None):
    """ID справочников → наименование; пустые → —."""
    if value in (None, ''):
        return '—'

    field_name = field_name or ''
    name = field_name[:-3] if field_name.endswith('_id') else field_name

    if name == 'kolesa_estimation':
        try:
            return _KOLESA_ESTIMATION_LABELS.get(int(value), str(value))
        except (TypeError, ValueError):
            return str(value)

    if isinstance(value, bool):
        return 'Да' if value else 'Нет'

    try:
        field = RegInteractivOcenkaKolesaReception._meta.get_field(name)
    except Exception:
        return str(value)

    # BooleanField может прийти как 0/1
    from django.db.models import BooleanField
    if isinstance(field, BooleanField):
        return 'Да' if value in (True, 1, '1', 'true', 'True') else 'Нет'

    if getattr(field, 'is_relation', False) and not getattr(field, 'many_to_many', False):
        related_model = field.related_model
        cache_key = (related_model._meta.label, value)
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        try:
            obj = related_model.objects.filter(pk=value).first()
            if obj is None:
                label = str(value)
            elif hasattr(obj, 'get_full_name'):
                label = (obj.get_full_name() or '').strip() or getattr(obj, 'username', None) or str(obj)
            else:
                label = _ref_display_name(obj)
        except Exception:
            label = str(value)
        if cache is not None:
            cache[cache_key] = label
        return label

    return str(value)


def _snapshot_reception_fields(reception):
    return {f: getattr(reception, f) for f in _TRACKED_RECEPTION_FIELDS}


def _diff_reception_fields(before, after):
    changes = []
    cache = {}
    for field in _TRACKED_RECEPTION_FIELDS:
        old = before.get(field)
        new = after.get(field)
        if old != new:
            changes.append({
                'field': field,
                'label': _TRACKED_FIELD_LABELS.get(field, field),
                'old': _format_reception_field_value(field, old, cache),
                'new': _format_reception_field_value(field, new, cache),
            })
    return changes


def _changelog_changes_with_names(log):
    """ChangeLog.data с ID справочников → список {name, value} с наименованиями."""
    cache = {}
    changes = []
    data = log.data or {}
    if not isinstance(data, dict):
        return changes
    for field_name, raw_value in data.items():
        label = _CHANGELOG_FIELD_LABELS.get(field_name)
        if not label:
            try:
                label = RegInteractivOcenkaKolesaReception._meta.get_field(field_name).verbose_name
            except Exception:
                label = field_name
        if field_name in ('route_sheet_file',):
            display = 'файл прикреплён' if raw_value else '—'
        else:
            display = _format_reception_field_value(field_name, raw_value, cache)
        changes.append({'name': label, 'value': display})
    return changes


def handle_kolesa_reception_route_sheet_post(request, reception):
    """Загрузка / удаление подписанного маршрутного листа."""
    action = request.POST.get('action', '')
    if action not in ('upload_route_sheet', 'delete_route_sheet'):
        return False

    if action == 'delete_route_sheet':
        if not request.user.is_superuser:
            messages.error(request, 'Удаление маршрутного листа доступно только суперпользователю')
            return True
        if reception.route_sheet_file:
            reception.route_sheet_file.delete(save=False)
        reception.route_sheet_file = None
        reception.route_sheet_attached = False
        reception.route_sheet_attached_at = None
        reception.route_sheet_attached_by = None
        reception.save(update_fields=[
            'route_sheet_file',
            'route_sheet_attached',
            'route_sheet_attached_at',
            'route_sheet_attached_by',
        ])
        log_kolesa_reception_event(
            reception,
            RegInteractivOcenkaKolesaReceptionEvent.EVENT_ROUTE_SHEET_DELETE,
            user=request.user,
            message='Удалён подписанный маршрутный лист',
        )
        messages.success(request, 'Подписанный маршрутный лист удалён')
        return True

    uploaded = request.FILES.get('route_sheet')
    if not uploaded:
        messages.warning(request, 'Не выбран файл маршрутного листа')
        return True

    content_type = (uploaded.content_type or '').lower()
    name_lower = (uploaded.name or '').lower()
    allowed = (
        content_type.startswith('image/')
        or content_type == 'application/pdf'
        or name_lower.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic'))
    )
    if not allowed:
        messages.error(request, 'Допустимы PDF или изображение')
        return True

    if reception.route_sheet_file:
        reception.route_sheet_file.delete(save=False)

    reception.route_sheet_file = uploaded
    reception.route_sheet_attached = True
    reception.route_sheet_attached_at = timezone.now()
    reception.route_sheet_attached_by = request.user
    reception.save(update_fields=[
        'route_sheet_file',
        'route_sheet_attached',
        'route_sheet_attached_at',
        'route_sheet_attached_by',
    ])
    log_kolesa_reception_event(
        reception,
        RegInteractivOcenkaKolesaReceptionEvent.EVENT_ROUTE_SHEET_ADD,
        user=request.user,
        message='Прикреплён подписанный маршрутный лист: {}'.format(uploaded.name),
        extra={'filename': uploaded.name},
    )
    messages.success(request, 'Подписанный маршрутный лист сохранён')
    return True


def get_kolesa_reception_history(reception):
    """События + ChangeLog реквизитов для таймлайна."""
    events = list(
        RegInteractivOcenkaKolesaReceptionEvent.objects
        .filter(reception=reception)
        .select_related('user')
        .order_by('-created_at', '-id')[:200]
    )
    changelog_rows = []
    try:
        from changelog.models import ChangeLog
        logs = (
            ChangeLog.objects
            .filter(model='RegInteractivOcenkaKolesaReception', record_id=reception.pk)
            .select_related('user')
            .order_by('-changed')[:100]
        )
        for log in logs:
            try:
                human = _changelog_changes_with_names(log)
            except Exception:
                try:
                    human = log.get_change_human()
                except Exception:
                    human = []
            changelog_rows.append({
                'when': log.changed,
                'user': user_display(log.user),
                'action': log.get_action_on_model_display() if hasattr(log, 'get_action_on_model_display') else log.action_on_model,
                'changes': human,
            })
    except Exception:
        pass
    return events, changelog_rows


def _kolesa_reception_list_queryset(request):
    """
    Основа списка: RegInteractivOcenkaRLK.
    По умолчанию фильтруем статус RLK = 8 (“АМ принят”).

    Важно: если пользователь явно выбрал “Все” (то есть status присутствует, но пустой),
    фильтр статуса НЕ применяется.
    """
    reception_sq = RegInteractivOcenkaKolesaReception.objects.filter(
        estimation_id=OuterRef('estimation_id'),
    )
    qs = (
        RegInteractivOcenkaRLK.objects.select_related(
            'unit',
            'status',
            'rlk',
            'estimation',
            'estimation__page_kolesa',
            'estimation__rlk',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
        )
        .filter(estimation__isnull=False)
        .filter(unit__name__icontains='КорсАвто')
        .annotate(
            has_reception=Exists(reception_sq),
            reception_id=Subquery(reception_sq.values('pk')[:1]),
        )
        .order_by('-estimation__start_estimation', '-id')
    )

    date_from = _parse_date(request.GET.get('date_from', ''))
    date_to = _parse_date(request.GET.get('date_to', ''))
    unit_ids = [v for v in request.GET.getlist('unit') if str(v).strip().isdigit()]
    kolesa2 = request.GET.get('kolesa2', '').strip()
    vin = request.GET.get('vin', '').strip()
    rlk_number = request.GET.get('rlk', '').strip()

    status_param_present = 'status' in request.GET
    status_id_raw = request.GET.get('status', '').strip()

    if date_from:
        qs = qs.filter(
            Q(estimation__start_estimation__date__gte=date_from)
            | Q(estimation__end_estimation__date__gte=date_from)
        )
    if date_to:
        qs = qs.filter(
            Q(estimation__start_estimation__date__lte=date_to)
            | Q(estimation__end_estimation__date__lte=date_to)
        )

    if unit_ids:
        qs = qs.filter(unit_id__in=[int(v) for v in unit_ids])

    if status_param_present:
        if status_id_raw.isdigit():
            qs = qs.filter(status_id=int(status_id_raw))
        # иначе status= (пусто) => “все статусы”
    else:
        qs = qs.filter(status_id=8)

    if vin:
        qs = qs.filter(
            Q(estimation__vin__icontains=vin)
            | Q(estimation__number_body__icontains=vin)
        )

    if rlk_number:
        qs = qs.filter(rlk__nomer__icontains=rlk_number)

    if kolesa2 == '1':
        qs = qs.filter(estimation__page_kolesa__kolesa2_estimation=1)
    elif kolesa2 == '0':
        qs = qs.filter(estimation__page_kolesa__kolesa2_estimation=0)

    return qs


@login_required
def kolesa_reception_help(request):
    """Инструкция: приёмка и отправка второго комплекта колёс."""
    return render(request, 'estimations/kolesa_reception_help.html', {'params': {}})


@login_required
def kolesa_reception_list(request):
    qs = _kolesa_reception_list_queryset(request)
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    rows = []
    for rlk in page_obj.object_list:
        est = rlk.estimation
        pk = est.page_kolesa.kolesa2_estimation if est.page_kolesa_id else 10
        rows.append({
            'estimation': est,
            'car_label': _estimation_car_label(est),
            'estimation_date': est.end_estimation or est.start_estimation,
            'status': rlk.status,
            'unit_name': rlk.unit.name if rlk.unit_id else '—',
            'kolesa2_estimation': pk,
            'has_second_set': pk == 1,
            'has_reception': rlk.has_reception,
            'reception_id': rlk.reception_id,
        })

    params = {
        'page_obj': page_obj,
        'rows': rows,
        'units': RefUnit.objects.filter(name__icontains='КорсАвто').order_by('name'),
        'statuses': RefStatusEstimation.objects.all().order_by('name'),
        'filters': {
            'date_from': request.GET.get('date_from', ''),
            'date_to': request.GET.get('date_to', ''),
            'unit': request.GET.getlist('unit'),
            'unit_ids_list': [
                int(v) for v in request.GET.getlist('unit') if str(v).strip().isdigit()
            ],
            'status': (
                request.GET.get('status', '')
                if 'status' in request.GET
                else '8'
            ),
            'kolesa2': request.GET.get('kolesa2', ''),
            'vin': request.GET.get('vin', ''),
            'rlk': request.GET.get('rlk', ''),
        },
    }
    return render(request, 'estimations/kolesa_reception_list.html', {'params': params})


@login_required
def kolesa_reception_create(request, estimation_id):
    estimation = get_object_or_404(
        RegInteractivOcenka.objects.select_related('page_kolesa', 'rlk'),
        pk=estimation_id,
    )
    if not estimation.page_kolesa_id or estimation.page_kolesa.kolesa2_estimation != 1:
        messages.error(request, 'Для этой оценки не указан второй комплект колес')
        return HttpResponseRedirect('/estimations/kolesa-reception/')

    reception = create_kolesa_reception(estimation, request.user)
    messages.success(request, 'Приёмка второго комплекта колёс создана')
    return HttpResponseRedirect(f'/estimations/kolesa-reception/{reception.pk}/')


@login_required
def kolesa_reception_detail(request, reception_id):
    reception = get_object_or_404(
        RegInteractivOcenkaKolesaReception.objects.select_related(
            'estimation',
            'estimation__page_kolesa',
            'estimation__status',
            'estimation__rlk',
            'estimation__rlk__unit',
            'rlk',
            'rlk__unit',
            'user',
            'route_sheet_attached_by',
            'mark_tyre',
            'width_tyre',
            'radius',
            'sezon',
            'disk_type',
        ),
        pk=reception_id,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        sent = bool(reception.send_wheels_ib)

        # Сброс признака отправки (только суперпользователь)
        if action == 'reset_send_wheels_ib':
            if not request.user.is_superuser:
                messages.error(request, 'Сброс признака отправки доступен только суперпользователю')
            else:
                reception.send_wheels_ib = False
                reception.send_wheels_ib_date = None
                reception.send_wheels_ib_number = ''
                reception.send_wheels_ib_uin = ''
                reception.save(update_fields=[
                    'send_wheels_ib',
                    'send_wheels_ib_date',
                    'send_wheels_ib_number',
                    'send_wheels_ib_uin',
                ])
                log_kolesa_reception_event(
                    reception,
                    RegInteractivOcenkaKolesaReceptionEvent.EVENT_RESET_SEND,
                    user=request.user,
                    message='Сброшен признак отправки в базу БУ колёс',
                )
                messages.success(request, 'Признак отправки в базу БУ колёс сброшен')
            return HttpResponseRedirect(request.path)

        # Отправка / переотправка в базу БУ колёс (1С)
        if action == 'send_to_1c':
            from task_manager.views import send_kolesa_reception_to_1c

            is_resend = bool(sent) or RegInteractivOcenkaKolesaReceptionEvent.objects.filter(
                reception=reception,
                event_type__in=(
                    RegInteractivOcenkaKolesaReceptionEvent.EVENT_SEND,
                    RegInteractivOcenkaKolesaReceptionEvent.EVENT_RESEND,
                ),
            ).exists()

            send_result = send_kolesa_reception_to_1c(reception, request=request)
            if send_result.get('ok'):
                doc = send_result.get('document') or {}
                parts = [
                    (
                        'Данные приёмки повторно отправлены в базу БУ колёс (HTTP {}).'
                        if is_resend
                        else 'Данные приёмки отправлены в базу БУ колёс (HTTP {}).'
                    ).format(send_result.get('status_code') or 200)
                ]
                if doc.get('number'):
                    parts.append('№ {}'.format(doc['number']))
                if doc.get('date'):
                    parts.append(doc['date'].strftime('%d.%m.%Y %H:%M'))
                if doc.get('uin'):
                    parts.append('УИН {}'.format(doc['uin']))
                event_type = (
                    RegInteractivOcenkaKolesaReceptionEvent.EVENT_RESEND
                    if is_resend
                    else RegInteractivOcenkaKolesaReceptionEvent.EVENT_SEND
                )
                log_kolesa_reception_event(
                    reception,
                    event_type,
                    user=request.user,
                    message=' · '.join(parts),
                    extra={
                        'number': doc.get('number') or '',
                        'uin': doc.get('uin') or '',
                        'resend': is_resend,
                    },
                )
                messages.success(request, ' · '.join(parts))
            else:
                err = send_result.get('error') or 'неизвестная ошибка'
                text = (send_result.get('text') or '').strip()
                if text and text not in err:
                    err = '{} — {}'.format(err, text[:500])
                messages.error(
                    request,
                    'Не удалось отправить в 1С: {}.'.format(err),
                )
            return HttpResponseRedirect(request.path)

        # Сохранение полей приёмки
        if action == 'save_reception':
            from refs.models import (
                RefMarkTyres,
                RefWidthTyres,
                RefProfileTyres,
                RefRadius,
                RefSezonTyres,
                RefTypeDisk,
                RefEtDisk,
                RefDiaDisk,
                RefPsdDisk,
            )

            def _int(val, default=0):
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return default

            before = _snapshot_reception_fields(reception)

            mark_id = request.POST.get('mark_tyre') or None
            width_id = request.POST.get('width_tyre') or None
            profil_id = request.POST.get('profil_tyre') or None
            radius_id = request.POST.get('radius') or None
            sezon_id = request.POST.get('sezon') or None
            disk_type_id = request.POST.get('disk_type') or None
            et_id = request.POST.get('et_disk') or None
            dia_id = request.POST.get('dia_disk') or None
            psd_id = request.POST.get('psd_disk') or None

            reception.mark_tyre = RefMarkTyres.objects.filter(pk=mark_id).first() if mark_id else None
            reception.model_tyre = request.POST.get('model_tyre', '').strip()
            reception.width_tyre = RefWidthTyres.objects.filter(pk=width_id).first() if width_id else None
            reception.profil_tyre = RefProfileTyres.objects.filter(pk=profil_id).first() if profil_id else None
            reception.radius = RefRadius.objects.filter(pk=radius_id).first() if radius_id else None
            reception.sezon = RefSezonTyres.objects.filter(pk=sezon_id).first() if sezon_id else None
            reception.disk_type = RefTypeDisk.objects.filter(pk=disk_type_id).first() if disk_type_id else None
            reception.model_disk = request.POST.get('model_disk', '').strip()
            reception.et_disk = RefEtDisk.objects.filter(pk=et_id).first() if et_id else None
            reception.dia_disk = RefDiaDisk.objects.filter(pk=dia_id).first() if dia_id else None
            reception.psd_disk = RefPsdDisk.objects.filter(pk=psd_id).first() if psd_id else None
            reception.count_disk = _int(request.POST.get('count_disk'), 0)
            reception.count_tyre = _int(request.POST.get('count_tyre'), 0)
            reception.kolesa_estimation = _int(request.POST.get('kolesa_estimation'), reception.kolesa_estimation)
            reception.save()

            changes = _diff_reception_fields(before, _snapshot_reception_fields(reception))
            if changes:
                summary = '; '.join(
                    '{}: {} → {}'.format(c['label'], c['old'] or '—', c['new'] or '—')
                    for c in changes[:12]
                )
                log_kolesa_reception_event(
                    reception,
                    RegInteractivOcenkaKolesaReceptionEvent.EVENT_SAVE,
                    user=request.user,
                    message=summary,
                    extra={'changes': changes},
                )

            try:
                from eco.reception import queue_estimation_for_1c
                queue_estimation_for_1c(reception.estimation, comment='kolesa_reception_save')
            except Exception:
                pass
            messages.success(request, 'Данные приёмки сохранены, оценка поставлена в очередь выгрузки в 1С')
            return HttpResponseRedirect(request.path)

        if handle_kolesa_reception_route_sheet_post(request, reception):
            return HttpResponseRedirect(request.path)

        # Работа с файлами
        if handle_kolesa_reception_files_post(request, reception):
            return HttpResponseRedirect(request.path)

    estimation = reception.estimation
    files = RegRegInteractivOcenkaFilesKolesaReception.objects.filter(
        kolesa_reception=reception,
    ).order_by('-date', '-id')

    # Справочники для удобного ввода (Select2 + поиск)
    from refs.models import (
        RefMarkTyres,
        RefWidthTyres,
        RefProfileTyres,
        RefRadius,
        RefSezonTyres,
        RefTypeDisk,
        RefEtDisk,
        RefDiaDisk,
        RefPsdDisk,
    )

    marks = RefMarkTyres.objects.all().order_by('name')
    widths = RefWidthTyres.objects.all().order_by('value')
    profiles = RefProfileTyres.objects.all().order_by('value')
    radii = RefRadius.objects.all().order_by('value')
    seasons = RefSezonTyres.objects.all().order_by('name')
    disk_types = RefTypeDisk.objects.all().order_by('name')
    et_disks = RefEtDisk.objects.all().order_by('value')
    dia_disks = RefDiaDisk.objects.all().order_by('value')
    psd_disks = RefPsdDisk.objects.all().order_by('value')

    from eco.reception import build_kolesa_reception_send_payload

    send_payload = build_kolesa_reception_send_payload(reception, request=request)

    # Подразделение: РЛ → оценка → DocLO
    unit_name = _resolve_reception_unit_name(reception, estimation)

    author_name = '—'
    if reception.user_id and reception.user:
        full = (reception.user.get_full_name() or '').strip()
        author_name = full or reception.user.username or '—'

    events, changelog_rows = get_kolesa_reception_history(reception)
    profile = getattr(request.user, 'profiles', None)
    is_user_sb = bool(getattr(profile, 'user_sb', False))

    params = {
        'reception': reception,
        'estimation': estimation,
        'car_label': _estimation_car_label(estimation) if estimation else '—',
        'unit_name': unit_name,
        'author_name': author_name,
        'sent_to_wheels': bool(reception.send_wheels_ib),
        'files': files,
        'files_count': files.count(),
        'marks': marks,
        'widths': widths,
        'profiles': profiles,
        'radii': radii,
        'seasons': seasons,
        'disk_types': disk_types,
        'et_disks': et_disks,
        'dia_disks': dia_disks,
        'psd_disks': psd_disks,
        'send_payload': send_payload,
        'events': events,
        'events_count': len(events),
        'changelog_rows': changelog_rows,
        'changelog_count': len(changelog_rows),
        'route_sheet_attached': bool(reception.route_sheet_attached and reception.route_sheet_file),
        'is_user_sb': is_user_sb,
        'can_see_sb_list': bool(request.user.is_superuser or is_user_sb),
    }
    return render(request, 'estimations/kolesa_reception_detail.html', {'params': params})


def _ref_name(obj):
    if obj is None:
        return ''
    return (getattr(obj, 'name', None) or getattr(obj, 'value', None) or str(obj) or '').strip()


def _complect_label(int_val, bool_val=None):
    """0 — НЕТ, 1 — есть, иначе пусто."""
    if int_val == 1:
        return 'есть'
    if int_val == 0:
        return 'НЕТ'
    if bool_val is True:
        return 'есть'
    if bool_val is False:
        return 'НЕТ'
    return ''


def _tyre_size(width, profil, radius):
    w = _ref_name(width)
    p = _ref_name(profil)
    r = _ref_name(radius)
    if not (w or p or r):
        return ''
    return '{} / {} - {}'.format(w or '—', p or '—', r or '—')


def _money(value):
    try:
        n = int(float(value or 0))
    except (TypeError, ValueError):
        return ''
    if n <= 0:
        return ''
    return '{:,}'.format(n).replace(',', ' ')


def build_route_sheet(*, estimation=None, rlk=None, kolesa_reception=None, page_reception=None, back_url=''):
    """Данные для печати маршрутного листа А/М (оценка / приём / 2КК)."""
    if estimation is None and kolesa_reception is not None:
        estimation = kolesa_reception.estimation
    if rlk is None and kolesa_reception is not None:
        rlk = kolesa_reception.rlk
    if rlk is None and estimation is not None:
        rlk = estimation.rlk

    page_kolesa = estimation.page_kolesa if estimation and estimation.page_kolesa_id else None
    page_comp = estimation.page_complectnost if estimation and estimation.page_complectnost_id else None
    page_salon = estimation.page_salon if estimation and estimation.page_salon_id else None
    page_sogl = estimation.page_soglasovanie if estimation and estimation.page_soglasovanie_id else None
    page_test = estimation.page_test_drive if estimation and estimation.page_test_drive_id else None

    lo = None
    if rlk is not None:
        from documents.models import DocLO
        lo = (
            DocLO.objects
            .filter(rlk=rlk)
            .select_related('organization', 'staff', 'store')
            .order_by('-active', '-dataTime', '-id')
            .first()
        )

    if page_reception is None and rlk is not None:
        try:
            link = getattr(rlk, 'reginteractivocenkarlk', None)
            if link is not None:
                page_reception = getattr(link, 'page_reception', None)
        except Exception:
            page_reception = None

    # Если 2КК-приёмка не передана — взять с РЛ, если есть
    if kolesa_reception is None and rlk is not None:
        kolesa_reception = (
            RegInteractivOcenkaKolesaReception.objects
            .filter(rlk=rlk)
            .select_related(
                'mark_tyre', 'width_tyre', 'profil_tyre', 'radius', 'sezon', 'disk_type',
            )
            .order_by('-id')
            .first()
        )

    sklad_nomer = ''
    if lo and lo.nomer:
        sklad_nomer = lo.nomer
    elif rlk and rlk.nomer:
        sklad_nomer = rlk.nomer

    org_name = ''
    if lo and lo.organization_id and lo.organization:
        org_name = lo.organization.name or ''
    elif page_reception and page_reception.organization_id and page_reception.organization:
        org_name = page_reception.organization.name or ''
    elif rlk is not None and rlk.unit_id and rlk.unit:
        org_name = rlk.unit.name or ''

    store_name = ''
    if page_reception and page_reception.store_id and page_reception.store:
        store_name = page_reception.store.name or ''
    elif lo and lo.store_id and lo.store:
        store_name = lo.store.name or ''
    else:
        try:
            link = getattr(rlk, 'reginteractivocenkarlk', None) if rlk else None
            if link is not None and link.store_id and link.store:
                store_name = link.store.name or ''
        except Exception:
            pass
        if not store_name and estimation and estimation.page_documents_id and estimation.page_documents:
            docs = estimation.page_documents
            if docs.store_id and docs.store:
                store_name = docs.store.name or ''

    appraiser = ''
    if estimation and estimation.staff_id and estimation.staff:
        appraiser = estimation.staff.name or str(estimation.staff)
    elif lo and lo.staff_id and lo.staff:
        appraiser = lo.staff.name or str(lo.staff)
    elif kolesa_reception and kolesa_reception.user_id and kolesa_reception.user:
        appraiser = (
            (kolesa_reception.user.get_full_name() or '').strip()
            or kolesa_reception.user.username
        )

    year = ''
    if estimation and estimation.year:
        year = str(estimation.year)
    elif page_reception and page_reception.year:
        year = str(page_reception.year)

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

    date_priem = None
    if kolesa_reception and kolesa_reception.date:
        date_priem = kolesa_reception.date
    elif page_reception and getattr(page_reception, 'actual_reception_at', None):
        date_priem = page_reception.actual_reception_at
    elif page_reception and getattr(page_reception, 'created_at', None):
        date_priem = page_reception.created_at
    elif lo and lo.dataTime:
        date_priem = lo.dataTime
    elif estimation and estimation.end_estimation:
        date_priem = estimation.end_estimation

    vin = ''
    if estimation:
        vin = (estimation.vin or estimation.number_body or '').strip()
    if not vin and page_reception:
        vin = (page_reception.vin or '').strip()

    plate_number = ''
    if page_reception and (page_reception.plate_number or '').strip():
        plate_number = page_reception.plate_number.strip()
    elif estimation and estimation.page_documents_id and estimation.page_documents:
        plate_number = (estimation.page_documents.plate_number or '').strip()
    elif lo and (lo.carsGRZ or '').strip():
        plate_number = lo.carsGRZ.strip()

    engine_number = ''
    if page_reception and (page_reception.engine_number or '').strip():
        engine_number = page_reception.engine_number.strip()
    elif estimation and estimation.page_documents_id and estimation.page_documents:
        engine_number = (estimation.page_documents.engine_number or '').strip()

    car_label = _estimation_car_label(estimation) if estimation else '—'
    if page_reception and (page_reception.mark or page_reception.model):
        car_label = '{} {}'.format(
            page_reception.mark or '',
            page_reception.model or '',
        ).strip() or car_label

    diagnostica_yes = False
    diagnostica_no = False
    diagnostica_text = ''
    if page_sogl is not None:
        if page_sogl.no_diagnostica:
            diagnostica_no = True
            diagnostica_text = (page_sogl.no_diagnostica_comment or '').strip()
            if not diagnostica_text:
                diagnostica_text = 'Без диагностики'
        else:
            diagnostica_text = (page_sogl.comment_diagnostica or '').strip()
            if diagnostica_text or page_sogl.price_after_kd:
                diagnostica_yes = True
    if not diagnostica_text and lo and (lo.recomendation or '').strip():
        diagnostica_text = lo.recomendation.strip()
        if not diagnostica_no:
            diagnostica_yes = True

    test_drive = ''
    if page_test is not None:
        if page_test.no_test:
            test_drive = 'не производился'
        elif (page_test.comment or '').strip():
            test_drive = page_test.comment.strip()
        else:
            test_drive = 'проведён'

    comment_podgotovka = ''
    if lo and (lo.description_podgotovka or '').strip():
        comment_podgotovka = lo.description_podgotovka.strip()
    elif page_sogl and (page_sogl.comment or '').strip():
        comment_podgotovka = page_sogl.comment.strip()

    # Вариант салона и химчистка — со страницы «Салон» (как выбирает оценщик)
    # type_salon_int: 0 — ткань, 1 — кожа (см. UI lo_v5)
    salon_variant = ''
    if page_salon is not None:
        salon_type_map = {
            0: 'ткань',
            1: 'кожа',
        }
        salon_variant = salon_type_map.get(page_salon.type_salon_int, '')
    # fallback: цвет салона из приёма, если тип не указан
    salon_color = salon_variant
    if not salon_color and page_reception and (page_reception.salon_color or '').strip():
        salon_color = page_reception.salon_color.strip()

    # cleaning_int: 0 — не требуется, 3 — лёгкая, 2 — средняя, 1 — сложная
    himchistka = ''
    if page_salon is not None:
        cleaning_map = {
            0: 'не требуется',
            3: 'лёгкая',
            2: 'средняя',
            1: 'сложная',
        }
        himchistka = cleaning_map.get(page_salon.cleaning_int, '')
        if not himchistka and page_salon.cleaning:
            himchistka = 'требуется'

    plan_rashodov = ''
    if page_sogl is not None:
        plan_rashodov = _money(page_sogl.amount_recovery or page_sogl.price_recovery)

    # Комплектность — все пункты со страницы оценки «Комплектность»
    complect_defs = [
        ('Прикуриватель', 'prikur_int', 'prikur'),
        ('Огнетушитель', 'ognet_int', 'ognet'),
        ('Коврики', 'kovrik_int', 'kovrik'),
        ('Буксировочный трос', 'tros_int', 'tros'),
        ('Домкрат', 'domkrat_int', 'domkrat'),
        ('Знак аварийной остановки', 'znak_av_int', 'znak_av'),
        ('Баллонный ключ', 'ball_key_int', 'ball_key'),
        ('Запасное колесо / докатка', 'zapas_int', 'zapas'),
        ('Аптечка', 'aptechka_int', 'aptechka'),
    ]
    complect_items = []
    for label, int_attr, bool_attr in complect_defs:
        if page_comp is not None:
            complect_items.append((
                label,
                _complect_label(getattr(page_comp, int_attr, None), getattr(page_comp, bool_attr, None)),
            ))
        else:
            complect_items.append((label, ''))

    # Ключи — из карточки приёма / ЛО (на странице комплектности нет, но нужны в маршрутном листе)
    keys_count = ''
    if page_reception and page_reception.count_keys:
        keys_count = str(page_reception.count_keys)
    elif lo and lo.keys:
        keys_count = str(lo.keys)
    if keys_count:
        complect_items.append(('Ключи зажигания, кол-во', keys_count))

    complect_pairs = []
    half = (len(complect_items) + 1) // 2
    left_col = complect_items[:half]
    right_col = complect_items[half:]
    while len(right_col) < len(left_col):
        right_col.append(('', ''))
    for left, right in zip(left_col, right_col):
        complect_pairs.append((left, right))

    wheels_on_car = {
        'sezon': _ref_name(page_kolesa.sezon) if page_kolesa else '',
        'size': _tyre_size(
            page_kolesa.width_tyre if page_kolesa else None,
            page_kolesa.profil_tyre if page_kolesa else None,
            page_kolesa.radius if page_kolesa else None,
        ) if page_kolesa else '',
        'count_tyre': '',
        'mark': '',
        'disk_type': _ref_name(page_kolesa.disk_type) if page_kolesa else '',
        'count_disk': '',
        'extra': '',
    }
    if page_kolesa:
        mark_parts = [_ref_name(page_kolesa.mark_tyre), (page_kolesa.model_tyre or '').strip()]
        wheels_on_car['mark'] = ' '.join(p for p in mark_parts if p)
        if wheels_on_car['size'] or wheels_on_car['mark']:
            wheels_on_car['count_tyre'] = '4'
        if wheels_on_car['disk_type']:
            wheels_on_car['count_disk'] = '4'

    wheels_2 = {'sezon': '', 'size': '', 'count_tyre': '', 'mark': '', 'disk_type': '', 'count_disk': '', 'extra': ''}
    if kolesa_reception is not None:
        wheels_2 = {
            'sezon': _ref_name(kolesa_reception.sezon),
            'size': _tyre_size(
                kolesa_reception.width_tyre,
                kolesa_reception.profil_tyre,
                kolesa_reception.radius,
            ),
            'count_tyre': str(kolesa_reception.count_tyre) if kolesa_reception.count_tyre else '',
            'mark': ' '.join(
                p for p in [
                    _ref_name(kolesa_reception.mark_tyre),
                    (kolesa_reception.model_tyre or '').strip(),
                ] if p
            ),
            'disk_type': _ref_name(kolesa_reception.disk_type),
            'count_disk': str(kolesa_reception.count_disk) if kolesa_reception.count_disk else '',
            'extra': (kolesa_reception.model_disk or '').strip(),
        }
    if page_kolesa and not (wheels_2['size'] or wheels_2['mark']):
        wheels_2 = {
            'sezon': _ref_name(page_kolesa.sezon2),
            'size': _tyre_size(page_kolesa.width_tyre2, page_kolesa.profil_tyre2, page_kolesa.radius2),
            'count_tyre': str(page_kolesa.count_tyre2) if page_kolesa.count_tyre2 else '',
            'mark': ' '.join(
                p for p in [_ref_name(page_kolesa.mark_tyre2), (page_kolesa.model_tyre2 or '').strip()] if p
            ),
            'disk_type': _ref_name(page_kolesa.disk_type2),
            'count_disk': str(page_kolesa.count_disk2) if page_kolesa.count_disk2 else '',
            'extra': (page_kolesa.model_disk2 or '').strip(),
        }

    if not back_url:
        if kolesa_reception is not None:
            back_url = '/estimations/kolesa-reception/{}/'.format(kolesa_reception.pk)
        elif rlk is not None:
            back_url = '/eco/{}/?page=24'.format(rlk.pk)

    return {
        'reception': kolesa_reception,
        'estimation': estimation,
        'rlk': rlk,
        'back_url': back_url,
        'sklad_nomer': sklad_nomer,
        'year': year,
        'mileage': mileage,
        'date_priem': date_priem,
        'org_name': org_name,
        'store_name': store_name,
        'appraiser': appraiser,
        'test_drive': test_drive,
        'vin': vin,
        'plate_number': plate_number,
        'engine_number': engine_number,
        'car_label': car_label,
        'diagnostica_yes': diagnostica_yes,
        'diagnostica_no': diagnostica_no,
        'diagnostica_text': diagnostica_text,
        'comment_podgotovka': comment_podgotovka,
        'salon_color': salon_color,
        'himchistka': himchistka,
        'plan_rashodov': plan_rashodov,
        'complect_items': complect_items,
        'complect_pairs': complect_pairs,
        'wheels_on_car': wheels_on_car,
        'wheels_2': wheels_2,
    }


def build_kolesa_route_sheet(reception):
    """Обёртка: печать со страницы приёмки 2КК."""
    return build_route_sheet(kolesa_reception=reception)


_ROUTE_SHEET_EST_RELATED = (
    'page_kolesa',
    'page_kolesa__mark_tyre',
    'page_kolesa__width_tyre',
    'page_kolesa__profil_tyre',
    'page_kolesa__radius',
    'page_kolesa__sezon',
    'page_kolesa__disk_type',
    'page_kolesa__mark_tyre2',
    'page_kolesa__width_tyre2',
    'page_kolesa__profil_tyre2',
    'page_kolesa__radius2',
    'page_kolesa__sezon2',
    'page_kolesa__disk_type2',
    'page_complectnost',
    'page_salon',
    'page_documents',
    'page_soglasovanie',
    'page_test_drive',
    'staff',
    'rlk',
    'rlk__unit',
)


@login_required
def kolesa_reception_print(request, reception_id):
    reception = get_object_or_404(
        RegInteractivOcenkaKolesaReception.objects.select_related(
            'estimation',
            *['estimation__' + p for p in _ROUTE_SHEET_EST_RELATED],
            'rlk',
            'rlk__unit',
            'user',
            'mark_tyre',
            'width_tyre',
            'profil_tyre',
            'radius',
            'sezon',
            'disk_type',
        ),
        pk=reception_id,
    )
    sheet = build_route_sheet(kolesa_reception=reception)
    return render(
        request,
        'estimations/kolesa_reception_print.html',
        {'params': sheet},
    )


@login_required
def estimation_route_sheet_print(request, rlk_id):
    """Печать маршрутного листа А/М со страницы приёма автомобиля (ЕЦО)."""
    from documents.models import DocRLK
    from register.models import RegInteractivOcenkaRLK

    rlk = get_object_or_404(
        DocRLK.objects.select_related('unit'),
        pk=rlk_id,
    )

    estimation = None
    page_reception = None
    try:
        link = RegInteractivOcenkaRLK.objects.select_related(
            'estimation',
            *['estimation__' + p for p in _ROUTE_SHEET_EST_RELATED],
            'page_reception',
            'page_reception__organization',
            'page_reception__store',
        ).get(rlk=rlk)
        estimation = link.estimation
        page_reception = getattr(link, 'page_reception', None)
    except RegInteractivOcenkaRLK.DoesNotExist:
        try:
            estimation = (
                RegInteractivOcenka.objects
                .select_related(*_ROUTE_SHEET_EST_RELATED)
                .get(rlk=rlk)
            )
        except RegInteractivOcenka.DoesNotExist:
            raise Http404('Интерактивная оценка для рабочего листа не найдена')

    sheet = build_route_sheet(
        estimation=estimation,
        rlk=rlk,
        page_reception=page_reception,
        back_url='/eco/{}/?page=24'.format(rlk.pk),
    )
    return render(
        request,
        'estimations/kolesa_reception_print.html',
        {'params': sheet},
    )
