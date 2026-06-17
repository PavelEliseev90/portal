"""Настройки столбцов списка калькуляций (таблица + Excel)."""

DEFAULT_CALC_LIST_COLUMNS = [
    'link', 'date', 'number', 'unit', 'rlk', 'car', 'vin',
    'client', 'author', 'kvp', 'soglasovanie_status', 'agreement', 'shipment',
]

SOGLASOVANIE_LIST_FILTER_CHOICES = (
    ('approved', 'Согласовано'),
    ('pending_director', 'Требуется согласование директором ДЦ'),
    ('pending_uk', 'Требуется согласование УК'),
    ('rejected', 'Отказ в согласовании'),
)

CALC_LIST_COLUMN_DEFS = {
    'link': {'label': '#', 'label_export': 'ID', 'sortable': False},
    'date': {'label': 'Дата', 'sortable': True, 'sort_key': 'date'},
    'number': {'label': 'Номер', 'sortable': True, 'sort_key': 'number'},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit'},
    'rlk': {'label': 'Рабочий лист', 'sortable': True, 'sort_key': 'rlk'},
    'car': {'label': 'Автомобиль', 'sortable': True, 'sort_key': 'car'},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin'},
    'client': {'label': 'Клиент', 'sortable': True, 'sort_key': 'client'},
    'author': {'label': 'Автор', 'sortable': True, 'sort_key': 'author'},
    'staff': {'label': 'Менеджер', 'sortable': True, 'sort_key': 'staff'},
    'kvp': {'label': 'КВ', 'sortable': True, 'sort_key': 'kvp'},
    'soglasovanie_status': {
        'label': 'Согласование КП',
        'label_export': 'Статус согласования',
        'sortable': True,
        'sort_key': 'soglasovanie_status',
    },
    'amount': {'label': 'Сумма итого', 'sortable': True, 'sort_key': 'amount'},
    'price': {'label': 'Цена автомобиля', 'sortable': True, 'sort_key': 'price'},
    'discount': {'label': 'Скидка', 'sortable': True, 'sort_key': 'discount'},
    'uin': {'label': 'UIN', 'sortable': True, 'sort_key': 'uin'},
    'date_success': {'label': 'Дата согласования', 'sortable': True, 'sort_key': 'date_success'},
    'agreement': {'label': 'Соглашение', 'sortable': True, 'sort_key': 'agreement'},
    'shipment': {'label': 'Отгрузка', 'sortable': True, 'sort_key': 'shipment'},
    'car_km': {'label': 'Расчетный КМ', 'sortable': True, 'sort_key': 'car_km'},
    'comment': {'label': 'Комментарий', 'sortable': True, 'sort_key': 'comment'},
}

CALC_LIST_SORT_FIELDS = {
    'date': 'date',
    'number': 'number',
    'unit': 'unit__name',
    'rlk': 'rlk__nomer',
    'car': 'car__name',
    'vin': 'car__vin',
    'client': 'rlk__clientName',
    'author': 'author__name',
    'staff': 'staff__name',
    'kvp': 'kvp',
    'soglasovanie_status': 'soglasovanie_status',
    'amount': 'amount',
    'price': 'price',
    'discount': 'discount',
    'uin': 'uin',
    'date_success': 'date_success',
    'agreement': 'agreement_nomer',
    'shipment': 'shipment_nomer',
    'car_km': 'car_last_km',
    'comment': 'comment',
}


def _calculation_client_name(item):
    rlk = getattr(item, 'rlk', None)
    if not rlk:
        return ''
    customer = getattr(rlk, 'customer', None)
    if customer:
        return customer.name or ''
    return rlk.clientName or ''


def normalize_columns(raw_columns):
    if not raw_columns:
        return list(DEFAULT_CALC_LIST_COLUMNS)
    valid = set(CALC_LIST_COLUMN_DEFS.keys())
    seen = set()
    result = []
    for key in raw_columns:
        if key in valid and key not in seen:
            result.append(key)
            seen.add(key)
    return result or list(DEFAULT_CALC_LIST_COLUMNS)


DEFAULT_LIST_SETTINGS = {
    'compare_km_kvp': True,
    'highlight_km_below_kvp': True,
}


def get_user_list_settings(user):
    from .models import CarCalculationsListSettings

    settings = dict(DEFAULT_LIST_SETTINGS)
    settings['columns'] = get_user_table_columns(user)
    if not user or not user.is_authenticated:
        return settings
    try:
        row = CarCalculationsListSettings.objects.get(user=user)
        settings['compare_km_kvp'] = bool(row.compare_km_kvp)
        settings['highlight_km_below_kvp'] = bool(row.highlight_km_below_kvp)
    except CarCalculationsListSettings.DoesNotExist:
        pass
    return settings


def get_user_table_columns(user):
    from .models import CarCalculationsListSettings

    if not user or not user.is_authenticated:
        return list(DEFAULT_CALC_LIST_COLUMNS)
    try:
        settings = CarCalculationsListSettings.objects.get(user=user)
        return normalize_columns(settings.columns)
    except CarCalculationsListSettings.DoesNotExist:
        return list(DEFAULT_CALC_LIST_COLUMNS)


