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
    RegRegInteractivOcenkaFilesKolesaReception,
)


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
            photo.delete()
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
            messages.success(request, f'Загружено файлов: {uploaded_count}')
        else:
            messages.warning(request, 'Не удалось загрузить изображения')

    return True


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
                messages.success(request, 'Признак отправки в базу БУ колёс сброшен')
            return HttpResponseRedirect(request.path)

        # Отправка в базу БУ колёс (1С)
        if action == 'send_to_1c':
            if sent:
                messages.warning(request, 'Приёмка уже отправлена в базу БУ колёс. Повторная отправка запрещена.')
                return HttpResponseRedirect(request.path)

            from task_manager.views import send_kolesa_reception_to_1c

            send_result = send_kolesa_reception_to_1c(reception, request=request)
            if send_result.get('ok'):
                doc = send_result.get('document') or {}
                parts = [
                    'Данные приёмки отправлены в базу БУ колёс (HTTP {}).'.format(
                        send_result.get('status_code') or 200,
                    )
                ]
                if doc.get('number'):
                    parts.append('№ {}'.format(doc['number']))
                if doc.get('date'):
                    parts.append(doc['date'].strftime('%d.%m.%Y %H:%M'))
                if doc.get('uin'):
                    parts.append('УИН {}'.format(doc['uin']))
                messages.success(request, ' · '.join(parts))
            else:
                err = send_result.get('error') or 'неизвестная ошибка'
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
            try:
                from eco.reception import queue_estimation_for_1c
                queue_estimation_for_1c(reception.estimation, comment='kolesa_reception_save')
            except Exception:
                pass
            messages.success(request, 'Данные приёмки сохранены, оценка поставлена в очередь выгрузки в 1С')
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

    # Подразделение из рабочего листа (DocRLK → unit)
    unit_name = '—'
    if reception.rlk_id and reception.rlk and reception.rlk.unit_id:
        unit_name = reception.rlk.unit.name
    elif estimation and estimation.rlk_id and estimation.rlk and estimation.rlk.unit_id:
        unit_name = estimation.rlk.unit.name

    author_name = '—'
    if reception.user_id and reception.user:
        full = (reception.user.get_full_name() or '').strip()
        author_name = full or reception.user.username or '—'

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
    }
    return render(request, 'estimations/kolesa_reception_detail.html', {'params': params})
