"""
Синхронизация канонических элементов схемы с полигонами RegInfoBody.
"""
from __future__ import annotations

import re

from django.db import transaction

from register.models import RegInfoBody

from .models import (
    PreparationWorkPackage,
    SchemeElement,
    SchemeElementPolygon,
)


def _slug_code(value: str, fallback: str) -> str:
    raw = (value or '').strip().lower()
    raw = raw.replace('ё', 'е')
    # латиница/цифры оставляем, кириллицу транслитерируем упрощённо
    table = str.maketrans({
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
        'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y',
        'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    })
    raw = raw.translate(table)
    raw = re.sub(r'[^a-z0-9]+', '_', raw).strip('_')
    return (raw or fallback)[:64]


def _guess_section(side: str) -> str:
    s = (side or '').lower()
    if 'салон' in s:
        return PreparationWorkPackage.SECTION_INTERIOR
    return PreparationWorkPackage.SECTION_EXTERIOR


@transaction.atomic
def sync_scheme_elements_from_polygons(*, only_missing: bool = False) -> dict:
    """
    Создаёт/обновляет SchemeElement по уникальным body_element из RegInfoBody
    и связывает полигоны.
    """
    created_elements = 0
    linked = 0
    skipped = 0

    bodies = RegInfoBody.objects.all().order_by('id')
    for body in bodies:
        key = (body.body_element or '').strip()
        if not key:
            skipped += 1
            continue

        code = _slug_code(key, fallback=f'elem_{body.id}')
        name = (body.body_elem_name or key).strip() or key
        section = _guess_section(body.side)

        element = SchemeElement.objects.filter(code=code).first()
        if element is None:
            # иногда один элемент уже есть под другим кодом по имени
            element = SchemeElement.objects.filter(name__iexact=name).first()

        if element is None:
            element = SchemeElement.objects.create(
                code=code,
                name=name,
                section=section,
                description=f'{body.type_body} / {body.side}'.strip(' /'),
                is_active=True,
            )
            created_elements += 1
        elif not only_missing:
            changed = False
            if not element.name and name:
                element.name = name
                changed = True
            if changed:
                element.save(update_fields=['name', 'updated_at'])

        _, was_created = SchemeElementPolygon.objects.get_or_create(
            element=element,
            info_body=body,
            defaults={'is_active': True},
        )
        if was_created:
            linked += 1

    return {
        'polygons_total': bodies.count(),
        'elements_created': created_elements,
        'links_created': linked,
        'skipped_empty': skipped,
        'elements_total': SchemeElement.objects.count(),
    }
