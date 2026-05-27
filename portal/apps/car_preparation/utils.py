"""Вспомогательные функции модуля подготовки."""
from django.db.models import Q

from refs.models import RefStaff


def get_staff_for_user(user):
    """Сотрудник RefStaff для пользователя портала."""
    if not user or not user.is_authenticated:
        return None
    staff = getattr(user, 'staff', None)
    if staff:
        return staff
    if user.username:
        staff = RefStaff.objects.filter(domain_login__iexact=user.username).first()
        if staff:
            return staff
    return None


def get_repair_zones_for_staff(staff, *, include_unit_fallback=True):
    """
    Ремонтные зоны, доступные сотруднику.
    Сначала явная привязка assigned_staff, иначе — зоны подразделений сотрудника.
    """
    from .models import RefRepairZone

    if not staff:
        return RefRepairZone.objects.none()

    zones = RefRepairZone.objects.filter(
        is_active=True,
        assigned_staff=staff,
    ).select_related('unit').distinct()

    if zones.exists() or not include_unit_fallback:
        return zones.order_by('sort_order', 'name')

    unit_ids = staff.units.values_list('id', flat=True)
    return RefRepairZone.objects.filter(
        is_active=True,
    ).filter(
        Q(unit_id__in=unit_ids) | Q(unit__isnull=True),
    ).select_related('unit').order_by('sort_order', 'name')
