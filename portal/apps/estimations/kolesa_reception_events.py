"""Журнал событий приёмки второго комплекта колёс (2КК)."""
from register.models import RegInteractivOcenkaKolesaReceptionEvent


def log_kolesa_reception_event(reception, event_type, user=None, message='', extra=None):
    """Записать событие по приёмке 2КК. Ошибки логирования не прерывают основное действие."""
    if reception is None or not getattr(reception, 'pk', None):
        return None
    try:
        return RegInteractivOcenkaKolesaReceptionEvent.objects.create(
            reception=reception,
            event_type=event_type,
            message=(message or '')[:1024],
            user=user if getattr(user, 'is_authenticated', False) else None,
            extra=extra or {},
        )
    except Exception:
        return None


def user_display(user):
    if not user:
        return '—'
    full = (user.get_full_name() or '').strip()
    return full or user.username or '—'
