# -*- coding: utf-8 -*-
"""Планируемые затраты оценки: подготовка, слесарка, кузовной участок."""
from register.models import (
    RegEstimationMCU,
    RegEstimationPodgotovka,
    RegEstimationSS,
    RegInteractivOcenka,
    RegInteractivOcenkaRLK,
)


def _db_row_to_dict(row):
    return {
        'id': row.id,
        'name': row.name or '',
        'normo': row.normo or 0,
        'price_podrad': row.price_podrad or 0,
        'price_kors': row.price_kors or 0,
        'materials_kf': row.materials_kf or 0,
        'materials_price': row.materials_price or 0,
        'materials_amount': row.materials_amount or 0,
    }


def _calc_item_to_dict(item):
    return {
        'name': item.get('name') or '',
        'normo': item.get('quantity') or item.get('normo') or 0,
        'price_podrad': item.get('amount_pod') or item.get('price_podrad') or 0,
        'price_kors': item.get('amount') or item.get('price_kors') or 0,
    }


def _sum_items(items):
    return sum((item.get('price_kors') or 0) for item in items)


def _load_saved_items(estimation_id):
    podgotovka = [
        _db_row_to_dict(row)
        for row in RegEstimationPodgotovka.objects.filter(estimation_id=estimation_id).order_by('id')
    ]
    ss = [
        _db_row_to_dict(row)
        for row in RegEstimationSS.objects.filter(estimation_id=estimation_id).order_by('id')
    ]
    mcu = [
        _db_row_to_dict(row)
        for row in RegEstimationMCU.objects.filter(estimation_id=estimation_id).order_by('id')
    ]
    return podgotovka, ss, mcu


def _recalculate_items(estimation):
    interactiv_rlk = RegInteractivOcenkaRLK.objects.filter(estimation_id=estimation.id).first()
    if not interactiv_rlk:
        return None
    from eco.views import estimations_price_calculation

    price_info = estimations_price_calculation(
        interactiv_rlk=interactiv_rlk,
        estimation=estimation,
        type_calculation='custom',
        persist=False,
    )
    if not price_info:
        return None
    return {
        'podgotovka': [_calc_item_to_dict(item) for item in price_info.get('list_work_podgotovka') or []],
        'ss': [_calc_item_to_dict(item) for item in price_info.get('list_work_service') or []],
        'mcu': [_calc_item_to_dict(item) for item in price_info.get('list_work_mcu') or []],
        'amount_podgotovka': price_info.get('amount_podgotovka') or 0,
        'amount_ss': price_info.get('amount_ss') or 0,
        'amount_mcu': price_info.get('amount_mcu') or 0,
    }


def _soglasovanie_amounts(estimation):
    sog = estimation.page_soglasovanie
    if sog is None:
        interactiv_rlk = RegInteractivOcenkaRLK.objects.filter(
            estimation_id=estimation.id,
        ).select_related('page_soglasovanie').first()
        if interactiv_rlk:
            sog = interactiv_rlk.page_soglasovanie
    if sog is None:
        return 0, 0, 0, 0
    podgotovka = sog.amount_podgotovka or 0
    ss = sog.amount_ss or 0
    mcu = sog.amount_mcu or 0
    recovery = sog.amount_recovery or 0
    if not recovery and any((podgotovka, ss, mcu)):
        recovery = podgotovka + ss + mcu
    return podgotovka, ss, mcu, recovery


def _resolve_totals(podgotovka_items, ss_items, mcu_items, sog_podgotovka, sog_ss, sog_mcu, sog_recovery):
    amount_podgotovka = _sum_items(podgotovka_items) if podgotovka_items else sog_podgotovka
    amount_ss = _sum_items(ss_items) if ss_items else sog_ss
    amount_mcu = _sum_items(mcu_items) if mcu_items else sog_mcu
    amount_recovery = sog_recovery or (amount_podgotovka + amount_ss + amount_mcu)
    return amount_podgotovka, amount_ss, amount_mcu, amount_recovery


def get_estimation_planned_costs(estimation_id, recalculate=False):
    """
    Планируемые затраты по id RegInteractivOcenka.

    :param estimation_id: id оценки
    :param recalculate: пересчитать через estimations_price_calculation
    :return: dict или None если оценка не найдена
    """
    estimation_rlk = RegInteractivOcenkaRLK.objects.filter(
        rlk__id=estimation_id,
    ).select_related('page_soglasovanie').first()
    
    estimation = estimation_rlk.estimation

    if not estimation:
        return None
    
    source = 'saved'
    podgotovka_items, ss_items, mcu_items = _load_saved_items(estimation_id)
    calc_amounts = None

    if recalculate or not any((podgotovka_items, ss_items, mcu_items)):
        calc = _recalculate_items(estimation)
        if calc:
            source = 'calculated'
            podgotovka_items = calc['podgotovka']
            ss_items = calc['ss']
            mcu_items = calc['mcu']
            calc_amounts = calc

    sog_podgotovka, sog_ss, sog_mcu, sog_recovery = _soglasovanie_amounts(estimation)
    if calc_amounts:
        sog_podgotovka = calc_amounts.get('amount_podgotovka') or sog_podgotovka
        sog_ss = calc_amounts.get('amount_ss') or sog_ss
        sog_mcu = calc_amounts.get('amount_mcu') or sog_mcu

    amount_podgotovka, amount_ss, amount_mcu, amount_recovery = _resolve_totals(
        podgotovka_items,
        ss_items,
        mcu_items,
        sog_podgotovka,
        sog_ss,
        sog_mcu,
        sog_recovery,
    )

    return {
        'estimation_id': estimation.id,
        'source': source,
        'totals': {
            'podgotovka': amount_podgotovka,
            'ss': amount_ss,
            'mcu': amount_mcu,
            'recovery': amount_recovery,
        },
        'sections': {
            'podgotovka': {
                'title': 'Подготовка',
                'amount': amount_podgotovka,
                'items': podgotovka_items,
            },
            'ss': {
                'title': 'Слесарка',
                'amount': amount_ss,
                'items': ss_items,
            },
            'mcu': {
                'title': 'Кузовной участок',
                'amount': amount_mcu,
                'items': mcu_items,
            },
        },
    }
