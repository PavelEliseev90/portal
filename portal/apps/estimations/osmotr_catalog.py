"""
Загрузка элементов схемы и типов повреждений для осмотра кузова/салона.

Элементы: SchemeElement ↔ RegInfoBody (полигоны).
Повреждения: DamageType (legacy_label пишется в type_point файлов оценки).
"""
from __future__ import annotations

import json

from register.models import RegInfoBody

# code DamageType → ui_code (файл /media_dop/static/estimation/{ui_code}.png)
DAMAGE_UI_CODE = {
    'dent': 'vmyat',
    'dent_strong': 'vmyat_strong',
    'scratch': 'carap',
    'scratch_strong': 'carap_strong',
    'rust': 'rzav',
    'rust_through': 'rzav_strong',
    'chip': 'skol',
    'paint': 'skol',  # «окрас» в справочнике — та же иконка, что скол ЛКП
    'crack': 'tr',
    'replace': 'replace',
    'replaced': 'replace',
    'replace_needed': 'replace_add',
    'repaint': 'perecras',
    'reupholstery': 'pereshiv',
    'hole': 'dirka',
    'restore': 'vost',
    'sticker': 'stiker',
    'tint': 'toner',
    'polish': 'poly',
}

# Файлы иконок, которые в legacy называются не как ui_code.png
DAMAGE_ICON_SRC = {
    'replace': '/media_dop/static/estimation/mbri-left-right.png',
    'replace_add': '/media_dop/static/estimation/replace_element.png',
}

BODY_SIDE_BY_TYPE = {
    'pered': 'перед',
    'vod': 'водительская',
    'pass': 'пассажирская',
    'zad': 'зад',
    'up': 'верх',
    'pol': 'пол',
    'pol_rama': 'пол рама',
}

SALON_SIDE_BY_TYPE = {
    'page_osmotr_salon': 'салон',
    'page_osmotr_salon_v1_1': 'cалон в1 1',  # кириллическая «с» как в legacy-данных
    'page_osmotr_salon_v1_2': 'cалон в1 2',
    'page_osmotr_salon_v1_3': 'cалон в1 3',
}

# Специальные метки кузова (не повреждения каталога)
BODY_SPECIAL_LEGACY = {
    'толщиномер': 'tol',
    'наклейка': 'stiker',
    'тонировка': 'toner',
    'полировка': 'poly',
    'заменен': 'replace',
    'заменить': 'replace_add',
}


def parse_polygon(poly_str: str) -> tuple[list[int], list[int]]:
    polygon_x: list[int] = []
    polygon_y: list[int] = []
    if not poly_str:
        return polygon_x, polygon_y
    parts = [p.strip() for p in str(poly_str).split(',') if p.strip() != '']
    i = 0
    while i + 1 < len(parts):
        try:
            polygon_x.append(int(float(parts[i])))
            polygon_y.append(int(float(parts[i + 1])))
        except (TypeError, ValueError):
            pass
        i += 2
    return polygon_x, polygon_y


def _serialize_body_row(body: RegInfoBody, element=None) -> dict:
    xs, ys = parse_polygon(body.polygon)
    name = ''
    code = ''
    element_id = None
    if element is not None:
        name = element.name or body.body_elem_name or body.body_element
        code = element.code
        element_id = element.pk
    else:
        name = (body.body_elem_name or body.body_element or '').strip()
        code = (body.body_element or '').strip()
    return {
        'name': name,
        'code': code,
        'element_id': element_id,
        'info_body_id': body.pk,
        'coor_x': xs,
        'coor_y': ys,
    }


def load_elements_for_side(*, side: str, type_body: str = 'седан') -> list[dict]:
    """
    Полигоны стороны с привязкой к SchemeElement (если есть sync).
    Fallback: сырые RegInfoBody, как в legacy.
    """
    from estimation_engine.models import SchemeElementPolygon

    bodies = list(
        RegInfoBody.objects.filter(type_body=type_body, side=side).order_by('id')
    )
    if not bodies:
        return []

    body_ids = [b.pk for b in bodies]
    links = {
        link.info_body_id: link.element
        for link in SchemeElementPolygon.objects.filter(
            is_active=True,
            info_body_id__in=body_ids,
            element__is_active=True,
        ).select_related('element')
    }

    result = []
    for body in bodies:
        result.append(_serialize_body_row(body, links.get(body.pk)))
    return result


def load_body_elements(*, view_type: str, rama: bool = False) -> list[dict]:
    if view_type == 'pol' and rama:
        side = BODY_SIDE_BY_TYPE['pol_rama']
    else:
        side = BODY_SIDE_BY_TYPE.get(view_type, '')
    if not side:
        return []
    return load_elements_for_side(side=side)


def load_salon_elements(*, view_type: str) -> list[dict]:
    side = SALON_SIDE_BY_TYPE.get(view_type, '')
    if not side:
        return []
    return load_elements_for_side(side=side)


def serialize_damage_types(*, section: str) -> list[dict]:
    """
    section: exterior | interior | all
    """
    from estimation_engine.models import DamageType

    qs = DamageType.objects.filter(is_active=True).order_by('sort_order', 'name')
    if section == 'exterior':
        qs = qs.filter(section__in=['exterior', 'common'])
    elif section == 'interior':
        qs = qs.filter(section__in=['interior', 'common'])

    items = []
    for dt in qs:
        ui_code = DAMAGE_UI_CODE.get(dt.code) or dt.code
        legacy = (dt.legacy_label or dt.name or '').strip()
        items.append({
            'id': dt.pk,
            'code': dt.code,
            'name': dt.name,
            'legacy_label': legacy,
            'ui_code': ui_code,
            'severity': dt.severity,
            'requires_photo': bool(getattr(dt, 'requires_photo', False)),
            'icon': DAMAGE_ICON_SRC.get(
                ui_code,
                f'/media_dop/static/estimation/{ui_code}.png',
            ),
        })
    return items


def damage_types_json(section: str) -> str:
    return json.dumps(serialize_damage_types(section=section), ensure_ascii=False)


def build_legacy_to_ui_map(section: str) -> dict[str, str]:
    """Русская метка type_point → ui_code для отрисовки сохранённых отметок."""
    mapping = dict(BODY_SPECIAL_LEGACY)
    for dt in serialize_damage_types(section=section):
        if dt['legacy_label']:
            mapping[dt['legacy_label']] = dt['ui_code']
        mapping[dt['name']] = dt['ui_code']
    # явные legacy-синонимы кузова
    mapping.update({
        'вмятина': 'vmyat',
        'вмятина сильная': 'vmyat_strong',
        'царапина': 'carap',
        'царапина сильная': 'carap_strong',
        'ржавчина': 'rzav',
        'ржавчина сквозная': 'rzav_strong',
        'скол': 'skol',
        'трещина': 'tr',
        'перекрас': 'perecras',
        'перешив': 'pereshiv',
        'дырка': 'dirka',
        'восстановление': 'vost',
    })
    return mapping


def mark_ui_code(type_point: str, *, section: str) -> str:
    label = (type_point or '').strip()
    if not label:
        return ''
    return build_legacy_to_ui_map(section).get(label, '')
