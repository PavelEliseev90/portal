from django.template.defaultfilters import floatformat
from django.template import Library
from django.utils.http import urlencode
import re
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Value, IntegerField
import datetime as DT
from dateutil.relativedelta import relativedelta

register = Library()

def formatted_number(value):
    if value is None or value == '':
        return '0'
    try:
        num = int(float(value))
        return '{0:,}'.format(num).replace(',', ' ')
    except (TypeError, ValueError):
        return '0'

def formatted_float(value):
    if value is None or value == '':
        return '0.00'
    try:
        value = floatformat(value, arg=2)
        return str(value).replace(',', '.')
    except (TypeError, ValueError):
        return '0.00'

def ammont_box_sum(value_list):
    amount = 0
    for value in value_list:
        val = value.balance()['amount_base__sum']
        if val != None:
            amount = amount + val
    return str(amount).replace(',','.')


register.filter('formatted_number', formatted_number)
register.filter('formatted_float', formatted_float)
register.filter('ammont_box_sum', ammont_box_sum)


@register.filter
def list_item(sequence, index):
    try:
        return sequence[int(index)]
    except (IndexError, TypeError, ValueError):
        return None


register.filter('list_item', list_item)


def second_to_time(seconds):
    if seconds != None:
        return str(DT.timedelta(seconds=seconds))
    return str(DT.timedelta(seconds=0))
register.filter('second_to_time', second_to_time)


def replace_simbol(value):
    return str(value).replace("_", " ")
@register.filter('replace_simbol', replace_simbol)


@register.filter(name='fromunix')
def fromunix(value):
    try:
        return DT.datetime.fromtimestamp(int(value))
    except:
        return ''


@register.simple_tag(takes_context=True)
def list_field_sum(context, **kwargs):
    name        = kwargs['name'] 
    value_list  = list(kwargs['value_list'])
    amount = 0
    for value in value_list:
        val = value[name]
        if val != None:
            amount = amount + val
    return str(amount).replace(',','.')



