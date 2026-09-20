# -*- coding: utf-8 -*-
"""Утилиты сквозной авторизации из 1С для Сводки продавца (Seller Brief).

Позволяет открывать страницу сводки по УИН сотрудника без django.contrib.auth.login(),
чтобы не перезаписывать current_session_key и не сбрасывать активную сессию
пользователя в обычном браузере на ПК.
"""
from __future__ import annotations

from typing import Any
from django.contrib.auth import get_user_model
from chats.rlk_chat_utils import resolve_user_by_staff_uin

User = get_user_model()

SELLER_BRIEF_PATH_PREFIX = '/cars/'
SELLER_BRIEF_1C_SESSION_FLAG = 'seller_brief_1c_session'
SELLER_BRIEF_1C_USER_ID_KEY = 'seller_brief_1c_user_id'
SELLER_BRIEF_1C_STAFF_UIN_KEY = 'seller_brief_1c_staff_uin'


def is_seller_brief_request(request: Any) -> bool:
    """Проверяет, относится ли запрос к сводке продавца по автомобилю."""
    path = getattr(request, 'path_info', '') or getattr(request, 'path', '') or ''
    return '/seller_brief/' in path or '/seller-brief/' in path


def is_seller_brief_1c_session(request: Any) -> bool:
    """Проверяет наличие активной изолированной сессии 1С для сводки продавца."""
    return bool(request.session.get(SELLER_BRIEF_1C_SESSION_FLAG))


def is_1c_seller_brief_entry(request: Any, staff_uin: str | None = None) -> bool:
    """Проверяет, является ли запрос точкой входа из 1С (URL-паттерн /1c/ или параметр ?uin=)."""
    if staff_uin is None:
        staff_uin = extract_seller_brief_1c_request(request)['staff_uin']
    path = getattr(request, 'path_info', '') or getattr(request, 'path', '') or ''
    if '/seller_brief/1c/' in path or '/seller-brief/1c/' in path:
        return True
    return bool((staff_uin or '').strip())


def extract_seller_brief_1c_request(request: Any) -> dict[str, str]:
    """Извлекает УИН сотрудника и slug автомобиля из path, query или сессии."""
    staff_uin = (
        request.GET.get('uin')
        or request.GET.get('staff_uin')
        or request.POST.get('uin')
        or request.POST.get('staff_uin')
        or ''
    ).strip()

    slug = (request.GET.get('slug') or request.POST.get('slug') or '').strip()

    path = getattr(request, 'path_info', '') or getattr(request, 'path', '') or ''
    # Вариант 1: /cars/<slug>/seller_brief/1c/<staff_uin>/
    # Вариант 2: /cars/seller_brief/1c/<staff_uin>/<slug>/
    if '/1c/' in path:
        parts = [p.strip() for p in path.strip('/').split('/') if p.strip()]
        for i, part in enumerate(parts):
            if part == '1c':
                if i + 1 < len(parts) and not staff_uin:
                    staff_uin = parts[i + 1]
                if i + 2 < len(parts) and not slug:
                    slug = parts[i + 2]
                break

    if not staff_uin:
        staff_uin = (request.session.get(SELLER_BRIEF_1C_STAFF_UIN_KEY) or '').strip()

    return {
        'staff_uin': staff_uin,
        'slug': slug,
    }


def store_seller_brief_1c_session(request: Any, staff_uin: str, slug: str | None = None):
    """Сохраняет данные 1С в сессию без вызова login()."""
    staff_uin = (staff_uin or '').strip()
    if staff_uin:
        request.session[SELLER_BRIEF_1C_STAFF_UIN_KEY] = staff_uin
    if slug:
        request.session['seller_brief_1c_slug'] = slug
    request.session.modified = True


def bind_seller_brief_1c_session(request: Any, staff_uin: str):
    """
    Сессия сводки продавца из 1С без django.contrib.auth.login — не трогает current_session_key
    и не разлогинивает пользователя в обычном браузере на рабочем компьютере.
    """
    user = resolve_user_by_staff_uin(staff_uin)
    if user is None:
        return None
    request.session[SELLER_BRIEF_1C_SESSION_FLAG] = True
    request.session[SELLER_BRIEF_1C_USER_ID_KEY] = user.pk
    store_seller_brief_1c_session(request, staff_uin)
    request.session.save()
    return user


def get_seller_brief_1c_user_from_session(request: Any):
    """Извлекает пользователя из изолированной сессии 1С."""
    if not is_seller_brief_1c_session(request):
        return None
    user_id = request.session.get(SELLER_BRIEF_1C_USER_ID_KEY)
    if not user_id:
        return None
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return None
    staff_uin = (request.session.get(SELLER_BRIEF_1C_STAFF_UIN_KEY) or '').strip()
    if staff_uin:
        resolved = resolve_user_by_staff_uin(staff_uin)
        if resolved and resolved.pk != user.pk:
            return None
    return user


def get_seller_brief_user(request: Any):
    """Возвращает пользователя: либо обычный вход в портал, либо сессия 1С."""
    user = get_seller_brief_1c_user_from_session(request)
    if user is not None:
        return user
    if getattr(request.user, 'is_authenticated', False):
        return request.user
    return None


def try_bind_seller_brief_1c_user(request: Any):
    """Пользователь 1С для сводки продавца: активная сессия или ?uin= в ссылке."""
    if not is_seller_brief_request(request):
        return None

    if is_seller_brief_1c_session(request):
        return get_seller_brief_1c_user_from_session(request)

    staff_uin = extract_seller_brief_1c_request(request)['staff_uin']
    if staff_uin and not getattr(request.user, 'is_authenticated', False):
        user = bind_seller_brief_1c_session(request, staff_uin)
        return user

    return None


def build_seller_brief_1c_url(staff_uin: str, slug: str) -> str:
    """Генерирует прямую ссылку для открытия из 1С."""
    staff_uin = (staff_uin or '').strip()
    slug = (slug or '').strip()
    return f'/cars/{slug}/seller_brief/1c/{staff_uin}/'
