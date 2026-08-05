import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from documents.models import DocRLK
from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK

from .photos_download import build_photos_zip_response, parse_photo_keys


def _estimation_from_rlk(rlk_id):
    doc_rlk = get_object_or_404(DocRLK, pk=rlk_id)
    interactiv_rlk, _ = RegInteractivOcenkaRLK.objects.get_or_create(rlk=doc_rlk)
    return interactiv_rlk.estimation


def _parse_keys_from_request(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except (TypeError, ValueError, UnicodeDecodeError):
            payload = {}
        if payload.get('all'):
            return None
        return parse_photo_keys(payload.get('ids') or payload.get('keys'))

    if request.POST.get('all') or request.GET.get('all'):
        return None
    raw = request.POST.getlist('ids') or request.GET.getlist('ids')
    if not raw:
        raw = request.POST.get('ids') or request.GET.get('ids')
    return parse_photo_keys(raw)


@login_required
@require_http_methods(['GET', 'POST'])
def estimation_photos_download(request, estimation_id):
    estimation = get_object_or_404(RegInteractivOcenka, pk=estimation_id)
    keys = _parse_keys_from_request(request)
    # GET без параметров / POST all → все; POST/GET с ids → выбранные
    if request.method == 'POST' and keys is None and not (
        request.POST.get('all')
        or (request.content_type and 'application/json' in request.content_type
            and b'"all"' in (request.body or b''))
    ):
        # пустой выбор
        if request.content_type and 'application/json' in request.content_type:
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
            if not payload.get('all') and not payload.get('ids') and not payload.get('keys'):
                return JsonResponse({'ok': False, 'error': 'Не выбраны фото'}, status=400)

    response = build_photos_zip_response(estimation, keys=keys)
    if response is None:
        return JsonResponse({'ok': False, 'error': 'Нет доступных файлов для скачивания'}, status=404)
    return response


@login_required
@require_http_methods(['GET', 'POST'])
def estimation_photos_download_by_rlk(request, rlk_id):
    estimation = _estimation_from_rlk(rlk_id)
    if estimation is None:
        return JsonResponse({'ok': False, 'error': 'Оценка не найдена'}, status=404)
    keys = _parse_keys_from_request(request)
    response = build_photos_zip_response(estimation, keys=keys)
    if response is None:
        return JsonResponse({'ok': False, 'error': 'Нет доступных файлов для скачивания'}, status=404)
    return response
