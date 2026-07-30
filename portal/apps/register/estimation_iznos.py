"""Коррекция цены по повышенному износу и такси в расчёте оценки."""


def apply_iznos_taxi_correction(
    price,
    estimation,
    *,
    kf_auction,
    list_info_price,
    auction,
    auction_comment,
    auction_success,
    defer_iznos=False,
    after_ss=False,
):
    """
    Корректирует цену по повышенному износу / такси.

    defer_iznos: если True, блоки с estimation.iznos переносятся на after_ss.
    after_ss: применить отложенную коррекцию износа (после слесарного ремонта).
    """
    iznos_price = 0
    suffix = ' (после слесарного ремонта)' if after_ss else ''

    if after_ss:
        if not defer_iznos or not estimation.iznos:
            return price, iznos_price, auction, auction_comment, auction_success
        if estimation.taxi:
            price_new = price - (price * 40 / 100)
            diff = price - price_new
            price = price_new
            list_info_price.append({
                'price': price,
                'dif': diff,
                'comment': (
                    'Цена скоректирована c учетом повышенного износа и использования в такси'
                    + suffix
                ),
                'name': 'износ',
            })
            if estimation.auction_auto_no_user is not True:
                auction = True
                auction_comment = (
                    auction_comment
                    + 'Повышенный износ и использование в такси. Коэфицент 0.6. '
                )
                auction_success = True
        else:
            price_new = price - (price * 10 / 100)
            diff = price - price_new
            price = price_new
            list_info_price.append({
                'price': price,
                'dif': diff,
                'comment': 'Цена скоректирована c учетом повышенного износа' + suffix,
                'name': 'износ',
            })
            iznos_price = diff
        return price, iznos_price, auction, auction_comment, auction_success

    # Ранний этап (до слесарного ремонта)
    if defer_iznos and estimation.iznos:
        if estimation.taxi:
            pass
        else:
            return price, iznos_price, auction, auction_comment, auction_success

    if estimation.iznos and estimation.taxi:
        price_new = price - (price * 40 / 100)
        diff = price - price_new
        price = price_new
        list_info_price.append({
            'price': price,
            'dif': diff,
            'comment': 'Цена скоректирована c учетом повышенного износа и использования в такси',
            'name': 'износ',
        })
        if estimation.auction_auto_no_user is not True:
            auction = True
            auction_comment = (
                auction_comment + 'Повышенный износ и использование в такси. Коэфицент 0.6. '
            )
            auction_success = True
    elif estimation.iznos:
        price_new = price - (price * 10 / 100)
        diff = price - price_new
        price = price_new
        list_info_price.append({
            'price': price,
            'dif': diff,
            'comment': 'Цена скоректирована c учетом повышенного износа ',
            'name': 'износ',
        })
        iznos_price = diff
    elif estimation.taxi:
        price_new = price - (price * (100 - kf_auction) / 100)
        diff = price - price_new
        price = price_new
        list_info_price.append({
            'price': price,
            'dif': diff,
            'comment': 'Цена скоректирована c учетом использования в такси ',
            'name': 'износ',
        })
        iznos_price = diff
        if estimation.auction_auto_no_user is not True:
            auction = True
            auction_comment = auction_comment + 'Использование в такси. Коэфицент ' + str(kf_auction)
            auction_success = True

    return price, iznos_price, auction, auction_comment, auction_success
