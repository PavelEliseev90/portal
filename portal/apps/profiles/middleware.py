# -*- coding: utf-8 -*-
"""Один вход с одного устройства: проверка session_key по кэшу и БД."""
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import logout

from chats.rlk_chat_utils import is_1c_rlk_chat_entry, is_rlk_chat_1c_session, is_rlk_chat_request

CURRENT_SESSION_CACHE_KEY = "current_session:{}"
CURRENT_SESSION_CACHE_TTL = getattr(settings, 'SESSION_COOKIE_AGE', 1209600)


class SingleDeviceSessionMiddleware:
    """Разрешает только одну активную сессию на пользователя (последний вход)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Чат 1С — отдельная сессия, не влияет на вход в браузере
        if is_rlk_chat_1c_session(request):
            return self.get_response(request)
        if is_rlk_chat_request(request) and is_1c_rlk_chat_entry(request):
            return self.get_response(request)

        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return self.get_response(request)

        if not request.session.session_key:
            request.session.create()

        current_sk = request.session.session_key
        user_id = request.user.pk
        cache_key = CURRENT_SESSION_CACHE_KEY.format(user_id)

        allowed_sk = cache.get(cache_key)
        if allowed_sk is None:
            try:
                profile = request.user.profiles
                allowed_sk = getattr(profile, 'current_session_key', None) or ""
            except Exception:
                allowed_sk = ""
            cache.set(cache_key, allowed_sk, CURRENT_SESSION_CACHE_TTL)

        if allowed_sk and allowed_sk != current_sk:
            logout(request)
            try:
                next = str(request.get_full_path_info())
                from django.http import HttpResponseRedirect
                login_url = getattr(settings, 'LOGIN_URL', '/login/')
                return HttpResponseRedirect(login_url + "?single_device=1" + "&next=" + next)
            except:
                from django.http import HttpResponseRedirect
                login_url = getattr(settings, 'LOGIN_URL', '/login/')
                return HttpResponseRedirect(login_url + "?single_device=1")

        return self.get_response(request)
