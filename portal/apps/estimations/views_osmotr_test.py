"""
Тестовая страница осмотра кузова (новый UI).
Не заменяет legacy osmotr / osmotr_salon.
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from register.models import RegInteractivOcenka

from .osmotr_catalog import damage_types_json, load_body_elements

BODY_SIDES = (
    ('pered', 'Перед', '/media_dop/body_capture/sedan_new.png', 701, 341),
    ('vod', 'Водитель', '/media_dop/body_capture/sedan_left_new.png', 701, 341),
    ('pass', 'Пассажир', '/media_dop/body_capture/sedan_right_new.png', 701, 341),
    ('zad', 'Зад', '/media_dop/body_capture/sedan_back_new.png', 701, 341),
    ('up', 'Крыша', '/media_dop/body_capture/sedan_up.png', 701, 341),
    ('pol', 'Днище', '/media_dop/body_capture/pol.png', 701, 341),
)

SIDE_META = {row[0]: row for row in BODY_SIDES}


@login_required
def osmotr_body_test(request, side='pered', rlk_id=None, rl_id=None):
    """
    Прототип UI осмотра кузова:
    - элементы из SchemeElement / RegInfoBody
    - повреждения из DamageType
    - обязательное фото по флагу requires_photo
    Сохранение в оценку пока не делается.
    """
    if side not in SIDE_META:
        side = 'pered'

    _, type_name, image_url, width, height = SIDE_META[side]
    estimation = None
    rama = False
    if rlk_id:
        estimation = RegInteractivOcenka.objects.filter(id=rlk_id).first()
        if estimation is not None:
            rama = bool(estimation.rama)

    if side == 'pol' and rama:
        image_url = '/media_dop/body_capture/pol_ram.png'

    elements = load_body_elements(view_type=side, rama=rama)
    damages = damage_types_json('exterior')

    sides_nav = [
        {
            'code': code,
            'label': label,
            'active': code == side,
            'url': (
                f'/estimations/{rlk_id}/{rl_id}/osmotr-test/{code}/'
                if rlk_id and rl_id
                else f'/estimations/osmotr-test/{code}/'
            ),
        }
        for code, label, *_ in BODY_SIDES
    ]

    back_url = '/estimation-engine/'
    if estimation is not None and getattr(estimation, 'rlk_id', None):
        back_url = f'/estimations/{estimation.rlk_id}/?page=3'
    elif rl_id:
        back_url = f'/estimations/{rl_id}/?page=3'

    params = {
        'side': side,
        'type_name': type_name,
        'image_url': image_url,
        'canvas_width': width,
        'canvas_height': height,
        'elements_body': json.dumps(elements, ensure_ascii=False),
        'damage_types_json': damages,
        'sides_nav': sides_nav,
        'estimation': estimation,
        'rlk_id': rlk_id,
        'rl_id': rl_id,
        'rama': rama,
        'back_url': back_url,
        'is_test': True,
    }
    return render(request, 'estimation/estimation_doc_body_osmotr_test.html', {'params': params})
