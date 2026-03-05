# -*- coding: utf-8 -*-
"""Сигналы: при логине сохраняем session_key в профиль и кэш (один вход с одного устройства)."""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.core.cache import cache

from .middleware import CURRENT_SESSION_CACHE_KEY, CURRENT_SESSION_CACHE_TTL


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    if not getattr(request, 'session', None):
        return
    if not request.session.session_key:
        request.session.create()
    sk = request.session.session_key
    if not sk:
        return
    try:
        profile = user.profiles
        profile.current_session_key = sk
        profile.save(update_fields=['current_session_key'])
    except Exception:
        pass
    cache.set(CURRENT_SESSION_CACHE_KEY.format(user.pk), sk, CURRENT_SESSION_CACHE_TTL)
