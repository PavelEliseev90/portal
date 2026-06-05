"""Настройки столбцов списка калькуляций (таблица + Excel)."""

DEFAULT_CALC_LIST_COLUMNS = [
    'link', 'date', 'number', 'unit', 'rlk', 'car', 'vin',
    'client', 'author', 'kvp', 'agreement', 'shipment',
]

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
    'amount': {'label': 'Сумма итого', 'sortable': True, 'sort_key': 'amount'},
    'price': {'label': 'Цена автомобиля', 'sortable': True, 'sort_key': 'price'},
    'discount': {'label': 'Скидка', 'sortable': True, 'sort_key': 'discount'},
    'uin': {'label': 'UIN', 'sortable': True, 'sort_key': 'uin'},
    'date_success': {'label': 'Дата согласования', 'sortable': True, 'sort_key': 'date_success'},
    'agreement': {'label': 'Соглашение', 'sortable': True, 'sort_key': 'agreement'},
    'shipment': {'label': 'Отгрузка', 'sortable': True, 'sort_key': 'shipment'},
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
    'amount': 'amount',
    'price': 'price',
    'discount': 'discount',
    'uin': 'uin',
    'date_success': 'date_success',
    'agreement': 'agreement_nomer',
    'shipment': 'shipment_nomer',
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


def get_user_table_columns(user):
    from .models import CarCalculationsListSettings

    if not user or not user.is_authenticated:
        return list(DEFAULT_CALC_LIST_COLUMNS)
    try:
        settings = CarCalculationsListSettings.objects.get(user=user)
        return normalize_columns(settings.columns)
    except CarCalculationsListSettings.DoesNotExist:
        return list(DEFAULT_CALC_LIST_COLUMNS)


def save_user_table_columns(user, columns):
    from .models import CarCalculationsListSettings

    normalized = normalize_columns(columns)
    if not normalized:
        raise ValueError('Выберите хотя бы один столбец.')
    CarCalculationsListSettings.objects.update_or_create(
        user=user,
        defaults={'columns': normalized},
    )
    return normalized


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
    if key == 'comment':
        return item.comment or ''
    return ''