@register.simple_tag(takes_context=True)
def puth_photo_mobile_replace(context, **kwargs):
    path = kwargs['path'] 
    path_new = path.replace('/data/user/0/ru.megaavto.megaavtopriemka/', 'http://carcopy.autoshina.net:8080/carcopy/')
    return path_new


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Сохраняет все значения GET (в т.ч. повторяющиеся ключи, например unit_ids)."""
    request = context['request']
    pairs = []
    override_keys = set(kwargs.keys())
    for key in request.GET.keys():
        if key in override_keys:
            continue
        for val in request.GET.getlist(key):
            pairs.append((key, val))
    for k, v in kwargs.items():
        pairs.append((k, str(v)))
    return urlencode(pairs)


@register.simple_tag(takes_context=True)
def query_transform(context, *args, **kwargs):
    """
    Формирует URL-encoded строку GET-параметров, объединяя базовые параметры и kwargs.
    Поддерживает:
      - {% query_transform params.filtr soglasovanie='auto_approved' page=1 %}
      - {% query_transform key=val %} (берёт request.GET из контекста)
    Пустые значения в kwargs (None, '') удаляют параметр из строки запроса.
    """
    params_dict = {}

    # 1. Извлекаем базовые параметры
    if args and args[0] is not None:
        source = args[0]
        if hasattr(source, 'GET'):
            source = source.GET
        if hasattr(source, 'lists'):  # QueryDict
            for k, vals in source.lists():
                params_dict[k] = list(vals)
        elif isinstance(source, dict):
            for k, v in source.items():
                if v is None or v == '' or v == []:
                    continue
                if k == 'filter_unit':
                    params_dict['unit_ids'] = [str(x) for x in v] if isinstance(v, (list, tuple)) else [str(v)]
                elif isinstance(v, (list, tuple)):
                    params_dict[k] = [str(x) for x in v]
                elif isinstance(v, bool):
                    if v:
                        params_dict[k] = ['1']
                else:
                    params_dict[k] = [str(v)]
    else:
        req = context.get('request')
        if req and hasattr(req, 'GET'):
            for k, vals in req.GET.lists():
                params_dict[k] = list(vals)

    # 2. Переопределяем / дополняем / удаляем параметры из kwargs
    for k, v in kwargs.items():
        if v is None or v == '':
            params_dict.pop(k, None)
            if k == 'unit_ids':
                params_dict.pop('filter_unit', None)
        else:
            if isinstance(v, (list, tuple)):
                params_dict[k] = [str(x) for x in v]
            elif isinstance(v, bool):
                if v:
                    params_dict[k] = ['1']
                else:
                    params_dict.pop(k, None)
            else:
                params_dict[k] = [str(v)]

    # 3. Собираем пары (key, value) и кодируем
    pairs = []
    for k, v_list in params_dict.items():
        for val in v_list:
            pairs.append((k, val))

    return urlencode(pairs)


@register.simple_tag(takes_context=True)
def razdelit(context, **kwargs):
    num = 0
    num1 = kwargs['num_1'] 
    num2 = kwargs['num_2'] 
    if num2 == 0:
        num2 = 1
    num = num1 / num2 * 100
    return round(num, 2)


@register.simple_tag(takes_context=True)
def url_replace_download(context, **kwargs):
    query = kwargs['data'] 
    url = '/'
    list_urls = query.split('/')
    for list_url in list_urls:
        if len(list_url) > 0:
            if list_url.find('?') >= 0:
                url = url + list_url
            else:
                url = url + list_url + '_export' + '/'
    
    return url


@register.simple_tag(takes_context=True)
def balance_unit(context, **kwargs):
    unit_id = kwargs['unit_id'] 
    date    = kwargs['date'] 
    date_start  = date - relativedelta(months=2)
    date_start  = date_start.replace(day=1, hour=1)
    date_end    = date

    from register.models import RegEstimationBalanceUnit
    request = RegEstimationBalanceUnit.objects.filter(unit__id = unit_id).order_by('-date')

    return None

@register.simple_tag(takes_context=True)
def balance_detail(context, **kwargs):
    unit_id = kwargs['unit_id'] 
    date    = kwargs['date'] 
    date_start  = date - relativedelta(months=2)
    date_start  = date_start.replace(day=1, hour=1)
    date_end    = date
    
    from register.models import RegEstimationBalanceUnit
    request = RegEstimationBalanceUnit.objects.filter(unit__id = unit_id).filter(date__gte = date_start).filter(date__lte = date_end).order_by('-date')
    return request

@register.simple_tag(takes_context=True)
def balance(context, **kwargs):
    unit_id = kwargs['unit_id'] 
    date    = kwargs['date'] 
    date_start  = date - relativedelta(months=2)
    date_start  = date_start.replace(day=1, hour=1)
    date_end    = date
    
    from register.models import RegEstimationBalanceUnit
    request = RegEstimationBalanceUnit.objects.filter(unit = unit_id).filter(date__gte = date_start).filter(date__lte = date_end).aggregate(Sum('amount'))
    if request['amount__sum'] == None:
        return 0
    return request['amount__sum']

@register.simple_tag(takes_context=True)
def balance_top_unit(context, **kwargs):
    
    unit_id = kwargs['unit_id'] 
    date    = kwargs['date'] 
    date_start  = date - relativedelta(months=2)
    date_start  = date_start.replace(day=1, hour=1)
    date_end    = date
    from register.models import RegEstimationBalanceUnit
    
    request = RegEstimationBalanceUnit.objects.filter(date__gte = date_start).filter(date__lte = date_end).values('unit').order_by('unit').distinct().annotate(sum = Sum('amount')).values('unit','sum' , ).order_by('-sum')
    
    all_count = RegEstimationBalanceUnit.objects.all().filter(date__gte = date_start).filter(date__lte = date_end).order_by('unit').distinct('unit').count()
    
    position = 0
    for uni in request:
        position = position + 1
        if unit_id == uni['unit']:
            break
        
    info = {
        'position'  : position,
        'all'       : all_count,
        'name'      : '' + str(position) + ' / ' + str(all_count)
    }
    return info

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Получить элемент из словаря по ключу"""
    if dictionary is None:
        return []
    # Если это словарь (dict), возвращаем значение или None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    # Для списков и других типов возвращаем элемент или пустой список
    return dictionary.get(key, [])