import io
import json

import qrcode
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from documents.models import DocRLK
from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK, RegRegInteractivOcenkaFiles

from .estimation_1c_utils import get_estimation_user
from .mobile_gallery_utils import (
    build_mobile_upload_url,
    make_estimation_upload_token,
    verify_estimation_upload_token,
)
from .mobile_inbox_service import (
    FILE_INPUT_TARGETS,
    OSMOTR_SIDE_TARGETS,
    assign_inbox_file,
    assign_inbox_to_osmotr_point,
    delete_inbox_file,
    get_estimation_inbox_queryset,
    get_estimation_or_none,
    get_target_for_input,
    inbox_count,
    normalize_input_name,
    serialize_inbox_file,
    upload_to_inbox,
)


def _resolve_estimation_from_rlk(rlk_id):
    doc_rlk = get_object_or_404(DocRLK, pk=rlk_id)
    interactiv_rlk, _ = RegInteractivOcenkaRLK.objects.get_or_create(rlk=doc_rlk)
    if interactiv_rlk.estimation is None:
        return None, interactiv_rlk
    return interactiv_rlk.estimation, interactiv_rlk


def _json_error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _require_estimation_access(request, estimation):
    user = get_estimation_user(request)
    if user is None and not request.user.is_authenticated:
        return None, _json_error('Требуется авторизация', status=401)
    if user is None:
        user = request.user
    return user, None


@login_required
@require_GET
def mobile_gallery_upload_page(request, token):
    estimation_id = verify_estimation_upload_token(token)
    if estimation_id is None:
        return render(
            request,
            'estimation/mobile_gallery_upload.html',
            {'error': 'Ссылка недействительна или устарела. Откройте QR-код заново на странице оценки.'},
            status=403,
        )

    estimation = get_estimation_or_none(estimation_id)
    if estimation is None:
        return render(
            request,
            'estimation/mobile_gallery_upload.html',
            {'error': 'Оценка не найдена.'},
            status=404,
        )

    return render(request, 'estimation/mobile_gallery_upload.html', {
        'token': token,
        'estimation': estimation,
        'inbox_count': inbox_count(estimation),
        'upload_url': f'/estimations/mobile-gallery/{token}/upload/',
    })


@login_required
@require_POST
def mobile_gallery_upload_api(request, token):
    estimation_id = verify_estimation_upload_token(token)
    if estimation_id is None:
        return _json_error('Ссылка недействительна или устарела', status=403)

    estimation = get_estimation_or_none(estimation_id)
    if estimation is None:
        return _json_error('Оценка не найдена', status=404)

    uploaded_files = request.FILES.getlist('files') or request.FILES.getlist('file')
    if not uploaded_files:
        return _json_error('Выберите хотя бы одно фото')

    user = get_estimation_user(request)
    created = []
    errors = []

    for uploaded_file in uploaded_files:
        try:
            inbox_file = upload_to_inbox(estimation, uploaded_file, user=user)
            created.append(serialize_inbox_file(inbox_file))
        except ValueError as exc:
            errors.append(str(exc))
        except Exception:
            errors.append(f'Не удалось загрузить {uploaded_file.name}')

    if not created and errors:
        return _json_error(errors[0])

    return JsonResponse({
        'ok': True,
        'created': created,
        'errors': errors,
        'inbox_count': inbox_count(estimation),
    })


@login_required
@require_GET
def mobile_gallery_inbox_api(request, rlk_id):
    estimation, _ = _resolve_estimation_from_rlk(rlk_id)
    if estimation is None:
        return _json_error('Оценка не найдена', status=404)

    files = [serialize_inbox_file(f) for f in get_estimation_inbox_queryset(estimation)]
    targets = [
        {'input_name': key, **value}
        for key, value in FILE_INPUT_TARGETS.items()
    ]
    return JsonResponse({
        'ok': True,
        'files': files,
        'inbox_count': len(files),
        'targets': targets,
        'upload_url': build_mobile_upload_url(request, estimation.pk),
        'token': make_estimation_upload_token(estimation.pk),
    })


@login_required
@require_GET
def mobile_gallery_inbox_by_estimation_api(request, estimation_id):
    estimation = get_object_or_404(RegInteractivOcenka, pk=estimation_id)
    files = [serialize_inbox_file(f) for f in get_estimation_inbox_queryset(estimation)]
    return JsonResponse({
        'ok': True,
        'files': files,
        'inbox_count': len(files),
        'upload_url': build_mobile_upload_url(request, estimation.pk),
        'token': make_estimation_upload_token(estimation.pk),
        'osmotr_targets': OSMOTR_SIDE_TARGETS,
    })


