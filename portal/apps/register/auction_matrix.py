"""Матрица наценки БЦП для экспресс-аукциона."""
from register.models import SettingsMatrixAuction


def _get_settings_matrix():
    return SettingsMatrixAuction.objects.get(pk=1)


def charge_bcp_for_price(client_price):
    """
    Наценка по матрице и стартовая цена экспресс-лота.
    client_price — цена клиента (желание по продаже).
    """
    client_price = int(client_price or 0)
    settings = _get_settings_matrix()

    if client_price < 200_000:
        charge = settings.charge_bcp_200
        price_group = '200'
    elif client_price < 400_000:
        charge = settings.charge_bcp_400
        price_group = '400'
    elif client_price < 700_000:
        charge = settings.charge_bcp_700
        price_group = '700'
    elif client_price < 1_200_000:
        charge = settings.charge_bcp_1200
        price_group = '1 200'
    elif client_price < 2_000_000:
        charge = settings.charge_bcp_2000
        price_group = '2 000'
    elif client_price < 3_000_000:
        charge = settings.charge_bcp_3000
        price_group = '3 000'
    elif client_price < 5_000_000:
        charge = settings.charge_bcp_5000
        price_group = '5 000'
    else:
        charge = settings.charge_bcp_5001
        price_group = '5 000+'

    charge = int(charge or 0)
    return {
        'client_price': client_price,
        'matrix_charge': charge,
        'price_group': price_group,
        'auction_start_price': client_price + charge,
    }
