"""
Расчёт интерактивной оценки для РЛ с аукциона Avito.

Изначальные коэффициенты и шаги совпадают с оценкой лота (/api/calculate_car/):
ЦНА → износ (>175к) → ТХТ (настройки аукциона) → защита СС → торг →
финансирование (РДО) → комиссия Авито → риск Автотеки (−40%).

Отдельная функция: не путать с type_calculation='avito' (рынок Автотеки).
"""
from __future__ import annotations

from typing import Any, Optional


def _dc_percents_for_zg(dc, zg: str) -> dict[str, float]:
    """percent_ss / percent_torg / sale-каналы по ЦГ — как в calculate_car."""
    mapping = {
        '200': ('markup_txt_200', 'percent_txt_200', 'max_discount_bargain_percent_200', 'percent_torg_txt_200',
                'correction_test_1c_200', 'ratio_1с_test_price_200',
                'correction_test_200', 'ratio_avtohub_test_price_200',
                'correction_rdo_200', 'ratio_avtohub_rdo_200',
                'correction_kor_200', 'ratio_avtohub_kor_200'),
        '400': ('markup_txt_400', 'percent_txt_400', 'max_discount_bargain_percent_400', 'percent_torg_txt_400',
                'correction_test_1c_400', 'ratio_1с_test_price_400',
                'correction_test_400', 'ratio_avtohub_test_price_400',
                'correction_rdo_400', 'ratio_avtohub_rdo_400',
                'correction_kor_400', 'ratio_avtohub_kor_400'),
        '700': ('markup_txt_700', 'percent_txt_700', 'max_discount_bargain_percent_700', 'percent_torg_txt_700',
                'correction_test_1c_700', 'ratio_1с_test_price_700',
                'correction_test_700', 'ratio_avtohub_test_price_700',
                'correction_rdo_700', 'ratio_avtohub_rdo_700',
                'correction_kor_700', 'ratio_avtohub_kor_700'),
        '1 200': ('markup_txt_1200', 'percent_txt_1200', 'max_discount_bargain_percent_1200', 'percent_torg_txt_1200',
                  'correction_test_1c_1200', 'ratio_1с_test_price_1200',
                  'correction_test_1200', 'ratio_avtohub_test_price_1200',
                  'correction_rdo_1200', 'ratio_avtohub_rdo_1200',
                  'correction_kor_1200', 'ratio_avtohub_kor_1200'),
        '2 000': ('markup_txt_2000', 'percent_txt_2000', 'max_discount_bargain_percent_2000', 'percent_torg_txt_2000',
                  'correction_test_1c_2000', 'ratio_1с_test_price_2000',
                  'correction_test_2000', 'ratio_avtohub_test_price_2000',
                  'correction_rdo_2000', 'ratio_avtohub_rdo_2000',
                  'correction_kor_2000', 'ratio_avtohub_kor_2000'),
        '3 000': ('markup_txt_3000', 'percent_txt_3000', 'max_discount_bargain_percent_3000', 'percent_torg_txt_3000',
                  'correction_test_1c_3000', 'ratio_1с_test_price_3000',
                  'correction_test_3000', 'ratio_avtohub_test_price_3000',
                  'correction_rdo_3000', 'ratio_avtohub_rdo_3000',
                  'correction_kor_3000', 'ratio_avtohub_kor_3000'),
        '5 000': ('markup_txt_5000', 'percent_txt_5000', 'max_discount_bargain_percent_5000', 'percent_torg_txt_5000',
                  'correction_test_1c_5000', 'ratio_1с_test_price_5000',
                  'correction_test_5000', 'ratio_avtohub_test_price_5000',
                  'correction_rdo_5000', 'ratio_avtohub_rdo_5000',
                  'correction_kor_5000', 'ratio_avtohub_kor_5000'),
        '5 000+': ('markup_txt_5001', 'percent_txt_5001', 'max_discount_bargain_percent_5001', 'percent_torg_txt_5001',
                   'correction_test_1c_5001', 'ratio_1с_test_price_5001',
                   'correction_test_5001', 'ratio_avtohub_test_price_5001',
                   'correction_rdo_5001', 'ratio_avtohub_rdo_5001',
                   'correction_kor_5001', 'ratio_avtohub_kor_5001'),
    }
    keys = mapping.get(zg)
    if not keys or dc is None:
        return {
            'percent_ss': 0.0,
            'percent_torg': 0.0,
            'percent_sale': 100.0,
            'percent_sale_rdo': 100.0,
            'percent_sale_kor': 100.0,
        }

    def _pick(primary, fallback, default=0.0):
        val = getattr(dc, primary, None)
        if val not in (None, 0):
            return float(val)
        val = getattr(dc, fallback, None)
        if val not in (None, 0):
            return float(val)
        return float(default)

    return {
        'percent_ss': _pick(keys[0], keys[1], 0),
        'percent_torg': _pick(keys[2], keys[3], 0),
        'percent_sale': _pick(keys[6], keys[7], 100),
        'percent_sale_rdo': _pick(keys[8], keys[9], 100),
        'percent_sale_kor': _pick(keys[10], keys[11], 100),
    }


