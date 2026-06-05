"""
Сборка клиентского пути покупки на основе рабочего листа (DocRLK).

Основа: РЛК отдела продаж → калькуляции → trade-in (дочерние eco-РЛК) →
соглашение → отгрузка.
"""

from datetime import datetime
from typing import List, Optional

from django.utils import timezone

from documents.models import DocCarAgreement, DocCarShipment, DocLO, DocRLK, DocRLKEvents
from prices_car.models import CarCalculations, CarCalculationsDetail
ORDER_STAGES = (
    ('order_confirmed', 'Заказ подтверждён'),
    ('production', 'Производство / отгрузка'),
    ('in_transit', 'В пути'),
    ('reception', 'Приёмка с автовоза'),
    ('inspection', 'Осмотр на повреждения'),
    ('preparation', 'Подготовка к выдаче'),
    ('ready', 'Готов к выдаче'),
)


def _resolve_sales_rlk(rlk: DocRLK) -> DocRLK:
    """Основной РЛК продаж (не eco-дочерний)."""
    if rlk.eco and rlk.footing_id:
        return rlk.footing
    return rlk


def _trade_in_rlks(sales_rlk: DocRLK):
    return DocRLK.objects.filter(footing=sales_rlk, eco=True).select_related(
        'reginteractivocenkarlk__status',
        'reginteractivocenkarlk__estimation__modification__model__mark',
    )


def _primary_calculation(sales_rlk: DocRLK) -> Optional[CarCalculations]:
    return (
        CarCalculations.objects.filter(rlk=sales_rlk)
        .select_related('car', 'car__modification_autoru__model__mark', 'unit')
        .order_by('-date')
        .first()
    )


def _agreement(sales_rlk: DocRLK) -> Optional[DocCarAgreement]:
    return (
        DocCarAgreement.objects.filter(rlk=sales_rlk, active=True)
        .order_by('-dataTime')
        .first()
    )


def _shipment(sales_rlk: DocRLK) -> Optional[DocCarShipment]:
    return (
        DocCarShipment.objects.filter(rlk=sales_rlk, active=True)
        .order_by('-dataTime')
        .first()
    )


def _manager_card(rlk: DocRLK) -> dict:
    staff = rlk.staff
    unit = rlk.unit_dc or rlk.unit
    return {
        'name': staff.name if staff else 'Менеджер',
        'phone': staff.phone if staff and getattr(staff, 'phone', None) else rlk.phone,
        'unit_name': unit.name if unit else '—',
        'unit_address': getattr(unit, 'adress', '') or getattr(unit, 'address', '') if unit else '',
        'visit_date': rlk.dataTime,
    }


def _client_card(rlk: DocRLK) -> dict:
    return {
        'name': rlk.clientName or 'Клиент',
        'phone': rlk.phone or '',
        'rlk_number': rlk.nomer,
        'rlk_date': rlk.dataTime,
    }


def _car_from_calculation(calc: CarCalculations) -> Optional[dict]:
    car = calc.car
    if not car:
        return None
    mod = car.modification_autoru
    title = car.name or ''
    if mod and mod.model_id:
        mark = mod.model.mark.name if mod.model.mark_id else ''
        model = mod.model.name
        title = title or f'{mark} {model}'.strip()
    photo = ''
    try:
        photo = car.get_photo() or car.get_photo_mini() or ''
    except Exception:
        pass
    in_stock = (car.quantity or 0) > 0
    return {
        'title': title or 'Автомобиль',
        'vin': car.vin or '',
        'year': car.year,
        'color': car.color or '',
        'price': calc.price or car.price,
        'complectation': (
            car.complectation_autoru.name
            if car.complectation_autoru_id
            else (mod.name if mod else '')
        ),
        'photo_url': photo,
        'in_stock': in_stock,
        'delivery_hint': 'Из наличия' if in_stock else 'Под заказ',
        'slug': car.slug,
    }


