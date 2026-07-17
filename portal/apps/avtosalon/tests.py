from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from avtosalon.deal_calc_approval import (
    can_auto_approve_calculation,
    director_can_approve_without_uk,
    is_prior_uk_approved_calculation,
    kvp_above_km_rule,
    kvp_above_min_dc_if_configured,
    kvp_above_min_km_dc,
    kvp_meets_prior_uk_threshold,
    prepare_calculation_soglasovanie_from_1c,
    submit_calculation_soglasovanie_from_1c,
    try_approve_by_prior_uk_threshold,
)
from prices_car.km_breakdown import get_km_rule_total


class DealCalculationApprovalRulesTests(SimpleTestCase):
    def setUp(self):
        self.car = SimpleNamespace(min_km=0)

    @staticmethod
    def cumulative_data(min_km_dc=0):
        return {
            'brand_km': SimpleNamespace(km_min_dc=min_km_dc),
            'automatic': {'km_min_automatic': 100},
        }

    def test_auto_blocked_when_kvp_does_not_exceed_min_dc(self):
        calc = SimpleNamespace(kvp=151, car=self.car)
        cumulative_data = self.cumulative_data(min_km_dc=200)

        with patch(
            'prices_car.km_breakdown.get_km_rule_total',
            return_value=150,
        ):
            self.assertTrue(kvp_above_km_rule(calc, cumulative_data))
            self.assertFalse(kvp_above_min_dc_if_configured(calc, cumulative_data))
            self.assertFalse(can_auto_approve_calculation(calc, cumulative_data))

    def test_rule_equal_to_min_does_not_block_auto_when_kvp_above_both(self):
        calc = SimpleNamespace(kvp=151, car=self.car)
        cumulative_data = self.cumulative_data(min_km_dc=150)

        with patch(
            'prices_car.km_breakdown.get_km_rule_total',
            return_value=150,
        ):
            self.assertTrue(can_auto_approve_calculation(calc, cumulative_data))

    def test_auto_blocked_when_kvp_equals_min_dc(self):
        calc = SimpleNamespace(kvp=151, car=self.car)
        cumulative_data = self.cumulative_data(min_km_dc=151)

        with patch(
            'prices_car.km_breakdown.get_km_rule_total',
            return_value=150,
        ):
            self.assertFalse(can_auto_approve_calculation(calc, cumulative_data))

    def test_auto_approval_when_kvp_above_valid_rule(self):
        calc = SimpleNamespace(kvp=151, car=self.car)
        cumulative_data = self.cumulative_data(min_km_dc=100)

        with patch(
            'prices_car.km_breakdown.get_km_rule_total',
            return_value=150,
        ):
            self.assertTrue(can_auto_approve_calculation(calc, cumulative_data))

    def test_missing_min_dc_does_not_block_rule_auto_approval(self):
        calc = SimpleNamespace(kvp=151, car=self.car)

        with patch(
            'prices_car.km_breakdown.get_km_rule_total',
            return_value=150,
        ):
            self.assertTrue(
                can_auto_approve_calculation(calc, self.cumulative_data()),
            )

    def test_auto_approval_requires_kvp_strictly_above_rule(self):
        calc = SimpleNamespace(kvp=150, car=self.car)

        with patch(
            'prices_car.km_breakdown.get_km_rule_total',
            return_value=150,
        ):
            self.assertFalse(can_auto_approve_calculation(calc, self.cumulative_data()))

    def test_director_approval_when_kvp_above_min_dc(self):
        calc = SimpleNamespace(kvp=120, car=self.car)
        cumulative_data = self.cumulative_data(min_km_dc=100)

        self.assertTrue(kvp_above_min_km_dc(calc, cumulative_data))
        self.assertTrue(director_can_approve_without_uk(calc, cumulative_data))

    def test_director_cannot_approve_when_min_dc_missing_or_not_exceeded(self):
        calc = SimpleNamespace(kvp=100, car=self.car)

        self.assertFalse(
            director_can_approve_without_uk(
                calc, self.cumulative_data(min_km_dc=100),
            ),
        )
        self.assertFalse(
            director_can_approve_without_uk(
                calc, self.cumulative_data(min_km_dc=0),
            ),
        )

    def test_rule_below_min_dc_does_not_block_director_when_kvp_above_min(self):
        calc = SimpleNamespace(kvp=120, car=self.car)
        cumulative_data = self.cumulative_data(min_km_dc=100)

        self.assertTrue(
            director_can_approve_without_uk(calc, cumulative_data),
        )

    def test_rule_uses_trade_in_state_from_calculation(self):
        calc = SimpleNamespace()
        cumulative_data = self.cumulative_data()
        cumulative_data.update({
            'automatic_k': {'km_min_automatic': 120},
            'automatic_k_tradein': {'km_min_automatic': 170},
        })

        with patch(
            'prices_car.km_raschet.calculation_has_applied_trade_in',
            return_value=True,
        ):
            self.assertEqual(
                get_km_rule_total(cumulative_data, self.car, calc=calc),
                170,
            )

    def test_prior_uk_threshold_accepts_equal_or_higher_kvp(self):
        approval = SimpleNamespace(approved_kvp=100)

        self.assertTrue(
            kvp_meets_prior_uk_threshold(
                SimpleNamespace(kvp=100), approval,
            ),
        )
        self.assertTrue(
            kvp_meets_prior_uk_threshold(
                SimpleNamespace(kvp=101), approval,
            ),
        )
        self.assertFalse(
            kvp_meets_prior_uk_threshold(
                SimpleNamespace(kvp=99), approval,
            ),
        )

    def test_prior_uk_threshold_approval_sets_uk_status_and_audit_fields(self):
        calc = SimpleNamespace(
            pk=2,
            soglasovanie_status='awaiting_1c',
            kvp=100,
            uk_approval_basis='',
            uk_approval_reference_id=None,
            save=Mock(),
        )
        source_calc = SimpleNamespace(pk=1, number='OLD-1')
        approval = SimpleNamespace(
            pk=10,
            approved_kvp=100,
            calculation=source_calc,
        )
        system_user = SimpleNamespace(pk=1)

        with (
            patch(
                'avtosalon.deal_calc_approval.get_prior_uk_approval',
                return_value=approval,
            ),
            patch(
                'avtosalon.deal_calc_approval.User.objects.filter',
            ) as users,
            patch(
                'avtosalon.deal_calc_approval.notify_calc_soglasovanie_result_email',
            ) as notify,
            patch(
                'avtosalon.deal_calc_approval.transaction.on_commit',
                side_effect=lambda callback: callback(),
            ),
        ):
            users.return_value.first.return_value = system_user
            self.assertTrue(
                try_approve_by_prior_uk_threshold(calc),
            )

        self.assertEqual(calc.soglasovanie_status, 'uk_approved')
        self.assertEqual(calc.uk_approval_basis, 'prior_threshold')
        self.assertEqual(calc.uk_approval_threshold_kvp, 100)
        self.assertIs(calc.uk_approval_reference, approval)
        self.assertIn('OLD-1', calc.uk_approve_comment)
        calc.save.assert_called_once()
        notify.assert_called_once()
        calc.uk_approval_reference_id = approval.pk
        self.assertTrue(is_prior_uk_approved_calculation(calc))

    def test_prior_uk_threshold_does_not_approve_lower_kvp(self):
        calc = SimpleNamespace(
            pk=2,
            soglasovanie_status='awaiting_1c',
            kvp=99,
            save=Mock(),
        )
        approval = SimpleNamespace(
            approved_kvp=100,
            calculation=SimpleNamespace(pk=1, number='OLD-1'),
        )

        with patch(
            'avtosalon.deal_calc_approval.get_prior_uk_approval',
            return_value=approval,
        ):
            self.assertFalse(
                try_approve_by_prior_uk_threshold(calc),
            )

        calc.save.assert_not_called()

    def test_prior_uk_approval_is_revoked_when_scope_changes(self):
        old_approval = SimpleNamespace(
            pk=10,
            rlk_id=1,
            car_id=1,
        )
        calc = SimpleNamespace(
            pk=2,
            rlk_id=2,
            car_id=1,
            soglasovanie_status='uk_approved',
            kvp=150,
            uk_approval_basis='prior_threshold',
            uk_approval_threshold_kvp=100,
            uk_approval_reference=old_approval,
            uk_approval_reference_id=old_approval.pk,
            save=Mock(),
        )

        with patch(
            'avtosalon.deal_calc_approval.get_prior_uk_approval',
            return_value=None,
        ):
            self.assertFalse(
                try_approve_by_prior_uk_threshold(calc),
            )

        self.assertEqual(calc.soglasovanie_status, 'awaiting_1c')
        self.assertTrue(calc._prior_uk_approval_revoked)
        calc.save.assert_called_once()

    def test_repeated_load_keeps_calculation_in_director_queue(self):
        calc = SimpleNamespace(
            soglasovanie_status='pending',
            date_start_soglasovanie=object(),
            save=Mock(),
        )
        car = SimpleNamespace(cumulative_data=lambda: {})

        with patch(
            'avtosalon.deal_calc_approval.try_auto_approve_calculation',
        ) as try_auto:
            self.assertFalse(
                prepare_calculation_soglasovanie_from_1c(
                    calc, car, SimpleNamespace(), SimpleNamespace(),
                ),
            )

        try_auto.assert_not_called()
        calc.save.assert_not_called()
        self.assertEqual(calc.soglasovanie_status, 'pending')

    def test_prepare_prefers_prior_uk_threshold_over_rule_auto(self):
        calc = SimpleNamespace(
            soglasovanie_status='awaiting_1c',
            date_start_soglasovanie=None,
        )
        car = SimpleNamespace(cumulative_data=lambda: {})

        with (
            patch(
                'avtosalon.deal_calc_approval.try_approve_by_prior_uk_threshold',
                return_value=True,
            ) as prior_uk,
            patch(
                'avtosalon.deal_calc_approval.try_auto_approve_calculation',
            ) as rule_auto,
        ):
            self.assertTrue(
                prepare_calculation_soglasovanie_from_1c(
                    calc, car, SimpleNamespace(), SimpleNamespace(),
                ),
            )

        prior_uk.assert_called_once()
        rule_auto.assert_not_called()

    def test_submit_pending_without_start_date_notifies_director(self):
        calc = SimpleNamespace(
            soglasovanie_status='pending',
            date_start_soglasovanie=None,
            director_approve_user_id=None,
            director_approve_comment='',
            save=Mock(),
        )

        with patch(
            'avtosalon.deal_calc_approval._send_pending_soglasovanie_notifications',
        ) as notify:
            self.assertTrue(
                submit_calculation_soglasovanie_from_1c(
                    calc,
                    SimpleNamespace(),
                    SimpleNamespace(),
                    SimpleNamespace(),
                ),
            )

        self.assertIsNotNone(calc.date_start_soglasovanie)
        calc.save.assert_called_once()
        notify.assert_called_once()

    def test_submit_skips_when_already_in_director_queue(self):
        calc = SimpleNamespace(
            soglasovanie_status='pending',
            date_start_soglasovanie=object(),
            save=Mock(),
        )

        with patch(
            'avtosalon.deal_calc_approval._send_pending_soglasovanie_notifications',
        ) as notify:
            self.assertTrue(
                submit_calculation_soglasovanie_from_1c(
                    calc,
                    SimpleNamespace(),
                    SimpleNamespace(),
                    SimpleNamespace(),
                ),
            )

        calc.save.assert_not_called()
        notify.assert_not_called()

    def test_prepare_sets_awaiting_when_pending_without_start_date(self):
        calc = SimpleNamespace(
            soglasovanie_status='pending',
            date_start_soglasovanie=None,
            save=Mock(),
        )
        car = SimpleNamespace(cumulative_data=lambda: {})

        with (
            patch(
                'avtosalon.deal_calc_approval.try_approve_by_prior_uk_threshold',
                return_value=False,
            ),
            patch(
                'avtosalon.deal_calc_approval.try_auto_approve_calculation',
                return_value=False,
            ),
        ):
            self.assertFalse(
                prepare_calculation_soglasovanie_from_1c(
                    calc, car, SimpleNamespace(), SimpleNamespace(),
                ),
            )

        self.assertEqual(calc.soglasovanie_status, 'awaiting_1c')
        self.assertIsNone(calc.date_start_soglasovanie)
        calc.save.assert_called_once()

    def test_submit_from_awaiting_notifies_and_sets_pending(self):
        calc = SimpleNamespace(
            soglasovanie_status='awaiting_1c',
            date_start_soglasovanie=None,
            save=Mock(),
        )

        with patch(
            'avtosalon.deal_calc_approval._send_pending_soglasovanie_notifications',
        ) as notify:
            self.assertTrue(
                submit_calculation_soglasovanie_from_1c(
                    calc,
                    SimpleNamespace(),
                    SimpleNamespace(),
                    SimpleNamespace(),
                ),
            )

        self.assertEqual(calc.soglasovanie_status, 'pending')
        self.assertIsNotNone(calc.date_start_soglasovanie)
        calc.save.assert_called_once()
        notify.assert_called_once()