def compute_avito_auction_lot_formula(
    *,
    zna: float,
    run: float = 0,
    dc=None,
    auction_settings=None,
    autoteka_risk: bool = False,
    autoteka_risk_note: str = '',
) -> Optional[dict[str, Any]]:
    """
    Чистая формула выкупа лота Avito (без Maxposter).
    Возвращает dict совместимый с answer calculate_car / estimations_price_calculation.
    """
    from auction_avito.models import AvitoAuctionSettings
    from auction_avito.services.auction_calc_settings import (
        resolve_avito_commission_amount,
        resolve_txt_kf_info,
        zg_from_zna,
    )
    from refs.price_group_stage_days import get_rdo_days_to
    from refs.price_groups import price_group_code as _price_group_code

    try:
        zna = float(zna or 0)
    except (TypeError, ValueError):
        zna = 0.0
    if zna <= 0:
        return None

    try:
        run = float(run or 0)
    except (TypeError, ValueError):
        run = 0.0

    if auction_settings is None:
        auction_settings = AvitoAuctionSettings.get_solo()

    if dc is None:
        from refs.models import RefUnit
        dc = RefUnit.objects.filter(pk=90).first()

    zg = zg_from_zna(zna)
    percents = _dc_percents_for_zg(dc, zg)
    percent_ss = percents['percent_ss']
    percent_torg = percents['percent_torg']
    percent_sale = percents['percent_sale']
    percent_sale_rdo = percents['percent_sale_rdo']
    percent_sale_kor = percents['percent_sale_kor']

    kf, kf_source = resolve_txt_kf_info(zg, auction_settings, dc=dc)

    fin_all = 25
    day_sale_all = 90
    rdo_days = get_rdo_days_to(_price_group_code(zg) or zg)
    if rdo_days > 0:
        day_sale_all = rdo_days

    if percent_torg < 0:
        percent_torg = percent_torg * -1
    if percent_ss < 0:
        percent_ss = percent_ss * -1

    list_info_price: list[dict] = []
    zachita_ot_ubitka = 0
    finance_price = 0
    iznos_price = 0
    discount_torg = 0
    avito_commission_amount = 0
    auction = False

    price = zna

    if run > 175000:
        price_new = price - (price * 10 / 100)
        diff = price - price_new
        price = price_new
        iznos_price = diff
        list_info_price.append({
            'price': price,
            'dif': diff,
            'comment': 'Цена скоректирована c учетом повышенного износа',
            'name': 'износ',
        })

    price_sale = price * percent_sale / 100
    price_sale_rdo = price * percent_sale_rdo / 100
    price_sale_kor = price * percent_sale_kor / 100

    price_old = price
    price = price - (price * (100 - kf) / 100)
    diff = (price_old * (100 - kf) / 100)
    list_info_price.append({
        'price': price,
        'dif': diff,
        'comment': (
            'ЦНА × ТХТ {kf}% ({src}, ЦГ {zg}) / цена с учетом продажи в токсичном стоке'
            .format(kf=kf, src=kf_source, zg=zg)
        ),
        'name': 'цена в токсичной продаже',
    })

    price_old = price
    price = price - (price * percent_ss / 100)
    diff = (price_old * percent_ss / 100)
    zachita_ot_ubitka = diff
    list_info_price.append({
        'price': price,
        'dif': diff,
        'comment': 'Цена с учетом защиты от убытка CC ' + str(percent_ss) + ' %',
        'name': 'защита от убытка',
    })

    price_old = price
    price = price - (price * percent_torg / 100)
    diff = (price_old * percent_torg / 100)
    discount_torg = diff
    list_info_price.append({
        'price': price,
        'dif': diff,
        'comment': 'Цена с учетом защиты скидки торг ' + str(percent_torg) + ' %',
        'name': 'скидка торг',
    })

    finance = round(price * ((fin_all / 365) / 100) * day_sale_all, 2)
    price = price - finance
    finance_price = finance
    list_info_price.append({
        'price': price,
        'dif': finance,
        'comment': (
            'Финансирование ' + str(fin_all) + '% для продажи авто за '
            + str(round(day_sale_all)) + ' дн. (по этапу РДО, ЦГ ' + str(zg) + ')'
        ),
        'name': 'финансирование',
    })

    avito_commission_info = resolve_avito_commission_amount(price, auction_settings)
    avito_commission_amount = avito_commission_info['total']
    if avito_commission_amount > 0:
        price = price - avito_commission_amount
        comment_parts = []
        if avito_commission_info['fixed'] > 0:
            comment_parts.append('{0} ₽'.format(avito_commission_info['fixed']))
        if avito_commission_info['percent'] > 0:
            comment_parts.append(
                '{pct:g}% = {amt} ₽'.format(
                    pct=avito_commission_info['percent'],
                    amt=avito_commission_info['percent_amount'],
                )
            )
        list_info_price.append({
            'price': price,
            'dif': avito_commission_amount,
            'comment': 'Комиссия Авито ' + ' + '.join(comment_parts),
            'name': 'комиссия Авито',
        })

    if autoteka_risk:
        auction = True
        price_new = price - (price * 40 / 100)
        diff = price - price_new
        price = price_new
        list_info_price.append({
            'price': price,
            'dif': diff,
            'comment': 'Цена скоректирована аукцион: ' + (autoteka_risk_note or 'риск Автотеки'),
            'name': 'пробег',
        })

    estimation_price = round(price, -2)
    profit = round(price_sale - price, -2)

    return {
        'profit': profit,
        'hub_sale_price_avg': zna,
        'hub_price_avg': day_sale_all,
        'zna': zna,
        'zna_type': 'Аукцион Avito',
        'estimation_price': estimation_price,
        'zg': zg,
        'kf': kf,
        'kf_source': kf_source,
        'kors_price_correction_sale': 0,
        'list_info_price': list_info_price,
        'sale': price_sale,
        'price_sale': price_sale,
        'price_sale_rdo': price_sale_rdo,
        'price_sale_kor': price_sale_kor,
        'cna_expenses': zna,
        'zachita_ot_ubitka': zachita_ot_ubitka,
        'finance_price': finance_price,
        'iznos_price': iznos_price,
        'discount_torg': discount_torg,
        'avito_commission': avito_commission_amount,
        'auction': auction,
        'calc_source': 'avito_auction',
    }