def _trade_in_blocks(sales_rlk: DocRLK) -> List[dict]:
    blocks = []
    for ti_rlk in _trade_in_rlks(sales_rlk):
        est_rlk = getattr(ti_rlk, 'reginteractivocenkarlk', None)
        est = est_rlk.estimation if est_rlk else None
        sog = est_rlk.page_soglasovanie if est_rlk else None
        lo = DocLO.objects.filter(rlk=ti_rlk, active=True).order_by('-dataTime').first()

        price_pre = sog.price_before_kd if sog else 0
        price_final = sog.price_after_kd if sog and sog.price_after_kd else price_pre

        stages = [
            {'key': 'data', 'label': 'Данные получены', 'done': bool(est)},
            {'key': 'pre', 'label': 'Предварительная оценка', 'done': bool(price_pre)},
            {'key': 'inspect', 'label': 'Осмотр', 'done': bool(sog and (sog.comment_diagnostica or sog.no_diagnostica))},
            {'key': 'final', 'label': 'Финальная оценка', 'done': bool(price_final)},
            {'key': 'accepted', 'label': 'Принят в зачёт', 'done': bool(lo and lo.active)},
        ]

        title = ti_rlk.tradeInModel or ti_rlk.estimation_modification_info() or 'Ваш автомобиль'
        blocks.append({
            'vin': ti_rlk.vin_trade_in or (est.vin if est else ''),
            'title': title,
            'status': ti_rlk.estimation_status() or 'В работе',
            'price_preliminary': price_pre,
            'price_final': price_final,
            'stages': stages,
            'current_stage': next((s['label'] for s in reversed(stages) if s['done']), 'Ожидаем данные'),
        })
    return blocks


def _calculation_block(calc: Optional[CarCalculations], agreement: Optional[DocCarAgreement]) -> dict:
    if not calc and not agreement:
        return {'has_data': False}

    lines = []
    if calc:
        if calc.price:
            lines.append({'label': 'Цена автомобиля', 'amount': calc.price, 'group': 'car'})
        if calc.discount:
            lines.append({'label': 'Скидка', 'amount': -abs(calc.discount), 'group': 'discount'})
        if calc.custom_tradein:
            lines.append({'label': 'Trade-in', 'amount': -abs(calc.custom_tradein), 'group': 'tradein'})
        if calc.custom_product:
            lines.append({'label': 'Допоборудование', 'amount': calc.custom_product, 'group': 'extra'})
        if calc.custom_work:
            lines.append({'label': 'Работы / установка', 'amount': calc.custom_work, 'group': 'extra'})
        if calc.custom_wheels:
            lines.append({'label': 'Колёса', 'amount': calc.custom_wheels, 'group': 'extra'})
        if calc.custom_grz:
            lines.append({'label': 'Гос. регистрация', 'amount': calc.custom_grz, 'group': 'service'})
        if calc.custom_opfu:
            lines.append({'label': 'ОПФУ', 'amount': calc.custom_opfu, 'group': 'opfu'})
        if calc.amount:
            lines.append({'label': 'Итого', 'amount': calc.amount, 'group': 'total', 'highlight': True})

        for detail in CarCalculationsDetail.objects.filter(calculation=calc).select_related('detail_type'):
            if detail.amount and detail.detail_type:
                lines.append({
                    'label': detail.detail_type.name,
                    'amount': detail.amount,
                    'group': 'detail',
                    'applied': detail.success,
                })

    if agreement:
        if agreement.discountAmountTradeIN:
            lines.append({
                'label': 'Trade-in (соглашение)',
                'amount': -abs(agreement.discountAmountTradeIN),
                'group': 'tradein',
            })
        if agreement.amount:
            lines.append({
                'label': 'Сумма соглашения',
                'amount': int(agreement.amount),
                'group': 'total',
                'highlight': True,
            })

    return {
        'has_data': bool(lines),
        'lines': lines,
        'comment': calc.comment if calc else '',
        'calc_number': calc.number if calc else '',
        'calc_date': calc.date if calc else None,
    }


def _extras_from_calc(calc: Optional[CarCalculations]) -> List[dict]:
    if not calc:
        return []
    extras = []
    mapping = (
        ('custom_product', 'Товары / допоборудование'),
        ('custom_work', 'Работы / установка'),
        ('custom_wheels', 'Колёса'),
        ('custom_grz', 'Гос. регистрация'),
        ('custom_opfu', 'ОПФУ'),
    )
    for field, label in mapping:
        val = getattr(calc, field, 0) or 0
        if val:
            extras.append({
                'name': label,
                'price': val,
                'status': 'Согласовано',
                'status_code': 'agreed',
            })
    return extras


def _order_timeline(car: Optional[dict], agreement: Optional[DocCarAgreement], shipment: Optional[DocCarShipment]) -> List[dict]:
    if not car or car.get('in_stock'):
        return []

    now = timezone.now()
    planned = agreement.date_planed_sale if agreement else None
    stages = []
    for key, label in ORDER_STAGES:
        done = False
        date = None
        note = ''
        if key == 'order_confirmed' and agreement:
            done = True
            date = agreement.dataTime
        elif key == 'ready' and shipment and shipment.active:
            done = True
            date = shipment.dataTime
        elif key == 'preparation' and agreement and planned and planned <= now:
            done = True
            date = planned
        stages.append({
            'key': key,
            'label': label,
            'done': done,
            'date': date,
            'note': note,
        })
    return stages


