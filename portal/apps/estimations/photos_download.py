"""Скачивание фото интерактивной оценки архивом ZIP."""
from __future__ import annotations

import io
import os
import re
import zipfile
from typing import Iterable, List, Optional, Tuple

from django.http import HttpResponse
from django.utils.text import slugify

from register.models import (
    RegInteractivOcenka,
    RegRegInteractivOcenkaFiles,
    RegRegInteractivOcenkaTaskFiles,
)

MAX_FILES = 250


def parse_photo_keys(raw) -> Optional[List[Tuple[str, int]]]:
    """
    keys: ['e:12', 't:3'] → [('e', 12), ('t', 3)]
    None / empty → все фото.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = [x.strip() for x in raw.replace(';', ',').split(',') if x.strip()]
    keys = []
    for item in raw:
        item = str(item).strip()
        if not item:
            continue
        if ':' in item:
            kind, _, sid = item.partition(':')
        elif item.startswith('e') or item.startswith('t'):
            kind, sid = item[0], item[1:]
        else:
            kind, sid = 'e', item
        kind = kind.lower()
        if kind not in ('e', 't'):
            continue
        try:
            keys.append((kind, int(sid)))
        except (TypeError, ValueError):
            continue
    return keys or None


def _unique_arcname(base: str, used: set) -> str:
    name = base or 'photo.jpg'
    name = name.replace('\\', '/').split('/')[-1]
    name = re.sub(r'[^\w.\-а-яА-ЯёЁ]+', '_', name, flags=re.UNICODE)
    if not name or name in ('.', '..'):
        name = 'photo.jpg'
    root, ext = os.path.splitext(name)
    if not ext:
        ext = '.jpg'
    candidate = root + ext
    n = 1
    while candidate.lower() in used:
        candidate = f'{root}_{n}{ext}'
        n += 1
    used.add(candidate.lower())
    return candidate


def _file_path(field) -> Optional[str]:
    if not field:
        return None
    try:
        path = field.path
    except Exception:
        return None
    if path and os.path.isfile(path):
        return path
    return None


def iter_estimation_photo_items(estimation: RegInteractivOcenka, keys=None):
    """Yield (kind, obj, disk_path) for zip."""
    e_ids = None
    t_ids = None
    if keys is not None:
        e_ids = {i for k, i in keys if k == 'e'}
        t_ids = {i for k, i in keys if k == 't'}

    fotos = (
        RegRegInteractivOcenkaFiles.objects
        .filter(estimation=estimation, blank=False)
        .exclude(type_file='mobile_inbox')
        .order_by('date', 'order', 'type_file', 'file_number', 'id')
    )
    if e_ids is not None:
        fotos = fotos.filter(id__in=e_ids)

    for obj in fotos:
        path = _file_path(obj.file)
        if path:
            yield 'e', obj, path

    task_files = (
        RegRegInteractivOcenkaTaskFiles.objects
        .filter(estimation_task__estimation=estimation)
        .order_by('id')
    )
    if t_ids is not None:
        task_files = task_files.filter(id__in=t_ids)

    for obj in task_files:
        path = _file_path(obj.file)
        if path:
            yield 't', obj, path


def build_photos_zip_response(estimation: RegInteractivOcenka, keys=None) -> HttpResponse:
    buf = io.BytesIO()
    used_names = set()
    added = 0

    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for kind, obj, path in iter_estimation_photo_items(estimation, keys=keys):
            if added >= MAX_FILES:
                break
            base_name = (getattr(obj, 'name', '') or '') or os.path.basename(path)
            type_file = getattr(obj, 'type_file', '') or ('task' if kind == 't' else 'foto')
            prefix = re.sub(r'[^\w.\-]+', '_', str(type_file))[:40]
            arc = _unique_arcname(f'{prefix}_{obj.pk}_{base_name}', used_names)
            try:
                zf.write(path, arcname=arc)
                added += 1
            except OSError:
                continue

    if added == 0:
        return None

    buf.seek(0)
    rlk = getattr(estimation, 'rlk', None)
    label = ''
    if rlk is not None:
        label = str(getattr(rlk, 'nomer', '') or rlk.pk or '')
    if not label:
        label = str(estimation.pk)
    safe = slugify(label) or str(estimation.pk)
    filename = f'estimation_{safe}_photos.zip'

    response = HttpResponse(buf.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['X-Photos-Count'] = str(added)
    return response
