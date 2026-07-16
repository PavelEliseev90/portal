from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from avtosalon.deal_calc_approval import (
    can_auto_approve_calculation,
    director_can_approve_without_uk,
    kvp_above_km_rule,
    kvp_above_min_dc_if_configured,
    kvp_above_min_km_dc,
    prepare_calculation_soglasovanie_from_1c,
    submit_calculation_soglasovanie_from_1c,
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
