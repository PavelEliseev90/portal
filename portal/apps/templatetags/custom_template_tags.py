from django.template.defaultfilters import floatformat
from django.template import Library
from django.utils.http import urlencode
import re
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Value, IntegerField
import datetime as DT

register = Library()

def formatted_number(value):
    if value != '':
        value = int(value)
        return '{0:,}'.format(value).replace(',', ' ')
    return 0

def formatted_float(value):
    value = floatformat(value, arg=2)
    return str(value).replace(',','.')

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


def replace_simbol(value):
    return str(value).replace("_", " ")

@register.filter('replace_simbol', replace_simbol)


@register.filter(name='fromunix')
def fromunix(value):
    return DT.datetime.fromtimestamp(int(value))


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
    query = context['request'].GET.dict()
    query.update(kwargs)
    return urlencode(query)


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