def estimations_price_calculation_avito_auction(
    interactiv_rlk,
    estimation,
    *,
    offer=None,
    avito_ctx=None,
    persist: bool = False,
    user=None,
) -> Optional[dict[str, Any]]:
    """
    Расчёт ИО для РЛ аукциона Avito.

    ЦНА приоритет:
      1) последний успешный расчёт лота (calc.zna)
      2) estimation.hub_avg / custom_zna / avito_price
    Пробег: salon/remote/lot vehicle.
    Риск Автотеки: с расчёта лота (auction_risk).
    """
    from auction_avito.services.estimation_context import (
        build_avito_auction_estimation_context,
        get_avito_offer_for_rlk,
    )

    doc_rlk = getattr(interactiv_rlk, 'rlk', None) if interactiv_rlk is not None else None
    if doc_rlk is None and estimation is not None:
        doc_rlk = getattr(estimation, 'rlk', None)

    if avito_ctx is None:
        avito_ctx = build_avito_auction_estimation_context(doc_rlk)
    if avito_ctx is None and offer is None:
        offer = get_avito_offer_for_rlk(doc_rlk)
        if offer is None:
            return None
        avito_ctx = build_avito_auction_estimation_context(doc_rlk)
    if avito_ctx is None:
        return None

    calc = avito_ctx.get('calc')
    zna = 0.0
    if calc is not None and calc.zna:
        zna = float(calc.zna)
    elif estimation is not None:
        for attr in ('hub_avg', 'custom_zna', 'avito_price_avg_market_price', 'hub_avg_k'):
            val = getattr(estimation, attr, None) or 0
            try:
                if float(val) > 0:
                    zna = float(val)
                    break
            except (TypeError, ValueError):
                continue

    run = 0.0
    if estimation is not None:
        if estimation.page_salon is not None and estimation.page_salon.run:
            run = estimation.page_salon.run
        elif estimation.page_remote is not None and estimation.page_remote.run:
            run = estimation.page_remote.run
    if not run:
        hints = avito_ctx.get('vehicle_hints') or {}
        run = hints.get('mileage') or 0

    dc = None
    if interactiv_rlk is not None and interactiv_rlk.unit_id:
        dc = interactiv_rlk.unit
    elif avito_ctx.get('lot') and getattr(avito_ctx['lot'], 'venue', None):
        dc = avito_ctx['lot'].venue.unit

    autoteka_risk = bool(calc.auction_risk) if calc is not None else False
    autoteka_risk_note = (calc.auction_risk_note if calc is not None else '') or ''

    result = compute_avito_auction_lot_formula(
        zna=zna,
        run=run,
        dc=dc,
        autoteka_risk=autoteka_risk,
        autoteka_risk_note=autoteka_risk_note,
    )
    if result is None:
        return None

    result['winning_bid'] = avito_ctx.get('bid')
    result['lot_id'] = avito_ctx['lot'].pk if avito_ctx.get('lot') else None
    result['lot_calc_estimation_price'] = avito_ctx.get('estimation_price')

    if persist and interactiv_rlk is not None:
        sog = getattr(interactiv_rlk, 'page_soglasovanie', None)
        if sog is None and estimation is not None:
            sog = getattr(estimation, 'page_soglasovanie', None)
        if sog is not None:
            # Стартовый авторасчёт Avito-аукциона кладём в price_auto_2 (как основной ЦНА-канал).
            sog.price_auto_2 = int(result['estimation_price'] or 0)
            sog.zachita_ot_ubitka = float(result.get('zachita_ot_ubitka') or 0)
            sog.finance_price = float(result.get('finance_price') or 0)
            sog.discount_torg = float(result.get('discount_torg') or 0)
            update_fields = [
                'price_auto_2', 'zachita_ot_ubitka', 'finance_price', 'discount_torg',
            ]
            sog.save(update_fields=update_fields)

    return result
