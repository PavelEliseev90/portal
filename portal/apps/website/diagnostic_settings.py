"""Настройки диагностики по ценовым группам (справочник RefGroupPrice)."""
from refs.price_groups import get_active_price_group_codes, get_active_price_groups

SECTION_TITLES = {
    'warning': 'Предупреждение',
    'danger': 'Опасность',
}


def _kf_min_fields(prefix):
    return [
        {'base': '{}_warning_kf'.format(prefix), 'label': '% понижения от оценки'},
        {'base': '{}_warning_amount_min'.format(prefix), 'label': 'Мин. сумма'},
    ]


def _danger_kf_min_fields(prefix):
    return [
        {'base': '{}_danger_kf'.format(prefix), 'label': '% понижения от оценки'},
        {'base': '{}_danger_amount_min'.format(prefix), 'label': 'Мин. сумма'},
    ]


def _warn_danger_card(title, prefix):
    return {
        'title': title,
        'sections': [
            {
                'level': 'warning',
                'title': SECTION_TITLES['warning'],
                'fields': _kf_min_fields(prefix),
            },
            {
                'level': 'danger',
                'title': SECTION_TITLES['danger'],
                'fields': _danger_kf_min_fields(prefix),
            },
        ],
    }


def _danger_amount_card(title, base):
    return {
        'title': title,
        'plain_fields': [
            {
                'base': base,
                'label': 'Мин. сумма опасность',
                'input_class': 'bg-danger bg-opacity-25',
            },
        ],
    }


DIAGNOSTIC_CARD_DEFINITIONS = [
    _warn_danger_card('Двигатель (Бензин)', 'engine'),
    _warn_danger_card('Двигатель (Дизель)', 'engine_dt'),
    _warn_danger_card('Коробка передач (Автомат - АТ)', 'gear_at'),
    _warn_danger_card('Коробка передач (Робот - АМТ)', 'gear_amt'),
    _warn_danger_card('Коробка передач (Вариатор - CVT)', 'gear_cvt'),
    _warn_danger_card('Коробка передач (Механика - MT)', 'gear_mt'),
    _warn_danger_card('Подвеска', 'suspension'),
    _warn_danger_card('Система выпука ОГ', 'system_og'),
    _warn_danger_card('Система кондиционирования', 'conditioner'),
    _warn_danger_card('Турбокомпрессор', 'turbo'),
    _warn_danger_card('Привод', 'drive'),
    _warn_danger_card('Рулевое управление', 'wheel'),
    _warn_danger_card('Тормозная система', 'brake'),
    _warn_danger_card('Подрамник', 'subframe'),
    {
        'title': 'Техническое обслуживание (ТО)',
        'plain_fields': [
            {'base': 'to_1', 'label': 'ТО 1', 'input_class': ''},
            {'base': 'to_2', 'label': 'ТО 2', 'input_class': ''},
            {'base': 'to_3', 'label': 'ТО 3', 'input_class': ''},
        ],
    },
    _danger_amount_card('Подушка водителя', 'airbag_driver_danger_amount_min'),
    _danger_amount_card('Подушка пассажира + перешив торпеды', 'airbag_passenger_danger_amount_min'),
    _danger_amount_card('Боковые подушки', 'airbag_side_danger_amount_min'),
    _danger_amount_card('Подушка коленная', 'airbag_knee_danger_amount_min'),
    _danger_amount_card('Восстановление ремней безопасности', 'seat_belt_restore_danger_amount_min'),
    _warn_danger_card('Блок SRS', 'srs_block'),
]


def diagnostic_field_name(field_base, price_group_code):
    return '{}_{}'.format(field_base, price_group_code)


def _legacy_field_exists(settings, field_name):
    return settings is not None and hasattr(settings, field_name)


