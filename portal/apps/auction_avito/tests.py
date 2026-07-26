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

    def test_no_max_bid_first_from_min(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=None,
            min_bid_step=5_000,
            our_bid=0,
            year=2019,
            mileage=50_000,
        )
        # next = ceil((800000+5000)/1000)*1000 = 805000
        self.assertTrue(d['should_bid'])
        self.assertEqual(d['bid_amount'], 805_000)
        self.assertEqual(d['mode'], 'first_from_min')

    def test_no_max_bid_zero_treated_as_empty(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=0,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
        )
        self.assertTrue(d['should_bid'])
        self.assertEqual(d['bid_amount'], 805_000)

    def test_no_max_bid_next_ge_buyout_skips(self):
        d = decide_auto_bid(
            _settings(),
            buyout_price=804_000,
            min_available_bid=800_000,
            max_bid=None,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
        )
        self.assertFalse(d['should_bid'])
        self.assertEqual(d['next_bid'], 805_000)
        self.assertIn('первая ставка', d['reason'])

    def test_min_bid_amount_floor(self):
        d = decide_auto_bid(
            _settings(min_bid_amount=900_000),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
        )
        self.assertFalse(d['should_bid'])
        self.assertIn('минимальной', d['reason'])

    def test_cap_by_seller_wish_blocks(self):
        d = decide_auto_bid(
            _settings(cap_bid_by_seller_wish=True),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
            seller_wish=824_000,  # next = 825000 > wish
        )
        self.assertFalse(d['should_bid'])
        self.assertEqual(d['reason_category'], 'above_seller_wish')
        self.assertIn('пожелания продавца', d['reason'])

    def test_cap_by_seller_wish_allows_equal(self):
        d = decide_auto_bid(
            _settings(cap_bid_by_seller_wish=True),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
            seller_wish=825_000,  # next = 825000 == wish
        )
        self.assertTrue(d['should_bid'])
        self.assertEqual(d['bid_amount'], 825_000)

    def test_cap_by_seller_wish_disabled_ignores(self):
        d = decide_auto_bid(
            _settings(cap_bid_by_seller_wish=False),
            buyout_price=950_000,
            min_available_bid=800_000,
            max_bid=820_000,
            min_bid_step=5_000,
            year=2019,
            mileage=50_000,
            seller_wish=824_000,
        )
        self.assertTrue(d['should_bid'])
        self.assertEqual(d['bid_amount'], 825_000)

class OutcomeClassifyTests(SimpleTestCase):
    def test_waiting_seller(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершен',
            detail='Ждём решения продавца. Обычно на это уходит день-два',
        )
        self.assertEqual(d['outcome_code'], 'waiting_seller')
        self.assertEqual(d['status_code'], 'finished')

    def test_waiting_not_false_won_from_notification_blob(self):
        """Шаблон Maxposter про «выбрал предложение ДЦ» + «ждём продавца» ≠ won."""
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён Дата аукциона 24 июля 2026 Ждём решения продавца',
            detail='Обычно на это уходит день-два',
            blob=(
                'Уведомление о том, что продавец автомобиля в Авито Аукционе '
                'выбрал предложение вашего дилерского центра среди прочих | '
                'Поздравляем вас выбрали'
            ),
        )
        self.assertEqual(d['outcome_code'], 'waiting_seller')

    def test_won_ignored_in_blob_only(self):
        """Победа только в blob без title/detail — не считаем won."""
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён',
            detail='',
            blob='Поздравляем! Вас выбрали. Лот ваш.',
        )
        self.assertNotEqual(d['outcome_code'], 'won')

    def test_won_phrase(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершен',
            detail='Поздравляем! Вас выбрали продавцом',
        )
        self.assertEqual(d['outcome_code'], 'won')
        self.assertEqual(d['status_code'], 'won')

    def test_lost_phrase(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            blob='Аукцион завершен. Продавец выбрал другого участника',
        )
        self.assertEqual(d['outcome_code'], 'lost')
        self.assertEqual(d['status_code'], 'lost')

    def test_lost_chose_another_buyer(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён',
            detail='Выбрали другого покупателя',
        )
        self.assertEqual(d['outcome_code'], 'lost')

    def test_not_redeemed_with_seller_wishes_blob(self):
        """Реальный кейс: title с «не выкупили», detail — пожелания/описание авто."""
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён Дата аукциона 22 июля 2026 Лот не выкупили',
            detail=(
                'Пожелания продавца 900 000 ₽ В трейд-ин: Обмен на авто с пробегом '
                'Про автомобиль Поколение:Mk6 (2008—2012) Кузов:Хетчбэк'
            ),
            blob='длинное описание без фразы итога',
        )
        self.assertEqual(d['outcome_code'], 'not_redeemed')

    def test_wishes_not_treated_as_waiting(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён',
            detail='Пожелания продавца 900 000 ₽',
        )
        # Без явного «ждём решения» не должно цепляться за «Пожелания»
        self.assertNotEqual(d['outcome_code'], 'waiting_seller')

    def test_we_refused(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(detail='Вы отказались от лота')
        self.assertEqual(d['outcome_code'], 'we_refused')

    def test_not_taken_to_work(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён Лот не взяли в работу Теперь лот доступен другим дилерам',
            detail='Пожелания продавца 300 000 ₽ Прогноз торга ~54 737 ₽ В трейд-ин: Обмен на авто с пробегом',
        )
        self.assertEqual(d['outcome_code'], 'not_taken')
        self.assertEqual(d['status_code'], 'finished')

    def test_not_processed_phrase(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён',
            detail='Лот не обработан',
        )
        self.assertEqual(d['outcome_code'], 'not_taken')
        self.assertEqual(d['status_code'], 'finished')

    def test_not_taken_in_win_notify_outcomes(self):
        from auction_avito.services.outcome import (
            OUTCOME_NOT_TAKEN,
            OUTCOME_WON,
            WIN_NOTIFY_OUTCOMES,
        )

        self.assertIn(OUTCOME_WON, WIN_NOTIFY_OUTCOMES)
        self.assertIn(OUTCOME_NOT_TAKEN, WIN_NOTIFY_OUTCOMES)

    def test_not_taken_compact_spaces(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён\u00a0Лот\u00a0не\u00a0взяли\u00a0в\u00a0работу',
        )
        self.assertEqual(d['outcome_code'], 'not_taken')

    def test_seller_canceled_auction(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершён Продавец отменил аукцион',
            detail='Пожелания продавца 100 000 ₽',
        )
        self.assertEqual(d['outcome_code'], 'canceled')
        self.assertEqual(d['status_code'], 'finished')

    def test_canceled_verb_forms(self):
        from auction_avito.services.outcome import classify_outcome_text

        for text in (
            'Продавец отменил аукцион',
            'Аукцион отменён',
            'Аукцион отменен продавцом',
        ):
            d = classify_outcome_text(detail=text)
            self.assertEqual(d['outcome_code'], 'canceled', text)

    def test_seller_chose_nobody(self):
        from auction_avito.services.outcome import classify_outcome_text

        d = classify_outcome_text(
            title='Аукцион завершен',
            detail='Продавец никого не выбрал',
        )
        self.assertEqual(d['outcome_code'], 'no_selection')
        self.assertEqual(d['status_code'], 'finished')
        self.assertIn('никого', d['outcome_detail'].lower())

    def test_final_outcomes_exclude_from_queue(self):
        from auction_avito.services.outcome import FINAL_OUTCOMES

        for code in (
            'not_redeemed', 'we_refused', 'not_taken',
            'no_selection', 'canceled', 'won', 'lost',
        ):
            self.assertIn(code, FINAL_OUTCOMES)
