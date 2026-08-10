"""Даты портала при USE_TZ=False: только naive через timezone.now()."""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def portal_now():
    return timezone.now()


def portal_today():
    return portal_now().date()


def compat_dt(dt):
    if dt is None:
        return None
    if settings.USE_TZ:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    if timezone.is_aware(dt):
        return timezone.make_naive(dt, timezone.get_current_timezone())
    return dt


def add_minutes(minutes: int, base=None):
    return compat_dt(base or portal_now()) + timedelta(minutes=minutes)


def is_past(dt, *, now=None) -> bool:
    dt = compat_dt(dt)
    now = compat_dt(now or portal_now())
    if dt is None or now is None:
        return False
    return dt <= now


def minutes_until(dt, *, now=None) -> int:
    dt = compat_dt(dt)
    now = compat_dt(now or portal_now())
    if dt is None or now is None:
        return 0
    delta = (dt - now).total_seconds()
    if delta <= 0:
        return 0
    return int(delta // 60)