def get_diagnostic_field_value(settings, field_base, price_group_code, default=0):
    if settings is None:
        return default
    field_name = diagnostic_field_name(field_base, price_group_code)
    if _legacy_field_exists(settings, field_name):
        value = getattr(settings, field_name)
        return default if value is None else value
    extra = getattr(settings, 'diagnostic_extra_by_price_group', None) or {}
    group_data = extra.get(str(price_group_code), {})
    if field_base in group_data:
        value = group_data[field_base]
        return default if value is None else value
    return default


def set_diagnostic_field_value(settings, field_base, price_group_code, value):
    field_name = diagnostic_field_name(field_base, price_group_code)
    if _legacy_field_exists(settings, field_name):
        setattr(settings, field_name, value)
        return
    extra = dict(getattr(settings, 'diagnostic_extra_by_price_group', None) or {})
    group_data = dict(extra.get(str(price_group_code), {}))
    group_data[field_base] = value
    extra[str(price_group_code)] = group_data
    settings.diagnostic_extra_by_price_group = extra


def iter_diagnostic_field_bases():
    seen = set()
    for card in DIAGNOSTIC_CARD_DEFINITIONS:
        for section in card.get('sections', []):
            for field in section.get('fields', []):
                seen.add(field['base'])
        for field in card.get('plain_fields', []):
            seen.add(field['base'])
    return sorted(seen)


def format_price_group_subtitle(price_group):
    min_p = price_group.min_price_rub or 0
    max_p = price_group.max_price_rub
    if max_p is None:
        return 'от {:,.0f} ₽'.format(min_p).replace(',', ' ')
    return '{:,.0f} – {:,.0f} ₽'.format(min_p, max_p).replace(',', ' ')


def _build_card_for_price_group(settings, card_def, price_group_code):
    card = {'title': card_def['title'], 'sections': [], 'plain_fields': []}
    for section_def in card_def.get('sections', []):
        section = {
            'level': section_def['level'],
            'title': section_def.get('title', SECTION_TITLES.get(section_def['level'], '')),
            'fields': [],
        }
        for field_def in section_def.get('fields', []):
            field_name = diagnostic_field_name(field_def['base'], price_group_code)
            section['fields'].append({
                'name': field_name,
                'label': field_def['label'],
                'value': get_diagnostic_field_value(settings, field_def['base'], price_group_code),
                'input_class': 'bg-{} bg-opacity-25'.format(section_def['level']),
            })
        card['sections'].append(section)

    for field_def in card_def.get('plain_fields', []):
        field_name = diagnostic_field_name(field_def['base'], price_group_code)
        card['plain_fields'].append({
            'name': field_name,
            'label': field_def['label'],
            'value': get_diagnostic_field_value(settings, field_def['base'], price_group_code),
            'input_class': field_def.get('input_class', ''),
        })
    return card


def build_diagnostic_price_groups(settings):
    groups = []
    for price_group in get_active_price_groups():
        code = price_group.code
        groups.append({
            'code': code,
            'title': price_group.name or price_group.label_1c or code,
            'subtitle': format_price_group_subtitle(price_group),
            'cards': [
                _build_card_for_price_group(settings, card_def, code)
                for card_def in DIAGNOSTIC_CARD_DEFINITIONS
            ],
        })
    return groups


def apply_diagnostic_post_to_settings(settings, post_data, price_group_codes=None):
    price_group_codes = price_group_codes or get_active_price_group_codes()
    field_bases = iter_diagnostic_field_bases()
    for code in price_group_codes:
        for field_base in field_bases:
            field_name = diagnostic_field_name(field_base, code)
            if field_name not in post_data:
                continue
            raw = post_data.get(field_name, '')
            if raw == '':
                value = 0
            else:
                try:
                    value = int(raw)
                except (ValueError, TypeError):
                    continue
            set_diagnostic_field_value(settings, field_base, code, value)
    return settings


def get_diagnostic_settings_map(settings, price_group_code):
    """Словарь base -> value для расчётов (legacy + JSON)."""
    return {
        field_base: get_diagnostic_field_value(settings, field_base, price_group_code)
        for field_base in iter_diagnostic_field_bases()
    }