@login_required
@require_POST
def mobile_gallery_assign_api(request, rlk_id):
    estimation, _ = _resolve_estimation_from_rlk(rlk_id)
    if estimation is None:
        return _json_error('Оценка не найдена', status=404)

    user, error_response = _require_estimation_access(request, estimation)
    if error_response:
        return error_response

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        payload = request.POST

    inbox_id = payload.get('inbox_id') or payload.get('file_id')
    if not inbox_id:
        return _json_error('Не указан файл галереи')

    try:
        if payload.get('osmotr_side'):
            try:
                result = assign_inbox_to_osmotr_point(
                    inbox_id,
                    side=payload['osmotr_side'],
                    type_point=payload.get('type_point', ''),
                    text=payload.get('text', ''),
                    cor_x=payload.get('cor_x', 0),
                    cor_y=payload.get('cor_y', 0),
                    kraska=payload.get('kraska', 0),
                    user=user,
                    estimation=estimation,
                )
            except RegRegInteractivOcenkaFiles.DoesNotExist:
                return _json_error('Файл не найден', status=404)
            except ValueError as exc:
                return _json_error(str(exc))
        else:
            input_name = normalize_input_name(payload.get('input_name', ''))
            target = payload.get('target')
            if not target and input_name:
                target = get_target_for_input(input_name)
            if not target:
                return _json_error('Не указан раздел для привязки')
            try:
                result = assign_inbox_file(inbox_id, target, user=user, estimation=estimation)
            except RegRegInteractivOcenkaFiles.DoesNotExist:
                return _json_error('Файл не найден', status=404)
            except ValueError as exc:
                return _json_error(str(exc))
    except Exception as exc:
        return _json_error(f'Ошибка привязки: {exc}', status=500)

    return JsonResponse({
        'ok': True,
        'file': {
            'id': result.pk,
            'url': result.get_absolute_url(),
            'thumb_url': result.get_thumbnail_url(),
            'type_file': result.type_file,
            'name': result.name,
        },
        'inbox_count': inbox_count(estimation),
        'message': 'Фото привязано. Не забудьте сохранить раздел.',
    })


@login_required
@require_POST
def mobile_gallery_assign_by_estimation_api(request, estimation_id):
    estimation = get_object_or_404(RegInteractivOcenka, pk=estimation_id)
    user, error_response = _require_estimation_access(request, estimation)
    if error_response:
        return error_response

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        payload = request.POST

    inbox_id = payload.get('inbox_id') or payload.get('file_id')
    if not inbox_id:
        return _json_error('Не указан файл галереи')

    try:
        if payload.get('osmotr_side'):
            try:
                result = assign_inbox_to_osmotr_point(
                    inbox_id,
                    side=payload['osmotr_side'],
                    type_point=payload.get('type_point', ''),
                    text=payload.get('text', ''),
                    cor_x=payload.get('cor_x', 0),
                    cor_y=payload.get('cor_y', 0),
                    kraska=payload.get('kraska', 0),
                    user=user,
                    estimation=estimation,
                )
            except RegRegInteractivOcenkaFiles.DoesNotExist:
                return _json_error('Файл не найден', status=404)
            except ValueError as exc:
                return _json_error(str(exc))
        else:
            target = payload.get('target')
            if not target:
                input_name = normalize_input_name(payload.get('input_name', ''))
                target = get_target_for_input(input_name)
            if not target:
                return _json_error('Не указан раздел для привязки')
            try:
                result = assign_inbox_file(inbox_id, target, user=user, estimation=estimation)
            except RegRegInteractivOcenkaFiles.DoesNotExist:
                return _json_error('Файл не найден', status=404)
            except ValueError as exc:
                return _json_error(str(exc))
    except Exception as exc:
        return _json_error(f'Ошибка привязки: {exc}', status=500)

    return JsonResponse({
        'ok': True,
        'file': {
            'id': result.pk,
            'url': result.get_absolute_url(),
            'thumb_url': result.get_thumbnail_url(),
            'type_file': result.type_file,
            'name': result.name,
        },
        'inbox_count': inbox_count(estimation),
    })


@login_required
@require_http_methods(['DELETE', 'POST'])
def mobile_gallery_delete_api(request, rlk_id, file_id):
    estimation, _ = _resolve_estimation_from_rlk(rlk_id)
    if estimation is None:
        return _json_error('Оценка не найдена', status=404)

    try:
        delete_inbox_file(file_id, estimation)
    except RegRegInteractivOcenkaFiles.DoesNotExist:
        return _json_error('Файл не найден', status=404)

    return JsonResponse({'ok': True, 'inbox_count': inbox_count(estimation)})


@login_required
@require_http_methods(['DELETE', 'POST'])
def mobile_gallery_delete_by_estimation_api(request, estimation_id, file_id):
    estimation = get_object_or_404(RegInteractivOcenka, pk=estimation_id)
    try:
        delete_inbox_file(file_id, estimation)
    except RegRegInteractivOcenkaFiles.DoesNotExist:
        return _json_error('Файл не найден', status=404)
    return JsonResponse({'ok': True, 'inbox_count': inbox_count(estimation)})


@login_required
@require_GET
def mobile_gallery_qr_by_estimation(request, estimation_id):
    estimation = get_object_or_404(RegInteractivOcenka, pk=estimation_id)
    upload_url = build_mobile_upload_url(request, estimation.pk)
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(upload_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#002a5a', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required
@require_GET
def mobile_gallery_qr_image(request, rlk_id):
    estimation, _ = _resolve_estimation_from_rlk(rlk_id)
    if estimation is None:
        return HttpResponse(status=404)

    upload_url = build_mobile_upload_url(request, estimation.pk)
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(upload_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#002a5a', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')
