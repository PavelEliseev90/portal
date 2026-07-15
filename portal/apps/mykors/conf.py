"""Настройки интеграции MyKors (изолированы от остального портала)."""
from django.conf import settings


def is_enabled():
    if not getattr(settings, 'MYKORS_ENABLED', False):
        return False
    key = (getattr(settings, 'MYKORS_API_KEY', '') or '').strip()
    secret = (getattr(settings, 'MYKORS_API_SECRET', '') or '').strip()
    return bool(key and secret)


def api_base_url():
    return (getattr(settings, 'MYKORS_API_BASE_URL', '') or 'https://my.kors-group.ru').rstrip('/')


def api_key():
    return (getattr(settings, 'MYKORS_API_KEY', '') or '').strip()


def api_secret():
    return (getattr(settings, 'MYKORS_API_SECRET', '') or '').strip()


def request_timeout():
    return int(getattr(settings, 'MYKORS_REQUEST_TIMEOUT', 15) or 15)


def request_delay_sec():
    """Пауза между POST (снижает нагрузку на оба сервера)."""
    return float(getattr(settings, 'MYKORS_REQUEST_DELAY_SEC', 0.15) or 0)


def batch_limit():
    """Сколько авто за один прогон команды (0 = все в наличии)."""
    return int(getattr(settings, 'MYKORS_EXPORT_BATCH_LIMIT', 0) or 0)


def skip_unchanged():
    """Не слать повторно, если payload не изменился с прошлой успешной выгрузки."""
    return bool(getattr(settings, 'MYKORS_SKIP_UNCHANGED', True))


def portal_public_base_url():
    """Базовый URL портала для абсолютных ссылок на фото (/media/...)."""
    return (
        getattr(settings, 'MYKORS_PORTAL_PUBLIC_BASE_URL', None)
        or getattr(settings, 'PORTAL_PUBLIC_BASE_URL', None)
        or 'https://ah.kors-group.com'
    ).rstrip('/')


def photos_limit():
    """Максимум фото на одну машину в ingest (0 = без лимита)."""
    return int(getattr(settings, 'MYKORS_PHOTOS_LIMIT', 50) or 0)
