# -*- coding: utf-8 -*-
"""Копирование версий RegEstimationsSettings без затирания незатронутых полей."""
from datetime import datetime

from django.db import ProgrammingError, OperationalError
from django.db.utils import DatabaseError

from register.models import RegEstimationsSettings


def get_latest_estimation_settings():
    """
    Последняя запись настроек.
    Если в БД ещё нет колонки mcu_kf (миграция не применена) — читаем с defer.
    """
    qs = RegEstimationsSettings.objects.order_by('pk')
    try:
        return qs.last()
    except (ProgrammingError, OperationalError, DatabaseError):
        try:
            return qs.defer('mcu_kf').last()
        except Exception:
            return None


def clone_estimation_settings(source=None, name=None):
    """
    Новая запись = полная копия source (или последних настроек).
    Незатронутые поля (диагностика и т.д.) сохраняются как в исходной версии.
    """
    if source is None:
        source = get_latest_estimation_settings()

    if source is None:
        clone = RegEstimationsSettings()
    else:
        # Перечитываем без отложенных полей, чтобы в копию попали все значения.
        try:
            clone = RegEstimationsSettings.objects.get(pk=source.pk)
        except (ProgrammingError, OperationalError, DatabaseError):
            clone = RegEstimationsSettings.objects.defer('mcu_kf').get(pk=source.pk)
        clone.pk = None
        clone.id = None
        clone._state.adding = True

    if name is None:
        # USE_TZ=False — localtime() на naive datetime падает
        name = 'Настройки от {}'.format(datetime.now().strftime('%d.%m.%Y %H:%M'))
    clone.name = name
    return clone


def apply_mcu_kf_from_post(settings_obj, post):
    try:
        settings_obj.mcu_kf = float(post.get('mcu_kf', getattr(settings_obj, 'mcu_kf', 1) or 1) or 1)
    except (TypeError, ValueError):
        settings_obj.mcu_kf = 1.0
    if not settings_obj.mcu_kf or settings_obj.mcu_kf <= 0:
        settings_obj.mcu_kf = 1.0
    return settings_obj
