"""Демо-данные для презентации клиентского пути (без привязки к БД)."""

from datetime import datetime, timedelta

from django.utils import timezone


def build_demo_context() -> dict:
    now = timezone.now()
    visit = now - timedelta(days=5)
    calc_date = now - timedelta(days=3)
    order_date = now - timedelta(days=2)
    transit_date = now - timedelta(days=1)

    return {
        'sales_rlk_id': None,
        'is_demo': True,
        'manager': {
            'name': 'Алексей Петров',
            'phone': '+7 (900) 123-45-67',
            'unit_name': 'KIA Корс Авто, Тверь',
            'unit_address': 'ул. Коминтерна, 95',
            'visit_date': visit,
        },
        'client': {
            'name': 'Иван Смирнов',
            'phone': '+7 (905) 555-12-34',
            'rlk_number': 'ОП-0001842',
            'rlk_date': visit,
        },
        'current_stage': 'В пути',
        'journey_stages': [
            {'key': 'visit', 'label': 'Визит в ДЦ', 'done': True, 'date': visit},
            {'key': 'selection', 'label': 'Подбор автомобиля', 'done': True, 'date': visit},
            {'key': 'calculation', 'label': 'Расчёт сделки', 'done': True, 'date': calc_date},
            {'key': 'trade_in', 'label': 'Trade-in', 'done': True, 'date': calc_date},
            {'key': 'agreement', 'label': 'Соглашение', 'done': True, 'date': order_date},
            {'key': 'delivery', 'label': 'Выдача', 'done': False, 'date': now + timedelta(days=4)},
        ],
        'car': {
            'title': 'Kia Sportage, IV',
            'vin': 'XWE***********4821',
            'year': 2025,
            'color': 'Серебристый',
            'price': 3_450_000,
            'complectation': '2.0 AT 4WD Prestige',
            'photo_url': '',
            'in_stock': False,
            'delivery_hint': 'Под заказ',
            'slug': '',
        },
        'order_timeline': [
            {'key': 'order_confirmed', 'label': 'Заказ подтверждён', 'done': True, 'date': order_date, 'note': ''},
            {'key': 'production', 'label': 'Производство / отгрузка', 'done': True, 'date': order_date + timedelta(hours=6), 'note': ''},
            {'key': 'in_transit', 'label': 'В пути', 'done': True, 'date': transit_date, 'note': 'Ориентир прибытия: 2 дня'},
            {'key': 'reception', 'label': 'Приёмка с автовоза', 'done': False, 'date': None, 'note': 'Фото появится после приёмки'},
            {'key': 'inspection', 'label': 'Осмотр на повреждения', 'done': False, 'date': None, 'note': ''},
            {'key': 'preparation', 'label': 'Подготовка к выдаче', 'done': False, 'date': None, 'note': 'Установка допоборудования'},
            {'key': 'ready', 'label': 'Готов к выдаче', 'done': False, 'date': now + timedelta(days=4), 'note': ''},
        ],
        'calculation': {
            'has_data': True,
            'calc_number': 'КР-2406-118',
            'calc_date': calc_date,
            'comment': 'Предложение действительно 7 дней',
            'lines': [
                {'label': 'Цена автомобиля', 'amount': 3_450_000, 'group': 'car'},
                {'label': 'Скидка', 'amount': -80_000, 'group': 'discount'},
                {'label': 'Trade-in (Hyundai Solaris)', 'amount': -1_850_000, 'group': 'tradein'},
                {'label': 'Коврики, защита картера', 'amount': 45_000, 'group': 'extra'},
                {'label': 'ОПФУ', 'amount': 120_000, 'group': 'opfu'},
                {'label': 'Гос. регистрация', 'amount': 3_500, 'group': 'service'},
                {'label': 'Итого к доплате', 'amount': 1_688_500, 'group': 'total', 'highlight': True},
            ],
        },
        'trade_ins': [
            {
                'vin': 'Z94***********9012',
                'title': 'Hyundai Solaris 2019',
                'status': 'Финальная оценка',
                'price_preliminary': 1_780_000,
                'price_final': 1_850_000,
                'current_stage': 'Финальная оценка',
                'stages': [
                    {'key': 'data', 'label': 'Данные получены', 'done': True},
                    {'key': 'pre', 'label': 'Предварительная оценка', 'done': True},
                    {'key': 'inspect', 'label': 'Осмотр', 'done': True},
                    {'key': 'final', 'label': 'Финальная оценка', 'done': True},
                    {'key': 'accepted', 'label': 'Принят в зачёт', 'done': False},
                ],
            }
        ],
        'extras': [
            {'name': 'Коврики', 'price': 12_000, 'status': 'Согласовано', 'status_code': 'agreed'},
            {'name': 'Защита картера', 'price': 18_000, 'status': 'Заказано', 'status_code': 'ordered'},
            {'name': 'Тонировка', 'price': 15_000, 'status': 'В работе', 'status_code': 'progress'},
            {'name': 'ОПФУ', 'price': 120_000, 'status': 'Согласовано', 'status_code': 'agreed'},
        ],
        'events': [
            {'date': visit, 'title': 'Визит в ДЦ', 'text': 'Обсудили Kia Sportage Prestige, trade-in Solaris', 'staff': 'Алексей Петров'},
            {'date': calc_date, 'title': 'Расчёт сделки', 'text': 'Отправлено коммерческое предложение', 'staff': 'Алексей Петров'},
            {'date': calc_date + timedelta(hours=2), 'title': 'Trade-in', 'text': 'Предварительная оценка: 1 780 000 ₽', 'staff': 'Отдел оценки'},
            {'date': order_date, 'title': 'Заказ подтверждён', 'text': 'Автомобиль заказан, ожидаем поставку', 'staff': 'Алексей Петров'},
            {'date': transit_date, 'title': 'Автомобиль в пути', 'text': 'Отгружен с завода, ориентир 2 дня', 'staff': 'Логистика'},
        ],
        'next_step': {
            'title': 'Ожидаем прибытие автомобиля',
            'text': 'Как только машина приедет на площадку, вы увидите фото приёмки и акт осмотра.',
            'date': now + timedelta(days=2),
            'actor': 'Алексей Петров',
        },
        'agreement': {
            'number': 'СП-0000921',
            'date': order_date,
            'planned_delivery': now + timedelta(days=4),
        },
    }
