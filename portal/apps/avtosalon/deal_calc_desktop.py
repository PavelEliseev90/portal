"""Рабочий стол директора новых автомобилей: очереди и история согласования КП."""
from django.db.models import Q

from avtosalon.deal_calc_approval import (
    AUTO_APPROVE_COMMENT,
    AUTO_APPROVE_USER_ID,
    user_has_deal_calc_uk_access,
)
from prices_car.models import CarCalculations

DESKTOP_HISTORY_LIMIT = 50

ROLE_UK = 'uk'
ROLE_DIRECTOR = 'director'


def _get_profile(user):
    return getattr(user, 'profiles', None)


def user_has_deal_calc_director_desktop_access(user):
    """Доступ к рабочему столу: УК (все ДЦ) или директор новых с подразделениями."""
    if user_has_deal_calc_uk_access(user):
        return True
    profile = _get_profile(user)
    if not profile or not profile.price_car_new_director:
        return False
    return profile.available_units.exists()


def get_desktop_role(user):
    if user_has_deal_calc_uk_access(user):
        return ROLE_UK
    if _get_profile(user) and _get_profile(user).price_car_new_director:
        return ROLE_DIRECTOR
    return None


def _director_unit_ids(user):
    profile = _get_profile(user)
    if profile is None:
        return []
    return list(profile.available_units.values_list('pk', flat=True))


def _auto_approved_q():
    return Q(
        soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
        director_approve_user_id=AUTO_APPROVE_USER_ID,
        director_approve_comment=AUTO_APPROVE_COMMENT,
    )


def _manual_director_approved_q():
    return Q(
        soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
    ) & ~_auto_approved_q()


def _reached_uk_q():
    return Q(soglasovanie_status__in=[
        CarCalculations.SOGLASOVANIE_PENDING_UK,
        CarCalculations.SOGLASOVANIE_UK_APPROVED,
        CarCalculations.SOGLASOVANIE_UK_REJECTED,
    ])


def _scope_units(qs, user, role):
    if role == ROLE_UK:
        return qs
    unit_ids = _director_unit_ids(user)
    if not unit_ids:
        return qs.none()
    return qs.filter(unit_id__in=unit_ids)


def _base_calc_qs():
    return CarCalculations.objects.select_related(
        'unit', 'car', 'rlk', 'rlk__customer', 'author', 'staff',
        'director_approve_user', 'uk_approve_user',
    )


def get_pending_queue(user, role, limit=DESKTOP_HISTORY_LIMIT):
    qs = _base_calc_qs().filter(active=True)
    if role == ROLE_UK:
        qs = qs.filter(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
    else:
        qs = qs.filter(
            Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING)
            | Q(soglasovanie_status='')
            | Q(soglasovanie_status__isnull=True),
        )
        qs = _scope_units(qs, user, role)
    return qs.order_by('-date_start_soglasovanie', '-date', '-pk')[:limit]


def get_pending_count(user, role):
    qs = _base_calc_qs().filter(active=True)
    if role == ROLE_UK:
        qs = qs.filter(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
    else:
        qs = qs.filter(
            Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING)
            | Q(soglasovanie_status='')
            | Q(soglasovanie_status__isnull=True),
        )
        qs = _scope_units(qs, user, role)
    return qs.count()


def get_uk_reached_history(user, limit=DESKTOP_HISTORY_LIMIT):
    """Все КП, дошедшие до согласования УК."""
    return _base_calc_qs().filter(
        _reached_uk_q(),
    ).order_by('-uk_approve_date', '-director_approve_date', '-date', '-pk')[:limit]


def get_director_manual_approvals_history(user, role, limit=DESKTOP_HISTORY_LIMIT):
    """Согласования директорами ДЦ (без автоматических)."""
    qs = _base_calc_qs().filter(_manual_director_approved_q())
    qs = _scope_units(qs, user, role)
    return qs.order_by('-director_approve_date', '-date', '-pk')[:limit]


def get_auto_approved_history(user, role, limit=DESKTOP_HISTORY_LIMIT):
    """Автоматически согласованные КП."""
    qs = _base_calc_qs().filter(_auto_approved_q())
    qs = _scope_units(qs, user, role)
    return qs.order_by('-director_approve_date', '-date', '-pk')[:limit]


def get_director_processed_history(user, limit=DESKTOP_HISTORY_LIMIT):
    """
    История для директора ДЦ: согласовано директором (вручную или отправлено в УК)
    и отказы директора по его подразделениям.
    """
    qs = _base_calc_qs().filter(
        Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_UK_APPROVED)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_UK_REJECTED)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED),
    ).exclude(_auto_approved_q())
    qs = _scope_units(qs, user, ROLE_DIRECTOR)
    return qs.order_by('-director_approve_date', '-date', '-pk')[:limit]


def build_desktop_context(user):
    role = get_desktop_role(user)
    if not role:
        return None

    ctx = {
        'role': role,
        'role_label': 'Управляющая компания' if role == ROLE_UK else 'Директор ДЦ',
        'pending_count': get_pending_count(user, role),
        'pending_queue': get_pending_queue(user, role),
        'auto_approved_history': get_auto_approved_history(user, role),
        'calculations_list_url': '/prices_car/calculations_list/',
        'pending_list_url': (
            '/prices_car/calculations_list/?soglasovanie_filter=pending_uk'
            if role == ROLE_UK
            else '/prices_car/calculations_list/?soglasovanie_filter=pending_director'
        ),
    }

    if role == ROLE_UK:
        ctx['uk_reached_history'] = get_uk_reached_history(user)
        ctx['director_approvals_history'] = get_director_manual_approvals_history(user, role)
    else:
        ctx['director_processed_history'] = get_director_processed_history(user)

    return ctx


def build_desktop_summary_for_user(user):
    """Краткая сводка для главной страницы портала."""
    if not user_has_deal_calc_director_desktop_access(user):
        return None
    role = get_desktop_role(user)
    return {
        'role': role,
        'role_label': 'УК' if role == ROLE_UK else 'Директор ДЦ',
        'pending_count': get_pending_count(user, role),
        'url': '/prices_car/director/kp/',
    }
