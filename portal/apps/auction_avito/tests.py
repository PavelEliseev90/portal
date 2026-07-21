from types import SimpleNamespace

from django.test import SimpleTestCase

from auction_avito.services.auto_bid import decide_auto_bid, round_up_to


def _settings(**kwargs):
    defaults = dict(
        auto_bid_enabled=True,
        mileage_min=None,
        mileage_max=None,
        year_min=None,
        year_max=None,
        block_taxi=True,
        block_carsharing=True,
        block_mileage_twisted=True,
        bid_round_to=1000,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class AutoBidDecideTests(SimpleTestCase):
    def test_round_up_to(self):
        self.assertEqual(round_up_to(820500, 1000), 821000)
        self.assertEqual(round_up_to(820000, 1000), 820000)

    def test_disabled(self):
        d = decide_auto_bid(
            _settings(auto_bid_enabled=False),
            buyout_price=900_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
        )
        self.assertFalse(d['should_bid'])
        self.assertIn('выключены', d['reason'])

    def test_filter_taxi(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=900_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
            risk_flags={'taxi': True, 'carsharing': False, 'mileageTwisted': False},
        )
        self.assertFalse(d['should_bid'])
        self.assertIn('такси', d['reason'])

    def test_filter_year_range(self):
        d = decide_auto_bid(
            _settings(year_min=2018, year_max=2022),
            buyout_price=900_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2015,
            mileage=50_000,
        )
        self.assertFalse(d['should_bid'])
        self.assertIn('год', d['reason'])

    def test_our_max_bid_skips(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=900_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            our_bid=820_000,
            year=2019,
            mileage=50_000,
        )
        self.assertFalse(d['should_bid'])
        self.assertIn('уже наша', d['reason'])

    def test_next_bid_ge_buyout_skips(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=824_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            our_bid=0,
            year=2019,
            mileage=50_000,
        )
        # next = ceil((820000+5000)/1000)*1000 = 825000 >= 824000
        self.assertFalse(d['should_bid'])
        self.assertEqual(d['next_bid'], 825_000)

    def test_should_bid_ok(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            our_bid=0,
            year=2019,
            mileage=50_000,
            risk_flags={'taxi': False, 'carsharing': False, 'mileageTwisted': False},
        )
        self.assertTrue(d['should_bid'])
        self.assertEqual(d['bid_amount'], 825_000)
        self.assertEqual(d['reason'], 'ok')

    def test_buyout_not_above_max(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=820_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
        )
        self.assertFalse(d['should_bid'])
        self.assertIn('maxBid', d['reason'])