def _effective_car_km(item):
    if getattr(item, 'km_raschet', None) is not None:
        return item.km_raschet
    return getattr(item, 'car_last_km', None)


def get_soglasovanie_status_display(item):
    from .models import CarCalculations

    status = getattr(item, 'soglasovanie_status', None)
    if not status:
        status = CarCalculations.SOGLASOVANIE_PENDING
    return dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES).get(status, status)


def apply_soglasovanie_status_filter(queryset, filter_values):
    from django.db.models import Q
    from .models import CarCalculations

    if not filter_values:
        return queryset

    status_q = Q()
    if 'approved' in filter_values:
        status_q |= Q(soglasovanie_status__in=[
            CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
            CarCalculations.SOGLASOVANIE_UK_APPROVED,
        ])
    if 'pending_director' in filter_values:
        status_q |= (
            Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING)
            | Q(soglasovanie_status='')
            | Q(soglasovanie_status__isnull=True)
        )
    if 'pending_uk' in filter_values:
        status_q |= Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
    if 'rejected' in filter_values:
        status_q |= Q(soglasovanie_status__in=[
            CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
            CarCalculations.SOGLASOVANIE_UK_REJECTED,
        ])

    if status_q:
        return queryset.filter(status_q)
    return queryset


def km_kvp_is_fulfilled(item):
    car_km = _effective_car_km(item)
    kvp = getattr(item, 'kvp', None)
    if car_km is None or kvp is None:
        return False
    return car_km >= kvp


def save_user_list_settings(user, columns=None, compare_km_kvp=None, highlight_km_below_kvp=None):
    from .models import CarCalculationsListSettings

    defaults = {}
    if columns is not None:
        normalized = normalize_columns(columns)
        if not normalized:
            raise ValueError('Выберите хотя бы один столбец.')
        defaults['columns'] = normalized
    if compare_km_kvp is not None:
        defaults['compare_km_kvp'] = bool(compare_km_kvp)
    if highlight_km_below_kvp is not None:
        defaults['highlight_km_below_kvp'] = bool(highlight_km_below_kvp)
    if not defaults:
        return get_user_list_settings(user)

    obj, _created = CarCalculationsListSettings.objects.get_or_create(
        user=user,
        defaults={
            'columns': list(DEFAULT_CALC_LIST_COLUMNS),
            **DEFAULT_LIST_SETTINGS,
        },
    )
    for key, value in defaults.items():
        setattr(obj, key, value)
    obj.save(update_fields=list(defaults.keys()))
    return get_user_list_settings(user)


def save_user_table_columns(user, columns):
    return save_user_list_settings(user, columns=columns)


def build_columns_settings(user):
    """Конфиг для модалки: все столбцы с флагом visible и порядком."""
    visible = get_user_table_columns(user)
    visible_set = set(visible)
    ordered = list(visible)
    for key in CALC_LIST_COLUMN_DEFS.keys():
        if key not in visible_set:
            ordered.append(key)
    return [
        {
            'key': key,
            'label': CALC_LIST_COLUMN_DEFS[key]['label'],
            'visible': key in visible_set,
        }
        for key in ordered
    ]


def build_table_columns(user):
    """Активные столбцы для отрисовки таблицы."""
    keys = get_user_table_columns(user)
    columns = []
    for key in keys:
        defn = CALC_LIST_COLUMN_DEFS[key]
        columns.append({
            'key': key,
            'label': defn['label'],
            'label_export': defn.get('label_export', defn['label']),
            'sortable': defn.get('sortable', False),
            'sort_key': defn.get('sort_key', ''),
        })
    return columns


def export_cell_value(item, key):
    if key == 'link':
        return item.pk
    if key == 'date':
        return item.date.strftime('%d.%m.%Y %H:%M') if item.date else ''
    if key == 'number':
        return item.number or ''
    if key == 'unit':
        return item.unit.name if item.unit else ''
    if key == 'rlk':
        return item.rlk.nomer if item.rlk else ''
    if key == 'car':
        return item.car.name if item.car else ''
    if key == 'vin':
        return item.car.vin if item.car else ''
    if key == 'client':
        return _calculation_client_name(item)
    if key == 'author':
        return item.author.name if item.author else ''
    if key == 'staff':
        return item.staff.name if item.staff else ''
    if key == 'kvp':
        return item.kvp if item.kvp is not None else ''
    if key == 'soglasovanie_status':
        return get_soglasovanie_status_display(item)
    if key == 'amount':
        return item.amount if item.amount is not None else ''
    if key == 'price':
        return item.price if item.price is not None else ''
    if key == 'discount':
        return item.discount if item.discount is not None else ''
    if key == 'uin':
        return item.uin or ''
    if key == 'date_success':
        return item.date_success.strftime('%d.%m.%Y %H:%M') if item.date_success else ''
    if key == 'agreement':
        return item.agreement_nomer or ''
    if key == 'shipment':
        return item.shipment_nomer or ''
    if key == 'car_km':
        value = _effective_car_km(item)
        return value if value is not None else ''
    if key == 'comment':
        return item.comment or ''
    return ''
