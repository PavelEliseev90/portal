"""Общий будильник ЕЦО на RegInteractivOcenkaRLK."""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Exists, OuterRef, Q, Subquery

from eco.services.datetime_portal import (
    add_minutes,
    compat_dt,
    is_past,
    minutes_until,
    portal_now,
)
from register.models import RegInteractivOcenkaAlarm, RegInteractivOcenkaRLK

ALARM_SNOOZE_MINUTES = 15


def user_can_manage_alarm(user) -> bool:
    profile = getattr(user, 'profiles', None)
    return bool(user and user.is_authenticated and profile and profile.eco)


def resolve_interactiv_rlk_by_rlk_id(rlk_id: int) -> RegInteractivOcenkaRLK | None:
    return (
        RegInteractivOcenkaRLK.objects
        .filter(rlk_id=rlk_id)
        .select_related('rlk', 'status')
        .first()
    )


def get_active_alarm(interactiv_rlk: RegInteractivOcenkaRLK):
    if interactiv_rlk is None:
        return None
    return (
        RegInteractivOcenkaAlarm.objects
        .filter(interactiv_rlk=interactiv_rlk, active=True)
        .select_related('set_by', 'set_by__profiles', 'dismissed_by', 'dismissed_by__profiles')
        .first()
    )


def alarm_status_dict(alarm, *, now=None) -> dict:
    now = compat_dt(now or portal_now())
    if alarm is None or not alarm.active:
        return {
            'has_alarm': False,
            'alarm_ringing': False,
            'alarm_due_at': '',
            'alarm_set_by_name': '',
            'alarm_set_by_id': None,
            'alarm_minutes_left': 0,
            'alarm_label': '',
        }
    due = compat_dt(alarm.due_at)
    ringing = is_past(due, now=now)
    set_by = alarm.set_by
    set_name = ''
    if set_by is not None:
        profile = getattr(set_by, 'profiles', None)
        set_name = (getattr(profile, 'eco_name', None) or '').strip()
        if not set_name:
            set_name = set_by.get_full_name() or set_by.username
    if ringing:
        label = 'Будильник!'
    else:
        mins = minutes_until(due, now=now)
        label = f'через {mins} мин' if mins else 'скоро'
    due_str = due.strftime('%d.%m.%Y %H:%M') if due else ''
    return {
        'has_alarm': True,
        'alarm_ringing': ringing,
        'alarm_due_at': due_str,
        'alarm_due_at_iso': due.isoformat() if due else '',
        'alarm_set_by_name': set_name,
        'alarm_set_by_id': set_by.pk if set_by else None,
        'alarm_minutes_left': 0 if ringing else minutes_until(due, now=now),
        'alarm_label': label,
    }


def build_alarm_context(interactiv_rlk, *, user=None) -> dict:
    ctx = alarm_status_dict(get_active_alarm(interactiv_rlk))
    ctx['can_manage_alarm'] = user_can_manage_alarm(user) if user is not None else False
    ctx['alarm_snooze_minutes'] = ALARM_SNOOZE_MINUTES
    return ctx


def set_alarm(interactiv_rlk: RegInteractivOcenkaRLK, user: User) -> RegInteractivOcenkaAlarm:
    if not user_can_manage_alarm(user):
        raise PermissionError('forbidden')
    if interactiv_rlk is None:
        raise ValueError('not_found')
    now = portal_now()
    due = add_minutes(ALARM_SNOOZE_MINUTES, now)
    alarm, _created = RegInteractivOcenkaAlarm.objects.get_or_create(
        interactiv_rlk=interactiv_rlk,
        defaults={
            'active': True,
            'due_at': due,
            'set_by': user,
            'set_at': now,
            'dismissed_by': None,
            'dismissed_at': None,
        },
    )
    if not _created:
        alarm.active = True
        alarm.due_at = due
        alarm.set_by = user
        alarm.set_at = now
        alarm.dismissed_by = None
        alarm.dismissed_at = None
        alarm.save(update_fields=[
            'active', 'due_at', 'set_by', 'set_at', 'dismissed_by', 'dismissed_at',
        ])
    return alarm


def dismiss_alarm(alarm: RegInteractivOcenkaAlarm, user: User | None, *, auto: bool = False):
    if not auto and not user_can_manage_alarm(user):
        raise PermissionError('forbidden')
    now = portal_now()
    alarm.active = False
    alarm.dismissed_at = now
    alarm.dismissed_by = None if auto else user
    alarm.save(update_fields=['active', 'dismissed_at', 'dismissed_by'])


def dismiss_alarm_for_rlk(rlk_id: int, user: User):
    interactiv_rlk = resolve_interactiv_rlk_by_rlk_id(rlk_id)
    if interactiv_rlk is None:
        raise RegInteractivOcenkaRLK.DoesNotExist()
    alarm = get_active_alarm(interactiv_rlk)
    if alarm is None:
        return None
    dismiss_alarm(alarm, user, auto=False)
    return alarm


def set_alarm_for_rlk(rlk_id: int, user: User) -> RegInteractivOcenkaAlarm:
    interactiv_rlk = resolve_interactiv_rlk_by_rlk_id(rlk_id)
    if interactiv_rlk is None:
        raise RegInteractivOcenkaRLK.DoesNotExist()
    return set_alarm(interactiv_rlk, user)


def alarm_exists_subquery(*, rlk_lookup='rlk_id', ringing_only=False, now=None):
    flt = Q(
        interactiv_rlk__rlk_id=OuterRef(rlk_lookup),
        active=True,
    )
    if ringing_only:
        flt &= Q(due_at__lte=compat_dt(now or portal_now()))
    return Exists(RegInteractivOcenkaAlarm.objects.filter(flt))


def alarm_due_at_subquery(*, rlk_lookup='rlk_id'):
    return Subquery(
        RegInteractivOcenkaAlarm.objects
        .filter(
            interactiv_rlk__rlk_id=OuterRef(rlk_lookup),
            active=True,
        )
        .order_by('due_at')
        .values('due_at')[:1]
    )


def alarm_set_by_name_subquery(*, rlk_lookup='rlk_id'):
    return Subquery(
        RegInteractivOcenkaAlarm.objects
        .filter(
            interactiv_rlk__rlk_id=OuterRef(rlk_lookup),
            active=True,
        )
        .order_by('due_at')
        .values('set_by__profiles__eco_name')[:1]
    )


def enrich_chat_row_alarm_fields(row: dict, *, now=None) -> None:
    now = compat_dt(now or portal_now())
    has = bool(row.get('has_alarm'))
    if not has:
        row['alarm_ringing'] = False
        row['alarm_minutes_left'] = 0
        row['alarm_label'] = ''
        return
    due = compat_dt(row.get('alarm_due_at'))
    ringing = is_past(due, now=now) if due else bool(row.get('alarm_ringing'))
    row['alarm_ringing'] = ringing
    if ringing:
        row['alarm_minutes_left'] = 0
        row['alarm_label'] = 'Будильник!'
    else:
        row['alarm_minutes_left'] = minutes_until(due, now=now)
        row['alarm_label'] = f"через {row['alarm_minutes_left']} мин"
    set_name = (row.get('alarm_set_by_name') or '').strip()
    if set_name:
        row['alarm_set_by_name'] = set_name