def _journey_stages(sales_rlk, calc, agreement, shipment, trade_ins, car) -> List[dict]:
    stages = [
        {
            'key': 'visit',
            'label': 'Визит в ДЦ',
            'done': True,
            'date': sales_rlk.dataTime,
        },
        {
            'key': 'selection',
            'label': 'Подбор автомобиля',
            'done': bool(calc or car),
            'date': calc.date if calc else None,
        },
        {
            'key': 'calculation',
            'label': 'Расчёт сделки',
            'done': bool(calc),
            'date': calc.date if calc else None,
        },
        {
            'key': 'trade_in',
            'label': 'Trade-in',
            'done': bool(trade_ins),
            'date': None,
        },
        {
            'key': 'agreement',
            'label': 'Соглашение',
            'done': bool(agreement),
            'date': agreement.dataTime if agreement else None,
        },
        {
            'key': 'delivery',
            'label': 'Выдача',
            'done': bool(shipment and shipment.active),
            'date': shipment.dataTime if shipment else None,
        },
    ]
    return stages


def _current_stage_label(stages: List[dict]) -> str:
    for stage in reversed(stages):
        if stage['done']:
            return stage['label']
    return stages[0]['label'] if stages else 'Визит в ДЦ'


def _events_feed(sales_rlk: DocRLK) -> List[dict]:
    feed = []
    for ev in DocRLKEvents.objects.filter(rlk=sales_rlk).order_by('-dataTime')[:20]:
        feed.append({
            'date': ev.dataTime,
            'title': (ev.contacType.name if ev.contacType_id else 'Событие'),
            'text': ev.comment or '',
            'staff': ev.staff.name if ev.staff_id else '',
        })
    return feed


def _next_step(sales_rlk, calc, agreement, shipment, trade_ins, car) -> dict:
    if shipment and shipment.active:
        return {
            'title': 'Автомобиль выдан',
            'text': 'Спасибо за покупку! Мы на связи по вопросам сервиса.',
            'date': shipment.dataTime,
            'actor': sales_rlk.staff.name if sales_rlk.staff_id else '',
        }
    if agreement and not (shipment and shipment.active):
        dt = agreement.date_planed_sale
        return {
            'title': 'Ожидаем выдачу',
            'text': 'Соглашение оформлено. Готовим автомобиль к передаче.',
            'date': dt,
            'actor': sales_rlk.staff.name if sales_rlk.staff_id else '',
        }
    if calc and not agreement:
        return {
            'title': 'Согласование расчёта',
            'text': 'Проверьте предложение и свяжитесь с менеджером для финализации.',
            'date': calc.date,
            'actor': sales_rlk.staff.name if sales_rlk.staff_id else '',
        }
    if trade_ins and not calc:
        return {
            'title': 'Оценка trade-in',
            'text': 'Завершаем оценку вашего автомобиля для расчёта сделки.',
            'date': None,
            'actor': sales_rlk.staff.name if sales_rlk.staff_id else '',
        }
    return {
        'title': 'Подбор автомобиля',
        'text': 'Менеджер подготовит для вас варианты и расчёт.',
        'date': sales_rlk.dataTime,
        'actor': sales_rlk.staff.name if sales_rlk.staff_id else '',
    }


def build_journey_context(rlk: DocRLK) -> dict:
    """Контекст клиентского пути по рабочему листу."""
    sales_rlk = _resolve_sales_rlk(rlk)
    calc = _primary_calculation(sales_rlk)
    agreement = _agreement(sales_rlk)
    shipment = _shipment(sales_rlk)
    trade_ins = _trade_in_blocks(sales_rlk)
    car = _car_from_calculation(calc) if calc else None
    stages = _journey_stages(sales_rlk, calc, agreement, shipment, trade_ins, car)

    return {
        'sales_rlk_id': sales_rlk.pk,
        'manager': _manager_card(sales_rlk),
        'client': _client_card(sales_rlk),
        'current_stage': _current_stage_label(stages),
        'journey_stages': stages,
        'car': car,
        'order_timeline': _order_timeline(car, agreement, shipment),
        'calculation': _calculation_block(calc, agreement),
        'trade_ins': trade_ins,
        'extras': _extras_from_calc(calc),
        'events': _events_feed(sales_rlk),
        'next_step': _next_step(sales_rlk, calc, agreement, shipment, trade_ins, car),
        'agreement': {
            'number': agreement.nomer if agreement else '',
            'date': agreement.dataTime if agreement else None,
            'planned_delivery': agreement.date_planed_sale if agreement else None,
        } if agreement else None,
        'is_demo': False,
    }
