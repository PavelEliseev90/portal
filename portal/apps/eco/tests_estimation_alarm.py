"""Тесты datetime_portal и estimation_alarm (USE_TZ=False)."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from documents.models import DocRLK
from eco.services.datetime_portal import compat_dt, is_past, minutes_until, portal_now
from eco.services.estimation_alarm import (
    alarm_status_dict,
    dismiss_alarm,
    set_alarm,
    should_keep_alarm,
    user_can_manage_alarm,
)
from profiles.models import Profiles
from register.models import RegInteractivOcenkaAlarm, RegInteractivOcenkaRLK


@override_settings(USE_TZ=False, TIME_ZONE='Europe/Moscow')
class EstimationAlarmTests(TestCase):
    def setUp(self):
        self.rlk = DocRLK.objects.create(nomer='T-1', uin='uin-alarm-1')
        self.interactiv_rlk = RegInteractivOcenkaRLK.objects.create(rlk=self.rlk)
        self.user = User.objects.create_user(username='eco_alarm', password='x')
        Profiles.objects.create(user=self.user, eco=True)

    def test_portal_now_is_naive(self):
        now = portal_now()
        self.assertIsNone(now.utcoffset())

    def test_compat_dt_naive_roundtrip(self):
        now = portal_now()
        self.assertEqual(compat_dt(now), now)

    @patch('eco.services.estimation_alarm.portal_now')
    def test_set_and_ringing(self, mock_now):
        base = portal_now().replace(microsecond=0)
        mock_now.return_value = base
        alarm = set_alarm(self.interactiv_rlk, self.user)
        self.assertTrue(alarm.active)
        self.assertEqual(alarm.due_at, base + timedelta(minutes=15))

        status = alarm_status_dict(alarm, now=base + timedelta(minutes=14))
        self.assertFalse(status['alarm_ringing'])
        self.assertEqual(status['alarm_minutes_left'], 1)

        status_ringing = alarm_status_dict(alarm, now=base + timedelta(minutes=16))
        self.assertTrue(status_ringing['alarm_ringing'])
        self.assertTrue(is_past(alarm.due_at, now=base + timedelta(minutes=16)))

    @patch('eco.services.estimation_alarm.portal_now')
    def test_dismiss(self, mock_now):
        base = portal_now().replace(microsecond=0)
        mock_now.return_value = base
        alarm = set_alarm(self.interactiv_rlk, self.user)
        dismiss_alarm(alarm, self.user)
        alarm.refresh_from_db()
        self.assertFalse(alarm.active)
        self.assertIsNotNone(alarm.dismissed_at)

    def test_user_can_manage_alarm(self):
        self.assertTrue(user_can_manage_alarm(self.user))
        other = User.objects.create_user(username='not_eco', password='x')
        Profiles.objects.create(user=other, eco=False)
        self.assertFalse(user_can_manage_alarm(other))

    def test_should_keep_alarm_false_when_archived(self):
        self.rlk.archive = True
        self.rlk.save(update_fields=['archive'])
        self.assertFalse(should_keep_alarm(self.interactiv_rlk))

    def test_one_alarm_per_interactiv_rlk(self):
        with patch('eco.services.estimation_alarm.portal_now', return_value=portal_now()):
            set_alarm(self.interactiv_rlk, self.user)
            set_alarm(self.interactiv_rlk, self.user)
        self.assertEqual(
            RegInteractivOcenkaAlarm.objects.filter(interactiv_rlk=self.interactiv_rlk).count(),
            1,
        )
