"""Отправка локальных фото IM-стока в 1С (очередь upload://)."""
import io
import os

import requests

from website.models import ImProductPhoto


def push_im_photo_to_1c(photo):
    """
    POST одного фото в HTTP-сервис 1С (как раньше в product()).
    Возвращает True при HTTP 200.
    """
    from website.views import server_im, time_out_im

    if not photo.file:
        return False
    product = photo.product
    url_search = '?kod=' + product.nomenclature_code
    fname = os.path.basename(photo.file.name) or 'photo.jpg'
    try:
        with photo.file.open('rb') as f:
            content = f.read()
    except OSError:
        return False
    bio = io.BytesIO(content)
    bio.seek(0)
    try:
        response = requests.post(
            server_im + 'product/' + url_search,
            params={'file_name': fname},
            files={'files': (fname, bio)},
            verify=False,
            timeout=time_out_im,
        )
    except requests.RequestException:
        return False
    return response.status_code == 200


def iter_push_pending_photos_to_1c():
    """
    Итератор событий для потоковой выдачи: push_start, push_item, push_done.
    Обрабатывает статусы pending и failed (повтор).
    """
    qs = (
        ImProductPhoto.objects.filter(
            upload_1c_status__in=(
                ImProductPhoto.UPLOAD_1C_PENDING,
                ImProductPhoto.UPLOAD_1C_FAILED,
            )
        )
        .select_related('product')
        .order_by('id')
    )
    total = qs.count()
    yield {'phase': 'push_start', 'total': total}
    ok = 0
    bad = 0
    for photo in qs:
        success = push_im_photo_to_1c(photo)
        if success:
            photo.upload_1c_status = ImProductPhoto.UPLOAD_1C_SYNCED
            photo.save(update_fields=['upload_1c_status'])
            ok += 1
        else:
            photo.upload_1c_status = ImProductPhoto.UPLOAD_1C_FAILED
            photo.save(update_fields=['upload_1c_status'])
            bad += 1
        yield {
            'phase': 'push_item',
            'photo_id': photo.id,
            'ok': success,
            'current': ok + bad,
            'total': total,
        }
    yield {'phase': 'push_done', 'pushed_ok': ok, 'pushed_fail': bad}


def run_push_then_pull_from_1c():
    """
    Синхронный прогон без потока: всё в очереди в 1С, затем sync_im_photos из 1С.
    """
    for _ in iter_push_pending_photos_to_1c():
        pass
    from django.core.management import call_command

    call_command('sync_im_photos', verbosity=0)
