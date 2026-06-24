"""Рабочий стол директора новых автомобилей: очереди и история согласования КП."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from avtosalon.deal_calc_approval import (
    AUTO_APPROVE_COMMENT,
    AUTO_APPROVE_USER_ID,
    user_has_deal_calc_uk_access,
)
from prices_car.models import CarCalculations

DESKTOP_HISTORY_LIMIT = 50

ROLE_UK = 'uk'
ROLE_DIRECTOR = 'director'

SECTION_PENDING = 'pending'
SECTION_UK_REACHED = 'uk_reached'
SECTION_DIRECTOR_APPROVALS = 'director_approvals'
SECTION_AUTO_APPROVED = 'auto_approved'
SECTION_DIRECTOR_PROCESSED = 'director_processed'

SECTION_LABELS = {
    SECTION_PENDING: 'Ожидают согласования',
    SECTION_UK_REACHED: 'Дошли до согласования УК',
    SECTION_DIRECTOR_APPROVALS: 'Согласования директорами ДЦ',
    SECTION_AUTO_APPROVED: 'Автоматически согласованные',
    SECTION_DIRECTOR_PROCESSED: 'История согласований по подразделениям',
}


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


def resolve_desktop_user(request):
    """Пользователь рабочего стола: из ?user_id= или текущий."""
    user = request.user
    raw_id = (request.GET.get('user_id') or '').strip()
    if not raw_id:
        return user
    try:
        return get_user_model().objects.get(pk=int(raw_id))
    except (ValueError, TypeError, get_user_model().DoesNotExist):
        return user


def can_view_desktop_as(request, view_user):
    """Свой стол или просмотр по ?user_id= (как на главной)."""
    if not user_has_deal_calc_director_desktop_access(view_user):
        return False
    if view_user.pk == request.user.pk:
        return True
    raw_id = (request.GET.get('user_id') or '').strip()
    try:
        return bool(raw_id) and int(raw_id) == view_user.pk
    except (ValueError, TypeError):
        return False


def desktop_user_query_suffix(view_user, request_user):
    if view_user.pk != request_user.pk:
        return '?user_id={}'.format(view_user.pk)
    return ''


def _today():
    now = timezone.now()
    if timezone.is_aware(now):
        return timezone.localtime(now).date()
    return now.date()


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


def _pending_status_q(role):
    if role == ROLE_UK:
        return Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
    return (
        Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING)
        | Q(soglasovanie_status='')
        | Q(soglasovanie_status__isnull=True)
    )


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


def _pending_qs(user, role):
    qs = _base_calc_qs().filter(active=True).filter(_pending_status_q(role))
    return _scope_units(qs, user, role)


def _pending_today_qs(user, role):
    today = _today()
    return _pending_qs(user, role).filter(
        Q(date_start_soglasovanie__date=today) | Q(date__date=today),
    )


def _uk_reached_qs(user):
    return _base_calc_qs().filter(_reached_uk_q())


def _uk_reached_today_qs(user):
    today = _today()
    return _uk_reached_qs(user).filter(director_approve_date__date=today)


def _director_approvals_qs(user, role):
    qs = _base_calc_qs().filter(
        Q(_manual_director_approved_q())
        | Q(
            soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_PENDING_UK,
                CarCalculations.SOGLASOVANIE_UK_APPROVED,
                CarCalculations.SOGLASOVANIE_UK_REJECTED,
            ],
            director_approve_user_id__isnull=False,
        ),
    ).exclude(_auto_approved_q())
    return _scope_units(qs, user, role)


def _director_approvals_today_qs(user, role):
    today = _today()
    return _director_approvals_qs(user, role).filter(director_approve_date__date=today)


def _auto_approved_qs(user, role):
    qs = _base_calc_qs().filter(_auto_approved_q())
    return _scope_units(qs, user, role)


def _auto_approved_today_qs(user, role):
    today = _today()
    return _auto_approved_qs(user, role).filter(director_approve_date__date=today)


def _director_processed_qs(user):
    qs = _base_calc_qs().filter(
        Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_UK_APPROVED)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_UK_REJECTED)
        | Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED),
    ).exclude(_auto_approved_q())
    return _scope_units(qs, user, ROLE_DIRECTOR)


def _director_processed_today_qs(user):
    today = _today()
    return _director_processed_qs(user).filter(director_approve_date__date=today)


def get_section_queryset(user, role, section):
    mapping = {
        SECTION_PENDING: lambda: _pending_qs(user, role),
        SECTION_UK_REACHED: lambda: _uk_reached_qs(user),
        SECTION_DIRECTOR_APPROVALS: lambda: _director_approvals_qs(user, role),
        SECTION_AUTO_APPROVED: lambda: _auto_approved_qs(user, role),
        SECTION_DIRECTOR_PROCESSED: lambda: _director_processed_qs(user),
    }
    builder = mapping.get(section)
    if builder is None:
        return _base_calc_qs().none()

    if section == SECTION_UK_REACHED and role != ROLE_UK:
        return _base_calc_qs().none()
    if section == SECTION_DIRECTOR_APPROVALS and role != ROLE_UK:
        return _base_calc_qs().none()
    if section == SECTION_DIRECTOR_PROCESSED and role != ROLE_DIRECTOR:
        return _base_calc_qs().none()

    qs = builder()
    if section == SECTION_PENDING:
        return qs.order_by('-date_start_soglasovanie', '-date', '-pk')
    if section == SECTION_UK_REACHED:
        return qs.order_by('-director_approve_date', '-uk_approve_date', '-date', '-pk')
    if section in (SECTION_DIRECTOR_APPROVALS, SECTION_AUTO_APPROVED, SECTION_DIRECTOR_PROCESSED):
        return qs.order_by('-director_approve_date', '-date', '-pk')
    return qs.order_by('-date', '-pk')


def get_section_today_count(user, role, section):
    counters = {
        SECTION_PENDING: lambda: _pending_today_qs(user, role).count(),
        SECTION_UK_REACHED: lambda: _uk_reached_today_qs(user).count() if role == ROLE_UK else 0,
        SECTION_DIRECTOR_APPROVALS: lambda: _director_approvals_today_qs(user, role).count() if role == ROLE_UK else 0,
        SECTION_AUTO_APPROVED: lambda: _auto_approved_today_qs(user, role).count(),
        SECTION_DIRECTOR_PROCESSED: lambda: _director_processed_today_qs(user).count() if role == ROLE_DIRECTOR else 0,
    }
    counter = counters.get(section)
    return counter() if counter else 0


def section_allowed_for_role(section, role):
    if section == SECTION_UK_REACHED:
        return role == ROLE_UK
    if section == SECTION_DIRECTOR_APPROVALS:
        return role == ROLE_UK
    if section == SECTION_DIRECTOR_PROCESSED:
        return role == ROLE_DIRECTOR
    return section in (SECTION_PENDING, SECTION_AUTO_APPROVED)


def get_section_label(section, role):
    if section == SECTION_PENDING:
        if role == ROLE_UK:
            return 'Ожидают согласования УК'
        return 'Ожидают согласования'
    return SECTION_LABELS.get(section, section)


def _section_list_url(section, user_query_suffix=''):
    base = reverse('prices_car:new_cars_director_desktop_list', kwargs={'section': section})
    return base + user_query_suffix


def build_desktop_context(user, request_user=None):
    role = get_desktop_role(user)
    if not role:
        return None

    request_user = request_user or user
    uid_suffix = desktop_user_query_suffix(user, request_user)

    tiles = [
        {
            'key': SECTION_PENDING,
            'label': get_section_label(SECTION_PENDING, role),
            'count_today': get_section_today_count(user, role, SECTION_PENDING),
            'url': _section_list_url(SECTION_PENDING, uid_suffix),
            'icon': '⏳',
        },
        {
            'key': SECTION_AUTO_APPROVED,
            'label': get_section_label(SECTION_AUTO_APPROVED, role),
            'count_today': get_section_today_count(user, role, SECTION_AUTO_APPROVED),
            'url': _section_list_url(SECTION_AUTO_APPROVED, uid_suffix),
            'icon': '🤖',
        },
    ]

    if role == ROLE_UK:
        tiles.insert(1, {
            'key': SECTION_UK_REACHED,
            'label': get_section_label(SECTION_UK_REACHED, role),
            'count_today': get_section_today_count(user, role, SECTION_UK_REACHED),
            'url': _section_list_url(SECTION_UK_REACHED, uid_suffix),
            'icon': '📜',
        })
        tiles.insert(2, {
            'key': SECTION_DIRECTOR_APPROVALS,
            'label': get_section_label(SECTION_DIRECTOR_APPROVALS, role),
            'count_today': get_section_today_count(user, role, SECTION_DIRECTOR_APPROVALS),
            'url': _section_list_url(SECTION_DIRECTOR_APPROVALS, uid_suffix),
            'icon': '✅',
        })
    else:
        tiles.insert(1, {
            'key': SECTION_DIRECTOR_PROCESSED,
            'label': get_section_label(SECTION_DIRECTOR_PROCESSED, role),
            'count_today': get_section_today_count(user, role, SECTION_DIRECTOR_PROCESSED),
            'url': _section_list_url(SECTION_DIRECTOR_PROCESSED, uid_suffix),
            'icon': '📜',
        })

    calc_list_url = reverse('prices_car:calculations_list') + uid_suffix
    desktop_url = reverse('prices_car:new_cars_director_desktop') + uid_suffix

    return {
        'role': role,
        'role_label': 'Управляющая компания' if role == ROLE_UK else 'Директор ДЦ',
        'view_user': user,
        'view_user_id': user.pk,
        'user_query_suffix': uid_suffix,
        'tiles': tiles,
        'calculations_list_url': calc_list_url,
        'desktop_url': desktop_url,
    }


def build_section_list_context(user, role, section, request_user=None):
    request_user = request_user or user
    uid_suffix = desktop_user_query_suffix(user, request_user)
    return {
        'role': role,
        'role_label': 'Управляющая компания' if role == ROLE_UK else 'Директор ДЦ',
        'section': section,
        'section_label': get_section_label(section, role),
        'count_today': get_section_today_count(user, role, section),
        'view_user': user,
        'view_user_id': user.pk,
        'user_query_suffix': uid_suffix,
        'desktop_url': reverse('prices_car:new_cars_director_desktop') + uid_suffix,
        'calculations_list_url': reverse('prices_car:calculations_list') + uid_suffix,
    }
