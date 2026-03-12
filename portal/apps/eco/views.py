from django.contrib.auth.decorators import login_required
from tkinter.tix import Tree
from collections import defaultdict
from django.shortcuts import redirect, render
from openpyxl import Workbook
from django.http import HttpResponse
from register.models import RegInteractivOcenkaRLK, SettingsMatrixAuction, RegEstimationBalanceUnit, RegEstimationsCalculationDetail, RegEstimationPodgotovka, RegEstimationSS, RegEstimationMCU, RegSwapKors, RegPodgotovkaWork, RegInfoBody, RegEstimationsSettings, RegRegInteractivOcenkaTaskFiles, RegInteractivOcenkaTask, RegInteractivOcenkaHistoryOpens, RegInteractivOcenkaEmailPush, RegInteractivOcenkaSoglasovanie, RegInteractivOcenkaProverki, RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive, RegInteractivOcenkaComplectnost, RegInteractivOcenkaVnesh, RegDashboardError, RegInteractivOcenka, RegInteractivOcenkaDocument, RegRegInteractivOcenkaFiles, RegInteractivOcenkaSalon, RegControlDiagnostic, RegControlDiagnosticVnesh, RegControlDiagnosticSalon, RegControlDiagnosticFile
from django.core.paginator import Paginator
from refs.models import RefCarsOrganization, RefCustomerFiltr, RefStatusEstimation, RefTypeDisk, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefEtDisk, RefDiaDisk, RefPsdDisk, RefStatusOcenka, RefUnit, RefStaff, RefTypeReceptionCarsOrganization, RefUnitGroup, RefGroupPrice
from profiles.models import Profiles
from documents.models import DocZNWorkKA, DocZNProductKA, DocZNServicesKA, DocServiceItem, DocCarShipment, DocCarAgreement, DocRLK, DocZN, DocLO
from task_manager.views import send_message_socket, get_info_max, kors_estimation_data
import json
from checklists.models import CheckListTradeIn
from chats.models import Chat, ChatMessage
from django.db.models import Count, Sum, Max, Min, Avg, F, OuterRef, Subquery, Q, Value, IntegerField, Case, When, CharField, FloatField, Exists
from django.db.models.functions import Extract, TruncDate, TruncMonth
from django.db import models
import datetime as DT
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.contrib.auth.models import User, Group
from django.db.models.functions import Cast, Coalesce
from avtosalon.models import Autoteka_signal
from dateutil.relativedelta import relativedelta

import re
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from django.http.response import JsonResponse
from rest_framework import status

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.views.decorators.csrf import csrf_exempt
from changelog.models import ChangeLog
from collections import defaultdict
from analytics.models import (
    InteractivePricingSnapshot,
    EcoAnalystSnapshot,
    AppraiserPerformanceSnapshot,
    TradeInFunnelSnapshot,
    TradeInFunnel,
)


def close_task(reg_interactiv_ocenka, user):
    tasks = RegInteractivOcenkaTask.objects.filter(estimation = reg_interactiv_ocenka).filter(staff_close = None)
    for task in tasks:
        task.comment_success = 'Закрыто согласованием цены после диагностики'
        task.date_close     = DT.datetime.now()
        task.staff_close    = user
        task.save()
    reg_interactiv_ocenka.returned = False


def add_swap(rlk, estimation):
    try:        
        swap                = RegSwapKors()
        swap.rlk            = rlk 
        swap.estimation     = estimation
        swap.save()        
    except:
        s = 1


def send_web_socket_message(group, chat, user, text, estimation_id):
    
    message_json = {
            'chat_id'       : str(chat.pk),
            'name'          : str(user),
            'chat'          : group,
            'message'       : text,
            'username'      : str(user),
            'last_name'     : user.last_name,
            'first_name'    : user.first_name,
            'psevdo_name'   : user.profiles.eco_name,
            'eco'           : user.profiles.eco,
            'estimation_id' : estimation_id
        }    
    
    send_message_socket(message = message_json)


def add_log_history_open(estimation, user, page):
    
    if user != None:
        if user.profiles.user_sb:
            return
        
    page_title = 'Главная'
    
    if page == 1:
        page_title = 'Документы'
    elif page == 2:
        page_title = 'Салон'
    elif page == 3:
        page_title = 'Внешний осмотр'
    elif page == 11:
        page_title = 'Дистанционная оценка'
    elif page == 4:
        page_title = 'Комплектность'
    elif page == 5:
        page_title = 'Колеса'
    elif page == 6:
        page_title = 'Тест - драйв'
    elif page == 7:
        page_title = 'Проверки'
    elif page == 8:
        page_title = 'История оценок'
    elif page == 13:
        page_title = 'История ремонтов'
    elif page == 9:
        page_title = 'Согласование'
    elif page == 17:
        page_title = 'Все фото осмотра'
    elif page == 18:
        page_title = 'История просмотров'
    elif page == 20:
        page_title = 'Ценообразование админ'
    elif page == 30:
        page_title = 'Ценообразование ДДЦ'
    elif page == 21:
        page_title = 'Ценообразование ЕЦО'
    elif page == 22:
        page_title = 'Ценообразование'
    elif page == 22:
        page_title = 'История изменений'
    elif page == 403:
        page_title = 'Отказано в доступе'
    elif page == 301:
        page_title = 'Не авторизованный пользователь'

    new_info                = RegInteractivOcenkaHistoryOpens()
    new_info.staff          = user
    new_info.estimation     = estimation
    new_info.page_title     = page_title
    new_info.page           = page
    new_info.save() 


def get_path_in_dict(dict_filtr):
    path = ''
    one = True
    for key in dict_filtr:
        if one:
            path = path + '?' + str(key) + '=' + dict_filtr[key]
            one = False
        else:
            path = path + '&' + str(key) + '=' + dict_filtr[key]
    return path


def _parse_date(value, default, is_end=False):
    if not value:
        return default
    try:
        year, month, day = [int(part) for part in value.split('-')]
        parsed = default.replace(year=year, month=month, day=day)
        if is_end:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        return parsed
    except Exception:
        return default


def _get_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_tradein_querysets(date_start, date_end, unit_id=None, staff_id=None, analyst_id=None, type_reception_id=None):
    tradein_rlk = (
        DocRLK.objects.filter(dataTime__gte=date_start)
        .filter(dataTime__lte=date_end)
        .filter(eco=True)
        .filter(tradeInModel__isnull=False)
    )

    if unit_id:
        tradein_rlk = tradein_rlk.filter(Q(unit__id=unit_id) | Q(unit_dc__id=unit_id))

    if staff_id:
        tradein_rlk = tradein_rlk.filter(staff__id=staff_id)

    if analyst_id:
        tradein_rlk = tradein_rlk.filter(
            Q(reginteractivocenka__staff_eco_1__id=analyst_id) |
            Q(reginteractivocenka__staff_eco_2__id=analyst_id)
        )

    if type_reception_id:
        tradein_rlk = tradein_rlk.filter(
            reginteractivocenka__page_documents__type_reception__id=type_reception_id
        )

    reg_qs = RegInteractivOcenka.objects.filter(rlk__in=tradein_rlk.values('pk'))

    if analyst_id:
        reg_qs = reg_qs.filter(
            Q(staff_eco_1__id=analyst_id) |
            Q(staff_eco_2__id=analyst_id)
        )

    if type_reception_id:
        reg_qs = reg_qs.filter(page_documents__type_reception__id=type_reception_id)

    return tradein_rlk, reg_qs


def _get_stage_counts(date_start, date_end, unit_id=None, staff_id=None, analyst_id=None, type_reception_id=None):
    tradein_rlk, reg_qs = _build_tradein_querysets(
        date_start,
        date_end,
        unit_id=unit_id,
        staff_id=staff_id,
        analyst_id=analyst_id,
        type_reception_id=type_reception_id,
    )

    stage_work_orders = tradein_rlk.count()
    stage_estimations = reg_qs.count()
    stage_diagnostics_qs = reg_qs.filter(page_soglasovanie__isnull=False).exclude(page_soglasovanie__comment_diagnostica = '').filter(page_soglasovanie__no_diagnostica = False) | reg_qs.filter(page_soglasovanie__isnull=False).filter(page_soglasovanie__no_diagnostica = True)
    stage_diagnostics = stage_diagnostics_qs.count()
    stage_accepted = stage_diagnostics_qs.filter(status__name__icontains='ам принят').count()

    return stage_work_orders, stage_estimations, stage_diagnostics, stage_accepted, stage_diagnostics_qs


def _get_type_distribution(date_start, date_end, unit_id=None, staff_id=None, analyst_id=None, type_reception_id=None):
    _, reg_qs = _build_tradein_querysets(
        date_start,
        date_end,
        unit_id=unit_id,
        staff_id=staff_id,
        analyst_id=analyst_id,
        type_reception_id=type_reception_id,
    )

    return (
        reg_qs.values(name=F('page_documents__type_reception__name'))
        .annotate(total=Count('id'))
        .order_by('-total')
    )


def _get_source_stats(date_start, date_end, unit_id=None, staff_id=None, analyst_id=None, type_reception_id=None):
    tradein_rlk, reg_qs = _build_tradein_querysets(
        date_start,
        date_end,
        unit_id=unit_id,
        staff_id=staff_id,
        analyst_id=analyst_id,
        type_reception_id=type_reception_id,
    )

    source_label = Coalesce(
        'unit_dc__name',
        'unit__name',
        Value('Без подразделения', output_field=CharField()),
    )
    work_orders = (
        tradein_rlk
        .annotate(source_name=source_label)
        .values('source_name')
        .annotate(total=Count('id'))
    )

    reg_source_label = Coalesce(
        'rlk__unit_dc__name',
        'rlk__unit__name',
        Value('Без подразделения', output_field=CharField()),
    )
    
    diagnostics_qs = (
        reg_qs.filter(page_soglasovanie__isnull=False)
        .exclude(page_soglasovanie__comment_diagnostica='')
        .filter(page_soglasovanie__no_diagnostica=False)
    ) | (
        reg_qs.filter(page_soglasovanie__isnull=False)
        .filter(page_soglasovanie__no_diagnostica=True)
    )
    
    reg_stats = (
        reg_qs
        .annotate(source_name=reg_source_label)
        .values('source_name')
        .annotate(
            evaluations=Count('id'),
        )
    )
    
    diagnostics_stats = (
        diagnostics_qs
        .annotate(source_name=reg_source_label)
        .values('source_name')
        .annotate(
            diagnostics=Count('id'),
            accepted=Count('id', filter=Q(status__name__icontains='ам принят')),
        )
    )

    # Собираем статистику по подразделениям
    stats_map = {}
    for row in work_orders:
        name = row['source_name'] or 'Без подразделения'
        stats_map[name] = {
            'source': name,
            'work_orders': row['total'],
            'evaluations': 0,
            'diagnostics': 0,
            'accepted': 0,
        }

    for row in reg_stats:
        name = row['source_name'] or 'Без подразделения'
        stats_map.setdefault(
            name,
            {
                'source': name,
                'work_orders': 0,
                'evaluations': 0,
                'diagnostics': 0,
                'accepted': 0,
            },
        )
        stats_map[name]['evaluations'] = row['evaluations']
    
    for row in diagnostics_stats:
        name = row['source_name'] or 'Без подразделения'
        stats_map.setdefault(
            name,
            {
                'source': name,
                'work_orders': 0,
                'evaluations': 0,
                'diagnostics': 0,
                'accepted': 0,
            },
        )
        stats_map[name]['diagnostics'] = row['diagnostics']
        stats_map[name]['accepted'] = row['accepted']

    # Вычисляем конверсии для каждого подразделения
    for item in stats_map.values():
        conv_to_eval = round((item['evaluations'] / item['work_orders'] * 100) if item['work_orders'] > 0 else 0, 1)
        conv_to_diag = round((item['diagnostics'] / item['evaluations'] * 100) if item['evaluations'] > 0 else 0, 1)
        conv_to_accepted = round((item['accepted'] / item['diagnostics'] * 100) if item['diagnostics'] > 0 else 0, 1)
        overall_conv = round((item['accepted'] / item['work_orders'] * 100) if item['work_orders'] > 0 else 0, 1)
        
        item['conv_to_eval'] = conv_to_eval
        item['conv_to_diag'] = conv_to_diag
        item['conv_to_accepted'] = conv_to_accepted
        item['overall_conv'] = overall_conv

    # Получаем все активные группы подразделений с bu_auto=True
    unit_groups = RefUnitGroup.objects.filter(active=True, bu_auto=True).prefetch_related('units').order_by('name')
    
    # Создаем карту: имя подразделения -> группа
    unit_to_group = {}
    for group in unit_groups:
        for unit in group.units.all():
            unit_to_group[unit.name] = group
    
    # Группируем статистику по группам
    grouped_stats = {}
    ungrouped_stats = []
    
    for unit_name, unit_stats in stats_map.items():
        if unit_name in unit_to_group:
            group = unit_to_group[unit_name]
            group_name = group.name or 'Без названия'
            if group_name not in grouped_stats:
                grouped_stats[group_name] = {
                    'group_name': group_name,
                    'group_id': group.id,
                    'units': [],
                    'work_orders': 0,
                    'evaluations': 0,
                    'diagnostics': 0,
                    'accepted': 0,
                }
            grouped_stats[group_name]['units'].append(unit_stats)
            grouped_stats[group_name]['work_orders'] += unit_stats['work_orders']
            grouped_stats[group_name]['evaluations'] += unit_stats['evaluations']
            grouped_stats[group_name]['diagnostics'] += unit_stats['diagnostics']
            grouped_stats[group_name]['accepted'] += unit_stats['accepted']
        else:
            ungrouped_stats.append(unit_stats)
    
    # Вычисляем итоговые показатели и конверсии для групп
    grouped_list = []
    for group_name, group_data in grouped_stats.items():
        # Сортируем подразделения внутри группы
        group_data['units'] = sorted(
            group_data['units'],
            key=lambda item: item['work_orders'],
            reverse=True,
        )
        
        # Вычисляем конверсии для группы
        group_data['conv_to_eval'] = round((group_data['evaluations'] / group_data['work_orders'] * 100) if group_data['work_orders'] > 0 else 0, 1)
        group_data['conv_to_diag'] = round((group_data['diagnostics'] / group_data['evaluations'] * 100) if group_data['evaluations'] > 0 else 0, 1)
        group_data['conv_to_accepted'] = round((group_data['accepted'] / group_data['diagnostics'] * 100) if group_data['diagnostics'] > 0 else 0, 1)
        group_data['overall_conv'] = round((group_data['accepted'] / group_data['work_orders'] * 100) if group_data['work_orders'] > 0 else 0, 1)
        
        grouped_list.append(group_data)
    
    # Сортируем группы по количеству рабочих листов
    grouped_list = sorted(
        grouped_list,
        key=lambda item: item['work_orders'],
        reverse=True,
    )
    
    # Сортируем негруппированные подразделения
    ungrouped_stats = sorted(
        ungrouped_stats,
        key=lambda item: item['work_orders'],
        reverse=True,
    )
    
    # Вычисляем общие итоги
    totals = {
        'work_orders': sum(item['work_orders'] for item in grouped_list) + sum(item['work_orders'] for item in ungrouped_stats),
        'evaluations': sum(item['evaluations'] for item in grouped_list) + sum(item['evaluations'] for item in ungrouped_stats),
        'diagnostics': sum(item['diagnostics'] for item in grouped_list) + sum(item['diagnostics'] for item in ungrouped_stats),
        'accepted': sum(item['accepted'] for item in grouped_list) + sum(item['accepted'] for item in ungrouped_stats),
    }
    totals['overall_conv'] = round((totals['accepted'] / totals['work_orders'] * 100) if totals['work_orders'] > 0 else 0, 1)
    
    avg_overall_conv = round((totals['accepted'] / totals['work_orders'] * 100) if totals['work_orders'] > 0 else 0, 1)
    
    # Отмечаем лучшие группы и подразделения
    for group_data in grouped_list:
        is_good = False
        if group_data['work_orders'] >= 5:
            if group_data['overall_conv'] >= max(avg_overall_conv, 30):
                is_good = True
        group_data['is_good'] = is_good
        
        for unit_item in group_data['units']:
            is_good_unit = False
            if unit_item['work_orders'] >= 5:
                if unit_item['overall_conv'] >= max(avg_overall_conv, 30):
                    is_good_unit = True
            unit_item['is_good'] = is_good_unit
    
    for item in ungrouped_stats:
        is_good = False
        if item['work_orders'] >= 5:
            if item['overall_conv'] >= max(avg_overall_conv, 30):
                is_good = True
        item['is_good'] = is_good

    # Формируем итоговый список: группы с подразделениями + негруппированные
    result_list = []
    for group_data in grouped_list:
        result_list.append({
            'type': 'group',
            **group_data
        })
        for unit_item in group_data['units']:
            result_list.append({
                'type': 'unit',
                'group_id': group_data['group_id'],
                **unit_item
            })
    
    for unit_item in ungrouped_stats:
        result_list.append({
            'type': 'unit',
            'group_id': None,
            **unit_item
        })

    return result_list, totals

def _get_price_category(price):
    """Определяет ценовую категорию на основе цены"""
    if not price or price <= 0:
        return 'Без цены'
    elif price < 200000:
        return 'До 200 тыс.'
    elif price < 400000:
        return '200-400 тыс.'
    elif price < 700000:
        return '400-700 тыс.'
    elif price < 1200000:
        return '700 тыс. - 1.2 млн'
    elif price < 2000000:
        return '1.2-2 млн'
    elif price < 3000000:
        return '2-3 млн'
    elif price < 5000000:
        return '3-5 млн'
    else:
        return 'Свыше 5 млн'


def _get_price_category_order(category_name):
    """Возвращает порядковый номер категории для сортировки по возрастанию цены"""
    order_map = {
        'Без цены': 0,
        'До 200 тыс.': 1,
        '200-400 тыс.': 2,
        '400-700 тыс.': 3,
        '700 тыс. - 1.2 млн': 4,
        '1.2-2 млн': 5,
        '2-3 млн': 6,
        '3-5 млн': 7,
        'Свыше 5 млн': 8,
    }
    return order_map.get(category_name, 999)


def _parse_multiple_ints(value):
    """Парсит строку с множественными ID (через запятую)"""
    if not value:
        return []
    try:
        return [int(x.strip()) for x in value.split(',') if x.strip().isdigit()]
    except (ValueError, AttributeError):
        return []


def tradein_funnel_new(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    
    default_end     = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start   = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)

    date_start  = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end    = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    type_report_id = _get_int(request.GET.get('type_report_id')) or 1
    
    type_reception_stats = []
    # Множественный выбор фильтров
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    unit_group_ids = _parse_multiple_ints(request.GET.get('unit_group_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    source_unit_ids = _parse_multiple_ints(request.GET.get('source_unit_ids', ''))
    staff_ids = _parse_multiple_ints(request.GET.get('staff_ids', ''))
    analyst_ids = _parse_multiple_ints(request.GET.get('analyst_ids', ''))
    
    # Одиночные фильтры (для обратной совместимости)
    unit_id             = _get_int(request.GET.get('unit_id'))
    staff_id            = _get_int(request.GET.get('staff_id'))
    analyst_id          = _get_int(request.GET.get('analyst_id'))
    type_reception_id   = _get_int(request.GET.get('type_reception_id'))
    brand               =  request.GET.get('brand', None)
    # Если передан одиночный фильтр, добавляем его в множественный
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if staff_id and staff_id not in staff_ids:
        staff_ids.append(staff_id)
    if analyst_id and analyst_id not in analyst_ids:
        analyst_ids.append(analyst_id)
    
    # Получаем подразделения из групп, если выбраны группы
    if unit_group_ids:
        unit_groups = RefUnitGroup.objects.filter(id__in=unit_group_ids).prefetch_related('units')
        for group in unit_groups:
            for unit in group.units.all():
                if unit.id not in unit_ids:
                    unit_ids.append(unit.id)
    
    # Загружаем справочники
    type_receptions = RefTypeReceptionCarsOrganization.objects.exclude(name='').order_by('name')
    units = RefUnit.objects.filter(buauto=True).filter(active_eco=True).exclude(name='').order_by('name')
    unit_groups = RefUnitGroup.objects.filter(active=True, bu_auto=True).order_by('name')
    staffs = RefStaff.objects.exclude(name='').order_by('name')
    analysts = User.objects.filter(profiles__eco=True)
    statuses = RefStatusEstimation.objects.order_by('name')
    
    # Получаем список источников поступления (unit_dc или unit из DocRLK с eco=True)
    # Источник = unit_dc если заполнен, иначе unit
    source_unit_ids_from_rlk = set()
    source_unit_ids_from_rlk.update(
        DocRLK.objects.filter(eco=True).exclude(unit_dc__isnull=True).values_list('unit_dc_id', flat=True).distinct()
    )
    source_unit_ids_from_rlk.update(
        DocRLK.objects.filter(eco=True, unit_dc__isnull=True).exclude(unit__isnull=True).values_list('unit_id', flat=True).distinct()
    )
    source_units = RefUnit.objects.filter(id__in=source_unit_ids_from_rlk).exclude(name='').order_by('name')
    
    # Инициализация переменных
    rlk_count = 0
    count_price_before_kd = 0
    count_price_after_kd = 0
    count_price_before_kd_p = 0
    count_price_after_kd_p = 0
    count_success = 0
    count_success_p = 0
    rlk_ids = []  # Список ID документов для статистики
    
    # Функция для расчета конверсии
    def _conversion(current, previous):
        if not previous:
            return 0
        return round(current / previous * 100, 1)
    
    # Базовый Q объект для оптимизации запросов DocRLK
    base_rlk_q = Q(
        Q(type__id=2, unit_dc__buauto=True) |
        Q(type__id=7, eco=True) |
        Q(type__id=1, eco=True) |
        Q(type__id=19, eco=True) |
        Q(eco=True)
    )
    
    # Вариант 1: Данные по периоду (по датам создания DocRLK)
    if type_report_id == 1:
        # Базовый запрос DocRLK
        docs_base = DocRLK.objects.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        ).filter(base_rlk_q)
        
        if brand:
           docs_base = docs_base.filter(Q(unit__name__icontains = brand) | Q(unit_dc__name__icontains = brand))

        # Применяем фильтры
        if unit_ids:
            docs_base = docs_base.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
        
        if source_unit_ids:
            docs_base = docs_base.filter(
                Q(unit_dc__id__in=source_unit_ids) |
                Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
            )
        
        if staff_id:
            docs_base = docs_base.filter(staff__id=staff_id)
        
        # Получаем ID документов для дальнейшей работы
        rlk_ids = list(docs_base.values_list('id', flat=True))
        
        if not rlk_ids:
            rlk_count = 0
            count_price_before_kd = 0
            count_price_after_kd = 0
            count_price_before_kd_p = 0
            count_price_after_kd_p = 0
            count_success = 0
            count_success_p = 0
        else:
            
            rlk_count = docs_base.exclude(vin_trade_in = '').values('vin_trade_in').distinct().count() + docs_base.filter(vin_trade_in = '').values('vin_trade_in').count()
            
            count_price_after_kd_q = RegInteractivOcenka.objects.filter(
                date_s_diag__gte=date_start,
                date_s_diag__lte=date_end
            )

            count_price_before_kd_q = RegInteractivOcenka.objects.filter(
                start_estimation__gte=date_start,
                start_estimation__lte=date_end
            ) | RegInteractivOcenka.objects.filter(
                page_remote__start_estimation__gte=date_start,
                page_remote__start_estimation__lte=date_end
            )
            accepted_count_q = DocLO.objects.filter(
                dataTime__gte=date_start,
                dataTime__lte=date_end,
                active=True
            )

            if type_reception_ids:
                count_price_after_kd_q  = count_price_after_kd_q.filter(page_documents__type_reception__id__in=type_reception_ids) | count_price_after_kd_q.filter(page_remote__type_reception__id__in=type_reception_ids)
                count_price_before_kd_q = count_price_before_kd_q.filter(page_documents__type_reception__id__in=type_reception_ids) | count_price_before_kd_q.filter(page_remote__type_reception__id__in=type_reception_ids)    
                accepted_count_q        = accepted_count_q.filter(type_reception__id__in = type_reception_ids)

            if brand:
                count_price_after_kd_q  = count_price_after_kd_q.filter(rlk__unit_dc__name__icontains = brand) | count_price_after_kd_q.filter(rlk__unit__name__icontains = brand) 
                count_price_before_kd_q = count_price_before_kd_q.filter(rlk__unit_dc__name__icontains = brand) | count_price_before_kd_q.filter(rlk__unit__name__icontains = brand)   
                accepted_count_q        = accepted_count_q.filter(rlk__unit_dc__name__icontains = brand) | accepted_count_q.filter(rlk__unit__name__icontains = brand)
            
            if unit_ids:
                count_price_after_kd_q  = count_price_after_kd_q.filter(page_documents__unit__id__in = unit_ids) | count_price_after_kd_q.filter(page_remote__unit__id__in = unit_ids) 
                count_price_before_kd_q = count_price_before_kd_q.filter(page_documents__unit__id__in = unit_ids) | count_price_before_kd_q.filter(page_remote__unit__id__in = unit_ids)   
                accepted_count_q        = accepted_count_q.filter(unit__id__in = unit_ids)
            
            count_price_before_kd = count_price_before_kd_q.values('vin').order_by('vin').distinct().count()
            count_price_after_kd = count_price_after_kd_q.count()

            count_success               = accepted_count_q.count()
            count_price_before_kd_p     = _conversion(count_price_before_kd, rlk_count)
            count_price_after_kd_p      = _conversion(count_price_after_kd, count_price_before_kd)
            count_success_p             = _conversion(count_success, count_price_after_kd)
            
            type_reception_stats = []
            accepted_rlk_ids = set()
            
            types_receptions = RefTypeReceptionCarsOrganization.objects.all().order_by('name')
            if type_reception_ids:
                types_receptions = types_receptions.filter(id__in = type_reception_ids)

            for type_reception in types_receptions:
                
                accepted_count_q_type           = accepted_count_q.filter(type_reception__id = type_reception.id)
                count_price_before_kd_q_type    = count_price_before_kd_q.filter(page_documents__type_reception__id = type_reception.id).values('vin').order_by('vin').distinct() | count_price_before_kd_q.filter(page_remote__type_reception__id = type_reception.id).values('vin').order_by('vin').distinct()
                count_price_after_kd_q_type     = count_price_after_kd_q.filter(page_documents__type_reception__id = type_reception.id).values('vin').order_by('vin').distinct() | count_price_after_kd_q.filter(page_remote__type_reception__id = type_reception.id).values('vin').order_by('vin').distinct()
                type_reception_stats.append({
                    'id'            : type_reception.id,
                    'name'          : type_reception.name,
                    'total'         : 0,
                    'before_kd'     : count_price_before_kd_q_type.count(),
                    'after_kd'      : count_price_after_kd_q_type.count(),
                    'success'       : accepted_count_q_type.count(),
                    'conv_before'   : _conversion(count_price_before_kd_q_type.count(), 0),
                    'conv_after'    : _conversion(count_price_after_kd_q_type.count(), count_price_before_kd_q_type.count()),
                    'conv_success'  : _conversion(accepted_count_q_type.count(), count_price_after_kd_q_type.count()),
                })
            
            # Статистика по ценовым категориям
            # price_category_stats = []
            
            # price_data = est_qs.values('rlk_id', 'page_soglasovanie__price_after_kd', 'page_soglasovanie__price_before_kd').filter(
            #     page_soglasovanie__price_after_kd__gt=0
            # )
            
            # price_categories = defaultdict(lambda: {'total': 0, 'before_kd': 0, 'after_kd': 0, 'success': 0})
            
            # # Обрабатываем данные из values (быстрее чем select_related)
            # for item in price_data:
            #     price_after = item.get('page_soglasovanie__price_after_kd') or 0
            #     price_before = item.get('page_soglasovanie__price_before_kd') or 0
            #     rlk_id = item.get('rlk_id')
                
            #     if price_after > 0:
            #         category = _get_price_category(price_after)
            #         price_categories[category]['total'] += 1
            #         if price_before > 0:
            #             price_categories[category]['before_kd'] += 1
            #         price_categories[category]['after_kd'] += 1
            #         if rlk_id in accepted_rlk_ids:
            #             price_categories[category]['success'] += 1
            
            # for category, stats in sorted(price_categories.items(), key=lambda x: _get_price_category_order(x[0])):
            #     price_category_stats.append({
            #         'name': category,
            #         'total': stats['total'],
            #         'before_kd': stats['before_kd'],
            #         'after_kd': stats['after_kd'],
            #         'success': stats['success'],
            #         'conv_before': _conversion(stats['before_kd'], stats['total']),
            #         'conv_after': _conversion(stats['after_kd'], stats['before_kd']),
            #         'conv_success': _conversion(stats['success'], stats['after_kd']),
            #     })
            
            
    # Вариант 2: Данные по датам рабочих листов (фильтр по dataTime DocRLK)
    elif type_report_id == 2:
        # Базовый запрос DocRLK (аналогично варианту 1)
        docs_base = DocRLK.objects.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        ).filter(base_rlk_q)
        
        # Применяем фильтры
        if unit_ids:
            docs_base = docs_base.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
        if source_unit_ids:
            docs_base = docs_base.filter(
                Q(unit_dc__id__in=source_unit_ids) |
                Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
            )
        if staff_id:
            docs_base = docs_base.filter(staff__id=staff_id)
        
        # Получаем ID документов
        rlk_ids = list(docs_base.values_list('id', flat=True))
        
        if not rlk_ids:
            rlk_count = 0
            count_price_before_kd = 0
            count_price_after_kd = 0
            count_price_before_kd_p = 0
            count_price_after_kd_p = 0
            count_success = 0
            count_success_p = 0
        else:
            # Работаем с оценками напрямую
            est_qs = RegInteractivOcenka.objects.filter(rlk_id__in=rlk_ids)
            
            # Фильтры по аналитику и типу приема
            if analyst_id:
                est_qs = est_qs.filter(
                    Q(staff_eco_1__id=analyst_id) |
                    Q(staff_eco_2__id=analyst_id)
                )
            if type_reception_ids:
                est_qs = est_qs.filter(page_documents__type_reception__id__in=type_reception_ids)
            
            # Подсчитываем через агрегацию
            rlk_count = len(rlk_ids)
            
            # Подсчет цен через агрегацию
            price_stats = est_qs.aggregate(
                before_kd_count=Count('id', filter=Q(page_soglasovanie__price_before_kd__gt=0)),
                after_kd_count=Count('id', filter=Q(page_soglasovanie__price_after_kd__gt=0)),
            )
            price_stats_remote = est_qs.filter(page_soglasovanie = None).aggregate(
                before_kd_count=Count('id', filter=Q(page_remote__price_eco__gt=0))
            )
            count_price_before_kd = price_stats['before_kd_count'] or 0 + price_stats_remote['before_kd_count'] or 0
            count_price_after_kd = price_stats['after_kd_count'] or 0
            
            # Подсчет принятых через DocLO
            accepted_count = DocLO.objects.filter(
                rlk_id__in=rlk_ids,
                active=True
            ).count()
            
            count_success = accepted_count
            count_price_before_kd_p = _conversion(count_price_before_kd, rlk_count)
            count_price_after_kd_p = _conversion(count_price_after_kd, count_price_before_kd)
            count_success_p = _conversion(count_success, count_price_after_kd)
    
    # Вариант 3: Данные по листам оценки (фильтр по датам DocLO)
    else:
        lo_qs = RegInteractivOcenka.objects.filter(
            start_estimation__gte=date_start,
            start_estimation__lte=date_end
        )
        
        # Получаем rlk_id из листов оценки
        lo_rlk_ids = list(lo_qs.values_list('rlk__id', flat=True).distinct())
        
        if not lo_rlk_ids:
            rlk_count = 0
            count_price_before_kd = 0
            count_price_after_kd = 0
            count_price_before_kd_p = 0
            count_price_after_kd_p = 0
            count_success = 0
            count_success_p = 0
            rlk_ids = []  # Убеждаемся, что переменная определена
        else:
            # Получаем DocRLK по найденным ID
            docs_base = DocRLK.objects.filter(id__in=lo_rlk_ids).filter(base_rlk_q)
            
            # Применяем фильтры
            if unit_ids:
                docs_base = docs_base.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
            if source_unit_ids:
                docs_base = docs_base.filter(
                    Q(unit_dc__id__in=source_unit_ids) |
                    Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
                )
            if staff_id:
                docs_base = docs_base.filter(staff__id=staff_id)
            
            # Дополнительные фильтры по номеру и VIN
            filtr_number_doc = request.GET.get('number_doc', '')
            filtr_vin = request.GET.get('vin', '')
            
            if filtr_number_doc:
                docs_base = docs_base.filter(nomer__icontains=filtr_number_doc)
            
            # Получаем финальные ID документов
            rlk_ids = list(docs_base.values_list('id', flat=True))
            
            if not rlk_ids:
                rlk_count = 0
                count_price_before_kd = 0
                count_price_after_kd = 0
                count_price_before_kd_p = 0
                count_price_after_kd_p = 0
                count_success = 0
                count_success_p = 0
            else:
                # Работаем с оценками
                est_qs = RegInteractivOcenka.objects.filter(rlk_id__in=rlk_ids)
                
                # Фильтр по VIN через оценки
                if filtr_vin:
                    est_qs = est_qs.filter(vin__icontains=filtr_vin)
                    rlk_ids = list(est_qs.values_list('rlk_id', flat=True).distinct())
                    if not rlk_ids:
                        rlk_count = 0
                        count_price_before_kd = 0
                        count_price_after_kd = 0
                        count_price_before_kd_p = 0
                        count_price_after_kd_p = 0
                        count_success = 0
                        count_success_p = 0
                        rlk_ids = []  # Убеждаемся, что переменная определена
                    else:
                        est_qs = RegInteractivOcenka.objects.filter(rlk_id__in=rlk_ids)
                
                # Фильтры по аналитику и типу приема
                if analyst_id:
                    est_qs = est_qs.filter(
                        Q(staff_eco_1__id=analyst_id) |
                        Q(staff_eco_2__id=analyst_id)
                    )
                if type_reception_ids:
                    est_qs = est_qs.filter(page_documents__type_reception__id__in=type_reception_ids)
                
                
                # Подсчитываем через агрегацию
                rlk_count = lo_qs.values('vin').distinct().count()
                count_price_before_kd = lo_qs.filter(page_soglasovanie__price_before_kd__gt = 0).values('vin').distinct().count() + lo_qs.filter(page_remote__price_eco__gt = 0).filter(page_soglasovanie = None).values('vin').distinct().count()
                count_price_after_kd = lo_qs.filter(page_soglasovanie__price_after_kd__gt = 0).count()
                rlk_ids = lo_qs.values_list('rlk_id', flat=True)
                # Подсчет принятых через DocLO (только активные в периоде)
                accepted_count = DocLO.objects.filter(
                    rlk_id__in=rlk_ids,
                    active=True,
                ).count()
                
                count_success = accepted_count
                count_price_before_kd_p = _conversion(count_price_before_kd, rlk_count)
                count_price_after_kd_p = _conversion(count_price_after_kd, count_price_before_kd)
                count_success_p = _conversion(count_success, count_price_after_kd)
    
    # Статистика по ценовым категориям
    price_category_stats = []
    if rlk_ids:
        # Используем уже полученные est_qs и accepted_rlk_ids из статистики по типам приема
        # Если est_qs не определен, создаем его
        if 'est_qs' not in locals():
            est_qs = RegInteractivOcenka.objects.filter(rlk_id__in=rlk_ids)
            if type_reception_ids:
                est_qs = est_qs.filter(page_documents__type_reception__id__in=type_reception_ids)
        
        if not accepted_rlk_ids:
            # Получаем ID принятых если еще не получены
            if type_report_id == 3:
                accepted_rlk_ids = set(DocLO.objects.filter(
                    rlk_id__in=rlk_ids,
                    active=True,
                    dataTime__gte=date_start,
                    dataTime__lte=date_end
                ).values_list('rlk_id', flat=True))
            else:
                accepted_rlk_ids = set(DocLO.objects.filter(
                    rlk_id__in=rlk_ids,
                    active=True
                ).values_list('rlk_id', flat=True))
        
        # Получаем только нужные поля через values для оптимизации
        price_data = est_qs.values('rlk_id', 'page_soglasovanie__price_after_kd', 'page_soglasovanie__price_before_kd').filter(
            page_soglasovanie__price_after_kd__gt=0
        )
        
        price_categories = defaultdict(lambda: {'total': 0, 'before_kd': 0, 'after_kd': 0, 'success': 0})
        
        # Обрабатываем данные из values (быстрее чем select_related)
        for item in price_data:
            price_after = item.get('page_soglasovanie__price_after_kd') or 0
            price_before = item.get('page_soglasovanie__price_before_kd') or 0
            rlk_id = item.get('rlk_id')
            
            if price_after > 0:
                category = _get_price_category(price_after)
                price_categories[category]['total'] += 1
                if price_before > 0:
                    price_categories[category]['before_kd'] += 1
                price_categories[category]['after_kd'] += 1
                if rlk_id in accepted_rlk_ids:
                    price_categories[category]['success'] += 1
        
        for category, stats in sorted(price_categories.items(), key=lambda x: _get_price_category_order(x[0])):
            price_category_stats.append({
                'name': category,
                'total': stats['total'],
                'before_kd': stats['before_kd'],
                'after_kd': stats['after_kd'],
                'success': stats['success'],
                'conv_before': _conversion(stats['before_kd'], stats['total']),
                'conv_after': _conversion(stats['after_kd'], stats['before_kd']),
                'conv_success': _conversion(stats['success'], stats['after_kd']),
            })
    
    # Эффективность дистанционной оценки и временные промежутки на основе TradeInFunnel
    date_invalid = DT.date(1, 1, 1)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    valid_date_start_estimation = Q(date_start_estimation__isnull=False) & ~Q(date_start_estimation=date_invalid)
    
    # Базовый QuerySet с фильтрами для TradeInFunnel
    funnel_qs = TradeInFunnel.objects.all()
    if date_start and date_end:
        funnel_qs = funnel_qs.filter(date_rlk__gte=date_start, date_rlk__lte=date_end)
    if unit_ids:
        funnel_qs = funnel_qs.filter(unit_id__in=unit_ids)
    if staff_id:
        funnel_qs = funnel_qs.filter(staff_id=staff_id)
    if analyst_id:
        funnel_qs = funnel_qs.filter(
            Q(analyst_remote_id=analyst_id) | Q(analyst_before_id=analyst_id) | Q(analyst_after_id=analyst_id)
        )
    if type_reception_ids:
        funnel_qs = funnel_qs.filter(type_reception_id__in=type_reception_ids)
    
    # Подсчет эффективности дистанционной оценки
    remote_effectiveness = {
        'total_remote': funnel_qs.filter(valid_date_remote).count(),
        'got_price_before': funnel_qs.filter(valid_date_remote).filter(valid_date_before).count(),
        'got_price_after': funnel_qs.filter(valid_date_remote).filter(valid_date_after).count(),
        'accepted': funnel_qs.filter(valid_date_remote).filter(valid_date_reception).count(),
    }
    
    # Проценты конверсии
    if remote_effectiveness['total_remote'] > 0:
        remote_effectiveness['conv_to_before'] = round(remote_effectiveness['got_price_before'] / remote_effectiveness['total_remote'] * 100, 1)
        remote_effectiveness['conv_to_after'] = round(remote_effectiveness['got_price_after'] / remote_effectiveness['total_remote'] * 100, 1)
        remote_effectiveness['conv_to_accepted'] = round(remote_effectiveness['accepted'] / remote_effectiveness['total_remote'] * 100, 1)
    else:
        remote_effectiveness['conv_to_before'] = 0
        remote_effectiveness['conv_to_after'] = 0
        remote_effectiveness['conv_to_accepted'] = 0
    
    # Временные промежутки между датами
    time_intervals_data = funnel_qs.values(
        'date_rlk', 'date_start_estimation', 'date_remote_success', 
        'date_before_success', 'date_after_success', 'date_reception_success'
    )
    
    # Собираем промежутки
    intervals_rlk_to_start = []
    intervals_start_to_remote = []
    intervals_start_to_before = []
    intervals_before_to_after = []
    intervals_after_to_reception = []
    
    for item in time_intervals_data:
        date_rlk = item.get('date_rlk')
        date_start_est = item.get('date_start_estimation')
        date_remote = item.get('date_remote_success')
        date_before = item.get('date_before_success')
        date_after = item.get('date_after_success')
        date_reception = item.get('date_reception_success')
        
        # Проверяем валидность дат (не None и не 1,1,1)
        def is_valid_date(d):
            if d is None:
                return False
            # Приводим к date для сравнения
            if isinstance(d, DT.datetime):
                d_date = d.date()
            elif isinstance(d, DT.date):
                d_date = d
            else:
                return False
            # Сравниваем с date_invalid (1,1,1)
            return d_date != date_invalid
        
        # РЛК до начала оценки
        if is_valid_date(date_rlk) and is_valid_date(date_start_est):
            delta = (date_start_est.date() if isinstance(date_start_est, DT.datetime) else date_start_est) - \
                    (date_rlk.date() if isinstance(date_rlk, DT.datetime) else date_rlk)
            if delta.days >= 0:
                intervals_rlk_to_start.append(delta.days)
        
        # Начало оценки до дистанционной оценки
        if is_valid_date(date_start_est) and is_valid_date(date_remote):
            delta = (date_remote.date() if isinstance(date_remote, DT.datetime) else date_remote) - \
                    (date_start_est.date() if isinstance(date_start_est, DT.datetime) else date_start_est)
            if delta.days >= 0:
                intervals_start_to_remote.append(delta.days)
        
        # Начало оценки до до КД (если нет дистанционной)
        if is_valid_date(date_start_est) and is_valid_date(date_before) and not is_valid_date(date_remote):
            delta = (date_before.date() if isinstance(date_before, DT.datetime) else date_before) - \
                    (date_start_est.date() if isinstance(date_start_est, DT.datetime) else date_start_est)
            if delta.days >= 0:
                intervals_start_to_before.append(delta.days)
        
        # До КД до после КД
        if is_valid_date(date_before) and is_valid_date(date_after):
            delta = (date_after.date() if isinstance(date_after, DT.datetime) else date_after) - \
                    (date_before.date() if isinstance(date_before, DT.datetime) else date_before)
            if delta.days >= 0:
                intervals_before_to_after.append(delta.days)
        
        # После КД до принятия
        if is_valid_date(date_after) and is_valid_date(date_reception):
            delta = (date_reception.date() if isinstance(date_reception, DT.datetime) else date_reception) - \
                    (date_after.date() if isinstance(date_after, DT.datetime) else date_after)
            if delta.days >= 0:
                intervals_after_to_reception.append(delta.days)
    
    # Вычисляем средние значения
    def avg_days(intervals):
        return round(sum(intervals) / len(intervals), 1) if intervals else 0
    
    time_intervals = {
        'rlk_to_start': {
            'avg_days': avg_days(intervals_rlk_to_start),
            'count': len(intervals_rlk_to_start),
        },
        'start_to_remote': {
            'avg_days': avg_days(intervals_start_to_remote),
            'count': len(intervals_start_to_remote),
        },
        'start_to_before': {
            'avg_days': avg_days(intervals_start_to_before),
            'count': len(intervals_start_to_before),
        },
        'before_to_after': {
            'avg_days': avg_days(intervals_before_to_after),
            'count': len(intervals_before_to_after),
        },
        'after_to_reception': {
            'avg_days': avg_days(intervals_after_to_reception),
            'count': len(intervals_after_to_reception),
        },
    }

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d') or '',
        'date_end': date_end.strftime('%Y-%m-%d') or '',
        'type_report_id': type_report_id,
        'unit_id': unit_id or '',
        'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
        'unit_ids_list': unit_ids,  # Список для проверки в шаблоне
        'unit_group_ids': ','.join(map(str, unit_group_ids)) if unit_group_ids else '',
        'unit_group_ids_list': unit_group_ids,  # Список для проверки в шаблоне
        'source_unit_ids': ','.join(map(str, source_unit_ids)) if source_unit_ids else '',
        'source_unit_ids_list': source_unit_ids,  # Список для проверки в шаблоне
        'staff_id': staff_id or '',
        'staff_ids': ','.join(map(str, staff_ids)) if staff_ids else '',
        'staff_ids_list': staff_ids,  # Список для проверки в шаблоне
        'analyst_id': analyst_id or '',
        'analyst_ids': ','.join(map(str, analyst_ids)) if analyst_ids else '',
        'analyst_ids_list': analyst_ids,  # Список для проверки в шаблоне
        'type_reception_id': type_reception_id or '',
        'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
        'type_reception_ids_list': type_reception_ids,  # Список для проверки в шаблоне
        'brand': brand or '',
    }

    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'rlk_count': rlk_count,
        'count_price_before_kd': count_price_before_kd,
        'count_price_after_kd': count_price_after_kd,
        'count_price_before_kd_p': count_price_before_kd_p,
        'count_price_after_kd_p': count_price_after_kd_p,
        'count_success': count_success,
        'count_success_p': count_success_p,
        'filters': filters,
        'units': units,
        'unit_groups': unit_groups,
        'source_units': source_units,
        'staffs': staffs,
        'analysts': analysts,
        'type_receptions': type_receptions,
        'type_reception_stats': type_reception_stats,
        'price_category_stats': price_category_stats,
        'remote_effectiveness': remote_effectiveness,
        'time_intervals': time_intervals,
        'no_data': rlk_count == 0,
    }

    return render(request, 'lo/tradein_funnel_new.html', {'params': params})


def tradein_funnel_export(request):
    """Экспорт VIN номеров в Excel для блоков воронки"""
    vin_list = None

    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        return HttpResponseRedirect('/')
    
    export_type = request.GET.get('export_type', '')  # before_kd, after_kd, success
    
    if export_type not in ['before_kd', 'after_kd', 'success', 'rl']:
        return HttpResponse('Неверный тип экспорта', status=400)
    
    # Парсим параметры фильтров (аналогично tradein_funnel_new)
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    type_report_id = _get_int(request.GET.get('type_report_id')) or 1
    
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    unit_group_ids = _parse_multiple_ints(request.GET.get('unit_group_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    source_unit_ids = _parse_multiple_ints(request.GET.get('source_unit_ids', ''))
    
    unit_id = _get_int(request.GET.get('unit_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    analyst_id = _get_int(request.GET.get('analyst_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    
    # Получаем подразделения из групп
    if unit_group_ids:
        unit_groups = RefUnitGroup.objects.filter(id__in=unit_group_ids).prefetch_related('units')
        for group in unit_groups:
            for unit in group.units.all():
                if unit.id not in unit_ids:
                    unit_ids.append(unit.id)
    
    # Базовый Q объект
    base_rlk_q = Q(
        Q(type__id=2, unit_dc__buauto=True) |
        Q(type__id=7, eco=True) |
        Q(type__id=1, eco=True) |
        Q(type__id=19, eco=True) |
        Q(eco=True)
    )
    
    # Получаем rlk_ids в зависимости от варианта отчета
    if type_report_id == 1:
        docs_base = DocRLK.objects.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        ).filter(base_rlk_q)
        
        if unit_ids:
            docs_base = docs_base.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
        if source_unit_ids:
            docs_base = docs_base.filter(
                Q(unit_dc__id__in=source_unit_ids) |
                Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
            )
        if staff_id:
            docs_base = docs_base.filter(staff__id=staff_id)
        
        rlk_ids = list(docs_base.values_list('id', flat=True))
        # Фильтруем по типу экспорта
        if export_type == 'before_kd':
            count_price_before_kd_q = RegInteractivOcenka.objects.filter(
                start_estimation__gte=date_start,
                start_estimation__lte=date_end
            ) | RegInteractivOcenka.objects.filter(
                page_remote__start_estimation__gte=date_start,
                page_remote__start_estimation__lte=date_end
            )
            vin_list = count_price_before_kd_q.values_list('vin', flat=True).distinct().order_by('vin')   
        elif export_type == 'after_kd':
            vin_list = RegInteractivOcenka.objects.filter(
                date_s_diag__gte = date_start,
                date_s_diag__lte = date_end
            ).values_list('vin', flat=True) 
        elif export_type == 'success':
            vin_list = DocLO.objects.filter(
                    dataTime__gte=date_start,
                    dataTime__lte=date_end,
                    active=True
                ).values_list('vin', flat=True)
            
    elif type_report_id == 2:
        docs_base = DocRLK.objects.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        ).filter(base_rlk_q)
        
        if unit_ids:
            docs_base = docs_base.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
        if source_unit_ids:
            docs_base = docs_base.filter(
                Q(unit_dc__id__in=source_unit_ids) |
                Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
            )
        if staff_id:
            docs_base = docs_base.filter(staff__id=staff_id)
        
        rlk_ids = list(docs_base.values_list('id', flat=True))
        
    else:  # type_report_id == 3
        lo_qs = RegInteractivOcenka.objects.filter(
            start_estimation__gte=date_start,
            start_estimation__lte=date_end
        )
        
        # Получаем rlk_id из листов оценки
        lo_rlk_ids = list(lo_qs.values_list('rlk__id', flat=True).distinct())
        
        if not lo_rlk_ids:
            rlk_ids = []
        else:
            docs_base = DocRLK.objects.filter(id__in=lo_rlk_ids).filter(base_rlk_q)
            
            if unit_ids:
                docs_base = docs_base.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
            if source_unit_ids:
                docs_base = docs_base.filter(
                    Q(unit_dc__id__in=source_unit_ids) |
                    Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
                )
            if staff_id:
                docs_base = docs_base.filter(staff__id=staff_id)
            
        rlk_ids = list(docs_base.values_list('id', flat=True))
        # Подсчитываем через агрегацию
        rlk_count = lo_qs.values('vin').distinct().count()
        count_price_before_kd = lo_qs.filter(page_soglasovanie__price_before_kd__gt = 0).values('vin').distinct() | lo_qs.filter(page_remote__price_eco__gt = 0).filter(page_soglasovanie = None).values('vin').distinct()
        count_price_after_kd = lo_qs.filter(page_soglasovanie__price_after_kd__gt = 0).count()
        rlk_ids = lo_qs.values_list('rlk_id', flat=True)
        # Подсчет принятых через DocLO (только активные в периоде)
        accepted_count = DocLO.objects.filter(
            rlk_id__in=rlk_ids,
            active=True,
        ).count()
        
        if export_type == 'rl':
            rl = lo_qs.values('rlk__dataTime', 'rlk__nomer', 'rlk__unit__name', 'rlk__unit_dc__name', 'rlk__vin_trade_in', 'rlk__reasonArchive',)
            wb = Workbook()
            ws = wb.active
            ws.title = "РЛ номера"
            ws.append(['Дата', 'РЛ номера', 'Подразделение', 'VIN', 'Архив',])
            for rl_data in rl:
                unit_name = rl_data['rlk__unit__name']
                if unit_name == None:
                    unit_name = rl_data['rlk__unit_dc__name']
                ws.append([rl_data['rlk__dataTime'], rl_data['rlk__nomer'], unit_name, rl_data['rlk__vin_trade_in'], rl_data['rlk__reasonArchive']])
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="vin_export_{export_type}.xlsx"'
            wb.save(response)
            return response
        elif export_type == 'before_kd': 
            vin_list = count_price_before_kd.values_list('vin', flat = True)
            wb = Workbook()
            ws = wb.active
            ws.title = "VIN номера"
            ws.append(['VIN'])
            for vin in sorted(vin_list):
                ws.append([vin])
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="vin_export_{export_type}.xlsx"'
            wb.save(response)
            return response
        elif export_type == 'after_kd':
            vin_list = DocLO.objects.filter(
                rlk_id__in=rlk_ids,
                active=True,
            ).values_list('vin', flat = True)
            wb = Workbook()
            ws = wb.active
            ws.title = "VIN номера"
            ws.append(['VIN'])
            for vin in sorted(vin_list):
                ws.append([vin])
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="vin_export_{export_type}.xlsx"'
            wb.save(response)
            return response
        elif export_type == 'success':
            vin_list = DocLO.objects.filter(
                rlk_id__in=rlk_ids,
                active=True,
            ).values_list('vin', flat = True)
            wb = Workbook()
            ws = wb.active
            ws.title = "VIN номера"
            ws.append(['VIN'])
            for vin in sorted(vin_list):
                ws.append([vin])
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="vin_export_{export_type}.xlsx"'
            wb.save(response)
            return response
    
    if not rlk_ids:
        # Нет данных - возвращаем пустой Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "VIN номера"
        ws.append(['VIN'])
        ws.append(['Нет данных'])
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="vin_export_{export_type}.xlsx"'
        wb.save(response)
        return response
    
    # Получаем оценки
    est_qs = RegInteractivOcenka.objects.filter(rlk_id__in=rlk_ids)
    
    if analyst_id:
        est_qs = est_qs.filter(
            Q(staff_eco_1__id=analyst_id) |
            Q(staff_eco_2__id=analyst_id)
        )
    if type_reception_ids:
        est_qs = est_qs.filter(page_documents__type_reception__id__in=type_reception_ids)
    
    # Фильтруем по типу экспорта
    if export_type == 'rl':
        
        rl_qs = docs_base.exclude(vin_trade_in = '') | docs_base.filter(vin_trade_in = '')
        rl = rl_qs.values('dataTime', 'nomer', 'unit__name', 'unit_dc__name', 'vin_trade_in', 'reasonArchive',)
        wb = Workbook()
        ws = wb.active
        ws.title = "РЛ номера"
        # Заголовок
        ws.append(['Дата', 'РЛ номера', 'Подразделение', 'VIN', 'Архив',])
        # Данные
        for rl_data in rl:
            unit_name = rl_data['unit__name']
            if unit_name == None:
                unit_name = rl_data['unit_dc__name']
            ws.append([rl_data['dataTime'], rl_data['nomer'], unit_name, rl_data['vin_trade_in'], rl_data['reasonArchive']])

    elif export_type == 'before_kd':
        price_before_kd_q = RegInteractivOcenka.objects.filter(
                start_estimation__gte=date_start,
                start_estimation__lte=date_end
            ) | RegInteractivOcenka.objects.filter(
                page_remote__start_estimation__gte=date_start,
                page_remote__start_estimation__lte=date_end
            )
        vin_list = price_before_kd_q.values_list('vin', flat=True).distinct()
        wb = Workbook()
        ws = wb.active
        ws.title = "VIN номера"
        # Заголовок
        ws.append(['VIN'])
        # Данные
        for vin in sorted(vin_list):
            ws.append([vin])
    elif export_type == 'after_kd':
        vin_list = RegInteractivOcenka.objects.filter(
                date_s_diag__gte=date_start,
                date_s_diag__lte=date_end
            ).values('vin')
        # VIN с price_after_kd > 0
        # Создаем Excel файл
        wb = Workbook()
        ws = wb.active
        ws.title = "VIN номера"
        # Заголовок
        ws.append(['VIN'])
        # Данные
        for vin in sorted(vin_list):
            ws.append([vin])

    elif export_type == 'success':
        # VIN с активными DocLO (как в основной функции)
        if type_report_id == 3:
            accepted_rlk_ids = set(DocLO.objects.filter(
                rlk_id__in=rlk_ids,
                active=True,
                dataTime__gte=date_start,
                dataTime__lte=date_end
            ).values_list('rlk_id', flat=True))
        else:
            accepted_rlk_ids = set(DocLO.objects.filter(
                dataTime__gte=date_start,
                dataTime__lte=date_end,
                active=True
            ).values_list('rlk_id', flat=True))
        
        vin_list = DocLO.objects.filter(
                dataTime__gte=date_start,
                dataTime__lte=date_end,
                active=True
            ).values_list('vin', flat=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "VIN номера"
        ws.append(['VIN'])
        for vin in sorted(vin_list):
            ws.append([vin])

    # Формируем ответ
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    export_names = {
        'рл': 'Рабочие_листы',
        'before_kd': 'До_диагностики',
        'after_kd': 'После_диагностики',
        'success': 'Принято'
    }
    
    filename = f"export_{export_names.get(export_type, export_type)}_{date_start.strftime('%Y%m%d')}_{date_end.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response


def tradein_funnel_rejected(request):
    """Отображение автомобилей, которые были осмотрены или прошли диагностику, но не приняты"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    
    default_end     = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start   = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)

    date_start  = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end    = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    # Множественный выбор фильтров
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    unit_group_ids = _parse_multiple_ints(request.GET.get('unit_group_ids', ''))
    source_unit_ids = _parse_multiple_ints(request.GET.get('source_unit_ids', ''))
    staff_ids = _parse_multiple_ints(request.GET.get('staff_ids', ''))
    analyst_ids = _parse_multiple_ints(request.GET.get('analyst_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    
    # Одиночные фильтры
    unit_id = _get_int(request.GET.get('unit_id'))
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    staff_id = _get_int(request.GET.get('staff_id'))
    if staff_id and staff_id not in staff_ids:
        staff_ids.append(staff_id)
    analyst_id = _get_int(request.GET.get('analyst_id'))
    if analyst_id and analyst_id not in analyst_ids:
        analyst_ids.append(analyst_id)
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    
    # Получаем подразделения из групп
    if unit_group_ids:
        unit_groups = RefUnitGroup.objects.filter(id__in=unit_group_ids).prefetch_related('units')
        for group in unit_groups:
            for unit in group.units.all():
                if unit.id not in unit_ids:
                    unit_ids.append(unit.id)
    
    # Загружаем справочники
    units = RefUnit.objects.filter(buauto=True).filter(active_eco=True).exclude(name='').order_by('name')
    unit_groups = RefUnitGroup.objects.filter(active=True, bu_auto=True).order_by('name')
    
    # Получаем список источников поступления
    source_unit_ids_from_rlk = set()
    source_unit_ids_from_rlk.update(
        DocRLK.objects.filter(eco=True).exclude(unit_dc__isnull=True).values_list('unit_dc_id', flat=True).distinct()
    )
    source_unit_ids_from_rlk.update(
        DocRLK.objects.filter(eco=True, unit_dc__isnull=True).exclude(unit__isnull=True).values_list('unit_id', flat=True).distinct()
    )
    source_units = RefUnit.objects.filter(id__in=source_unit_ids_from_rlk).exclude(name='').order_by('name')
    
    # Базовый Q объект для DocRLK
    base_rlk_q = Q(
        Q(type__id=2, unit_dc__buauto=True) |
        Q(type__id=7, eco=True) |
        Q(type__id=1, eco=True) |
        Q(type__id=19, eco=True) |
        Q(eco=True)
    )
    
    # Получаем список оценщиков из всех оценок в периоде (до применения фильтров)
    docs_all = DocRLK.objects.filter(
        dataTime__gte=date_start,
        dataTime__lte=date_end
    ).filter(base_rlk_q)
    staff_ids_from_est = list(RegInteractivOcenka.objects.filter(
        rlk__in=docs_all.values_list('id', flat=True)
    ).exclude(staff__isnull=True).values_list('staff_id', flat=True).distinct())
    staffs = RefStaff.objects.filter(id__in=staff_ids_from_est).exclude(name='').order_by('name') if staff_ids_from_est else RefStaff.objects.none()
    
    # Получаем список аналитиков из всех оценок в периоде (до применения фильтров)
    analyst_ids_from_est = set()
    analyst_ids_from_est.update(
        RegInteractivOcenka.objects.filter(
            rlk__in=docs_all.values_list('id', flat=True)
        ).exclude(staff_eco_1__isnull=True).values_list('staff_eco_1_id', flat=True).distinct()
    )
    analyst_ids_from_est.update(
        RegInteractivOcenka.objects.filter(
            rlk__in=docs_all.values_list('id', flat=True)
        ).exclude(staff_eco_2__isnull=True).values_list('staff_eco_2_id', flat=True).distinct()
    )
    analysts = RefStaff.objects.filter(id__in=list(analyst_ids_from_est)).exclude(name='').order_by('name') if analyst_ids_from_est else RefStaff.objects.none()
    
    # Получаем список типов приема из всех оценок в периоде (до применения фильтров)
    type_reception_ids_from_est = set()
    type_reception_ids_from_est.update(
        RegInteractivOcenka.objects.filter(
            rlk__in=docs_all.values_list('id', flat=True)
        ).exclude(page_documents__type_reception__isnull=True).values_list('page_documents__type_reception__id', flat=True).distinct()
    )
    type_reception_ids_from_est.update(
        RegInteractivOcenka.objects.filter(
            rlk__in=docs_all.values_list('id', flat=True)
        ).exclude(page_remote__type_reception__isnull=True).values_list('page_remote__type_reception__id', flat=True).distinct()
    )
    type_receptions = RefTypeReceptionCarsOrganization.objects.filter(
        id__in=list(type_reception_ids_from_est)
    ).exclude(name='').order_by('name') if type_reception_ids_from_est else RefTypeReceptionCarsOrganization.objects.none()
    
    # Получаем DocRLK в периоде
    docs = DocRLK.objects.filter(
        dataTime__gte=date_start,
        dataTime__lte=date_end
    ).filter(base_rlk_q)
    
    # Применяем фильтры
    if unit_ids:
        docs = docs.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))

    if source_unit_ids:
        docs = docs.filter(
            Q(unit_dc__id__in=source_unit_ids) |
            Q(unit__id__in=source_unit_ids, unit_dc__isnull=True)
        )
    
    # Подключаем оценки и листы оценки
    subquery_est = RegInteractivOcenka.objects.filter(rlk__id=OuterRef('id'))
    subquery_lo = DocLO.objects.filter(rlk__id=OuterRef('id'))
    
    # Фильтр по причине архива (если указан)
    reason_archive_filter = request.GET.get('reason_archive', '').strip()
    
    # Дополнительные фильтры для анализа причин непринятия
    has_agreement_filter = request.GET.get('has_agreement', '').strip()
    has_footing_agreement_filter = request.GET.get('has_footing_agreement', '').strip()
    has_diagnostics_filter = request.GET.get('has_diagnostics', '').strip()
    has_lo_filter = request.GET.get('has_lo', '').strip()
    status_filter = request.GET.get('status', '').strip()
    price_before_exists_filter = request.GET.get('price_before_exists', '').strip()
    price_after_exists_filter = request.GET.get('price_after_exists', '').strip()
    
    docs = docs.annotate(
        has_estimation=Exists(RegInteractivOcenka.objects.filter(rlk=OuterRef('id'))),
        start_estimation=Subquery(subquery_est.values('start_estimation')[:1]),
        has_diagnostics=Subquery(subquery_est.values('page_soglasovanie__comment_diagnostica')[:1]),
        no_diagnostica=Subquery(subquery_est.values('page_soglasovanie__no_diagnostica')[:1]),
        lo_active=Subquery(subquery_lo.values('active')[:1]),
        lo_exists=Exists(DocLO.objects.filter(rlk=OuterRef('id'))),
        status_name=Subquery(subquery_est.values('status__name')[:1]),
        price_before_kd=Subquery(subquery_est.values('page_soglasovanie__price_before_kd')[:1]),
        price_after_kd=Subquery(subquery_est.values('page_soglasovanie__price_after_kd')[:1]),
        price_auto_2=Subquery(subquery_est.values('page_soglasovanie__price_auto_2')[:1]),
        type_reception_name=Subquery(subquery_est.values('page_documents__type_reception__name')[:1]),
        type_reception_id=Subquery(subquery_est.values('page_documents__type_reception__id')[:1]),
        # Для дистанционной оценки
        page_remote_type_reception=Subquery(subquery_est.values('page_remote__type_reception__name')[:1]),
        page_remote_type_reception_id=Subquery(subquery_est.values('page_remote__type_reception__id')[:1]),
        page_remote_price_auto=Subquery(subquery_est.values('page_remote__price_auto')[:1]),
        page_remote_price_eco=Subquery(subquery_est.values('page_remote__price_eco')[:1]),
        is_remote=Exists(RegInteractivOcenka.objects.filter(rlk=OuterRef('id')).exclude(page_remote__isnull=True)),
        vin=Subquery(subquery_est.values('vin')[:1]),
        mark=Subquery(subquery_est.values('modification__model__mark__name')[:1]),
        model=Subquery(subquery_est.values('modification__model__name')[:1]),
        modification=Subquery(subquery_est.values('modification__name')[:1]),
        year=Subquery(subquery_est.values('year')[:1]),
        staff_name=Subquery(subquery_est.values('staff__name')[:1]),
        estimation_staff_id=Subquery(subquery_est.values('staff__id')[:1]),
        # Аналитики
        analyst_remote_id=Subquery(subquery_est.values('staff_eco_1__id')[:1]),
        analyst_before_id=Subquery(subquery_est.values('staff_eco_2__id')[:1]),
        analyst_after_id=Subquery(subquery_est.values('staff_eco_2__id')[:1]),
        reg_estimation_id=Subquery(subquery_est.values('id')[:1]),
    )
    
    # Фильтруем: были осмотрены (start_estimation не пусто) ИЛИ прошли диагностику
    # И НЕ приняты (lo_active != True)
    # Проверяем диагностику через дополнительный подзапрос
    est_with_diagnostics = RegInteractivOcenka.objects.filter(
        rlk=OuterRef('id')
    ).filter(
        Q(page_soglasovanie__comment_diagnostica__isnull=False) |
        Q(page_soglasovanie__no_diagnostica=True)
    )
    
    docs = docs.annotate(
        has_diagnostics_check=Exists(est_with_diagnostics)
    ).filter(
        Q(has_estimation=True) & (
            Q(start_estimation__isnull=False) |
            Q(has_diagnostics_check=True)
        ) & (
            Q(lo_active__isnull=True) |
            Q(lo_active=False)
        )
    )
    
    # Фильтр по причине архива (если указан)
    if reason_archive_filter:
        docs = docs.filter(reasonArchive__istartswith=reason_archive_filter)
    
    # Фильтр по оценщикам
    if staff_ids:
        docs = docs.filter(staff_id__in=staff_ids)
    
    # Фильтр по аналитикам
    if analyst_ids:
        analyst_q = Q()
        for a_id in analyst_ids:
            analyst_q |= Q(analyst_remote_id=a_id) | Q(analyst_before_id=a_id) | Q(analyst_after_id=a_id)
        docs = docs.filter(analyst_q)
    
    # Фильтр по типам приема
    if type_reception_ids:
        type_reception_q = Q()
        for tr_id in type_reception_ids:
            type_reception_q |= Q(type_reception_id=tr_id) | Q(page_remote_type_reception_id=tr_id)
        docs = docs.filter(type_reception_q)
    
    # Собираем все документы в один список (без группировки)
    rejected_items = []
    reason_archive_stats = defaultdict(int)  # Статистика причин архива
    failure_reasons_stats = defaultdict(int)  # Статистика причин срыва
    footing_stats = defaultdict(int)  # Статистика по основаниям
    
    # Импортируем модели для анализа сделки
    from documents.models import DocCarShipment, DocCarAgreement
    
    for doc in docs.select_related('unit', 'unit_dc', 'footing').prefetch_related('footing'):
        # Определяем подразделение (источник поступления)
        source_unit = doc.unit_dc if doc.unit_dc else doc.unit
        source_unit_name = source_unit.name if source_unit else 'Не указано'
        
        # Определяем причину архива (первая часть до ":")
        reason_archive_short = ''
        if doc.reasonArchive:
            reason_archive_short = doc.reasonArchive.split(':')[0].strip()
            if reason_archive_short:
                reason_archive_stats[reason_archive_short] += 1
        
        # Определяем тип приема, авторасчет и цену ецо
        # Для дистанционной оценки берем из page_remote
        if doc.is_remote and doc.status_name and 'дистанционн' in doc.status_name.lower():
            type_reception = doc.page_remote_type_reception or ''
            price_auto_2 = doc.page_remote_price_auto or 0
            price_eco = doc.page_remote_price_eco or 0
        else:
            type_reception = doc.type_reception_name or ''
            price_auto_2 = doc.price_auto_2 or 0
            price_eco = 0
        
        # Анализ сделки по документу основанию (footing)
        footing_analysis = []
        footing_dop = DocRLK.objects.filter(uin = doc.uin).exclude(footing = None).values_list('footing__uin', flat = True)
        # Проверяем отгрузку
        shipment = DocCarShipment.objects.filter(rlk__uin__in=footing_dop, active=True).first()
        if shipment:
            footing_analysis.append(f"Отгрузка: {shipment.nomer} от {shipment.dataTime.strftime('%d.%m.%Y')}")
        
        # Проверяем соглашение
        agreement = DocCarAgreement.objects.filter(rlk__uin__in=footing_dop, active=True).first()
        if agreement:
            footing_analysis.append(f"Соглашение: {agreement.nomer} от {agreement.dataTime.strftime('%d.%m.%Y')}")
        dops = DocRLK.objects.filter(uin__in = footing_dop)
        for dop in dops:
            if dop.archive:
                footing_analysis.append(f"Основание в архиве: {dop.reasonArchive or 'Без причины'}")

        
        # Анализ причин срыва
        failure_analysis = []
        if not doc.lo_exists:
            failure_analysis.append("Не создан лист оценки")
            failure_reasons_stats["Не создан лист оценки"] += 1
        elif doc.lo_active is False:
            failure_analysis.append("Лист оценки не проведен")
            failure_reasons_stats["Лист оценки не проведен"] += 1
        
        if doc.status_name and 'принят' not in doc.status_name.lower():
            failure_analysis.append(f"Статус: {doc.status_name}")
            failure_reasons_stats[f"Статус: {doc.status_name}"] += 1
        
        if doc.price_before_kd and doc.price_before_kd == 0:
            failure_analysis.append("Не согласована цена до КД")
            failure_reasons_stats["Не согласована цена до КД"] += 1
        elif doc.price_after_kd and doc.price_after_kd == 0:
            failure_analysis.append("Не согласована цена после КД")
            failure_reasons_stats["Не согласована цена после КД"] += 1
        
        if not doc.start_estimation:
            failure_analysis.append("Оценка не начата")
            failure_reasons_stats["Оценка не начата"] += 1
        
        if doc.archive:
            failure_analysis.append("Документ в архиве")
            failure_reasons_stats["Документ в архиве"] += 1
        
        # Определяем наличие соглашения
        has_agreement = (doc.price_before_kd and doc.price_before_kd > 0) or (doc.price_after_kd and doc.price_after_kd > 0)
        
        # Определяем наличие соглашения/отгрузки в основании
        has_footing_agreement = len(footing_analysis) > 0
        if has_footing_agreement:
            for footing_item in footing_analysis:
                if "Соглашение" in footing_item:
                    footing_stats["Есть соглашение в основании"] += 1
                elif "Отгрузка" in footing_item:
                    footing_stats["Есть отгрузка в основании"] += 1
                elif "Основание в архиве" in footing_item:
                    footing_stats["Основание в архиве"] += 1
        
        # Применяем дополнительные фильтры
        if has_agreement_filter == 'yes' and not has_agreement:
            continue
        if has_agreement_filter == 'no' and has_agreement:
            continue
        
        if has_footing_agreement_filter == 'yes' and not has_footing_agreement:
            continue
        if has_footing_agreement_filter == 'no' and has_footing_agreement:
            continue
        
        if has_diagnostics_filter == 'yes' and not bool(doc.has_diagnostics or doc.no_diagnostica):
            continue
        if has_diagnostics_filter == 'no' and bool(doc.has_diagnostics or doc.no_diagnostica):
            continue
        
        if has_lo_filter == 'yes' and not doc.lo_exists:
            continue
        if has_lo_filter == 'no' and doc.lo_exists:
            continue
        
        if status_filter and doc.status_name and status_filter.lower() not in doc.status_name.lower():
            continue
        
        if price_before_exists_filter == 'yes' and not (doc.price_before_kd and doc.price_before_kd > 0):
            continue
        if price_before_exists_filter == 'no' and (doc.price_before_kd and doc.price_before_kd > 0):
            continue
        
        if price_after_exists_filter == 'yes' and not (doc.price_after_kd and doc.price_after_kd > 0):
            continue
        if price_after_exists_filter == 'no' and (doc.price_after_kd and doc.price_after_kd > 0):
            continue
        
        rejected_items.append({
            'rlk': doc,
            'nomer': doc.nomer,
            'dataTime': doc.dataTime,
            'unit_name': source_unit_name,
            'clientName': doc.clientName,
            'vin': doc.vin or doc.vin_trade_in or '',
            'mark': doc.mark or '',
            'model': doc.model or '',
            'modification': doc.modification or '',
            'year': doc.year or '',
            'type_reception': type_reception,
            'staff': doc.staff_name or '',
            'price_before_kd': doc.price_before_kd or 0,
            'price_after_kd': doc.price_after_kd or 0,
            'price_auto_2': price_auto_2,
            'price_eco': price_eco,
            'start_estimation': doc.start_estimation,
            'status': doc.status_name or '',
            'reasonArchive': doc.reasonArchive or '',
            'reasonArchive_short': reason_archive_short,
            'dateArchive': doc.dateArchive,
            'failure_analysis': failure_analysis,
            'footing_analysis': footing_analysis,
            'estimation_id': doc.reg_estimation_id,
            'has_diagnostics': bool(doc.has_diagnostics or doc.no_diagnostica),
            'has_agreement': has_agreement,
            'has_footing_agreement': has_footing_agreement,
            'lo_exists': doc.lo_exists,
        })
    
    # Сортируем по дате (новые сверху)
    rejected_items.sort(key=lambda x: x['dataTime'], reverse=True)
    
    filters = {
        'date_start': date_start.strftime('%Y-%m-%d') or '',
        'date_end': date_end.strftime('%Y-%m-%d') or '',
        'unit_id': unit_id or '',
        'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
        'unit_ids_list': unit_ids,
        'unit_group_ids': ','.join(map(str, unit_group_ids)) if unit_group_ids else '',
        'unit_group_ids_list': unit_group_ids,
        'source_unit_ids': ','.join(map(str, source_unit_ids)) if source_unit_ids else '',
        'source_unit_ids_list': source_unit_ids,
        'staff_id': staff_id or '',
        'staff_ids': ','.join(map(str, staff_ids)) if staff_ids else '',
        'staff_ids_list': staff_ids,
        'analyst_id': analyst_id or '',
        'analyst_ids': ','.join(map(str, analyst_ids)) if analyst_ids else '',
        'analyst_ids_list': analyst_ids,
        'type_reception_id': type_reception_id or '',
        'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
        'type_reception_ids_list': type_reception_ids,
        'reason_archive': reason_archive_filter,
        'has_agreement': has_agreement_filter,
        'has_footing_agreement': has_footing_agreement_filter,
        'has_diagnostics': has_diagnostics_filter,
        'has_lo': has_lo_filter,
        'status': status_filter,
        'price_before_exists': price_before_exists_filter,
        'price_after_exists': price_after_exists_filter,
    }
    
    # Сортируем статистику причин архива по количеству (по убыванию)
    reason_archive_stats_sorted = sorted(reason_archive_stats.items(), key=lambda x: x[1], reverse=True)
    
    # Сортируем статистику причин срыва по количеству (по убыванию)
    failure_reasons_stats_sorted = sorted(failure_reasons_stats.items(), key=lambda x: x[1], reverse=True)
    
    # Сортируем статистику по основаниям по количеству (по убыванию)
    footing_stats_sorted = sorted(footing_stats.items(), key=lambda x: x[1], reverse=True)
    
    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'filters': filters,
        'units': units,
        'unit_groups': unit_groups,
        'source_units': source_units,
        'staffs': staffs,
        'analysts': analysts,
        'type_receptions': type_receptions,
        'rejected_items': rejected_items,
        'total_count': len(rejected_items),
        'reason_archive_stats': reason_archive_stats_sorted,
        'failure_reasons_stats': failure_reasons_stats_sorted,
        'footing_stats': footing_stats_sorted,
    }
    
    return render(request, 'lo/tradein_funnel_rejected.html', {'params': params})


# УДАЛЕНО: функция tradein_funnel больше не используется, заменена на tradein_funnel_new
# Функция была удалена для освобождения кода и устранения путаницы


def eco_monitors(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    new_filtr       = request.GET.get('new_filtr', '')
    path_start      = request.path
    delite_filter   = request.GET.get('delite_filter', '')
    
    if len(delite_filter) > 0:
        if RefCustomerFiltr.objects.filter(pk = delite_filter).count() > 0:
            RefCustomerFiltr.objects.get(pk = delite_filter).delete()

    date                = request.GET.get('date_start', '')
    date_e              = request.GET.get('date_end', '')
    
    date_period = DT.datetime.now()
    date_start 	= date_period.replace(hour = 0, minute=0, second=0, microsecond=0)
    date_end    = date_period.replace(hour = 23, minute=59, second=59, microsecond=0)
    
    if date != '':
        dates = date.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_start 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            
    if date_e != '':
        dates = date_e.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_end 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            
    countList = 15

    staffKKID   = ""
    staffsKK    = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
			
    unit_id      = ""
    units_select = RefUnit.objects.filter(buauto = True).filter(active_eco = True).exclude(name = '').order_by("name")
    
    type_receptions_id = request.GET.get('type_receptions_id', '')

    staffID         = ""
    staffsSelect    = ""
    
    docs        = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 7).filter(eco = True).order_by('-dataTime')
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
    docs        = docs.annotate(
        unit_name               = Subquery(subquery.values('page_documents__unit__name')[:1])).annotate(
        unit_name_dc               = Subquery(subquery.values('page_documents__unit__id')[:1])).annotate(
        status_estimation       = Subquery(subquery.values('status__name')[:1])).annotate(
        status_estimation_id    = Subquery(subquery.values('status__id')[:1])).annotate(
        start_estimation        = Subquery(subquery.values('start_estimation')[:1])).annotate(
        end_estimation          = Subquery(subquery.values('end_estimation')[:1])).annotate(
        staff_estimation_name    = Subquery(subquery.values('staff__name')[:1])).annotate(
        staff_estimation    = Subquery(subquery.values('staff')[:1])).annotate(
        mark                = Subquery(subquery.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subquery.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subquery.values('modification__name')[:1])).annotate(
        type_estimation_ocenka = Subquery(subquery.values('page_documents__type_reception__name')[:1])).annotate(
        type_estimation_ocenka_id = Subquery(subquery.values('page_documents__type_reception__id')[:1])).annotate(
        year = Subquery(subquery.values('year')[:1])).annotate(
        vin = Subquery(subquery.values('vin')[:1])).annotate(
        lo_pk = Subquery(subquery.values('id')[:1])).annotate(
        count_data = Value(1, output_field=IntegerField())
        )

    filtr_number_doc = request.GET.get('number_doc', '')
    
    data        = docs.order_by('type_estimation_ocenka').values('type_estimation_ocenka').distinct().annotate(Sum('count_data')).exclude(type_estimation_ocenka = None)
    data_unit   = docs.order_by('unit_name').values('unit_name').distinct().annotate(Sum('count_data')).exclude(unit_name = None)
    
    count_new               = docs.filter(status_estimation_id = 1).count()
    count_estimations       = docs.filter(status_estimation_id = 2).count()
    count_soglasovanie      = docs.filter(status_estimation_id = 3).count()
    count_ok                = docs.filter(status_estimation_id = 4).count()
    count_kd                = docs.filter(status_estimation_id = 5).count()
    count_soglasovanie_kd   = docs.filter(status_estimation_id = 6).count()
    count_8                 = docs.filter(status_estimation_id = 8).count()

    count_6 = count_ok
    count_5 = count_soglasovanie_kd + count_6
    count_4 = count_kd + count_5 
    count_3 = count_soglasovanie + count_4
    count_2 = count_estimations + count_3 
    count_1 = count_new + count_estimations + count_soglasovanie + count_ok + count_kd + count_soglasovanie_kd + count_8
    
    count_1_detail = docs.filter(status_estimation_id = 1) 
    count_2_detail = docs.filter(status_estimation_id = 2) 

    if filtr_number_doc != '':
        docs = docs.filter(nomer__icontains = filtr_number_doc)    
    if type_receptions_id != '':
        type_receptions_id = int(type_receptions_id)
        docs = docs.filter(type_estimation_ocenka_id = type_receptions_id)    
    
        
    status_id = request.GET.get('status_id', '')
    if status_id != '':
        status_id = int(status_id)
        docs = docs.filter(status_estimation_id = status_id)
    else:
        docs = docs.exclude(status_estimation_id = 0)
 
    if request.GET.get('unit_id', '') != '':
        unit_id         = int(request.GET['unit_id'])
        docs            = docs.filter(unit__id = unit_id) | docs.filter(unit_dc__id = unit_id) | docs.filter(unit_name_dc = unit_id) 
        #staffsSelect    = list(RefStaff.objects.filter(unit = RefUnit.objects.get(id = unit_id)).order_by('name'))
   
    filtr = {
        'date_start'    : date_start,
        'date_end'      : date_end,
    }

    params = {
        'type'          : 'eco_monitors',
        'nav_selected'  : 4,
        'request'       : request,
        'filtr'         : filtr,
        'count_new'     : count_new,
        'count_estimations'     : count_estimations,
        'count_soglasovanie'    : count_soglasovanie,
        'count_ok'              : count_ok,
        'count_kd'              : count_kd,
        'count_soglasovanie_kd' : count_soglasovanie_kd,
        'count_1'   : count_1,
        'count_2'   : count_2,
        'count_3'   : count_3,
        'count_4'   : count_4,
        'count_5'   : count_5,
        'count_6'   : count_6,
        'count_8'   : count_8,
        'count_1_detail'    : count_1_detail,
        'count_2_detail'    : count_2_detail,
        'data_unit'         : data_unit,
        'data'              : data
    }

    return render(request, 'lo/eco_monitors.html', {'params': params})


@csrf_exempt
def post_chats_list(request):
    
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)

    channel_layer = get_channel_layer()
    message_json = json.dumps(data['message'])
    
    async_to_sync(channel_layer.group_send)(
        'chat_rlk_list_eco',
        {'type'     : 'channel_message',
         'message'  : message_json}
    )

    return JsonResponse(body_unicode, safe=False, status=status.HTTP_200_OK)


def get_chats_list(request):
    
    chats                   = Chat.objects.all()
    subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1])) 
    chats = chats.annotate(
        rlk_unit = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
        rlk_unit_dc = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
        vin = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
        mark = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
        staff_name = Subquery(subqyery_message_rlk.values('staff__name')[:1])).annotate(
        content = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_content = Subquery(subqyery_message_info.values('user')[:1]))
    
    return JsonResponse(list(chats.values()), safe=False, status=status.HTTP_200_OK)


def text_to_dict(text_json):
    text_json_replace = text_json.replace("/sdcard",'')
    data = json.loads(text_json_replace)
    return data


def get_chats_list_online_info(request, id):
    
    chats                   = Chat.objects.filter(slug = id)
    subqyery_reg_interactiv = RegInteractivOcenkaRLK.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    #subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    
    # Количество РЛК, в которых используется та же оценка (по RegInteractivOcenkaRLK.estimation)
    subq_estimation_id = RegInteractivOcenkaRLK.objects.filter(
        rlk_id=OuterRef('rlk_id')
    ).values('estimation_id')[:1]
    # Сначала аннотируем чат estimation_id, затем считаем по нему — так корреляция в подзапросе одна
    chats = chats.annotate(_estimation_id=Subquery(subq_estimation_id))
    subq_rlk_count = RegInteractivOcenkaRLK.objects.filter(
        estimation_id=OuterRef('_estimation_id')
    ).values('estimation_id').annotate(cnt=Count('id')).values('cnt')[:1]
    chats = chats.annotate(
        estimation_rlk_count=Coalesce(
            Subquery(subq_rlk_count),
            Value(0),
            output_field=IntegerField()
        )
    )
        
    # chats = chats.annotate(
    #     type_estimation_ocenka = Subquery(subqyery_reg_interactiv.values('page_documents__type_reception__name')[:1])).annotate(
    #     car_year                = Subquery(subqyery_reg_interactiv.values('year')[:1])).annotate( 
    #     car_prev_img            = Subquery(subqyery_reg_interactiv.values('prev_img')[:1])).annotate( 
    #     car_run                 = Subquery(subqyery_reg_interactiv.values('page_salon__run')[:1])).annotate(    
    #     unit_name               = Subquery(subqyery_reg_interactiv.values('page_documents__unit__name')[:1])).annotate(
    #     unit_name_dc            = Subquery(subqyery_reg_interactiv.values('page_documents__unit__id')[:1])).annotate(
    #     status_estimation       = Subquery(subqyery_reg_interactiv.values('status__name')[:1])).annotate(
    #     status_estimation_id    = Subquery(subqyery_reg_interactiv.values('status__id')[:1])).annotate(
    #     start_estimation        = Subquery(subqyery_reg_interactiv.values('start_estimation')[:1])).annotate(
    #     end_estimation          = Subquery(subqyery_reg_interactiv.values('end_estimation')[:1])).annotate(
    #     staff_estimation_name   = Subquery(subqyery_reg_interactiv.values('staff__name')[:1])).annotate(
    #     staff_estimation        = Subquery(subqyery_reg_interactiv.values('staff')[:1])).annotate(            
    #     soglasovanie_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
    #     car_price_before_kd = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_before_kd')[:1])).annotate(                       
    #     car_price_after_kd  = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_after_kd')[:1])).annotate(                       
    #     car_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
    #     car_price_sale      = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_sale')[:1])).annotate(                       
    #     car_price_bcp       = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_bcp')[:1])).annotate(                       
    #     rlk_date = Subquery(subqyery_message_rlk.values('dataTime')[:1])).annotate(    
    #     rlk_number = Subquery(subqyery_message_rlk.values('nomer')[:1])).annotate(    
    #     rlk_unit = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
    #     rlk_unit_dc = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
    #     vin = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
    #     mark = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
    #     model = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
    #     modification = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
    #     staff_name = Subquery(subqyery_message_rlk.values('staff__name')[:1])).annotate(
    #     content = Subquery(subqyery_message_info.values('content')[:1])).annotate(
    #     user_name = Subquery(subqyery_message_info.values('user__profiles__eco_name')[:1])).annotate(
    #     user_content = Subquery(subqyery_message_info.values('user')[:1])).annotate(
    #     eco         = Subquery(subqyery_message_info.values('user__profiles__eco')[:1]))
    chats = chats.annotate(
        type_estimation_ocenka          = Subquery(subqyery_reg_interactiv.values('type_reception__name')[:1])).annotate(
        car_year                        = Subquery(subqyery_reg_interactiv.values('estimation__year')[:1])).annotate( 
        car_prev_img                    = Subquery(subqyery_reg_interactiv.values('estimation__year')[:1])).annotate( 
        car_run                         = Coalesce(Subquery(subqyery_reg_interactiv.values('estimation__page_salon__run')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__page_remote__run')[:1]))).annotate(    
        unit_name                       = Coalesce(Subquery(subqyery_reg_interactiv.values('unit__name')[:1]), Subquery(subqyery_reg_interactiv.values('unit__name')[:1]))).annotate(
        unit_name_dc                    = Coalesce(Subquery(subqyery_reg_interactiv.values('unit__id')[:1]), Subquery(subqyery_reg_interactiv.values('unit__id')[:1]))).annotate(
        status_estimation               = Subquery(subqyery_reg_interactiv.values('status__name')[:1])).annotate(
        status_estimation_id            = Subquery(subqyery_reg_interactiv.values('status__id')[:1])).annotate(
        start_estimation                = Subquery(subqyery_reg_interactiv.values('estimation__start_estimation')[:1])).annotate(
        end_estimation                  = Subquery(subqyery_reg_interactiv.values('estimation__end_estimation')[:1])).annotate(
        staff_estimation_name           = Subquery(subqyery_reg_interactiv.values('staff_rlk__name')[:1])).annotate(
        staff_estimation                = Subquery(subqyery_reg_interactiv.values('staff_rlk')[:1])).annotate(            
        soglasovanie_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
        car_price_before_kd         = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_before_kd')[:1])).annotate(                       
        car_price_after_kd          = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_after_kd')[:1])).annotate(                       
        car_price_reception         = Coalesce(Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__page_remote__price_reception')[:1]))).annotate(                       
        car_price_sale              = Coalesce(Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_sale')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__page_remote__price_sale')[:1]))).annotate(                       
        car_price_bcp               = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_bcp')[:1])).annotate(                       
        rlk_date                    = Subquery(subqyery_message_rlk.values('dataTime')[:1])).annotate(    
        rlk_number                  = Subquery(subqyery_message_rlk.values('nomer')[:1])).annotate(    
        rlk_unit                    = Coalesce(Subquery(subqyery_message_rlk.values('unit__name')[:1]), Subquery(subqyery_reg_interactiv.values('unit__name')[:1]))).annotate(
        rlk_unit_dc                 = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
        vin                         = Coalesce(Subquery(subqyery_reg_interactiv.values('estimation__vin')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__number_body')[:1]))).annotate(
        mark                        = Subquery(subqyery_reg_interactiv.values('estimation__modification__model__mark__name')[:1])).annotate(
        model                       = Subquery(subqyery_reg_interactiv.values('estimation__modification__model__name')[:1])).annotate(
        modification                = Subquery(subqyery_reg_interactiv.values('estimation__modification__name')[:1])).annotate(
        staff_name                  = Coalesce(Subquery(subqyery_message_rlk.values('staff__name')[:1]), Subquery(subqyery_reg_interactiv.values('staff_rlk__name')[:1]))).annotate(
        content                     = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_name                   = Subquery(subqyery_message_info.values('user__profiles__eco_name')[:1])).annotate(
        user_content                = Subquery(subqyery_message_info.values('user')[:1])).annotate(
        eco                         = Subquery(subqyery_message_info.values('user__profiles__eco')[:1])).annotate(
        auction                     = Subquery(subqyery_reg_interactiv.values('estimation__auction')[:1]))
    
    chats = chats.filter(status_estimation_id__gte = 2)
    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1]))[:1] 

    return JsonResponse(list(chats.values()), safe=False, status=status.HTTP_200_OK)


def get_users_list_online(request, id):
    search = request.GET.get('search', '')
    users = list()
    if id != '' and search != '':
        estimation = RegInteractivOcenkaRLK.objects.get(rlk__id = id)
        users = User.objects.exclude(pk__in = estimation.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True)
        if search != '':
            users = users.filter(Q(profiles__eco_name__icontains = search) | Q(email__icontains = search))    
            users = list(users.order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email'))
    return JsonResponse(users, safe=False, status=status.HTTP_200_OK)


def get_chats_list_online(request):
    
    filtr_search                = request.GET.get('search', '')
    filtr_vin                   = request.GET.get('vin', '')
    page                        = int(request.GET.get('page', '1')) - 1

    
    chats                   = Chat.objects.all()
    subqyery_reg_interactiv = RegInteractivOcenkaRLK.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    # subqyery_reg_interactiv = subqyery_reg_interactiv.annotate()
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    
    # Количество РЛК, в которых используется та же оценка (по RegInteractivOcenkaRLK.estimation)
    subq_estimation_id = RegInteractivOcenkaRLK.objects.filter(
        rlk_id=OuterRef('rlk_id')
    ).values('estimation_id')[:1]
    # Сначала аннотируем чат estimation_id, затем считаем по нему — так корреляция в подзапросе одна
    chats = chats.annotate(_estimation_id=Subquery(subq_estimation_id))
    subq_rlk_count = RegInteractivOcenkaRLK.objects.filter(
        estimation_id=OuterRef('_estimation_id')
    ).values('estimation_id').annotate(cnt=Count('id')).values('cnt')[:1]
    chats = chats.annotate(
        estimation_rlk_count=Coalesce(
            Subquery(subq_rlk_count),
            Value(0),
            output_field=IntegerField()
        )
    )
        
    chats = chats.annotate(
        type_estimation_ocenka          = Subquery(subqyery_reg_interactiv.values('type_reception__name')[:1])).annotate(
        car_year                        = Subquery(subqyery_reg_interactiv.values('estimation__year')[:1])).annotate( 
        car_prev_img                    = Subquery(subqyery_reg_interactiv.values('estimation__year')[:1])).annotate( 
        car_run                         = Coalesce(Subquery(subqyery_reg_interactiv.values('estimation__page_salon__run')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__page_remote__run')[:1]))).annotate(    
        unit_name                       = Coalesce(Subquery(subqyery_reg_interactiv.values('unit__name')[:1]), Subquery(subqyery_reg_interactiv.values('unit__name')[:1]))).annotate(
        unit_name_dc                    = Coalesce(Subquery(subqyery_reg_interactiv.values('unit__id')[:1]), Subquery(subqyery_reg_interactiv.values('unit__id')[:1]))).annotate(
        status_estimation               = Subquery(subqyery_reg_interactiv.values('status__name')[:1])).annotate(
        status_estimation_id            = Subquery(subqyery_reg_interactiv.values('status__id')[:1])).annotate(
        start_estimation                = Subquery(subqyery_reg_interactiv.values('estimation__start_estimation')[:1])).annotate(
        end_estimation                  = Subquery(subqyery_reg_interactiv.values('estimation__end_estimation')[:1])).annotate(
        staff_estimation_name           = Subquery(subqyery_reg_interactiv.values('staff_rlk__name')[:1])).annotate(
        staff_estimation                = Subquery(subqyery_reg_interactiv.values('staff_rlk')[:1])).annotate(            
        soglasovanie_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
        car_price_before_kd         = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_before_kd')[:1])).annotate(                       
        car_price_after_kd          = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_after_kd')[:1])).annotate(                       
        car_price_reception         = Coalesce(Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__page_remote__price_reception')[:1]))).annotate(                       
        car_price_sale              = Coalesce(Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_sale')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__page_remote__price_sale')[:1]))).annotate(                       
        car_price_bcp               = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_bcp')[:1])).annotate(                       
        rlk_date                    = Subquery(subqyery_message_rlk.values('dataTime')[:1])).annotate(    
        rlk_number                  = Subquery(subqyery_message_rlk.values('nomer')[:1])).annotate(    
        rlk_unit                    = Coalesce(Subquery(subqyery_message_rlk.values('unit__name')[:1]), Subquery(subqyery_reg_interactiv.values('unit__name')[:1]))).annotate(
        rlk_unit_dc                 = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
        vin                         = Coalesce(Subquery(subqyery_reg_interactiv.values('estimation__vin')[:1]), Subquery(subqyery_reg_interactiv.values('estimation__number_body')[:1]))).annotate(
        mark                        = Subquery(subqyery_reg_interactiv.values('estimation__modification__model__mark__name')[:1])).annotate(
        model                       = Subquery(subqyery_reg_interactiv.values('estimation__modification__model__name')[:1])).annotate(
        modification                = Subquery(subqyery_reg_interactiv.values('estimation__modification__name')[:1])).annotate(
        staff_name                  = Coalesce(Subquery(subqyery_message_rlk.values('staff__name')[:1]), Subquery(subqyery_reg_interactiv.values('staff_rlk__name')[:1]))).annotate(
        content                     = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_name                   = Subquery(subqyery_message_info.values('user__profiles__eco_name')[:1])).annotate(
        user_content                = Subquery(subqyery_message_info.values('user')[:1])).annotate(
        eco                         = Subquery(subqyery_message_info.values('user__profiles__eco')[:1])).annotate(
        auction                     = Subquery(subqyery_reg_interactiv.values('estimation__auction')[:1]))
    
    chats = chats.filter(status_estimation_id__gte = 2)
    
    if filtr_vin != '':
        chats = chats.filter(vin__icontains = filtr_vin)

    if filtr_search != '':
        chats = chats.filter(mark__icontains = filtr_search) | chats.filter(model__icontains = filtr_search) | chats.filter(modification__icontains = filtr_search)
    
    start   = 0 + (30 * page)
    end     = 30 + (30 * page)

    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1]))[start:end] 

    return JsonResponse(list(chats.values()), safe=False, status=status.HTTP_200_OK)


def list_eco_online(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    params = {
        'type'          : 'eco',
        'nav_selected'  : 4
    }

    return render(request, 'lo/lo_list_online.html', {'params': params})


def list_eco(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    new_filtr       = request.GET.get('new_filtr', '')
    path_start      = request.path
    delite_filter   = request.GET.get('delite_filter', '')
    if len(delite_filter) > 0:
        if RefCustomerFiltr.objects.filter(pk = delite_filter).count() > 0:
            RefCustomerFiltr.objects.get(pk = delite_filter).delete()

    filters_user    = RefCustomerFiltr.objects.filter(user = request.user).filter(page = path_start).order_by('-date')  
    custom          = request.GET.get('custom', '') 
    if len(new_filtr) > 0:
        dict_filtr = request.GET.copy()
        dict_filtr.pop('new_filtr')
        dict_filtr.pop('save_filtr')
        path_filtr = get_path_in_dict(dict_filtr)

        path_redirect = path_start + path_filtr 
        new_filtr_object = RefCustomerFiltr()
        new_filtr_object.page = path_start
        new_filtr_object.path = path_filtr
        new_filtr_object.user = request.user
        new_filtr_object.name = new_filtr 
        new_filtr_object.save()

        return HttpResponseRedirect(path_redirect + '&custom='+ str(new_filtr_object.pk))
    
    date            = request.GET.get('date_start', '')

    if len(date) == 0:
    
        date_period = DT.datetime.now()
        date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        if date_period.month > 11:
            month_end	= 1
            year_end 	= date_period.year + 1
        else:
            month_end	= date_period.month + 1
            year_end 	= date_period.year
        date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
    
    else:
    
        dates = date.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_start 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            if month > 11:
                month_end 	= 1
                year_end 	= year + 1
            else:
                month_end 	= month + 1 
                year_end 	= year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
    
    countList = 15

    staffKKID   = ""
    staffsKK    = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
			
    unit_id      = ""
    units_select = RefUnit.objects.filter(buauto = True).filter(active_eco = True).exclude(name = '').order_by("name")
    
    type_receptions_id = request.GET.get('type_receptions_id', '')

    staffID         = ""
    staffsSelect    = ""
    
    docs        = DocRLK.objects.filter(dataTime__gte = date_start).filter(eco = True).order_by('-dataTime')
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
    docs        = docs.annotate(
        unit_name               = Subquery(subquery.values('page_documents__unit__name')[:1])).annotate(
        unit_name_dc               = Subquery(subquery.values('page_documents__unit__id')[:1])).annotate(
        status_estimation       = Subquery(subquery.values('status__name')[:1])).annotate(
        status_estimation_id    = Subquery(subquery.values('status__id')[:1])).annotate(
        start_estimation        = Subquery(subquery.values('start_estimation')[:1])).annotate(
        end_estimation          = Subquery(subquery.values('end_estimation')[:1])).annotate(
        staff_estimation_name    = Subquery(subquery.values('staff__name')[:1])).annotate(
        staff_estimation    = Subquery(subquery.values('staff')[:1])).annotate(
        mark                = Subquery(subquery.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subquery.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subquery.values('modification__name')[:1])).annotate(
        type_estimation_ocenka = Subquery(subquery.values('page_documents__type_reception__name')[:1])).annotate(
        type_estimation_ocenka_id = Subquery(subquery.values('page_documents__type_reception__id')[:1])).annotate(
        year = Subquery(subquery.values('year')[:1])).annotate(
        vin = Subquery(subquery.values('vin')[:1])).annotate(
        lo_pk = Subquery(subquery.values('id')[:1]))

    filtr_number_doc = request.GET.get('number_doc', '')
    
    if filtr_number_doc != '':
        docs = docs.filter(nomer__icontains = filtr_number_doc)    
    if type_receptions_id != '':
        type_receptions_id = int(type_receptions_id)
        docs = docs.filter(type_estimation_ocenka_id = type_receptions_id)    
    
    #docs = RegInteractivOcenka.objects.filter(page__id = 1).order_by('-rlk__dataTime')
    chats                   = Chat.objects.all()
    subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1])) 
    chats = chats.annotate(
        rlk_unit = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
        vin = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
        mark = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
        staff_name = Subquery(subqyery_message_rlk.values('staff__name')[:1])).annotate(
        content = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_content = Subquery(subqyery_message_info.values('user')[:1]))
    
    search = request.GET.get('search', '')
    if len(search) > 0:
        docs = docs.filter(vin__icontains = search) | docs.filter(
            mark__icontains = search) | docs.filter(
                model__icontains = search) | docs.filter(
                    modification__icontains = search) | docs.filter(
                    staff_estimation_name__icontains = search)
        
        
    status_id = request.GET.get('status_id', '')
    if status_id != '':
        status_id = int(status_id)
        docs = docs.filter(status_estimation_id = status_id)
    else:
        docs = docs.exclude(status_estimation_id = 0)
 
    if request.GET.get('unit_id', '') != '':
        unit_id         = int(request.GET['unit_id'])
        docs            = docs.filter(unit__id = unit_id) | docs.filter(unit_dc__id = unit_id) | docs.filter(unit_name_dc = unit_id) 
        #staffsSelect    = list(RefStaff.objects.filter(unit = RefUnit.objects.get(id = unit_id)).order_by('name'))
    
    paginator   = Paginator(docs, countList)	
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    filtr = {
        'unit_id'           : unit_id,
        'staffID'           : staffID,
		'staffKKID'         : staffKKID,
        'number_doc'        : filtr_number_doc,
        'date_start'        : date_start,
        'type_receptions_id': type_receptions_id, 
        'date_end'          : date_end,
        'status_id'         : status_id,
        'custom'            : custom,
        'search'            : search
    }
    selected = {
        'units'             : units_select,
        'staffs'            : staffsSelect,
        'staffsKK'          : '',
        'statuses'          : list(RefStatusEstimation.objects.all().order_by('-pk')),
        'type_receptions'   : RefTypeReceptionCarsOrganization.objects.exclude(name = '').order_by('name')
    }
    params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'objects'       : page_obj,
        'request'       : request,
        'counts'        : len(docs),
        'selected'      : selected,
        'filtr'         : filtr,
        'filters_user'  : filters_user,
        'chats'         : chats
    }

    return render(request, 'lo/lo_list.html', {'params': params})


# Типы файлов для копирования во внешний осмотр и салон (КД)
CONTROL_DIAGNOSTIC_FILE_TYPES = frozenset([
    'vnesh_car_all', 'vin', 'pod_capot', 'windshield_error', 'light_error',
    'vnesh_windows_error', 'vnesh_light_error',
    'vnesh_car_osmotr_pered', 'vnesh_car_osmotr_vod', 'vnesh_car_osmotr_zad',
    'vnesh_car_osmotr_up', 'vnesh_car_osmotr_pass',
    'array_images_pered', 'array_images_vod', 'array_images_zad',
    'array_images_up', 'array_images_pass',
    'salon_all', 'salon_error', 'run', 'osmotr_salon',
])


def _create_control_diagnostic_from_estimation(estimation, user, interactiv_rlk):
    """Создаёт контрольную диагностику: копирует vnesh/salon/файлы и пересчитывает результат."""
    cd = RegControlDiagnostic(estimation=estimation, author=user)
    cd.save()

    # 1. Копируем внешний осмотр
    if estimation.page_vnesh:
        v = estimation.page_vnesh
        cd_vnesh = RegControlDiagnosticVnesh(
            control_diagnostic=cd,
            text_json=v.text_json,
            windshield_error=v.windshield_error,
            light_error=v.light_error,
            oil_error=v.oil_error,
            water_error=v.water_error,
            color=v.color or '',
            check_vin=v.check_vin,
            check_engine=v.check_engine,
            comment_vnesh=v.comment_vnesh or '',
            check_vin_int=getattr(v, 'check_vin_int', 10) or 10,
            check_engine_int=getattr(v, 'check_engine_int', 10) or 10,
            windshield_error_int=getattr(v, 'windshield_error_int', 10) or 10,
            light_error_int=getattr(v, 'light_error_int', 10) or 10,
            oil_error_int=getattr(v, 'oil_error_int', 10) or 10,
            water_error_int=getattr(v, 'water_error_int', 10) or 10,
            windshield_heat_int=getattr(v, 'windshield_heat_int', 10) or 10,
        )
        cd_vnesh.save()

    # 2. Копируем салон
    if estimation.page_salon:
        s = estimation.page_salon
        cd_salon = RegControlDiagnosticSalon(
            control_diagnostic=cd,
            text_json=s.text_json,
            run=s.run or 0,
            run_confirmed=s.run_confirmed or False,
            hand_brake=s.hand_brake if s.hand_brake is not None else 10,
            conductor=s.conductor if s.conductor is not None else 10,
            wiper=s.wiper if s.wiper is not None else 10,
            signal=s.signal if s.signal is not None else 10,
            power_windows=s.power_windows if s.power_windows is not None else 10,
            seat_belt=s.seat_belt if s.seat_belt is not None else 10,
            cleaning=s.cleaning or False,
            damage_kpp=s.damage_kpp or False,
            damage_wheel=s.damage_wheel or False,
            damage_pedal=s.damage_pedal or False,
            damage_door=s.damage_door or False,
            damage_seat=s.damage_seat or False,
            run_respond=getattr(s, 'run_respond', 10) or 10,
            run_confirmed_comment=s.run_confirmed_comment or '',
            cleaning_int=getattr(s, 'cleaning_int', 10) or 10,
            damage_kpp_int=getattr(s, 'damage_kpp_int', 10) or 10,
            damage_wheel_int=getattr(s, 'damage_wheel_int', 10) or 10,
            damage_pedal_int=getattr(s, 'damage_pedal_int', 10) or 10,
            damage_door_int=getattr(s, 'damage_door_int', 10) or 10,
            damage_seat_int=getattr(s, 'damage_seat_int', 10) or 10,
            type_salon_int=getattr(s, 'type_salon_int', 10) or 10,
        )
        cd_salon.save()
        if hasattr(s, 'dashboard_error') and s.dashboard_error.exists():
            cd_salon.dashboard_error.set(s.dashboard_error.all())

    # 3. Создаём mock estimation для пересчёта (подмена page_vnesh/page_salon)
    class _MockEstimation:
        pass

    mock = _MockEstimation()
    for attr in dir(estimation):
        if not attr.startswith('_'):
            try:
                setattr(mock, attr, getattr(estimation, attr))
            except Exception:
                pass
    if hasattr(cd, 'page_vnesh_copy') and cd.page_vnesh_copy:
        mock.page_vnesh = cd.page_vnesh_copy
    if hasattr(cd, 'page_salon_copy') and cd.page_salon_copy:
        mock.page_salon = cd.page_salon_copy

    # 4. Пересчёт и сохранение результата
    price_kors = estimations_price_calculation(interactiv_rlk, mock, type_calculation='kors')
    price_autohub = estimations_price_calculation(interactiv_rlk, mock, type_calculation='autohub')
    price_avito = estimations_price_calculation(interactiv_rlk, mock, type_calculation='avito')
    price_custom = estimations_price_calculation(interactiv_rlk, mock, type_calculation='custom')

    if price_kors:
        cd.price_auto_1 = int(price_kors.get('estimation_price', 0) or 0)
        cd.price_auto_bcp_1 = int(price_kors.get('cna_expenses', 0) or 0)
        cd.price_zna_1 = int(price_kors.get('zna', 0) or 0)
    if price_autohub:
        cd.price_auto_2 = int(price_autohub.get('estimation_price', 0) or 0)
        cd.price_auto_bcp_2 = int(price_autohub.get('cna_expenses', 0) or 0)
        cd.price_zna_2 = int(price_autohub.get('zna', 0) or 0)
    if price_avito:
        cd.price_auto_3 = int(price_avito.get('estimation_price', 0) or 0)
        cd.price_auto_bcp_3 = int(price_avito.get('cna_expenses', 0) or 0)
        cd.price_zna_3 = int(price_avito.get('zna', 0) or 0)
    if price_custom:
        cd.amount_podgotovka = float(price_custom.get('amount_podgotovka', 0) or 0)
        cd.amount_ss = float(price_custom.get('amount_ss', 0) or 0)
        cd.amount_mcu = float(price_custom.get('amount_mcu', 0) or 0)
        cd.amount_recovery = float(
            (price_custom.get('amount_podgotovka', 0) or 0) +
            (price_custom.get('amount_ss', 0) or 0) +
            (price_custom.get('amount_mcu', 0) or 0)
        )
    cd.save()

    # 5. Копируем файлы
    for src in RegRegInteractivOcenkaFiles.objects.filter(estimation=estimation).filter(
            type_file__in=CONTROL_DIAGNOSTIC_FILE_TYPES
    ).order_by('type_file', 'file_number'):
        RegControlDiagnosticFile.objects.create(
            control_diagnostic=cd,
            source_file=src,
            name=src.name or '',
            type_file=src.type_file or '',
            file=src.file,
            file_mini=src.file_mini,
            comment=src.comment or '',
            file_number=src.file_number or 0,
            text=src.text or '',
            type_point=src.type_point or '',
            cor_x=src.cor_x or 0,
            cor_y=src.cor_y or 0,
            kraska=src.kraska or 0,
            order=src.order or 0,
            blank=src.blank or False,
            date=src.date,
            user=user,
        )

    return cd


@login_required
def create_control_diagnostic(request, id):
    """Создаёт контрольную диагностику для оценки (RLK id)."""
    if request.method != 'POST':
        return HttpResponseRedirect('/eco/' + str(id) + '/')
    rlk = DocRLK.objects.get(pk=id)
    interactiv_rlk, _ = RegInteractivOcenkaRLK.objects.get_or_create(rlk=rlk)
    estimation = interactiv_rlk.estimation
    if not estimation:
        return HttpResponseRedirect('/eco/' + str(id) + '/')
    cd = _create_control_diagnostic_from_estimation(estimation, request.user, interactiv_rlk)
    return HttpResponseRedirect('/eco/' + str(id) + '/?page=9#control_diagnostics')


@login_required
def control_diagnostic_comparison(request, id, cd_id):
    """Отчёт сравнения: интерактивная оценка vs контрольная диагностика."""
    rlk = DocRLK.objects.get(pk=id)
    interactiv_rlk, _ = RegInteractivOcenkaRLK.objects.get_or_create(rlk=rlk)
    estimation = interactiv_rlk.estimation
    if not estimation:
        return HttpResponseRedirect('/eco/' + str(id) + '/')
    cd = RegControlDiagnostic.objects.filter(estimation=estimation, pk=cd_id).first()
    if not cd:
        raise Http404('Контрольная диагностика не найдена')

    # Файлы для сравнения (оригинал vs КД) — пары по type_file + file_number
    orig_files = list(RegRegInteractivOcenkaFiles.objects.filter(
        estimation=estimation
    ).filter(type_file__in=CONTROL_DIAGNOSTIC_FILE_TYPES).order_by('type_file', 'file_number'))
    cd_files_by_key = {(f.type_file, f.file_number or 0): f for f in RegControlDiagnosticFile.objects.filter(control_diagnostic=cd)}
    cd_files_by_source = {f.source_file_id: f for f in RegControlDiagnosticFile.objects.filter(control_diagnostic=cd) if f.source_file_id}
    file_pairs = []
    seen_cd_ids = set()
    for orig in orig_files:
        cf = cd_files_by_source.get(orig.id) or cd_files_by_key.get((orig.type_file or '', orig.file_number or 0))
        if cf:
            seen_cd_ids.add(cf.id)
        file_pairs.append((orig, cf))
    for cf in RegControlDiagnosticFile.objects.filter(control_diagnostic=cd).order_by('type_file', 'file_number'):
        if cf.id not in seen_cd_ids:
            file_pairs.append((None, cf))

    orig_soglasovanie = estimation.page_soglasovanie
    params = {
        'estimation': estimation,
        'rlk': rlk,
        'cd': cd,
        'orig_soglasovanie': orig_soglasovanie,
        'file_pairs': file_pairs,
        'request': request,
    }
    return render(request, 'lo/control_diagnostic_comparison.html', {'params': params})


@login_required
def doc(request, id):
     
    if not request.user.is_authenticated:
        try:
            rlk                     = DocRLK.objects.get(pk=id)
            estimation, created     = RegInteractivOcenka.objects.get_or_create(rlk = rlk)
            add_log_history_open(estimation, None, 301)
        except:
            s = 1
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    rlk     = DocRLK.objects.get(pk=id)
    interactiv_rlk, created = RegInteractivOcenkaRLK.objects.get_or_create(rlk = rlk)
    #estimation, created  = RegInteractivOcenka.objects.get_or_create(rlk = rlk)
    
    estimation = interactiv_rlk.estimation 
    if estimation == None:
        return HttpResponseRedirect('/estimations/' + str(id) + '/')
    
    if not request.user.profiles.user_sb and not request.user.profiles.eco and not request.user.profiles.eco_visible and not request.user.username == interactiv_rlk.staff_rlk.domain_login and not request.user in interactiv_rlk.access_user.all() and not request.user in estimation.access_user.all() and not request.user.username == estimation.staff.domain_login  and (estimation.page_documents.store != None and not estimation.page_documents.store in request.user.profiles.korsavto_stores.all()):
        
        add_log_history_open(estimation, request.user, 403)
        
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})

    warning_list = list()
    rlk_estimations = RegInteractivOcenkaRLK.objects.filter(estimation = estimation) 
    
    params  = {}
    selected            = ''
    balance_date        = estimation.start_estimation 
    if balance_date == None:
        balance_date = estimation.rlk.dataTime 

    balance_date_start  = balance_date - relativedelta(months=1)
    balance_date_start  = balance_date_start.replace(day=1, hour=1)
    balance_date_end    = balance_date

    chat = Chat.objects.filter(name=rlk.pk, slug='rlk_' + str(rlk.pk)).first()
    if chat is None:
        chat = Chat.objects.create(name=rlk.pk, slug='rlk_' + str(rlk.pk))
    # chat    = Chat.objects.get_or_create(name = rlk.pk, slug = 'rlk_' + str(rlk.pk))[0]
        
    user    = request.user
    messages = chat.get_last_messages()
    versions = ''
    body     = ''
    salon    = '' 
    list_work_podgotovka    = list()
    list_work_mcu           = list()
    list_work_ss            = list()
    lo                      = None
    car                     = None
    agreement               = None
    agreement_car           = None
    balance                 = None
    balance_unit            = None
    expenses                = list()
    
    body            = body_estimation(estimation=estimation)
    salon           = salon_estimation(estimation=estimation)
    
    car_sales = DocCarShipment.objects.filter(cars__vin = estimation.vin).filter(active = True).filter(dataTime__lte = estimation.start_estimation)
    
    for car_sale in car_sales:
        if car_sale.dataTime > estimation.start_estimation - DT.timedelta(days = 30):
            info_warning = {
                'text'  : 'Автомобиль продан нами менее 30 дней назад',
                'dop'   : 'Документ продажи (отгрузка ам) ' + car_sale.nomer + ' от ' + car_sale.dataTime.strftime("%d.%m.%Y") + "г. ДЦ продажи " + car_sale.unit.name
            }
            warning_list.append(info_warning)

    if DocLO.objects.filter(rlk = interactiv_rlk.rlk).count() > 0:
        lo  = DocLO.objects.filter(rlk = interactiv_rlk.rlk)[0]  

    if request.method == "GET":
        
        if 'playcar' in request.GET:
            page_remote = estimation.page_remote
            page_remote.end_estimation = DT.datetime.now()
            page_remote.save()
            
            estimation.avtoteka_web = ''
            estimation.avtoteka_preview = ''
            estimation.avtoteka_task = None 
            estimation.hub_start = None
            estimation.kors_start_store = DT.datetime.now().replace(year=2024)

            estimation.end_estimation = None
            
            if estimation.page_documents == None:
                reg_interactiv_ocenka_document = RegInteractivOcenkaDocument()
                reg_interactiv_ocenka_document.save()
                estimation.page_documents = reg_interactiv_ocenka_document
            else:
                reg_interactiv_ocenka_document = estimation.page_documents
            
            reg_interactiv_ocenka_document.unit             = estimation.page_remote.unit
            reg_interactiv_ocenka_document.type_reception   = estimation.page_remote.type_reception
            reg_interactiv_ocenka_document.store            = estimation.page_remote.store
            reg_interactiv_ocenka_document.organization     = estimation.page_remote.organization
            reg_interactiv_ocenka_document.filial           = estimation.page_remote.filial
            reg_interactiv_ocenka_document.save()

            if estimation.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovane = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovane.save()
                estimation.page_soglasovanie = reg_interactiv_ocenka_soglasovane
            else:
                reg_interactiv_ocenka_soglasovane = estimation.page_soglasovanie
            
            reg_interactiv_ocenka_soglasovane.price_sale            = estimation.page_remote.price_sale
            reg_interactiv_ocenka_soglasovane.price_reception       = estimation.page_remote.price_reception
            reg_interactiv_ocenka_soglasovane.car_sale_info         = estimation.page_remote.car_sale_info
            reg_interactiv_ocenka_soglasovane.car_sale_price        = estimation.page_remote.car_sale_price
            reg_interactiv_ocenka_soglasovane.comment               = estimation.page_remote.comment
            reg_interactiv_ocenka_soglasovane.save()

            estimation.save()
            
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= User.objects.get(pk = 1), text='Автомобиль приехал на осмотр. Данные автотека, корсавто будут обновлены автоматически.', estimation_id= estimation.id)
            return HttpResponseRedirect('/estimations/' + str(estimation.rlk.pk) + '/')
            
        price           = {}
        price_autohub   = {}
        price_custom    = {}
        price_kors      = {}

        repair_info         = list()
        estimation_history  = list()
        users               = list()
        opens_infos         = list()
        json_autoteka       = list()
        signal              = list() 
        list_store_info     = list()

        page = 0
        
        if 'page' in request.GET:
            page = int(request.GET['page'])

        add_log_history_open(estimation, user, page)

        if page == 21 or page == 20 or page == 23:
            
            if page == 20:
                if not request.user.profiles.eco_page_price_info:
                    return HttpResponseRedirect(request.build_absolute_uri().replace('page=21', 'page=9'))
            elif page == 21:
                if not request.user.profiles.eco and not request.user.profiles.eco_page_price_info:
                    return HttpResponseRedirect(request.build_absolute_uri().replace('page=21', 'page=9'))
            
            expenses = list_expenses(estimation)
            
            signal  = Autoteka_signal.objects.filter(vin = estimation.vin)
            refresh = request.GET.get('refresh_data', '')
            if refresh != '':
                if refresh == 'autohub':
                    get_info_max(interactiv_rlk, estimation.id)
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'kors':
                    kors_estimation_data(estimation.id)
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'all':
                    get_info_max(interactiv_rlk, estimation.id)
                    kors_estimation_data(estimation.id)
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'data1c':
                    from task_manager.views import estimation_send_1c
                    try:
                        estimation_send_1c(interactiv_rlk.rlk.id, interactiv_rlk.estimation.id)
                    except:
                        s= 1
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'balance_doc':
                    try:
                        from website.views import refresh_estimation_balance_unit
                        refresh_estimation_balance_unit(estimation.rlk.id)
                    except:
                        s = 1
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'analitik':
                    from website.views import refresh_estimation_analitik
                    try:
                        refresh_estimation_analitik(estimation.rlk.id)
                    except:
                        s= 1
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                
            balance_count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count()
            if balance_count == 1:
                balance = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0]   

            if DocLO.objects.filter(rlk = interactiv_rlk.rlk).count() > 0:
                lo  = DocLO.objects.filter(rlk = interactiv_rlk.rlk)[0]  
                if RefCarsOrganization.objects.filter(lo = lo).count() > 0:
                    car = RefCarsOrganization.objects.get(lo = lo)
                    if car.quantity == 0:
                        agreements_car = DocCarAgreement.objects.filter(lo = lo).filter(active = True).count()
                        if agreements_car > 0:
                            agreement_car = DocCarAgreement.objects.filter(lo = lo).filter(active = True)[0]     
                    if lo.agreement_number != '':
                        agreements = DocCarAgreement.objects.filter(nomer__icontains = lo.agreement_number).filter(active = True).filter(unit__name__icontains = lo.agreement_unit.name).count()
                        if agreements > 0:
                            agreement = DocCarAgreement.objects.filter(nomer__icontains = lo.agreement_number).filter(active = True).filter(unit__name__icontains = lo.agreement_unit.name)[0]

            price_kors      = None #estimations_price_calculation(interactiv_rlk, estimation, type_calculation='kors')
            price           = estimations_price_calculation(interactiv_rlk, estimation, type_calculation='avito')
            price_autohub   = estimations_price_calculation(interactiv_rlk, estimation, type_calculation='autohub')
            price_custom    = estimations_price_calculation(interactiv_rlk, estimation, type_calculation='custom')
            
            if page == 20:
                
                if lo != None and lo.agreement_number != '':
                    query_balance_unit = RegEstimationBalanceUnit.objects.filter(unit = lo.agreement_unit).filter(date__gte = balance_date_start).filter(date__lte = balance_date_end).aggregate(Sum('amount'))
                    if query_balance_unit['amount__sum'] == None:
                        balance_unit = 0
                    else:
                        balance_unit = query_balance_unit['amount__sum']
                elif estimation.rlk.unit_dc != None:
                    query_balance_unit = RegEstimationBalanceUnit.objects.filter(unit = estimation.rlk.unit_dc).filter(date__gte = balance_date_start).filter(date__lte = balance_date_end).aggregate(Sum('amount'))
                    if query_balance_unit['amount__sum'] == None:
                        balance_unit = 0
                    else:
                        balance_unit = query_balance_unit['amount__sum']
                else:
                    query_balance_unit = RegEstimationBalanceUnit.objects.filter(unit = estimation.rlk.unit).filter(date__gte = balance_date_start).filter(date__lte = balance_date_end).aggregate(Sum('amount'))
                    if query_balance_unit['amount__sum'] == None:
                        balance_unit = 0
                    else:
                        balance_unit = query_balance_unit['amount__sum']

                    #lo.agreement_number
                    #estimation.rlk.unit
                    #estimation.rlk.unit

            if estimation.avtoteka_data != '' and estimation.avtoteka_data != None:
                json_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
            list_store_info = list()

        if page == 30:
            
            if page == 30:
                if not request.user.profiles.eco_page_price_auto:
                    return HttpResponseRedirect(request.build_absolute_uri().replace('page=21', 'page=9'))
            
            balance_count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count()
            if balance_count == 1:
                balance = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0]   

            if DocLO.objects.filter(rlk = interactiv_rlk.rlk).count() > 0:
                lo  = DocLO.objects.filter(rlk = interactiv_rlk.rlk)[0]  
                if RefCarsOrganization.objects.filter(lo = lo).count() > 0:
                    car = RefCarsOrganization.objects.get(lo = lo)
                    if car.quantity == 0:
                        agreements_car = DocCarAgreement.objects.filter(lo = lo).filter(active = True).count()
                        if agreements_car > 0:
                            agreement_car = DocCarAgreement.objects.filter(lo = lo).filter(active = True)[0]     
                    if lo.agreement_number != '':
                        agreements = DocCarAgreement.objects.filter(nomer__icontains = lo.agreement_number).filter(active = True).filter(unit__name__icontains = lo.agreement_unit.name).count()
                        if agreements > 0:
                            agreement = DocCarAgreement.objects.filter(nomer__icontains = lo.agreement_number).filter(active = True).filter(unit__name__icontains = lo.agreement_unit.name)[0]

            expenses        = list_expenses(estimation)

            price_kors      = None #estimations_price_calculation(interactiv_rlk, estimation, type_calculation='kors')
            price           = estimations_price_calculation(interactiv_rlk, estimation, type_calculation='avito')
            price_autohub   = estimations_price_calculation(interactiv_rlk, estimation, type_calculation='autohub')
            price_custom    = estimations_price_calculation(interactiv_rlk, estimation, type_calculation='custom')
            body            = body_estimation(estimation=estimation)
            if estimation.avtoteka_data != '' and estimation.avtoteka_data != None:
                json_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
            list_store_info = list()
            
        if page == 22:
            versions = {}
            versions_page_1 = get_versions('RegInteractivOcenka', estimation.id)
            versions['page_1'] = versions_page_1

        if page == 18:
            if request.user.profiles.eco or request.user.profiles.eco_page_price_info:
                opens_infos = opens_info(estimation)
            else:
                return HttpResponseRedirect(request.path_info + '?page=0')
            
        if page == 13:
            repair_info = repair_history(estimation)
        if page == 5:
            selected = {
                'mark_tyres' : RefMarkTyres.objects.all().order_by('name'),
                'width_tyres' : RefWidthTyres.objects.all().order_by('name'),
                'disk_types' : RefTypeDisk.objects.all().order_by('name'),
                'profil_tyres' : RefProfileTyres.objects.all().order_by('name'),
                'radiuses' : RefRadius.objects.all().order_by('name'),
                'sezons' : RefSezonTyres.objects.all().order_by('name'),
                'et_disks' : RefEtDisk.objects.all().order_by('name'),
                'dia_disks' : RefDiaDisk.objects.all().order_by('name'),
                'psd_disks' : RefPsdDisk.objects.all().order_by('name')
            }
            params = params = {
                            'type'          : 'eco',
                            'rlk'           : rlk,
                            'estimation'    : estimation,
                            'tabindex'      : page,
                            'chat'          : chat,
                            'messages'      : messages,
                            'selected'      : selected,
                            'tab_repairs_count'     : repair_history(estimation, count = True),
                            'tab_estimations_count' : estimation_lo_history(estimation, count = True),
                            'repairs_info'          : repair_info,
                            'estimations_info'      : estimation_history,
                            'user'                  : user,
                        }
             
        if page == 8:
            estimation_history = estimation_lo_history(estimation) 
        if page == 14:
            if estimation.avtoteka_data != '' and estimation.avtoteka_data != None:
                json_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
        if page == 9:
            
            if 'del_u' in request.GET:
                uusr = User.objects.get(id = request.GET.get('del_u'))
                interactiv_rlk.access_user.remove(uusr)
                interactiv_rlk.save()
                return HttpResponseRedirect(request.path_info + '?page=9')
            
            if 'add_u' in request.GET:
                
                uusr = User.objects.get(id = request.GET.get('add_u'))
                interactiv_rlk.access_user.add(uusr)
                interactiv_rlk.save()
                
                new_message = RegInteractivOcenkaEmailPush()
                new_message.estimation  = interactiv_rlk.estimation
                new_message.rlk         = interactiv_rlk.rlk
                new_message.user        = uusr
                new_message.email       = uusr.email
                new_message.comment     = 'Вы добавлены в участники интерактивной оценки.'
                new_message.save()

                return HttpResponseRedirect(request.path_info + '?page=9') 

            #users = User.objects.exclude(pk__in = estimation.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email')
            start_eco_1 = request.GET.get('start_eco_1','')
            if start_eco_1 != '':
                interactiv_rlk.staff_eco_1_rlk = request.user
                interactiv_rlk.save()
            start_eco_2 = request.GET.get('start_eco_2','')
            if start_eco_2 != '':
                interactiv_rlk.staff_eco_2_rlk = request.user
                interactiv_rlk.save()   

        list_work_podgotovka    = RegEstimationPodgotovka.objects.filter(estimation = estimation)
        list_work_ss            = RegEstimationSS.objects.filter(estimation = estimation)
        list_work_mcu           = RegEstimationMCU.objects.filter(estimation = estimation)

        # Загрузка выбранных элементов справочника диагностики
        selected_references = {}
        if estimation.page_test_drive:
            from register.models import DiagnosticReferenceSelection
            selections = DiagnosticReferenceSelection.objects.filter(
                test_drive=estimation.page_test_drive
            ).select_related('reference_item', 'reference_item__category')
            
            for selection in selections:
                category_code = selection.category_code
                if category_code not in selected_references:
                    selected_references[category_code] = []
                selected_references[category_code].append({
                    'id': selection.reference_item.id,
                    'title': selection.reference_item.title,
                    'description': selection.reference_item.description,
                    'observation_zones': selection.reference_item.observation_zones,
                    'possible_causes': selection.reference_item.possible_causes,
                    'consequences': selection.reference_item.consequences,
                    'additional_info': selection.reference_item.additional_info,
                })
        
        params = {
                'page'                  : page,
                'type'                  : 'eco',
                'interactiv_rlk'      : interactiv_rlk,
                'rlk'                   : rlk,
                'rlk_estimations'       : rlk_estimations,
                'estimation'            : estimation,
                'price'                 : price,
                'price_kors'            : price_kors,
                'price_autohub'         : price_autohub,
                'price_custom'          : price_custom,
                'tabindex'              : page,
                'chat'                  : chat,
                'messages'              : messages,
                'opens_infos'           : opens_infos,
                'json_autoteka'         : json_autoteka,
                'tab_repairs_count'     : repair_history(estimation, count = True),
                'tab_estimations_count' : estimation_lo_history(estimation, count = True),
                'repairs_info'          : repair_info,
                'estimations_info'      : estimation_history,
                'user'                  : user,
                'users'                 : users,
                'store_info'            : list_store_info,
                'versions'              : versions,
                'selected_references'   : selected_references,
                'body'                  : body,
                'salon'                 : salon,
                'list_work_podgotovka'  : list_work_podgotovka,
                'list_work_ss'          : list_work_ss,
                'list_work_mcu'         : list_work_mcu,
                'lo'                    : lo,
                'car'                   : car,
                'agreement'             : agreement,
                'agreement_car'         : agreement_car,
                'balance'               : balance,
                'balance_date_start'    : balance_date_start,
                'balance_date_end'      : balance_date_end,
                'balance_unit'          : balance_unit,
                'signal'                : signal,
                'warning_list'          : warning_list,
                'expenses'              : expenses,
                'selected'              : selected,
                'control_diagnostics'   : estimation.control_diagnostics.all(),

            }
    
    elif request.method == "POST":
        
        reg_interactiv_ocenka = interactiv_rlk.estimation
        
        if 'cancel_auction' in request.POST:
            comment_cancel_auction = request.POST.get('auction_cancel', '')
            if comment_cancel_auction != '':
                reg_interactiv_ocenka.auction_auto_no_user = True
            else:
                reg_interactiv_ocenka.auction_auto_no_user = False
            reg_interactiv_ocenka.auction_auto_comment = comment_cancel_auction
            reg_interactiv_ocenka.save()
            interactiv_rlk.save()
            if comment_cancel_auction != '':
                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Автоматический аукцион не подтвержден - ' + comment_cancel_auction, estimation_id= reg_interactiv_ocenka.id)
            else:
                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Автоматический аукцион подтвержден - ' + comment_cancel_auction, estimation_id= reg_interactiv_ocenka.id)
            
            return HttpResponseRedirect(request.build_absolute_uri())

        add_swap(interactiv_rlk.rlk, reg_interactiv_ocenka)

        if 'custom_zna' in request.POST:
            zna = int(request.POST.get('custom_zna', 0)) 
            reg_interactiv_ocenka.custom_zna = zna
            reg_interactiv_ocenka.custom_zna_comment    = request.POST.get('custom_zna_comment', "")
            reg_interactiv_ocenka.custom_zna_author     = request.user
            reg_interactiv_ocenka.save(update_fields=['custom_zna', 'custom_zna_comment', 'custom_zna_author'])
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'save_new_task_text' in request.POST:
            
            new_task = RegInteractivOcenkaTask()
            new_task.comment_task   = request.POST.get('save_new_task_text')
            new_task.estimation     = interactiv_rlk.estimation
            new_task.staff_open     = request.user
            new_task.save()

            reg_interactiv_ocenka.end_estimation = DT.datetime(1,1,1)
            reg_interactiv_ocenka.returned = True
            reg_interactiv_ocenka.save()
            interactiv_rlk.save()

            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Новая задача - ' + new_task.comment_task, estimation_id= reg_interactiv_ocenka.id)
            reg_interactiv_ocenka.save()
            interactiv_rlk.save()
            return HttpResponseRedirect(request.build_absolute_uri())            
        
        if 'save_test_drive' in request.POST:
            
            if reg_interactiv_ocenka.page_test_drive == None:
                reg_interactiv_ocenka_test_drive = RegInteractivOcenkaTestDrive()
                reg_interactiv_ocenka_test_drive.save()
                reg_interactiv_ocenka.page_test_drive = reg_interactiv_ocenka_test_drive
                reg_interactiv_ocenka.save()
                interactiv_rlk.save()
            else:
                reg_interactiv_ocenka_test_drive = reg_interactiv_ocenka.page_test_drive

            if reg_interactiv_ocenka_test_drive.start_estimation == None:
                reg_interactiv_ocenka_test_drive.start_estimation     = DT.datetime.now()
            
            reg_interactiv_ocenka_test_drive.engine         = int(request.POST.get('radio_engine', '3'))
            reg_interactiv_ocenka_test_drive.comment_engine = request.POST.get('comment_engine', '')

            reg_interactiv_ocenka_test_drive.system_og          = int(request.POST.get('radio_system_og', '3'))
            reg_interactiv_ocenka_test_drive.comment_system_og  = request.POST.get('comment_system_og', '')

            reg_interactiv_ocenka_test_drive.gear         = int(request.POST.get('radio_gear', '3'))
            reg_interactiv_ocenka_test_drive.comment_gear = request.POST.get('comment_gear', '')

            reg_interactiv_ocenka_test_drive.suspension         = int(request.POST.get('radio_suspension', '3'))
            reg_interactiv_ocenka_test_drive.comment_suspension = request.POST.get('comment_suspension', '')

            reg_interactiv_ocenka_test_drive.conditioner         = int(request.POST.get('radio_conditioner', '3'))
            reg_interactiv_ocenka_test_drive.comment_conditioner = request.POST.get('comment_conditioner', '')

            reg_interactiv_ocenka_test_drive.turbo              = int(request.POST.get('radio_turbo', '3'))
            reg_interactiv_ocenka_test_drive.comment_turbo      = request.POST.get('comment_turbo', '')
            
            reg_interactiv_ocenka_test_drive.drive              = int(request.POST.get('radio_drive', '3'))
            reg_interactiv_ocenka_test_drive.comment_drive      = request.POST.get('comment_drive', '')
            
            reg_interactiv_ocenka_test_drive.wheel              = int(request.POST.get('radio_wheel', '3'))
            reg_interactiv_ocenka_test_drive.comment_wheel      = request.POST.get('comment_wheel', '')


            reg_interactiv_ocenka_test_drive.airbag             = int(request.POST.get('radio_airbag', '3'))
            reg_interactiv_ocenka_test_drive.comment_airbag     = request.POST.get('comment_airbag', '')
            
            # Сохранение конкретных проблем безопасности
            reg_interactiv_ocenka_test_drive.airbag_driver_issue = 'airbag_driver_issue' in request.POST
            reg_interactiv_ocenka_test_drive.airbag_passenger_issue = 'airbag_passenger_issue' in request.POST
            reg_interactiv_ocenka_test_drive.airbag_side_issue = 'airbag_side_issue' in request.POST
            reg_interactiv_ocenka_test_drive.airbag_knee_issue = 'airbag_knee_issue' in request.POST
            reg_interactiv_ocenka_test_drive.seat_belt_restore_issue = 'seat_belt_restore_issue' in request.POST
            reg_interactiv_ocenka_test_drive.srs_block_issue = 'srs_block_issue' in request.POST

            reg_interactiv_ocenka_test_drive.brake              = int(request.POST.get('radio_brake', '3'))  
            reg_interactiv_ocenka_test_drive.comment_brake      = request.POST.get('comment_brake', '')

            reg_interactiv_ocenka_test_drive.subframe              = int(request.POST.get('radio_subframe', '10'))  
            reg_interactiv_ocenka_test_drive.comment_subframe      = request.POST.get('comment_subframe', '')

            reg_interactiv_ocenka_test_drive.hood_trunk_shock_absorber = int(request.POST.get('radio_hood_trunk_shock_absorber', '10'))
            reg_interactiv_ocenka_test_drive.comment_hood_trunk_shock_absorber = request.POST.get('comment_hood_trunk_shock_absorber', '')

            reg_interactiv_ocenka_test_drive.to                 = int(request.POST.get('radio_to', '10'))
            
            # Стапель
            stapele_type = request.POST.get('radio_stapele', '')
            if stapele_type:
                try:
                    stapele_type_int = int(stapele_type)
                    stapele_hours = request.POST.get('stapele_hours', '')
                    
                    if stapele_hours:
                        stapele_hours_int = int(stapele_hours)
                        # Определяем минимальное количество часов в зависимости от типа
                        min_hours = 12 if stapele_type_int in [1, 2] else 14
                        
                        # Валидация минимального количества часов
                        if stapele_hours_int < min_hours:
                            stapele_hours_int = min_hours
                        
                        # Определяем стоимость в зависимости от типа
                        stapele_cost = 3000 if stapele_type_int == 1 else (6000 if stapele_type_int == 2 else 9000)
                        
                        reg_interactiv_ocenka_test_drive.stapele_type = stapele_type_int
                        reg_interactiv_ocenka_test_drive.stapele_hours = stapele_hours_int
                        reg_interactiv_ocenka_test_drive.stapele_cost = stapele_cost
                    else:
                        # Если тип выбран, но часы не указаны, сбрасываем тип
                        reg_interactiv_ocenka_test_drive.stapele_type = None
                        reg_interactiv_ocenka_test_drive.stapele_hours = None
                        reg_interactiv_ocenka_test_drive.stapele_cost = None
                except (ValueError, TypeError):
                    reg_interactiv_ocenka_test_drive.stapele_type = None
                    reg_interactiv_ocenka_test_drive.stapele_hours = None
                    reg_interactiv_ocenka_test_drive.stapele_cost = None
            else:
                reg_interactiv_ocenka_test_drive.stapele_type = None
                reg_interactiv_ocenka_test_drive.stapele_hours = None
                reg_interactiv_ocenka_test_drive.stapele_cost = None

            reg_interactiv_ocenka_test_drive.pp_dinamyc             = int(request.POST.get('radio_pp_dinamyc', '3'))
            reg_interactiv_ocenka_test_drive.pp_kpp                 = int(request.POST.get('radio_pp_kpp', '3'))
            reg_interactiv_ocenka_test_drive.pp_uvod                = int(request.POST.get('radio_pp_uvod', '3'))
            reg_interactiv_ocenka_test_drive.pp_pribor              = int(request.POST.get('radio_pp_pribor', '3'))
            

            reg_interactiv_ocenka_test_drive.no_test            = 'no_test' in request.POST
            reg_interactiv_ocenka_test_drive.comment            = request.POST.get('comment', '')
            reg_interactiv_ocenka_test_drive.end_estimation     = DT.datetime.now()
            reg_interactiv_ocenka_test_drive.save()
            
            # Обработка выбранных элементов справочника диагностики
            from register.models import DiagnosticReferenceSelection, DiagnosticReferenceItem
            # Удаляем старые выборы для этого test_drive
            DiagnosticReferenceSelection.objects.filter(test_drive=reg_interactiv_ocenka_test_drive).delete()
            
            # Обрабатываем выбранные элементы для каждой категории
            category_codes = ['engine', 'gear', 'brake', 'suspension', 'system_og', 'wheel', 
                            'conditioner', 'turbo', 'drive', 'to', 'subframe', 'airbag', 'hood_trunk_shock_absorber']
            
            for category_code in category_codes:
                selected_items_key = f'selected_reference_items_{category_code}'
                if selected_items_key in request.POST:
                    selected_ids_str = request.POST.get(selected_items_key, '')
                    if selected_ids_str:
                        try:
                            selected_ids = [int(id.strip()) for id in selected_ids_str.split(',') if id.strip().isdigit()]
                            if selected_ids:
                                items = DiagnosticReferenceItem.objects.filter(
                                    id__in=selected_ids,
                                    category__code=category_code,
                                    is_active=True
                                )
                                for item in items:
                                    DiagnosticReferenceSelection.objects.get_or_create(
                                        test_drive=reg_interactiv_ocenka_test_drive,
                                        category_code=category_code,
                                        reference_item=item
                                    )
                        except (ValueError, DiagnosticReferenceItem.DoesNotExist):
                            pass  # Игнорируем ошибки при обработке
            
            comment_diagnostica = request.POST.get('comment_diagnostica', '')
            if interactiv_rlk.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovanie.save()
                interactiv_rlk.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                interactiv_rlk.save()
                
            else:
                reg_interactiv_ocenka_soglasovanie = interactiv_rlk.page_soglasovanie
            if comment_diagnostica != reg_interactiv_ocenka_soglasovanie.comment_diagnostica:
                reg_interactiv_ocenka_soglasovanie.comment_diagnostica = comment_diagnostica
                reg_interactiv_ocenka_soglasovanie.save()
            
            type_point  = ''
            text        = ''
            x = 0
            y = 0
            
            send_diagnostic = False
            no_diagnostica_comment = request.POST.get('no_diagnostica_comment', '')
            if no_diagnostica_comment != '':
                reg_interactiv_ocenka_soglasovanie.no_diagnostica_comment = no_diagnostica_comment
                reg_interactiv_ocenka_soglasovanie.no_diagnostica = True
                reg_interactiv_ocenka.date_diagnostic = DT.datetime.now()
            else:
                reg_interactiv_ocenka_soglasovanie.no_diagnostica_comment = ''
                reg_interactiv_ocenka_soglasovanie.no_diagnostica = False

            reg_interactiv_ocenka_soglasovanie.comment_no_endoscop = request.POST.get('comment_no_endoscop', '')
            reg_interactiv_ocenka_soglasovanie.comment_no_scaner = request.POST.get('comment_no_scaner', '')

            file_scaner = request.FILES.getlist('file_scaner')
            for file_object in file_scaner: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'scaner', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.file_number    = 1 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()

            file_endoscop = request.FILES.getlist('file_endoscop')
            for file_object in file_endoscop: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'endoscop', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.file_number    = 1 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()

            files_diagnostic = request.FILES.getlist('file_diagnistic')
            for file_object in files_diagnostic: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'diagnostic', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.file_number    = 1 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()
                send_diagnostic = True
                reg_interactiv_ocenka.date_diagnostic = DT.datetime.now()
            if len(comment_diagnostica) > 0:
                reg_interactiv_ocenka.date_diagnostic = DT.datetime.now()
                send_diagnostic = True

            reg_interactiv_ocenka_soglasovanie.save()
            reg_interactiv_ocenka.save()
            interactiv_rlk.save()
            if send_diagnostic:
                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Пройдена диагностика - ' + comment_diagnostica, estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'task_edit' in request.POST:
            task_edit = request.POST.get('task_edit', 0)
            if task_edit != 0:
                
                task = RegInteractivOcenkaTask.objects.get(id = task_edit)
                task.comment_success = request.POST.get('comment_success', '')
                task.date_close = DT.datetime.now()
                task.staff_close = request.user
                task.save()

                images_task = request.FILES.getlist('images_task')
                for file_object in images_task: 
                    name = file_object.name.lower()
                    new_estimation_files, created       = RegRegInteractivOcenkaTaskFiles.objects.get_or_create(estimation_task = task, name = name)
                    new_estimation_files.name           = name
                    new_estimation_files.file           = file_object
                    new_estimation_files.save()

                #reg_interactiv_ocenka.save()
                interactiv_rlk.save()
                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Закрыта задача ' + str(task.comment_task) + " - " + task.comment_success, estimation_id= reg_interactiv_ocenka.id)

            return HttpResponseRedirect(request.build_absolute_uri())   

        if 'price_before_kd' in request.POST:
            if reg_interactiv_ocenka.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovanie.save()
                reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                reg_interactiv_ocenka.save()
                interactiv_rlk.save()
            else:
                reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            reg_interactiv_ocenka_soglasovanie.price_before_kd = int(request.POST.get('price_before_kd', '0'))
            reg_interactiv_ocenka_soglasovanie.save()
            reg_interactiv_ocenka.date_s_do_diag = DT.datetime.now()
            reg_interactiv_ocenka.save()
            interactiv_rlk.save()
            
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_before_kd).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'price_after_kd' in request.POST:
            close_task(reg_interactiv_ocenka, request.user)
            if reg_interactiv_ocenka.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovanie.save()
                reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                reg_interactiv_ocenka.save()
                interactiv_rlk.save()
            else:
                reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            reg_interactiv_ocenka_soglasovanie.price_after_kd   = int(request.POST.get('price_after_kd', '0'))
            reg_interactiv_ocenka_soglasovanie.price_bcp        = int(request.POST.get('price_bcp', '0'))
            text = ''
            try:
                auction = request.POST.get('auction', '')
                if auction == 'Аукцион':
                    reg_interactiv_ocenka.auction = True
                    reg_interactiv_ocenka.auction_comment = request.POST.get('auction_comment', '')
                    reg_interactiv_ocenka.auction_data = request.POST.get('auction_type', '')
                    reg_interactiv_ocenka.save()
                    interactiv_rlk.save()  
                    text = "Продажа: Аукцион. Комментарий: " + reg_interactiv_ocenka.auction_comment
                else:
                    reg_interactiv_ocenka.auction = False
                    reg_interactiv_ocenka.auction_comment = ''
                    reg_interactiv_ocenka.save()
                    interactiv_rlk.save()
                    text = "Продажа: Розница."                  
            except:
                s=1

            '''   
            price_kors      = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='kors')
            if price_kors != None:
                if price_kors['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                    reg_interactiv_ocenka_soglasovanie.price_auto_1         = price_kors['estimation_price']
                    reg_interactiv_ocenka_soglasovanie.price_auto_bcp_1     = price_kors['cna_expenses']
                    reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_kors['zachita_ot_ubitka']
                    reg_interactiv_ocenka_soglasovanie.finance_price        = price_kors['finance_price']
                    reg_interactiv_ocenka_soglasovanie.price_zna_1          = price_kors['zna']
                    reg_interactiv_ocenka_soglasovanie.save()
            ''' 
            price_autohub   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='autohub')
            if price_autohub != None:
                #if price_autohub['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                reg_interactiv_ocenka_soglasovanie.discount_torg        = price_autohub['discount_torg']
                reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                reg_interactiv_ocenka_soglasovanie.price_zna_2          = price_autohub['zna']
                reg_interactiv_ocenka_soglasovanie.save()
            else:
                price_avito   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='avito')
                if price_avito != None:
                    #if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                    reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                    reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                    reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                    reg_interactiv_ocenka_soglasovanie.discount_torg        = price_avito['discount_torg']
                    reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                    reg_interactiv_ocenka_soglasovanie.price_zna_3          = price_avito['zna']
                    reg_interactiv_ocenka_soglasovanie.save()
            
            reg_interactiv_ocenka_soglasovanie.save()
            reg_interactiv_ocenka.date_s_diag = DT.datetime.now()
            reg_interactiv_ocenka.save()
            interactiv_rlk.save()
            
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_after_kd).replace(',', ' ') + ' ₽' + " " + text, estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'type_post' in request.POST:
            
            type_post = request.POST.get('type_post', '')
            if type_post == 'price_remote':
                price_remote    = float(request.POST.get('price_remote', '0'))
                page_remote     = reg_interactiv_ocenka.page_remote
                price_autohub   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='autohub')
                if price_autohub != None:            
                    page_remote.price_auto          = price_autohub['estimation_price']
                    page_remote.price_auto_bcp      = price_autohub['cna_expenses']
                    page_remote.zachita_ot_ubitka   = price_autohub['zachita_ot_ubitka']
                    page_remote.discount_torg       = price_autohub['discount_torg']
                    page_remote.finance_price       = price_autohub['finance_price']
                    page_remote.price_zna           = price_autohub['zna']
                
                page_remote.price_eco       = price_remote
                page_remote.price_eco_user  = request.user
                page_remote.save()
                
                reg_interactiv_ocenka.date_s_remote = DT.datetime.now()
                reg_interactiv_ocenka.save()
                interactiv_rlk.save()

                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до осмотра автомобиля - ' + '{:0,.2f}'.format(price_remote).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
                return HttpResponseRedirect(request.build_absolute_uri()) 
            
            elif type_post == 'save_auto_price':
                
                reg_interactiv_ocenka_soglasovanie = interactiv_rlk.page_soglasovanie

                price_info = estimations_price_calculation(interactiv_rlk = interactiv_rlk, estimation= reg_interactiv_ocenka, type_calculation = 'custom')
                #Сохраняем данные по планированию восстановительного ремонта
                save_recovery_estimations(interactiv_rlk = interactiv_rlk, reg_interactiv_ocenka = reg_interactiv_ocenka)

                estimation_price_do_kd  = float(request.POST.get('estimation_price_do_kd', '0')) 
                price_before_kd_comment = request.POST.get('price_before_kd_comment', '')
                
                reg_interactiv_ocenka_soglasovanie.price_before_kd          = estimation_price_do_kd
                reg_interactiv_ocenka_soglasovanie.price_before_kd_comment  = price_before_kd_comment

                if 'estimation_price_after_kd' in request.POST: 
                    reg_interactiv_ocenka_soglasovanie.price_after_kd              = float(request.POST.get('estimation_price_after_kd', '0')) 
                    reg_interactiv_ocenka_soglasovanie.price_after_kd_comment      = request.POST.get('price_after_kd_comment', '') 
                    reg_interactiv_ocenka_soglasovanie.price_bcp                   = float(request.POST.get('price_bcp', '0')) 

                    type_price                  = request.POST.get('type_price', '')
                if price_info != None:
                    reg_interactiv_ocenka_soglasovanie.amount_podgotovka    = price_info['amount_podgotovka']
                    reg_interactiv_ocenka_soglasovanie.amount_ss            = price_info['amount_ss']
                    reg_interactiv_ocenka_soglasovanie.amount_mcu           = price_info['amount_mcu']
                reg_interactiv_ocenka_soglasovanie.save()
                
                try:
                    auction = request.POST.get('auction', '')
                    if auction == 'Аукцион':
                        reg_interactiv_ocenka.auction = True
                        reg_interactiv_ocenka.auction_comment = request.POST.get('auction_comment', '')
                        reg_interactiv_ocenka.auction_data = request.POST.get('auction_type', '')
                        reg_interactiv_ocenka.save()
                        interactiv_rlk.save()  
                        text = "Продажа: Аукцион. Комментарий: " + reg_interactiv_ocenka.auction_comment
                    else:
                        reg_interactiv_ocenka.auction = False
                        reg_interactiv_ocenka.auction_comment = ''
                        reg_interactiv_ocenka.save()
                        interactiv_rlk.save()
                        text = "Продажа: Розница."                  
                except:
                    s=1
                
                reg_interactiv_ocenka.save()
                interactiv_rlk.save()

                if reg_interactiv_ocenka_soglasovanie.price_after_kd > 0:
                    close_task(reg_interactiv_ocenka, request.user)
                    RegEstimationsCalculationDetail.objects.filter(estimations = reg_interactiv_ocenka).delete()
                    '''
                    price_kors      = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='kors')
                    if price_kors != None:
                        if price_kors['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_1         = price_kors['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_1     = price_kors['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_kors['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_kors['finance_price']
                            reg_interactiv_ocenka_soglasovanie.price_zna_1          = price_kors['zna']
                            reg_interactiv_ocenka_soglasovanie.save()
                    else:
                    '''
                    price_autohub   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='autohub')
                    if price_autohub != None:
                        #if price_autohub['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                        reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                        reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                        reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                        reg_interactiv_ocenka_soglasovanie.discount_torg        = price_autohub['discount_torg']
                        reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                        reg_interactiv_ocenka_soglasovanie.price_zna_2          = price_autohub['zna']
                        reg_interactiv_ocenka_soglasovanie.save()
                    else:
                        price_avito   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='avito')
                        if price_avito != None:
                            #if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.discount_torg        = price_avito['discount_torg']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                            reg_interactiv_ocenka_soglasovanie.price_zna_3          = price_avito['zna']
                            reg_interactiv_ocenka_soglasovanie.save()

                    interactiv_rlk.staff_eco_2_rlk = request.user
                    interactiv_rlk.date_s_diag = DT.datetime.now() 
                    reg_interactiv_ocenka.save()
                    interactiv_rlk.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_after_kd).replace(',', ' ') + ' ₽' + " " + text, estimation_id= reg_interactiv_ocenka.id)
                elif reg_interactiv_ocenka_soglasovanie.price_before_kd > 0:
                    interactiv_rlk.staff_eco_1_rlk = request.user
                    interactiv_rlk.date_s_do_diag = DT.datetime.now()
                    reg_interactiv_ocenka.save()
                    interactiv_rlk.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_before_kd).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
  
            else:

                type_post = request.POST.get('type_post', '')
                
                if type_post == "save_auto_price":
                    if reg_interactiv_ocenka.page_soglasovanie == None:
                        reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                        reg_interactiv_ocenka_soglasovanie.save()
                        reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                        reg_interactiv_ocenka.save()
                        interactiv_rlk.save()
                    else:
                        reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            
                reg_interactiv_ocenka_soglasovanie.price_type                      = request.POST.get('type_price', '')
                reg_interactiv_ocenka_soglasovanie.price_correction                = int(request.POST.get('price_correction', '0'))
                reg_interactiv_ocenka_soglasovanie.price_correction_comment        = request.POST.get('price_correction_comment', '')
                reg_interactiv_ocenka_soglasovanie.price_correction_comment_author = request.user                

                custom_estimation_price_do_kd_old   = float(request.POST.get('custom_estimation_price_do_kd_old', '0'))
                custom_estimation_price_old         = float(request.POST.get('custom_estimation_price_old', '0'))
                custom_estimation_price_do_kd       = float(request.POST.get('custom_estimation_price_do_kd', '0'))
                custom_estimation_price             = float(request.POST.get('custom_estimation_price', '0'))

                price_info = estimations_price_calculation(interactiv_rlk = interactiv_rlk, estimation= reg_interactiv_ocenka, type_calculation = 'custom')
                save_recovery_estimations(interactiv_rlk = interactiv_rlk, reg_interactiv_ocenka = reg_interactiv_ocenka)
                
                if custom_estimation_price_do_kd > 0:
                    reg_interactiv_ocenka_soglasovanie.price_before_kd = custom_estimation_price_do_kd

                if custom_estimation_price > 0:
                    reg_interactiv_ocenka_soglasovanie.price_after_kd      = custom_estimation_price
                    reg_interactiv_ocenka_soglasovanie.price_bcp            = int(request.POST.get('price_bcp', '0'))
                    
                amount_podgotovka   = float(request.POST.get('amount_podgotovka', '0'))
                amount_ss           = float(request.POST.get('amount_ss', '0'))
                amount_mcu          = float(request.POST.get('amount_mcu', '0'))
                
                reg_interactiv_ocenka_soglasovanie.amount_podgotovka    = amount_podgotovka
                reg_interactiv_ocenka_soglasovanie.amount_ss            = amount_ss
                reg_interactiv_ocenka_soglasovanie.amount_mcu           = amount_mcu
                reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = 0
                reg_interactiv_ocenka_soglasovanie.save()
            
                try:
                    auction = request.POST.get('auction', '')
                    if auction == 'Аукцион':
                        reg_interactiv_ocenka.auction = True
                        reg_interactiv_ocenka.auction_comment = request.POST.get('auction_comment', '')
                        reg_interactiv_ocenka.auction_data = request.POST.get('auction_type', '')
                        reg_interactiv_ocenka.save()
                        interactiv_rlk.save()  
                        text = "Продажа: Аукцион. Комментарий: " + reg_interactiv_ocenka.auction_comment
                    else:
                        reg_interactiv_ocenka.auction = False
                        reg_interactiv_ocenka.auction_comment = ''
                        reg_interactiv_ocenka.save()
                        interactiv_rlk.save()
                        text = "Продажа: Розница."                  
                except:
                    s=1
                reg_interactiv_ocenka.save()
                interactiv_rlk.save()
                
                if reg_interactiv_ocenka_soglasovanie.price_after_kd > 0:
                    close_task(reg_interactiv_ocenka, request.user)
                    RegEstimationsCalculationDetail.objects.filter(estimations = reg_interactiv_ocenka).delete()
                    '''
                    price_kors      = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='kors')
                    if price_kors != None:
                        if price_kors['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_1         = price_kors['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_1     = price_kors['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_kors['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_kors['finance_price']
                            reg_interactiv_ocenka_soglasovanie.save()
                    else:
                    '''
                    price_autohub   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='autohub')
                    if price_autohub != None:
                        #if price_autohub['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                        reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                        reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                        reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                        reg_interactiv_ocenka_soglasovanie.discount_torg        = price_autohub['discount_torg']
                        reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                        reg_interactiv_ocenka_soglasovanie.save()
                    else:
                        price_avito   = estimations_price_calculation(interactiv_rlk, reg_interactiv_ocenka, type_calculation='avito')
                        if price_avito != None:
                            #if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.discount_torg        = price_avito['discount_torg']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                            reg_interactiv_ocenka_soglasovanie.save()

                    interactiv_rlk.staff_eco_2_rlk = request.user
                    interactiv_rlk.date_s_diag = DT.datetime.now()
                    reg_interactiv_ocenka.save()
                    interactiv_rlk.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_after_kd).replace(',', ' ') + ' ₽' + " " + text, estimation_id= reg_interactiv_ocenka.id)
                elif reg_interactiv_ocenka_soglasovanie.price_before_kd > 0:
                    interactiv_rlk.staff_eco_1_rlk = request.user
                    interactiv_rlk.date_s_do_diag = DT.datetime.now()
                    reg_interactiv_ocenka.save()
                    interactiv_rlk.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_before_kd).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
            
            #send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + str(reg_interactiv_ocenka_soglasovanie.price_after_kd) + " " + text, estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())    

        return HttpResponseRedirect(request.build_absolute_uri())  
    return render(request, 'lo/lo_v3.html', {'params': params})  
    if estimation.v > 1:
        return render(request, 'lo/lo_v' + str(estimation.v) + '.html', {'params': params})             
    else:
        return render(request, 'lo/lo.html', {'params': params}) 

def save_recovery_estimations(interactiv_rlk, reg_interactiv_ocenka):
    
    price_info = estimations_price_calculation(interactiv_rlk = interactiv_rlk, estimation = reg_interactiv_ocenka, type_calculation = 'custom')
    if price_info != None:
        RegEstimationPodgotovka.objects.filter(estimation = reg_interactiv_ocenka).delete()
        RegEstimationSS.objects.filter(estimation = reg_interactiv_ocenka).delete()
        RegEstimationMCU.objects.filter(estimation = reg_interactiv_ocenka).delete()
        for podgotovka in price_info['list_work_podgotovka']:
            new_record = RegEstimationPodgotovka()
            new_record.estimation       = reg_interactiv_ocenka
            new_record.name             = podgotovka['name']
            new_record.normo            = podgotovka['quantity']
            new_record.price_podrad     = podgotovka['amount_pod']
            new_record.price_kors       = podgotovka['amount']
            new_record.save()
            #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
            #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
            #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
        for podgotovka in price_info['list_work_service']:
            new_record                  = RegEstimationSS()
            new_record.estimation       = reg_interactiv_ocenka
            new_record.name             = podgotovka['name']
            new_record.normo            = podgotovka['quantity']
            new_record.price_podrad     = podgotovka['amount_pod']
            new_record.price_kors       = podgotovka['amount']
            new_record.save()
            #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
            #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
            #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
        for podgotovka in price_info['list_work_mcu']:
            new_record                  = RegEstimationMCU()
            new_record.estimation       = reg_interactiv_ocenka
            new_record.name             = podgotovka['name']
            new_record.normo            = podgotovka['quantity']
            new_record.price_podrad     = podgotovka['amount_pod']
            new_record.price_kors       = podgotovka['amount']
            new_record.save()
        if reg_interactiv_ocenka.page_soglasovanie != None:
            reg_interactiv_ocenka.page_soglasovanie.amount_podgotovka    = price_info['amount_podgotovka']
            reg_interactiv_ocenka.page_soglasovanie.amount_ss            = price_info['amount_ss']
            reg_interactiv_ocenka.page_soglasovanie.amount_mcu           = price_info['amount_mcu']
            reg_interactiv_ocenka.page_soglasovanie.save()            

def list_expenses(estimation):
    list_info = list()
    #DocZNWorkKA, DocZNProductKA, DocZNServicesKA, DocServiceItem
    if DocLO.objects.filter(rlk = estimation.rlk).count() > 0:
        lo  = DocLO.objects.filter(rlk = estimation.rlk)[0]
        list_works                  = DocZNWorkKA.objects.filter(zn__lo = lo)
        for list_work in list_works:
            item = {
                'type'          : list_work.zn.typeRemont,
                'date'          : list_work.zn.dataTime,
                'document'      : list_work.zn.nomer,
                'name'          : list_work.work.name,
                'qyantity'      : list_work.quantity,
                'price'         : list_work.price,
                'amount'        : list_work.amount,
                'description'   : '',
            }
            list_info.append(item)
        list_products               = DocZNProductKA.objects.filter(zn__lo = lo)
        for list_product in list_products:
            item = {
                'type'          : list_product.zn.typeRemont,
                'date'          : list_product.zn.dataTime,
                'document'      : list_product.zn.nomer,
                'name'          : list_product.product.name,
                'qyantity'      : list_product.quantity,
                'price'         : list_product.price,
                'amount'        : list_product.amount,
                'description'   : '',
            }
            list_info.append(item)
        list_services               = DocZNServicesKA.objects.filter(zn__lo = lo)
        for list_service in list_services:
            item = {
                'type'          : list_service.zn.typeRemont,
                'date'          : list_service.zn.dataTime,
                'document'      : list_service.zn.nomer,
                'name'          : list_service.service.name,
                'qyantity'      : list_service.quantity,
                'price'         : list_service.price,
                'amount'        : list_service.amount,
                'description'   : '',
            }
            list_info.append(item)
        list_services_podgotovka    = DocServiceItem.objects.filter(doc_service__lo = lo)
        for list_service_podgotovka in list_services_podgotovka:
            item = {
                'type'          : list_service_podgotovka.type_service.name,
                'date'          : list_service_podgotovka.doc_service.date_time,
                'document'      : list_service_podgotovka.doc_service.nomer,
                'name'          : list_service_podgotovka.service.name,
                'qyantity'      : list_service_podgotovka.quantity,
                'price'         : list_service_podgotovka.price,
                'amount'        : list_service_podgotovka.amount,
                'description'   : list_service_podgotovka.description,
            }
            list_info.append(item)
    return list_info


def body_estimation(estimation):
    
    array_info  = list()
    polys = RegInfoBody.objects.exclude(side = 'салон').order_by('body_elem_name').values('body_elem_name').distinct().order_by('body_elem_name')
    for poly in polys:
        dict_elem = dict()
        dict_elem['name']           = poly['body_elem_name']
        dict_elem['tr']             = 0
        dict_elem['carap']          = 0
        dict_elem['carap_strong']   = 0
        dict_elem['rzav']           = 0
        dict_elem['rzav_strong']    = 0
        dict_elem['vmyat']          = 0
        dict_elem['vmyat_strong']   = 0
        dict_elem['skol']           = 0
        dict_elem['perecras']       = 0
        dict_elem['perecras_strong'] = 0
        dict_elem['stiker']         = 0
        dict_elem['toner']          = 0
        dict_elem['poly']           = 0
        dict_elem['replace']        = 0
        dict_elem['replace_add']    = 0
        dict_elem['work']           = ''
        dict_elem['normo']          = 0.0
        dict_elem['podryad']        = 0
        dict_elem['all']            = 0
        dict_elem['kors']           = 0
        array_info.append(dict_elem)

    array_body  = list()
    files       = RegRegInteractivOcenkaFiles.objects.filter(type_file__icontains = 'array_images').filter(estimation = estimation).order_by('-type_file')
    
    
    carap           = 0
    carap_strong    = 0
    rzav            = 0
    rzav_strong     = 0
    vmyat           = 0
    vmyat_strong    = 0
    skol            = 0
    perecras        = 0
    perecras_strong = 0
    tr              = 0    
    all             = 0
    replace_add     = 0
    stiker          = 0
    toner           = 0
    poly            = 0
    replace         = 0

    for file in files:
        
        if file.type_file == 'array_images_pass':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'пассажирская')
        elif file.type_file == 'array_images_vod':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'водительская')
        elif file.type_file == 'array_images_pered':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'перед')
        elif file.type_file == 'array_images_zad':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'зад')
        elif file.type_file == 'array_images_up':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'верх')
        else:
            bodys_info = list()

        point = Point(file.cor_x , file.cor_y)
        for body in bodys_info:
            polygon  = list()
            poly_str = body.polygon
            lens_str = poly_str.split(',')
            len_mas  = len(lens_str)
            s = 0
            while s < len_mas:
                if s % 2 == 0:
                    polygon.append(Point(int(lens_str[s]), int(lens_str[s+1])))   
                s = s + 1
            # Check if the point is inside the polygon
            if point_in_polygon(point, polygon):
                dict_elem = ''
                elem_name = body.body_elem_name
                name = '' + body.body_elem_name + ' - ' + file.type_point 
                if file.type_point == 'толщиномер':
                    if file.kraska > 300:
                        name = '' + body.body_elem_name + ' - окрашено'
                    else:
                        name = ''
                if elem_name != '':
                    try:
                        index = array_body.index(elem_name)
                        for elem_data in array_info:
                            if elem_data['name'] == elem_name:
                                dict_elem = elem_data
                    except ValueError:
                        for elem_data in array_info:
                            if elem_data['name'] == elem_name:
                                dict_elem = elem_data
                                all = elem_data['all']
                        if dict_elem == '':
                            all = 0
                            dict_elem = dict()
                            dict_elem['name']               = elem_name
                            dict_elem['tr']                 = 0
                            dict_elem['carap']              = 0
                            dict_elem['carap_strong']       = 0
                            dict_elem['rzav']               = 0
                            dict_elem['rzav_strong']        = 0
                            dict_elem['vmyat']              = 0
                            dict_elem['vmyat_strong']       = 0
                            dict_elem['skol']               = 0
                            dict_elem['perecras']           = 0
                            dict_elem['perecras_strong']    = 0
                            dict_elem['replace_add']        = 0
                            dict_elem['replace']            = 0
                            dict_elem['stiker']             = 0
                            dict_elem['toner']              = 0
                            dict_elem['poly']               = 0
                            dict_elem['work']               = ''
                            dict_elem['normo']              = 0.0
                            dict_elem['podryad']            = 0
                            dict_elem['all']                = 0
                            dict_elem['kors']               = 0
                            

                    if file.type_point == 'толщиномер':
                        if file.kraska > 300:
                            dict_elem['perecras'] = dict_elem['perecras'] + 1
                            perecras = perecras + 1
                        if file.kraska > 900:
                            dict_elem['perecras_strong'] = dict_elem['perecras_strong'] + 1
                            perecras_strong = perecras_strong + 1
                    if file.type_point == 'ржавчина':
                        dict_elem['rzav']           = dict_elem['rzav']  + 1
                        rzav = rzav + 1
                        all = all + 1
                    elif file.type_point == 'ржавчина сквозная':
                        dict_elem['rzav_strong']    =  dict_elem['rzav_strong']  + 1
                        rzav_strong = rzav_strong + 1
                        all = all + 1
                    elif file.type_point == 'царапина':
                        dict_elem['carap']          =  dict_elem['carap']  + 1
                        carap = carap + 1
                        all = all + 1
                    elif file.type_point == 'царапина сильная':
                        dict_elem['carap_strong']    =  dict_elem['carap_strong']  + 1
                        carap_strong = carap_strong + 1
                        all = all + 1
                    elif file.type_point == 'вмятина':
                        dict_elem['vmyat']          =  dict_elem['vmyat']  + 1
                        vmyat = vmyat + 1
                        all = all + 1
                    elif file.type_point == 'вмятина сильная':
                        dict_elem['vmyat_strong']    =  dict_elem['vmyat_strong']  + 1
                        vmyat_strong = vmyat_strong + 1
                        all = all + 1
                    elif file.type_point == 'скол':
                        dict_elem['skol']               =  dict_elem['skol']  + 1
                        skol = skol + 1
                        all = all + 1
                    elif file.type_point == 'трещина':
                        dict_elem['tr']               =  dict_elem['tr']  + 1
                        tr = tr + 1
                        all = all + 1
                    elif file.type_point == 'заменить':
                        dict_elem['replace_add'] = dict_elem['replace_add']  + 1
                        replace_add = replace_add + 1
                        all = all + 1
                    elif file.type_point == 'заменен':
                        dict_elem['replace'] = dict_elem['replace']  + 1
                        replace = replace + 1
                        all = all + 1
                    elif file.type_point == 'наклейка':
                        dict_elem['stiker'] = dict_elem['stiker']  + 1
                        stiker = stiker + 1
                        all = all + 1
                    elif file.type_point == 'тонировка':
                        dict_elem['toner'] = dict_elem['toner']  + 1
                        toner = toner + 1
                        all = all + 1
                    elif file.type_point == 'полировка':
                        dict_elem['poly'] = dict_elem['poly']  + 1
                        poly = poly + 1
                        all = all + 1
                    dict_elem['all'] = all
                    for elem_data in array_info:
                        if elem_data['name'] == elem_name:
                            elem_data = dict_elem
                    
                    array_body.append(elem_name)

    body = {
        'array'             : array_info,
        'carap'             : carap,
        'carap_strong'      : carap_strong,
        'rzav'              : rzav,
        'rzav_strong'       : rzav_strong,
        'vmyat'             : vmyat,
        'vmyat_strong'      : vmyat_strong,
        'skol'              : skol,
        'perecras'          : perecras,
        'perecras_strong'   : perecras_strong,
        'tr'                : tr,
        'replace_add'       : replace_add,
        'stiker'            : stiker,
        'toner'             : toner,
        'poly'              : poly,
        'replace'           : replace
        }
    
    
    return body


def salon_estimation(estimation):
    
    array_info  = list()
    polys = RegInfoBody.objects.filter(side = 'салон').order_by('body_elem_name').values('body_elem_name').distinct().order_by('-body_elem_name')
    for poly in polys:
        dict_elem = dict()
        dict_elem['name']           = poly['body_elem_name']
        dict_elem['perecras']       = 0
        dict_elem['dirka']          = 0
        dict_elem['pereshiv']       = 0
        dict_elem['vost']           = 0
        dict_elem['work']           = ''
        dict_elem['normo']          = 0.0
        dict_elem['podryad']        = 0
        dict_elem['all']            = 0
        dict_elem['kors']           = 0
        array_info.append(dict_elem)

    array_salon     = list()
    files           = RegRegInteractivOcenkaFiles.objects.filter(type_file__icontains = 'array_images_osmotr_salon').filter(estimation = estimation).order_by('-type_file')
    
    perecras        = 0
    dirka           = 0
    pereshiv        = 0
    vost            = 0
    
    for file in files:
        
        salons_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'салон').order_by('-body_elem_name')

        point = Point(file.cor_x , file.cor_y)
        for salon in salons_info:
            polygon  = list()
            poly_str = salon.polygon
            lens_str = poly_str.split(',')
            len_mas  = len(lens_str)
            s = 0
            while s < len_mas:
                if s % 2 == 0:
                    polygon.append(Point(int(lens_str[s]), int(lens_str[s+1])))   
                s = s + 1
            # Check if the point is inside the polygon
            if point_in_polygon(point, polygon):
                dict_elem = ''
                elem_name = salon.body_elem_name
                name = '' + salon.body_elem_name + ' - ' + file.type_point 
                if name != '':
                    try:
                        index = array_salon.index(name)
                    except ValueError:
                        for elem_data in array_info:
                            if elem_data['name'] == elem_name:
                                dict_elem = elem_data
                                all = elem_data['all']
                        if dict_elem == '':
                            all = 0
                            dict_elem = dict()
                            dict_elem['name']               = elem_name
                            dict_elem['perecras']           = 0
                            dict_elem['dirka']              = 0
                            dict_elem['pereshiv']           = 0
                            dict_elem['vost']               = 0
                            dict_elem['work']               = ''
                            dict_elem['normo']              = 0.0
                            dict_elem['podryad']            = 0
                            dict_elem['all']                = 0
                            dict_elem['kors']               = 0                            

                        if file.type_point == 'перекрас':
                            dict_elem['perecras']   = dict_elem['perecras']  + 1
                            perecras = perecras + 1
                            all = all + 1
                        elif file.type_point == 'дырка':
                            dict_elem['dirka']    =  dict_elem['dirka']  + 1
                            dirka = dirka + 1
                            all = all + 1
                        elif file.type_point == 'перешив':
                            dict_elem['pereshiv']          =  dict_elem['pereshiv']  + 1
                            pereshiv = pereshiv + 1
                            all = all + 1
                        elif file.type_point == 'восстановление':
                            dict_elem['vost']    =  dict_elem['vost']  + 1
                            vost = vost + 1
                            all = all + 1
                        dict_elem['all'] = all
                        for elem_data in array_info:
                            if elem_data['name'] == elem_name:
                                elem_data = dict_elem
                        
                        array_salon.append(name)

    salon = {
        'array'             : array_info,
        'perecras'          : perecras,
        'dirka'             : dirka,
        'pereshiv'          : pereshiv,
        'vost'              : vost
        }
    
    
    return salon


def repair_history(estimation, count = False):
    if estimation.vin != '':
        if count:
            return DocZN.objects.filter(cars__vin__icontains = estimation.vin).count()
        else:
            return DocZN.objects.filter(cars__vin__icontains = estimation.vin).order_by('-dataTime')
    return list()


def repair_history_vin(vin, count = False):
    if vin != '':
        if count:
            return DocZN.objects.filter(cars__vin__icontains = vin).count()
        else:
            return DocZN.objects.filter(cars__vin__icontains = vin).order_by('-dataTime')
    return list()


def estimation_lo_history(estimation, count = False):
    if estimation.vin != '':
        if count:
            lo = DocLO.objects.filter(vin = estimation.vin)
            subqyery_interactiv = Subquery(RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='rlk__id')).values('rlk_id')[:1], output_field = models.IntegerField())
            lo = lo.annotate(interactiv = Count(subqyery_interactiv))
            lo = lo.filter(interactiv = 0).count()
            interatciv = RegInteractivOcenka.objects.filter(vin = estimation.vin).count()
            return lo + interatciv
        else:
            list_info = list()
            interatcivs = RegInteractivOcenka.objects.filter(vin = estimation.vin).order_by('-start_estimation')
            sub_lo = DocLO.objects.filter(rlk__id = OuterRef(name='rlk__id'))
            interatcivs = interatcivs.annotate(
                lo_number   = Subquery(sub_lo.values('nomer')[:1])).annotate(
                interactiv  = Value(True))
            
            for interatciv in interatcivs:
                list_info.append(interatciv)
            lo = DocLO.objects.filter(vin = estimation.vin).order_by('-dataTime')
            subqyery_interactiv = Subquery(RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='rlk__id')).values('rlk_id')[:1], output_field = models.IntegerField())
            lo = lo.annotate(interactiv = Count(subqyery_interactiv))
            lo = lo.filter(interactiv = 0)
            for lo_info in lo:
                list_info.append(lo_info)
            return list_info
        
    return list()


def estimations_price_calculation(interactiv_rlk, estimation, type_calculation, remote = False):


    estimation_settings     = RegEstimationsSettings.objects.all().last()
    if interactiv_rlk.page_soglasovanie != None:
        if interactiv_rlk.page_soglasovanie.settings != None:
            estimation_settings = interactiv_rlk.page_soglasovanie.settings 

    modification            = estimation.modification
    
    list_work_podgotovka    = list()
    list_work_service       = list()
    list_work_mcu           = list()

    run_estimation = 0
    if estimation.page_salon != None:  
        run_estimation = estimation.page_salon.run
    elif estimation.page_remote != None:
        run_estimation = estimation.page_remote.run

    auction_success     = False
    auction             = False
    auction_comment     = ''
    amount_podgotovka   = 0
    amount_ss           = 0
    amount_mcu          = 0
    ammount_sum         = 0
    kf_auction          = 75 

    list_info_price     = list()
    zna_type            = ''
    zna                 = 0
    zachita_ot_ubitka   = 0
    finance_price       = 0
    iznos_price         = 0
    damage_gear         = False
    damage_wheels       = False

    if type_calculation == 'kors':
        zna         = estimation.kors_price
        zna_type    = '1C'
    if type_calculation == 'autohub':
        if estimation.hub_avg == 0 and estimation.page_remote != None:
            zna = estimation.page_remote.hub_avg
        else:
            zna         = estimation.hub_avg
        if remote:
            if estimation.page_remote != None:
                zna = estimation.page_remote.hub_avg    
        zna_type    = 'Автохаб'
    elif type_calculation == 'avito':
        zna = estimation.avito_price_avg_market_price
        zna_type = 'Авито'   
    elif type_calculation == 'custom':
        zna = estimation.custom_zna
        zna_type = 'Ручная'

    if zna == 0:
        return None
    
    zg  = "Неопределена"
    # if interactiv_rlk.unit == None:
    #     dc              = estimation.page_remote.unit
    # else:
    #     dc              = estimation.unit
    dc = interactiv_rlk.unit

    fin_all         = estimation_settings.all_percent_financity
    day_sale_all    = estimation_settings.all_days_stok_financity
    
    kf                  = 100
    percent_ss          = 0
    percent_torg        = 0
    zna_izp_kf          = 0
    zna_izp_type        = 0
    percent_sale_1C     = 100
    percent_sale        = 100
    percent_sale_rdo    = 100
    percent_sale_kor    = 100
    battery             = 0
    matrix_auction      = 0
    
    settings_matrix = SettingsMatrixAuction.objects.get(pk = 1)
    
    if zna < 200000:
        zg              = '200'
        matrix_auction  = settings_matrix.charge_bcp_200
        # ИРЦ ТХТ / защита от скидок / лимиты
        kf              = getattr(dc, 'correction_txt_200', None) if getattr(dc, 'correction_txt_200', None) not in (None, 0) else dc.ratio_avtohub_txt_200
        percent_ss      = getattr(dc, 'markup_txt_200',   None) if getattr(dc, 'markup_txt_200',   None) not in (None, 0) else dc.percent_txt_200
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_200', None) if getattr(dc, 'max_discount_bargain_percent_200', None) not in (None, 0) else dc.percent_torg_txt_200
        zna_izp_kf      = estimation_settings.izp_200
        zna_izp_type    = estimation_settings.izp_200_v
        # Коэффициенты продажи по каналам
        percent_sale_1C = getattr(dc, 'correction_test_1c_200', None) if getattr(dc, 'correction_test_1c_200', None) not in (None, 0) else dc.ratio_1с_test_price_200
        percent_sale    = getattr(dc, 'correction_test_200',    None) if getattr(dc, 'correction_test_200',    None) not in (None, 0) else dc.ratio_avtohub_test_price_200
        percent_sale_rdo= getattr(dc, 'correction_rdo_200',     None) if getattr(dc, 'correction_rdo_200',     None) not in (None, 0) else dc.ratio_avtohub_rdo_200
        percent_sale_kor= getattr(dc, 'correction_kor_200',     None) if getattr(dc, 'correction_kor_200',     None) not in (None, 0) else dc.ratio_avtohub_kor_200
        kf_auction      = estimation_settings.auction_kf_200
        fin_zg          = estimation_settings.percent_financity_200
        day_sale_zg     = estimation_settings.days_stok_financity_200
        
        windshield      = estimation_settings.windshield_200
        windshield_heat = estimation_settings.windshield_heat_200
        light_pered     = estimation_settings.light_pered_200
        light_pered_kf  = estimation_settings.light_pered_kf_200
        light_zad       = estimation_settings.light_zad_200
        light_zad_kf    = estimation_settings.light_zad_kf_200
        battery         = estimation_settings.battery_200
        engine_danger_kf            = estimation_settings.engine_danger_kf_200            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_200        
        engine_warning_kf           = estimation_settings.engine_warning_kf_200 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_200 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_200   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_200   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_200    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_200    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_200 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_200 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_200  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_200  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_200  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_200  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_200   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_200   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_200  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_200  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_200   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_200   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_200 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_200 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_200     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_200   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_200   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_200       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_200        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_200       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_200     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_200     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_200      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_200
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_200
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_200
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_200
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_200
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_200
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_200
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_200
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_200
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_200
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_200
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_200
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_200
        brake_danger_kf              = estimation_settings.brake_danger_kf_200
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_200
        brake_warning_kf             = estimation_settings.brake_warning_kf_200
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_200
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_200
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_200
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_200
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_200
        drive_danger_kf              = estimation_settings.drive_danger_kf_200
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_200
        drive_warning_kf             = estimation_settings.drive_warning_kf_200
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_200
        to_1                         = estimation_settings.to_1_200
        to_2                         = estimation_settings.to_2_200
        to_3                         = estimation_settings.to_3_200
    elif zna < 400000:
        zg              = '400'
        matrix_auction  = settings_matrix.charge_bcp_400
        fin_zg          = estimation_settings.percent_financity_400
        day_sale_zg     = estimation_settings.days_stok_financity_400
        kf              = getattr(dc, 'correction_txt_400', None) if getattr(dc, 'correction_txt_400', None) not in (None, 0) else dc.ratio_avtohub_txt_400
        percent_ss      = getattr(dc, 'markup_txt_400',   None) if getattr(dc, 'markup_txt_400',   None) not in (None, 0) else dc.percent_txt_400
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_400', None) if getattr(dc, 'max_discount_bargain_percent_400', None) not in (None, 0) else dc.percent_torg_txt_400
        zna_izp_kf      = estimation_settings.izp_400
        zna_izp_type    = estimation_settings.izp_400_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_400', None) if getattr(dc, 'correction_test_1c_400', None) not in (None, 0) else dc.ratio_1с_test_price_400
        percent_sale    = getattr(dc, 'correction_test_400',    None) if getattr(dc, 'correction_test_400',    None) not in (None, 0) else dc.ratio_avtohub_test_price_400
        percent_sale_rdo= getattr(dc, 'correction_rdo_400',     None) if getattr(dc, 'correction_rdo_400',     None) not in (None, 0) else dc.ratio_avtohub_rdo_400
        percent_sale_kor= getattr(dc, 'correction_kor_400',     None) if getattr(dc, 'correction_kor_400',     None) not in (None, 0) else dc.ratio_avtohub_kor_400
        kf_auction      = estimation_settings.auction_kf_400
        windshield      = estimation_settings.windshield_400
        windshield_heat = estimation_settings.windshield_heat_400
        light_pered     = estimation_settings.light_pered_400
        light_pered_kf  = estimation_settings.light_pered_kf_400
        light_zad       = estimation_settings.light_zad_400
        light_zad_kf    = estimation_settings.light_zad_kf_400
        battery         = estimation_settings.battery_400
        engine_danger_kf            = estimation_settings.engine_danger_kf_400            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_400
        engine_warning_kf           = estimation_settings.engine_warning_kf_400 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_400 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_400   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_400   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_400    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_400    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_400 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_400 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_400  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_400  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_400  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_400  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_400   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_400   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_400  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_400  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_400   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_400   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_400 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_400 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_400     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_400   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_400   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_400       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_400        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_400       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_400     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_400     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_400      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_400
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_400
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_400
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_400
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_400
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_400
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_400
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_400
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_400
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_400
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_400
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_400
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_400
        brake_danger_kf              = estimation_settings.brake_danger_kf_400
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_400
        brake_warning_kf             = estimation_settings.brake_warning_kf_400
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_400
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_400
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_400
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_400
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_400
        drive_danger_kf              = estimation_settings.drive_danger_kf_400
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_400
        drive_warning_kf             = estimation_settings.drive_warning_kf_400
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_400
        to_1                         = estimation_settings.to_1_400
        to_2                         = estimation_settings.to_2_400
        to_3                         = estimation_settings.to_3_400
    elif zna < 700000:
        zg              = '700'
        matrix_auction  = settings_matrix.charge_bcp_700
        fin_zg          = estimation_settings.percent_financity_700
        day_sale_zg     = estimation_settings.days_stok_financity_700
        kf              = getattr(dc, 'correction_txt_700', None) if getattr(dc, 'correction_txt_700', None) not in (None, 0) else dc.ratio_avtohub_txt_700
        percent_ss      = getattr(dc, 'markup_txt_700',   None) if getattr(dc, 'markup_txt_700',   None) not in (None, 0) else dc.percent_txt_700
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_700', None) if getattr(dc, 'max_discount_bargain_percent_700', None) not in (None, 0) else dc.percent_torg_txt_700
        zna_izp_kf      = estimation_settings.izp_700
        zna_izp_type    = estimation_settings.izp_700_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_700', None) if getattr(dc, 'correction_test_1c_700', None) not in (None, 0) else dc.ratio_1с_test_price_700
        percent_sale    = getattr(dc, 'correction_test_700',    None) if getattr(dc, 'correction_test_700',    None) not in (None, 0) else dc.ratio_avtohub_test_price_700
        percent_sale_rdo= getattr(dc, 'correction_rdo_700',     None) if getattr(dc, 'correction_rdo_700',     None) not in (None, 0) else dc.ratio_avtohub_rdo_700
        percent_sale_kor= getattr(dc, 'correction_kor_700',     None) if getattr(dc, 'correction_kor_700',     None) not in (None, 0) else dc.ratio_avtohub_kor_700
        kf_auction      = estimation_settings.auction_kf_700
        windshield      = estimation_settings.windshield_700
        windshield_heat = estimation_settings.windshield_heat_700
        light_pered     = estimation_settings.light_pered_700
        light_pered_kf  = estimation_settings.light_pered_kf_700
        light_zad       = estimation_settings.light_zad_700
        light_zad_kf    = estimation_settings.light_zad_kf_700
        battery         = estimation_settings.battery_700
        engine_danger_kf            = estimation_settings.engine_danger_kf_700            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_700
        engine_warning_kf           = estimation_settings.engine_warning_kf_700 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_700 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_700   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_700   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_700    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_700    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_700 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_700 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_700  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_700  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_700  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_700  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_700   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_700   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_700  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_700  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_700   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_700   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_700 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_700 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_700     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_700   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_700   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_700       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_700        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_700       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_700     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_700     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_700      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_700
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_700
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_700
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_700
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_700
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_700
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_700
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_700
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_700
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_700
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_700
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_700
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_700
        brake_danger_kf              = estimation_settings.brake_danger_kf_700
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_700
        brake_warning_kf             = estimation_settings.brake_warning_kf_700
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_700
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_700
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_700
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_700
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_700
        drive_danger_kf              = estimation_settings.drive_danger_kf_700
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_700
        drive_warning_kf             = estimation_settings.drive_warning_kf_700
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_700
        to_1                         = estimation_settings.to_1_700
        to_2                         = estimation_settings.to_2_700
        to_3                         = estimation_settings.to_3_700
    elif zna < 1200000:
        zg              = '1 200'
        matrix_auction  = settings_matrix.charge_bcp_1200
        fin_zg          = estimation_settings.percent_financity_1200
        day_sale_zg     = estimation_settings.days_stok_financity_1200
        kf              = getattr(dc, 'correction_txt_1200', None) if getattr(dc, 'correction_txt_1200', None) not in (None, 0) else dc.ratio_avtohub_txt_1200
        percent_ss      = getattr(dc, 'markup_txt_1200',   None) if getattr(dc, 'markup_txt_1200',   None) not in (None, 0) else dc.percent_txt_1200
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_1200', None) if getattr(dc, 'max_discount_bargain_percent_1200', None) not in (None, 0) else dc.percent_torg_txt_1200
        zna_izp_kf      = estimation_settings.izp_1200
        zna_izp_type    = estimation_settings.izp_1200_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_1200', None) if getattr(dc, 'correction_test_1c_1200', None) not in (None, 0) else dc.ratio_1с_test_price_1200
        percent_sale    = getattr(dc, 'correction_test_1200',    None) if getattr(dc, 'correction_test_1200',    None) not in (None, 0) else dc.ratio_avtohub_test_price_1200
        percent_sale_rdo= getattr(dc, 'correction_rdo_1200',     None) if getattr(dc, 'correction_rdo_1200',     None) not in (None, 0) else dc.ratio_avtohub_rdo_1200
        percent_sale_kor= getattr(dc, 'correction_kor_1200',     None) if getattr(dc, 'correction_kor_1200',     None) not in (None, 0) else dc.ratio_avtohub_kor_1200
        kf_auction      = estimation_settings.auction_kf_1200
        windshield      = estimation_settings.windshield_1200
        windshield_heat = estimation_settings.windshield_heat_1200
        light_pered     = estimation_settings.light_pered_1200
        light_pered_kf  = estimation_settings.light_pered_kf_1200
        light_zad       = estimation_settings.light_zad_1200
        light_zad_kf    = estimation_settings.light_zad_kf_1200
        battery         = estimation_settings.battery_1200
        engine_danger_kf            = estimation_settings.engine_danger_kf_1200            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_1200
        engine_warning_kf           = estimation_settings.engine_warning_kf_1200 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_1200 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_1200   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_1200   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_1200    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_1200    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_1200 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_1200 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_1200  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_1200  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_1200  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_1200  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_1200   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_1200   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_1200  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_1200  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_1200   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_1200   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_1200 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_1200 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_1200     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_1200   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_1200   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_1200       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_1200        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_1200       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_1200     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_1200     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_1200      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_1200
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_1200
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_1200
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_1200
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_1200
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_1200
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_1200
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_1200
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_1200
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_1200
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_1200
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_1200
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_1200
        brake_danger_kf              = estimation_settings.brake_danger_kf_1200
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_1200
        brake_warning_kf             = estimation_settings.brake_warning_kf_1200
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_1200
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_1200
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_1200
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_1200
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_1200
        drive_danger_kf              = estimation_settings.drive_danger_kf_1200
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_1200
        drive_warning_kf             = estimation_settings.drive_warning_kf_1200
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_1200
        to_1                         = estimation_settings.to_1_1200
        to_2                         = estimation_settings.to_2_1200
        to_3                         = estimation_settings.to_3_1200
    elif zna < 2000000:
        zg              = '2 000'
        matrix_auction  = settings_matrix.charge_bcp_2000
        fin_zg          = estimation_settings.percent_financity_2000
        day_sale_zg     = estimation_settings.days_stok_financity_2000
        kf              = getattr(dc, 'correction_txt_2000', None) if getattr(dc, 'correction_txt_2000', None) not in (None, 0) else dc.ratio_avtohub_txt_2000
        percent_ss      = getattr(dc, 'markup_txt_2000',   None) if getattr(dc, 'markup_txt_2000',   None) not in (None, 0) else dc.percent_txt_2000
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_2000', None) if getattr(dc, 'max_discount_bargain_percent_2000', None) not in (None, 0) else dc.percent_torg_txt_2000
        zna_izp_kf      = estimation_settings.izp_2000
        zna_izp_type    = estimation_settings.izp_2000_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_2000', None) if getattr(dc, 'correction_test_1c_2000', None) not in (None, 0) else dc.ratio_1с_test_price_2000
        percent_sale    = getattr(dc, 'correction_test_2000',    None) if getattr(dc, 'correction_test_2000',    None) not in (None, 0) else dc.ratio_avtohub_test_price_2000
        percent_sale_rdo= getattr(dc, 'correction_rdo_2000',     None) if getattr(dc, 'correction_rdo_2000',     None) not in (None, 0) else dc.ratio_avtohub_rdo_2000
        percent_sale_kor= getattr(dc, 'correction_kor_2000',     None) if getattr(dc, 'correction_kor_2000',     None) not in (None, 0) else dc.ratio_avtohub_kor_2000
        kf_auction      = estimation_settings.auction_kf_2000
        windshield      = estimation_settings.windshield_2000
        windshield_heat = estimation_settings.windshield_heat_2000
        light_pered     = estimation_settings.light_pered_2000
        light_pered_kf  = estimation_settings.light_pered_kf_2000
        light_zad       = estimation_settings.light_zad_2000
        light_zad_kf    = estimation_settings.light_zad_kf_2000
        battery         = estimation_settings.battery_2000
        engine_danger_kf            = estimation_settings.engine_danger_kf_2000            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_2000
        engine_warning_kf           = estimation_settings.engine_warning_kf_2000 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_2000 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_2000   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_2000   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_2000    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_2000    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_2000 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_2000 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_2000  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_2000  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_2000  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_2000  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_2000   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_2000   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_2000  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_2000  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_2000   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_2000   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_2000 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_2000 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_2000     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_2000   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_2000   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_2000       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_2000        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_2000       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_2000     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_2000     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_2000      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_2000
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_2000
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_2000
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_2000
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_2000
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_2000
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_2000
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_2000
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_2000
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_2000
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_2000
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_2000
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_2000
        brake_danger_kf              = estimation_settings.brake_danger_kf_2000
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_2000
        brake_warning_kf             = estimation_settings.brake_warning_kf_2000
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_2000
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_2000
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_2000
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_2000
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_2000
        drive_danger_kf              = estimation_settings.drive_danger_kf_2000
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_2000
        drive_warning_kf             = estimation_settings.drive_warning_kf_2000
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_2000
        to_1                         = estimation_settings.to_1_2000
        to_2                         = estimation_settings.to_2_2000
        to_3                         = estimation_settings.to_3_2000
    elif zna < 3000000:
        zg              = '3 000'
        matrix_auction  = settings_matrix.charge_bcp_3000
        fin_zg          = estimation_settings.percent_financity_3000
        day_sale_zg     = estimation_settings.days_stok_financity_3000
        kf              = getattr(dc, 'correction_txt_3000', None) if getattr(dc, 'correction_txt_3000', None) not in (None, 0) else dc.ratio_avtohub_txt_3000
        percent_ss      = getattr(dc, 'markup_txt_3000',   None) if getattr(dc, 'markup_txt_3000',   None) not in (None, 0) else dc.percent_txt_3000
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_3000', None) if getattr(dc, 'max_discount_bargain_percent_3000', None) not in (None, 0) else dc.percent_torg_txt_3000
        zna_izp_kf      = estimation_settings.izp_3000
        zna_izp_type    = estimation_settings.izp_3000_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_3000', None) if getattr(dc, 'correction_test_1c_3000', None) not in (None, 0) else dc.ratio_1с_test_price_3000
        percent_sale    = getattr(dc, 'correction_test_3000',    None) if getattr(dc, 'correction_test_3000',    None) not in (None, 0) else dc.ratio_avtohub_test_price_3000
        percent_sale_rdo= getattr(dc, 'correction_rdo_3000',     None) if getattr(dc, 'correction_rdo_3000',     None) not in (None, 0) else dc.ratio_avtohub_rdo_3000
        percent_sale_kor= getattr(dc, 'correction_kor_3000',     None) if getattr(dc, 'correction_kor_3000',     None) not in (None, 0) else dc.ratio_avtohub_kor_3000
        kf_auction      = estimation_settings.auction_kf_3000
        windshield      = estimation_settings.windshield_3000
        windshield_heat = estimation_settings.windshield_heat_3000
        light_pered     = estimation_settings.light_pered_3000
        light_pered_kf  = estimation_settings.light_pered_kf_3000
        light_zad       = estimation_settings.light_zad_3000
        light_zad_kf    = estimation_settings.light_zad_kf_3000
        battery         = estimation_settings.battery_3000
        engine_danger_kf            = estimation_settings.engine_danger_kf_3000            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_3000
        engine_warning_kf           = estimation_settings.engine_warning_kf_3000 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_3000 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_3000   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_3000   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_3000    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_3000    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_3000 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_3000 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_3000  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_3000  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_3000  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_3000  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_3000   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_3000   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_3000  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_3000  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_3000   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_3000   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_3000 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_3000 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_3000     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_3000   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_3000   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_3000       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_3000        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_3000       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_3000     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_3000     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_3000      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_3000
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_3000
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_3000
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_3000
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_3000
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_3000
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_3000
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_3000
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_3000
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_3000
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_3000
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_3000
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_3000
        brake_danger_kf              = estimation_settings.brake_danger_kf_3000
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_3000
        brake_warning_kf             = estimation_settings.brake_warning_kf_3000
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_3000
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_3000
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_3000
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_3000
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_3000
        drive_danger_kf              = estimation_settings.drive_danger_kf_3000
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_3000
        drive_warning_kf             = estimation_settings.drive_warning_kf_3000
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_3000
        to_1                         = estimation_settings.to_1_3000
        to_2                         = estimation_settings.to_2_3000
        to_3                         = estimation_settings.to_3_3000
    elif zna < 5000000:
        zg              = '5 000'
        matrix_auction  = settings_matrix.charge_bcp_5000
        fin_zg          = estimation_settings.percent_financity_5000
        day_sale_zg     = estimation_settings.days_stok_financity_5000
        kf              = getattr(dc, 'correction_txt_5000', None) if getattr(dc, 'correction_txt_5000', None) not in (None, 0) else dc.ratio_avtohub_txt_5000
        percent_ss      = getattr(dc, 'markup_txt_5000',   None) if getattr(dc, 'markup_txt_5000',   None) not in (None, 0) else dc.percent_txt_5000
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_5000', None) if getattr(dc, 'max_discount_bargain_percent_5000', None) not in (None, 0) else dc.percent_torg_txt_5000
        zna_izp_kf      = estimation_settings.izp_5000
        zna_izp_type    = estimation_settings.izp_5000_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_5000', None) if getattr(dc, 'correction_test_1c_5000', None) not in (None, 0) else dc.ratio_1с_test_price_5000
        percent_sale    = getattr(dc, 'correction_test_5000',    None) if getattr(dc, 'correction_test_5000',    None) not in (None, 0) else dc.ratio_avtohub_test_price_5000
        percent_sale_rdo= getattr(dc, 'correction_rdo_5000',     None) if getattr(dc, 'correction_rdo_5000',     None) not in (None, 0) else dc.ratio_avtohub_rdo_5000
        percent_sale_kor= getattr(dc, 'correction_kor_5000',     None) if getattr(dc, 'correction_kor_5000',     None) not in (None, 0) else dc.ratio_avtohub_kor_5000
        kf_auction      = estimation_settings.auction_kf_5000
        windshield      = estimation_settings.windshield_5000
        windshield_heat = estimation_settings.windshield_heat_5000
        light_pered     = estimation_settings.light_pered_5000
        light_pered_kf  = estimation_settings.light_pered_kf_5000
        light_zad       = estimation_settings.light_zad_5000
        light_zad_kf    = estimation_settings.light_zad_kf_5000
        battery         = estimation_settings.battery_5000
        engine_danger_kf            = estimation_settings.engine_danger_kf_5000            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_5000
        engine_warning_kf           = estimation_settings.engine_warning_kf_5000 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_5000 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_5000   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_5000   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_5000    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_5000    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_5000 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_5000 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_5000  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_5000  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_5000  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_5000  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_5000   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_5000   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_5000  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_5000  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_5000   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_5000   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_5000 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_5000 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_5000     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_5000   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_5000   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_5000       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_5000        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_5000       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_5000     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_5000     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_5000      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_5000
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_5000
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_5000
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_5000
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_5000
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_5000
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_5000
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_5000
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_5000
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_5000
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_5000
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_5000
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_5000
        brake_danger_kf              = estimation_settings.brake_danger_kf_5000
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_5000
        brake_warning_kf             = estimation_settings.brake_warning_kf_5000
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_5000
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_5000
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_5000
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_5000
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_5000
        drive_danger_kf              = estimation_settings.drive_danger_kf_5000
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_5000
        drive_warning_kf             = estimation_settings.drive_warning_kf_5000
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_5000
        to_1                         = estimation_settings.to_1_5000
        to_2                         = estimation_settings.to_2_5000
        to_3                         = estimation_settings.to_3_5000
    else:
        zg              = '5 000+'
        matrix_auction  = settings_matrix.charge_bcp_5001
        fin_zg          = estimation_settings.percent_financity_5001
        day_sale_zg     = estimation_settings.days_stok_financity_5001
        kf              = getattr(dc, 'correction_txt_5001', None) if getattr(dc, 'correction_txt_5001', None) not in (None, 0) else dc.ratio_avtohub_txt_5001
        percent_ss      = getattr(dc, 'markup_txt_5001',   None) if getattr(dc, 'markup_txt_5001',   None) not in (None, 0) else dc.percent_txt_5001
        percent_torg    = getattr(dc, 'max_discount_bargain_percent_5001', None) if getattr(dc, 'max_discount_bargain_percent_5001', None) not in (None, 0) else dc.percent_torg_txt_5001
        zna_izp_kf      = estimation_settings.izp_5001
        zna_izp_type    = estimation_settings.izp_5001_v
        percent_sale_1C = getattr(dc, 'correction_test_1c_5001', None) if getattr(dc, 'correction_test_1c_5001', None) not in (None, 0) else dc.ratio_1с_test_price_5001
        percent_sale    = getattr(dc, 'correction_test_5001',    None) if getattr(dc, 'correction_test_5001',    None) not in (None, 0) else dc.ratio_avtohub_test_price_5001
        percent_sale_rdo= getattr(dc, 'correction_rdo_5001',     None) if getattr(dc, 'correction_rdo_5001',     None) not in (None, 0) else dc.ratio_avtohub_rdo_5001
        percent_sale_kor= getattr(dc, 'correction_kor_5001',     None) if getattr(dc, 'correction_kor_5001',     None) not in (None, 0) else dc.ratio_avtohub_kor_5001
        kf_auction      = estimation_settings.auction_kf_5001
        windshield      = estimation_settings.windshield_5001
        windshield_heat = estimation_settings.windshield_heat_5001
        light_pered     = estimation_settings.light_pered_5001
        light_pered_kf  = estimation_settings.light_pered_kf_5001
        light_zad       = estimation_settings.light_zad_5001
        light_zad_kf    = estimation_settings.light_zad_kf_5001
        battery         = estimation_settings.battery_5001
        engine_danger_kf            = estimation_settings.engine_danger_kf_5001            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_5001
        engine_warning_kf           = estimation_settings.engine_warning_kf_5001 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_5001 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_5001   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_5001   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_5001    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_5001    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_5001 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_5001 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_5001  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_5001  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_5001  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_5001  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_5001   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_5001   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_5001  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_5001  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_5001   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_5001   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_5001 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_5001 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_5001     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_5001   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_5001   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_5001       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_5001        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_5001       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_5001     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_5001     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_5001      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_5001
        conditioner_danger_kf        = estimation_settings.conditioner_danger_kf_5001
        conditioner_danger_amount_min = estimation_settings.conditioner_danger_amount_min_5001
        conditioner_warning_kf       = estimation_settings.conditioner_warning_kf_5001
        conditioner_warning_amount_min = estimation_settings.conditioner_warning_amount_min_5001
        turbo_danger_kf              = estimation_settings.turbo_danger_kf_5001
        turbo_danger_amount_min      = estimation_settings.turbo_danger_amount_min_5001
        turbo_warning_kf             = estimation_settings.turbo_warning_kf_5001
        turbo_warning_amount_min     = estimation_settings.turbo_warning_amount_min_5001
        wheel_danger_kf              = estimation_settings.wheel_danger_kf_5001
        wheel_danger_amount_min      = estimation_settings.wheel_danger_amount_min_5001
        wheel_warning_kf             = estimation_settings.wheel_warning_kf_5001
        wheel_warning_amount_min     = estimation_settings.wheel_warning_amount_min_5001
        brake_danger_kf              = estimation_settings.brake_danger_kf_5001
        brake_danger_amount_min      = estimation_settings.brake_danger_amount_min_5001
        brake_warning_kf             = estimation_settings.brake_warning_kf_5001
        brake_warning_amount_min     = estimation_settings.brake_warning_amount_min_5001
        subframe_danger_kf           = estimation_settings.subframe_danger_kf_5001
        subframe_danger_amount_min   = estimation_settings.subframe_danger_amount_min_5001
        subframe_warning_kf          = estimation_settings.subframe_warning_kf_5001
        subframe_warning_amount_min  = estimation_settings.subframe_warning_amount_min_5001
        drive_danger_kf              = estimation_settings.drive_danger_kf_5001
        drive_danger_amount_min      = estimation_settings.drive_danger_amount_min_5001
        drive_warning_kf             = estimation_settings.drive_warning_kf_5001
        drive_warning_amount_min     = estimation_settings.drive_warning_amount_min_5001
        to_1                         = estimation_settings.to_1_5001
        to_2                         = estimation_settings.to_2_5001
        to_3                         = estimation_settings.to_3_5001

    if percent_torg < 0:
        percent_torg = percent_torg * -1

    if percent_ss < 0:
        percent_ss = percent_ss * -1
                                            
    price = zna 
    # повышенный износ / такси
    if estimation.iznos and estimation.taxi:
        price_new  = price - (price * 40 / 100)
        diff       = price - price_new
        price = price_new
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована c учетом повышенного износа и использования в такси",  
            'name'      : "износ"
        }
        list_info_price.append(inf_price)
        if estimation.auction_auto_no_user != True:
            auction = True
            auction_comment = auction_comment + "Повышенный износ и использование в такси. Коэфицент 0.6."
            auction_success = True
    elif estimation.iznos:
        price_new  = price - (price * 10 / 100)
        diff       = price - price_new
        price = price_new
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'  : "Цена скоректирована c учетом повышенного износа",  
            'name'      : "износ" 
        }
        iznos_price = diff
        list_info_price.append(inf_price)
    elif estimation.taxi:
        price_new  = price - (price * (100 - kf_auction) / 100)
        diff       = price - price_new
        price = price_new
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'  : "Цена скоректирована c учетом использования в такси",  
            'name'      : "износ" 
        }
        iznos_price = diff
        list_info_price.append(inf_price)

    #Считаем авто в продаже 
    price_sale_rdo = 0
    price_sale_kor = 0
    if type_calculation == 'kors':
        price_sale      = price *  percent_sale_1C / 100
        price_sale_rdo  = price * percent_sale_rdo / 100
        price_sale_kor  = price *  percent_sale_kor / 100
        
    if type_calculation == 'autohub':
        price_sale = price * percent_sale / 100
        price_sale_rdo  = price * percent_sale_rdo / 100
        price_sale_kor  = price *  percent_sale_kor / 100
        
    elif type_calculation == 'avito':
        price_sale = price * percent_sale / 100
        price_sale_rdo  = price * percent_sale_rdo/ 100
        price_sale_kor  = price *  percent_sale_kor / 100
        
    elif type_calculation == 'custom':
        price_sale = price *  percent_sale_1C / 100
        price_sale_rdo  = price * percent_sale_rdo / 100
        price_sale_kor  = price *  percent_sale_kor / 100
    
    #Считаем авто в токсичке
    price_old       = price
    price           = price - (price * (100 - kf) / 100) 
    diff            = (price_old * (100 - kf) / 100)
    inf_price = {
        'price'     : price,
        'dif'       : diff,
        'comment'   : "ЦНА * ИРЦ ТХТ / посчитана цена с учетом продажи в токсичном стоке",
        'name'      : "цена в токсичной продаже"
    }
    list_info_price.append(inf_price)
    
    #Cчитаем с защитой от убытка
    price_old       = price
    price           = price - (price * percent_ss / 100) 
    diff            = (price_old * percent_ss / 100)
    inf_price = {
        'price'     : price,
        'dif'       : diff,
        'comment'   : "Цена с учетом защиты от убытка CC " + str(percent_ss) + " %",
        'name'      : "защита от убытка"   
    }
    zachita_ot_ubitka = diff
    list_info_price.append(inf_price)
    
    # cчитаем с защитой от скидкой торг
    price_old       = price
    price           = price - (price * percent_torg / 100) 
    diff            = (price_old * percent_torg / 100)
    inf_price = {
        'price'     : price,
        'dif'       : diff,
        'comment'   : "Цена с учетом защиты скидки торг " + str(percent_torg) + " %",
        'name'      : "скидка торг"  
    }
    discount_torg    = diff
    list_info_price.append(inf_price)
    
    
    # продажи и статистика корсавто
    # пока убрали
    #if estimation.kors_sale_cost_price_avg > 0:
    #    price_new   = (price + estimation.kors_sale_cost_price_avg) / 2
    #    diff        = price - price_new
    #    if diff > 0:
    #        price = price_new
    #        inf_price = {
    #            'price'     : price,
    #            'dif'       : diff,
    #            'comment'   : "Цена скоректирована c учетом истории продаж аналогичных АМ КорсАвто",  
    #            'name'      : "история корсавто"  
    #        }
    #        list_info_price.append(inf_price)

    # расчеты ремонта
    autodex = 0
    if estimation.avtoteka_car_autodex > 0:
        price           = price - (estimation.avtoteka_car_autodex / 2)
        diff            = estimation.avtoteka_car_autodex / 2
        autodex         = diff
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована на основании суммы ремонтов / 2",  
            'name'      : "расчеты ремонтов"   
        }
        list_info_price.append(inf_price)
    lob_add = False
    if estimation.page_vnesh != None:
        if estimation.page_vnesh.windshield_error_int == 1:
                if estimation.page_vnesh.windshield_heat_int == 1:
                    price_diff = windshield_heat
                    info_diff   = "Лобовое стекло c подогревом"
                else:
                    price_diff = windshield
                    info_diff   = "Лобовое стекло"

                work        = info_diff.capitalize()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum 
                lob_add = True 

    if estimation.page_salon != None:        
        # Химчистка +
        if estimation.page_salon.cleaning_int == 1:
            work = RegPodgotovkaWork.objects.get(pk = 117) 
            diff = work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : diff
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff
        elif estimation.page_salon.cleaning_int == 2:
            work = RegPodgotovkaWork.objects.get(pk = 116) 
            diff = work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : diff
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff
        elif estimation.page_salon.cleaning_int == 3:
            work = RegPodgotovkaWork.objects.get(pk = 115) 
            diff = work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : diff
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff
            
        #Рычаг КПП +
        if estimation.page_salon.damage_kpp_int == 1:
            diff_sum = 0
            work = RegPodgotovkaWork.objects.get(pk = 66) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            work = RegPodgotovkaWork.objects.get(pk = 67) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff_sum

        #Руль +
        if estimation.page_salon.damage_wheel_int == 2:
            diff_sum = 0
            work = RegPodgotovkaWork.objects.get(pk = 96) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            work = RegPodgotovkaWork.objects.get(pk = 99) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff_sum
        #Руль +
        if estimation.page_salon.damage_wheel_int == 1:
            diff_sum = 0
            work = RegPodgotovkaWork.objects.get(pk = 96) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            work = RegPodgotovkaWork.objects.get(pk = 133) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff_sum

        if estimation.page_salon.damage_pedal_int == 1:
            price           = price - estimation_settings.damage_pedal_int
            diff            = estimation_settings.damage_pedal_int
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'   : "Цена скоректирована повреждений / затертости педалей",  
                'name'      : "салон - педали"  
            }
            list_info_price.append(inf_price)
            amount_podgotovka = amount_podgotovka + diff

        if estimation.page_salon.damage_door_int == 1:
            price           = price - estimation_settings.damage_door_int
            diff            = estimation_settings.damage_door_int
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'   : "Цена скоректирована повреждений / затертости дверей",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)
            amount_podgotovka = amount_podgotovka + diff
        
        if estimation.page_salon.damage_seat_int == 1:
            price           = price - estimation_settings.damage_seat_int
            diff            = estimation_settings.damage_seat_int
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована повреждений / затертости сидений",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price) 
            amount_podgotovka = amount_podgotovka + diff 

        if estimation.page_salon.hand_brake == 0:
            price           = price - estimation_settings.hand_brake
            diff            = estimation_settings.hand_brake
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего ручного тормоза",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)  

        if estimation.page_salon.conductor == 0:
            price           = price - estimation_settings.conductor
            diff            = estimation_settings.conductor
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего кондиционера",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price) 
        
        if estimation.page_salon.wiper == 0:
            price           = price - estimation_settings.wiper
            diff            = estimation_settings.wiper
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего стеклоочистителей",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)

        if estimation.page_salon.signal == 0:
            price           = price - estimation_settings.signal
            diff            = estimation_settings.signal
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего сигнала",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)

        if estimation.page_salon.power_windows == 0:
            price           = price - estimation_settings.power_windows
            diff            = estimation_settings.power_windows
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающющих стеклоподъемников",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)   

        if estimation.page_salon.seat_belt == 0:
            price           = price - estimation_settings.seat_belt
            diff            = estimation_settings.seat_belt
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающющих ремней безопастности",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)      


    # двигатель
    if estimation.page_test_drive != None and estimation.page_test_drive.engine == 0:
        
        info_diff = ''
        price_diff = 0
        if modification.typeEngine.id == 1:
            price_diff  = (price * engine_danger_kf / 100)
            info_diff   = 'Бензиновый двигатель ремонт'

            if price_diff < engine_danger_amount_min:
                price_diff  = engine_danger_amount_min
                info_diff   = 'Бензиновый двигатель ремонт'
        else:
            price_diff  = (price * engine_dt_danger_kf / 100)
            info_diff   = 'Дизельный двигатель ремонт'

            if price_diff < engine_dt_danger_amount_min:
                price_diff  = engine_dt_danger_amount_min
                info_diff   = 'Дизельный двигатель ремонт'
        dop = {
            'name'      : info_diff,
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.engine == 2:
        
        info_diff = ''
        price_diff = 0
        
        if modification.typeEngine.id == 1:  
            price_diff = (price * engine_warning_kf / 100)
            info_diff   = 'Бензиновый двигатель устранение замечаний'
            
            if price_diff < engine_warning_amount_min:
                price_diff = engine_warning_amount_min
                info_diff   = 'Бензиновый двигатель устранение замечаний'
        else:
        
            price_diff = (price * engine_dt_warning_kf / 100)
            info_diff   = 'Дизельный двигатель устранение замечаний'

            if price_diff < engine_dt_warning_amount_min:
                price_diff = engine_dt_warning_amount_min
                info_diff   = 'Дизельный двигатель устранение замечаний'

        dop = {
            'name'      : info_diff,
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff

    # кпп
    if estimation.page_test_drive != None and estimation.page_test_drive.gear == 0:
        
        info_diff = ''
        price_diff = 0
        
        if modification.typeGear.id == 1:
            price_diff = (price * gear_amt_danger_kf / 100)
            info_diff   = 'Робот устранение замечаний'

            if price_diff < gear_amt_danger_amount_min:
                price_diff = gear_amt_danger_amount_min
                info_diff   = 'Робот устранение замечаний'

        elif modification.typeGear.id == 2:
            price_diff = (price * gear_mt_danger_kf / 100)
            info_diff   = 'Механика устранение замечаний'

            if price_diff < gear_mt_danger_amount_min:
                price_diff = gear_mt_danger_amount_min
                info_diff   = 'Механика устранение замечаний'

        elif modification.typeGear.id == 3:
            price_diff = (price * gear_at_danger_kf / 100)
            info_diff   = 'Автомат устранение замечаний'
            if price_diff < gear_at_danger_amount_min:
                price_diff = gear_at_danger_amount_min
                info_diff   = 'Автомат устранение замечаний'

        elif modification.typeGear.id == 4:
            price_diff = (price * gear_cvt_danger_kf / 100)
            info_diff   = 'Вариатор устранение замечаний'

            if price_diff < gear_cvt_danger_amount_min:
                price_diff = gear_cvt_danger_amount_min
                info_diff   = 'Вариатор устранение замечаний'

        dop = {
            'name'      : info_diff,
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.gear == 2:
        
        price_diff = 0
        info_diff = ''

        if modification.typeGear.id == 1:
            
            price_diff = (price * gear_amt_warning_kf / 100)
            info_diff   = 'Робот ремонт'

            if price_diff < gear_amt_warning_amount_min:
                price_diff = gear_amt_warning_amount_min
                info_diff   = 'Робот ремонт'

        elif modification.typeGear.id == 2:
            
            price_diff = (price * gear_mt_warning_kf / 100)
            info_diff   = 'Механика ремонт'

            if price_diff < gear_mt_warning_amount_min:
                price_diff = gear_mt_warning_amount_min
                info_diff   = 'Механика ремонт'

        elif modification.typeGear.id == 3:
            
            price_diff = (price * gear_at_warning_kf / 100)
            info_diff   = 'Автомат ремонт'

            if price_diff < gear_at_warning_amount_min:
                price_diff = gear_at_warning_amount_min
                info_diff   = 'Автомат ремонт'
        
        elif modification.typeGear.id == 4:
            
            price_diff = (price * gear_cvt_warning_kf / 100)
            info_diff   = 'Вариатор ремонт'

            if price_diff < gear_cvt_warning_amount_min:
                price_diff = gear_cvt_warning_amount_min
                info_diff   = 'Вариатор ремонт'
        
        dop = {
            'name'      : info_diff,
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff
    
    # подвеска
    if estimation.page_test_drive != None and estimation.page_test_drive.suspension == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * suspension_danger_kf / 100)
        info_diff   = 'Сумма ремонта в процентах ' +  str(suspension_danger_kf)

        if price_diff < suspension_danger_amount_min:
            price_diff = suspension_danger_amount_min
            info_diff   = 'Сумма ремонта минимальное значение ' +  str(suspension_danger_amount_min)

        dop = {
            'name'      : 'Подвеска ремонт неисправности',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)  
        
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.suspension == 2:
        
        info_diff = ''
        price_diff = 0
        
        price_diff = (price * suspension_warning_kf / 100)
        
        if price_diff < suspension_warning_amount_min:
            price_diff = suspension_warning_amount_min
            
        dop = {
            'name'      : 'Подвеска устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # система выпуска ог
    if estimation.page_test_drive != None and estimation.page_test_drive.system_og == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * system_og_danger_kf / 100)
        
        if price_diff < system_og_danger_amount_min:
            price_diff = system_og_danger_amount_min
            
        dop = {
            'name'      : 'Система выпуска ОГ ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.system_og == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * system_og_warning_kf / 100)
        
        if price_diff < system_og_warning_amount_min:
            price_diff = system_og_warning_amount_min
           
        dop = {
            'name'      : 'Система выпуска ОГ устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # кондиционер
    if estimation.page_test_drive != None and estimation.page_test_drive.conditioner == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * conditioner_danger_kf / 100)
        
        if price_diff < conditioner_danger_amount_min:
            price_diff = conditioner_danger_amount_min
            
        dop = {
            'name'      : 'Кондиционер ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.conditioner == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * conditioner_warning_kf / 100)
       
        if price_diff < conditioner_warning_amount_min:
            price_diff = conditioner_warning_amount_min
            
        dop = {
            'name'      : 'Кондиционер устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # турбокомпрессор
    if estimation.page_test_drive != None and estimation.page_test_drive.turbo == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * turbo_danger_kf / 100)
        
        if price_diff < turbo_danger_amount_min:
            price_diff = turbo_danger_amount_min
            
        dop = {
            'name'      : 'Турбокомпрессор ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.turbo == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * turbo_warning_kf / 100)
       
        if price_diff < turbo_warning_amount_min:
            price_diff = turbo_warning_amount_min
            
        dop = {
            'name'      : 'Турбокомпрессор устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # рулевое управление
    if estimation.page_test_drive != None and estimation.page_test_drive.wheel == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * wheel_danger_kf / 100)
       
        if price_diff < wheel_danger_amount_min:
            price_diff = wheel_danger_amount_min
           
        dop = {
            'name'      : 'Рулевое управление ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.wheel == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * wheel_warning_kf / 100)
       
        if price_diff < wheel_warning_amount_min:
            price_diff = wheel_warning_amount_min
           
        dop = {
            'name'      : 'Рулевое управление устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # привод
    if estimation.page_test_drive != None and estimation.page_test_drive.drive == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * drive_danger_kf / 100)
        
        if price_diff < drive_danger_amount_min:
            price_diff = drive_danger_amount_min
           
        dop = {
            'name'      : 'Привод ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.drive == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * drive_warning_kf / 100)
        
        if price_diff < drive_warning_amount_min:
            price_diff = drive_warning_amount_min
            
        dop = {
            'name'      : 'Привод устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # тормозная система
    if estimation.page_test_drive != None and estimation.page_test_drive.brake == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * brake_danger_kf / 100)
       
        if price_diff < brake_danger_amount_min:
            price_diff = brake_danger_amount_min
           
        dop = {
            'name'      : 'Тормозная система ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.brake == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * brake_warning_kf / 100)
       
        if price_diff < brake_warning_amount_min:
            price_diff = brake_warning_amount_min
           
        dop = {
            'name'      : 'Тормозная система устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # подрамник
    if estimation.page_test_drive != None and estimation.page_test_drive.subframe == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * subframe_danger_kf / 100)
       
        if price_diff < subframe_danger_amount_min:
            price_diff = subframe_danger_amount_min
           
        dop = {
            'name'      : 'Подрамник ремонт',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.subframe == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * subframe_warning_kf / 100)
       
        if price_diff < subframe_warning_amount_min:
            price_diff = subframe_warning_amount_min
           
        dop = {
            'name'      : 'Подрамник устранение замечаний',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # Амортизатор 
    if estimation.page_test_drive != None and estimation.page_test_drive.hood_trunk_shock_absorber != None and estimation.page_test_drive.hood_trunk_shock_absorber == 0:
        price_diff = 10000 
        dop = {
            'name'      : 'Амортизатор капата/багажника',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff
    # Стапель 
    if estimation.page_test_drive != None and estimation.page_test_drive.stapele_hours != None and estimation.page_test_drive.stapele_hours > 0:
        price_diff = estimation.page_test_drive.stapele_hours * estimation.page_test_drive.stapele_cost 
        dop = {
            'name'      : 'Стапель',
            'quantity'  : estimation.page_test_drive.stapele_hours,
            'amount_pod': price_diff, 
            'amount'    : price_diff
        }
        list_work_mcu.append(dop) 
        amount_mcu = amount_mcu + price_diff
    # ТО
    if estimation.page_test_drive != None and estimation.page_test_drive.to == 1:
        price_diff = to_1 
        dop = {
            'name'      : 'ТО Minimal (масло, масляный фильтр)',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff
    elif estimation.page_test_drive != None and estimation.page_test_drive.to == 2:
        price_diff = to_2 
        dop = {
            'name'      : 'ТО Middle (масло, масляный фильтр, воздушный фильтр, салонный фильтр, свечи зажигания)',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff
    elif estimation.page_test_drive != None and estimation.page_test_drive.to == 3:
        price_diff = to_3 
        dop = {
            'name'      : 'ТО Full (масло, масляный фильтр, воздушный фильтр, салонный фильтр, свечи зажигания, тормозные колодки)',
            'quantity'  : 1,
            'amount_pod': 1, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # Безопасность - расчет для каждого пункта, если выбрано "не исправны" или "есть замечания"
    # Используем только минимальную сумму опасности для обоих случаев
    if estimation.page_test_drive != None and (estimation.page_test_drive.airbag == 0 or estimation.page_test_drive.airbag == 2):
        # Получаем значения для текущей ценовой группы
        airbag_driver_danger_amount_min = getattr(estimation_settings, f'airbag_driver_danger_amount_min_{zg}', 0)
        airbag_passenger_danger_amount_min = getattr(estimation_settings, f'airbag_passenger_danger_amount_min_{zg}', 0)
        airbag_side_danger_amount_min = getattr(estimation_settings, f'airbag_side_danger_amount_min_{zg}', 0)
        airbag_knee_danger_amount_min = getattr(estimation_settings, f'airbag_knee_danger_amount_min_{zg}', 0)
        seat_belt_restore_danger_amount_min = getattr(estimation_settings, f'seat_belt_restore_danger_amount_min_{zg}', 0)
        srs_block_danger_amount_min = getattr(estimation_settings, f'srs_block_danger_amount_min_{zg}', 0)
        
        # Подушка водителя
        if estimation.page_test_drive.airbag_driver_issue and airbag_driver_danger_amount_min > 0:
            dop = {
                'name': 'Подушка водителя',
                'quantity': 1,
                'amount_pod': 1,
                'amount': airbag_driver_danger_amount_min
            }
            list_work_podgotovka.append(dop)
            amount_podgotovka = amount_podgotovka + airbag_driver_danger_amount_min
        
        # Подушка пассажира + перешив торпеды
        if estimation.page_test_drive.airbag_passenger_issue and airbag_passenger_danger_amount_min > 0:
            dop = {
                'name': 'Подушка пассажира + перешив торпеды',
                'quantity': 1,
                'amount_pod': 1,
                'amount': airbag_passenger_danger_amount_min
            }
            list_work_podgotovka.append(dop)
            amount_podgotovka = amount_podgotovka + airbag_passenger_danger_amount_min
        
        # Боковые подушки
        if estimation.page_test_drive.airbag_side_issue and airbag_side_danger_amount_min > 0:
            dop = {
                'name': 'Боковые подушки',
                'quantity': 1,
                'amount_pod': 1,
                'amount': airbag_side_danger_amount_min
            }
            list_work_podgotovka.append(dop)
            amount_podgotovka = amount_podgotovka + airbag_side_danger_amount_min
        
        # Подушка коленная
        if estimation.page_test_drive.airbag_knee_issue and airbag_knee_danger_amount_min > 0:
            dop = {
                'name': 'Подушка коленная',
                'quantity': 1,
                'amount_pod': 1,
                'amount': airbag_knee_danger_amount_min
            }
            list_work_podgotovka.append(dop)
            amount_podgotovka = amount_podgotovka + airbag_knee_danger_amount_min
        
        # Восстановление ремней безопасности
        if estimation.page_test_drive.seat_belt_restore_issue and seat_belt_restore_danger_amount_min > 0:
            dop = {
                'name': 'Восстановление ремней безопасности',
                'quantity': 1,
                'amount_pod': 1,
                'amount': seat_belt_restore_danger_amount_min
            }
            list_work_podgotovka.append(dop)
            amount_podgotovka = amount_podgotovka + seat_belt_restore_danger_amount_min
        
        # Блок SRS
        if estimation.page_test_drive.srs_block_issue and srs_block_danger_amount_min > 0:
            dop = {
                'name': 'Блок SRS',
                'quantity': 1,
                'amount_pod': 1,
                'amount': srs_block_danger_amount_min
            }
            list_work_podgotovka.append(dop)
            amount_podgotovka = amount_podgotovka + srs_block_danger_amount_min

    kors_price_reception = 0
    if estimation.kors_count_sale > 0: 
        kors_price_reception = round(((estimation.kors_sale_cost_price_min + estimation.kors_sale_cost_price_max)  / 2) - estimation.kors_outlay_avg, -3)
    
    hub_sale_price_avg = 0
    if estimation.hub_sale_total > 0:
        hub_sale_price_avg = (estimation.hub_sale_price_min + estimation.hub_sale_price_max)  / 2 
    
    kors_hub_correction_sale = 0
    kors_hub_correction_store = 0
    count_hub = (estimation.hub_sale_total + estimation.hub_total) / 2

    hub_sale_price_avg = 0
    if estimation.hub_sale_total > 0:
        hub_sale_price_avg  = (estimation.hub_sale_price_min + estimation.hub_sale_price_max)  / 2 
    
    hub_price_avg = 0
    if estimation.hub_total > 0:
        hub_price_avg       = (estimation.hub_price_min + estimation.hub_price_max)  / 2

    if count_hub > 0:
        kors_hub_correction = round((kors_hub_correction_sale + kors_hub_correction_store) / 2 * 0.82, 0)
    
    ###Проверяем пробег
    run_ok  = True
    run_sum = 0
    if estimation.avtoteka_data != None and len(estimation.avtoteka_data) > 100:
        data_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
        eventsOthersHistory = data_autoteka.get('eventsOthersHistory')
        run         = 0
        run_other   = 0
        
        for event in eventsOthersHistory:
            if event['source'] != 'Audatex':
                if event['mileage'] > 0:
                    run = event['mileage']
                    if run_other > run:
                        if run_other - run > 1000:
                            run_ok = False
                            run_sum = run_sum + (run_other - run)
                            if estimation.auction_auto_no_user != True:
                                auction = True
                            
                    run_other = run
        if run_sum > 0:
            real_runs = run_estimation + run_sum 
            auction_comment = auction_comment + 'Пробег автомобиля вызывает сомнения. (примерно на '  + str(run_sum) + ' км.). Реальный пробег примерно: ' + '{0:,}'.format(real_runs).replace(',', ' ')  + ' км.'

    ###Проверяем требуется ли замена аккумулятора
    if battery > 0:
        try:
            if estimation.start_estimation.year - estimation.year > 4:
                diff_sum    = 0
                work        = 'Замена аккумулятора'
                diff_sum    = battery
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
        except:
            s = 1

    salon_info = salon_estimation(estimation)
    for info in salon_info['array']:
        if info['name'] == 'ручка кпп':
            if info['all'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 66)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 67)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum
        elif info['name'] == 'подлокотник':
            if info['all'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 57)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 58)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
        elif info['name'] == 'рулевое колесо':
            if info['all'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 96)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
            if info['perecras'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 99)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
            if info['pereshiv'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 133)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
        elif info['name'].find('сиденье') > 0 or info['name'].find('сидение') > 0:
            if info['pereshiv'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 134)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum
            elif info['vost'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 135)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum
            elif info['dirka'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 130)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo * info['dirka'],
                    'amount_pod': work.price_podrad * info['dirka'], 
                    'amount'    : work.price_kors * info['dirka']
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum
            elif info['perecras'] > 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 130)
                if work.price_kors == 0:
                    price_kors = work.price_podrad
                else:
                    price_kors = work.price_kors               
                diff_sum    = price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum   


    body_info = body_estimation(estimation)            
    elem_rzav = 0
    elem_rzav_data = ''
    for info in body_info['array']:
        if (info['name'] == 'фара правая' or info['name'] == 'фара левая') and info['all'] > 0:
            if info['poly'] > 0 and info['replace_add'] == 0 and info['tr'] == 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 77)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
            elif info['replace_add'] > 0:
                price_diff = (price * light_pered_kf / 100)
                info_diff   = info['name'].capitalize() + ' / замена'

                if price_diff < light_pered:
                    price_diff = light_pered
                    info_diff   = info['name']
                work        = info_diff.capitalize()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum * 2, 
                    'amount'    : diff_sum * 2
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum
            else:
                price_diff = (price * light_pered_kf / 100)
                info_diff   = info['name'].capitalize()

                if price_diff < light_pered:
                    price_diff = light_pered
                    info_diff   = info['name']
                work        = info_diff.capitalize()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum
        elif (info['name'] == 'фонарь правый' or info['name'] == 'фонарь левый' ) and info['all'] > 0:
            if info['poly'] > 0 and info['replace_add'] == 0 and info['tr'] == 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 77)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
            elif info['replace_add'] > 0:
                price_diff = (price * light_zad_kf / 100)
                info_diff   = info['name'] + ' / замена'

                if price_diff < light_zad:
                    price_diff = light_zad
                    info_diff   = info['name']
                work        = info_diff.capitalize()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum 
            else:
                price_diff = (price * light_zad_kf / 100)
                info_diff   = info['name']

                if price_diff < light_zad:
                    price_diff = light_zad
                    info_diff   = info['name']
                work        = info_diff.capitalize()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum              
        elif (info['name'] == 'лобовое стекло') and info['all'] > 0:
            if lob_add == False:
                if estimation.page_vnesh.windshield_heat_int == 1:
                    price_diff = windshield_heat
                    info_diff   = info['name'] + " c подогревом"
                else:
                    price_diff = windshield
                    info_diff   = info['name']

                work        = info_diff.capitalize()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum    
        else:
            if info['rzav_strong'] > 0:
                elem_rzav = elem_rzav + 1
                elem_rzav_data    = elem_rzav_data + info['name'] + "; "
            
            if info['replace_add'] > 0:
                if info['name'] == 'передний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 14)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum 
                elif info['name'] ==  'крыло заднее левое' or info['name'] ==  'крыло заднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 43) 
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'задний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 9)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'порог левый' or info['name'] ==  'порог правый':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 59)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крыло переднее левое' or info['name'] ==  'крыло переднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 46)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крыша':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 51)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крышка багажника':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 4)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'дверь задняя левая' or info['name'] ==  'дверь задняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 24)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'дверь передняя левая' or info['name'] ==  'дверь передняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 28)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'капот':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 38)
                    diff_sum    = work.price_podrad * 2
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name  + ' / замена',
                        'quantity'  : work.normo * 2,
                        'amount_pod': work.price_podrad * 2, 
                        'amount'    : work.price_kors * 2
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
            if (info['carap_strong'] > 0 or info['rzav'] > 0 or info['tr'] > 0 or info['rzav_strong'] > 0) and info['replace_add'] == 0:
                if info['name'] == 'передний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 14)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum 
                elif info['name'] ==  'крыло заднее левое' or info['name'] ==  'крыло заднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 43)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'задний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 9)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'порог левый' or info['name'] ==  'порог правый':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 59)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крыло переднее левое' or info['name'] ==  'крыло переднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 46)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крыша':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 51)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крышка багажника':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 4)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'дверь задняя левая' or info['name'] ==  'дверь задняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 24)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'дверь передняя левая' or info['name'] ==  'дверь передняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 28)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'капот':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 38)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
            elif info['carap'] > 0:
                if info['name'] == 'передний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 16)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum 
                elif info['name'] ==  'крыло заднее левое' or info['name'] ==  'крыло заднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 45)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'задний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 11)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'порог левый' or info['name'] ==  'порог правый':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 61)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'крыло переднее левое' or info['name'] ==  'крыло переднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 47)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'крыша':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 52)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'крышка багажника':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 5)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'дверь задняя левая' or info['name'] ==  'дверь задняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 25)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'дверь передняя левая' or info['name'] ==  'дверь передняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 29)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'капот':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 39)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
            elif (info['vmyat_strong'] > 0 or info['vmyat'] > 0):
                if info['vmyat_strong'] > 0:
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 131)
                    diff_sum    = work.price_kors * info['vmyat_strong']
                    dop = {
                        'name'      : info['name'] + ' / ' + work.name_group + ' / ' +  work.name + " сильная " +  ' (' + str(info['vmyat_strong']) +')',
                        'quantity'  : work.normo * info['vmyat_strong'],
                        'amount_pod': work.price_podrad * info['vmyat_strong'], 
                        'amount'    : work.price_kors * info['vmyat_strong']
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                if info['vmyat'] > 0:
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 131)
                    diff_sum    = work.price_kors * info['vmyat']
                    dop = {
                        'name'      : info['name'] + ' / ' + work.name_group + ' / ' +  work.name +  ' (' + str(info['vmyat']) +')',
                        'quantity'  : work.normo * info['vmyat'],
                        'amount_pod': work.price_podrad * info['vmyat'], 
                        'amount'    : work.price_kors * info['vmyat']
                    } 
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum                 
 
            if info['skol'] > 0 and info['vmyat_strong'] == 0 and info['carap_strong'] == 0 and info['rzav'] == 0 and info['rzav_strong'] == 0:
            
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 80)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 

    if elem_rzav > 3 and estimation.auction_auto_no_user != True:
        auction = True
        auction_comment = auction_comment + " " + "3 более элемента с сквозной корозией (" +  elem_rzav_data +  "). "

    if amount_ss > 0:
        price           = price - amount_ss
        diff            = amount_ss
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована с учетом затрат на слесарный ремонт " + '{:0,.2f}'.format(diff).replace(',', ' ') + ' ₽',  
            'name'      : "слесарный"
        }
        list_info_price.append(inf_price)     

    if amount_podgotovka > 0:
        price           = price - amount_podgotovka
        diff            = amount_podgotovka
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована с учетом затрат на подготовку " + '{:0,.2f}'.format(diff).replace(',', ' ') + ' ₽',  
            'name'      : "подготовка"
        }
        list_info_price.append(inf_price)   

    if amount_mcu > 0:
        price           = price - amount_mcu
        diff            = amount_mcu
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована с учетом затрат на кузовной ремонт " + '{:0,.2f}'.format(diff).replace(',', ' ') + ' ₽',  
            'name'      : "кузовной"
        }
        list_info_price.append(inf_price)
    
    if estimation.auction_auto_no_user != True:
        if auction_success == False and auction:
            price_new  = price - (price * (100 - kf_auction) / 100)
            diff       = price - price_new
            price = price_new
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована c учетом продажи АМ на АУКЦИОНЕ " + str(kf_auction) + "%"  
            }
            list_info_price.append(inf_price)

    #Финансирование
    if zna_type != '1C':
        #Проверяем корректировку ЦНА
        if zna_izp_type > -1:            
            #if zna_izp_type == 2 or zna_izp_type == 1 and estimation.kors_sale_cost_price_avg == 0:
            zna_type_name = ''
            if zna_izp_type == 1:
                zna_type_name = '""'
            else:
                zna_type_name = '""'
            price_old       = price
            day = day_sale_all
            if day_sale_zg > 0:
                day = day_sale_zg

            fin = fin_all
            if fin_zg > 0:
                fin = fin_zg

            if estimation.hub_days_in_stok_avg > 0:
                day = estimation.hub_sale_days_in_stok_avg
                #day = estimation.hub_days_in_stok_avg # Переключил по согласованию с Серебрянниковым, для расчета дней не текущего рынка а истории продаж
            
            finance = round(price * ((fin / 365) / 100) * day, 2) 
            
            price           = price - finance
            diff            = finance
            finance_price   = finance

            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'   : "Финансирование " + str(fin)  + "% для продажи авто за " + str(round(day)) + " дней",
                'name'      : "финансирование"
            }
            '''
            price           = price - (price * zna_izp_kf / 100) 
            diff            = (price_old *  zna_izp_kf / 100)
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "ЦНА скоректирована на " + str(zna_izp_kf)  + "% (вариант использования: " + zna_type_name + ")"
            }
            '''
            list_info_price.append(inf_price)
    if estimation.auction_auto_no_user == True:
        auction = False
        auction_comment = ''

    #ИТОГ
    estimation_price    = round(price, -2)
    amount_sum          = amount_mcu + amount_podgotovka + amount_ss
    profit              = round(price_sale - price - amount_sum, -2)
    estimation_price_do_kd  = estimation_price + amount_ss
    difference_sum          = 0     
    
    if zna_type == "custom":
        if estimation.page_test_drive != None and estimation.page_test_drive.end_estimation != None:
            estimation_price = estimation_price_do_kd - amount_ss 
            if estimation_price < 1000:
                estimation_price = 1000
        else:
            estimation_price = 0

        if estimation_price_do_kd < 1000:
            estimation_price_do_kd = 1000 
        
        difference_sum = 0
        if estimation.page_soglasovanie != None:
            if estimation.page_soglasovanie.price_after_kd > 0 and estimation.page_soglasovanie.price_after_kd > estimation_price:
                difference_sum = estimation.page_soglasovanie.price_after_kd - estimation_price 
        
        estimation_price = estimation_price + difference_sum
    
    if estimation.page_test_drive != None and estimation.page_test_drive.end_estimation != None:
        estimation_price = estimation_price_do_kd - amount_ss 
        if estimation_price < 1000:
            estimation_price = 1000
       
        if estimation_price_do_kd < 1000:
            estimation_price_do_kd = 1000 
        
        difference_sum = 0
        if estimation.page_soglasovanie != None:
            if estimation.page_soglasovanie.price_after_kd > 0 and estimation.page_soglasovanie.price_after_kd > estimation_price:
                difference_sum = estimation.page_soglasovanie.price_after_kd - estimation_price

    #cna_expenses = zna + difference_sum - amount_sum
    cna_expenses = zna - amount_sum - autodex
    
    if estimation_price < 1000:
        estimation_price = 1000
    
    if estimation.page_test_drive != None and estimation.page_test_drive.end_estimation != None:
        estimation_price = estimation_price_do_kd - amount_ss 
        if estimation_price < 1000:
            estimation_price = 1000

    if estimation_price_do_kd < 1000:
        estimation_price_do_kd = 1000 

    if cna_expenses < 0:
        cna_expenses = zna
    estimation_price_to_bcp = 0    
    
    

    difference_sum = 0
    if estimation.page_soglasovanie != None:
        if estimation.page_soglasovanie.price_after_kd > 0 and estimation.page_soglasovanie.price_after_kd > estimation_price:
            difference_sum = estimation.page_soglasovanie.price_after_kd - estimation_price 
    if difference_sum > 0:
        estimation_price_to_bcp = estimation_price + difference_sum
    else:
        estimation_price_to_bcp = estimation_price         
    
    matrix_auction = 0

    if auction:   
        if estimation_price_to_bcp < 200000:
            matrix_auction  = settings_matrix.charge_bcp_200
        elif estimation_price_to_bcp < 400000:
            matrix_auction  = settings_matrix.charge_bcp_400
        elif estimation_price_to_bcp < 700000:
            matrix_auction  = settings_matrix.charge_bcp_700
        elif estimation_price_to_bcp < 1200000:
            matrix_auction  = settings_matrix.charge_bcp_1200
        elif estimation_price_to_bcp < 2000000:
            matrix_auction  = settings_matrix.charge_bcp_2000
        elif estimation_price_to_bcp < 3000000:
            matrix_auction  = settings_matrix.charge_bcp_3000
        elif estimation_price_to_bcp < 5000000:
            matrix_auction  = settings_matrix.charge_bcp_5000
        else:
            matrix_auction  = settings_matrix.charge_bcp_5001        
        cna_expenses = estimation_price_to_bcp + matrix_auction + difference_sum
    else:
        cna_expenses = cna_expenses + difference_sum
    
    try:
        if type_calculation == 'custom':
            s = 1
            estimation.page_soglasovanie.amount_podgotovka  = amount_podgotovka
            estimation.page_soglasovanie.amount_ss          = amount_ss
            estimation.page_soglasovanie.amount_mcu         = amount_mcu
            estimation.page_soglasovanie.amount_recovery    = amount_podgotovka + amount_ss + amount_mcu
            estimation.page_soglasovanie.save()
        if type_calculation == 'kors':
            estimation.page_soglasovanie.price_auto_1       = estimation_price
            estimation.page_soglasovanie.price_auto_bcp_1   = cna_expenses
            estimation.page_soglasovanie.price_zna_1        = zna
            estimation.page_soglasovanie.save()
        elif type_calculation == 'autohub':
            estimation.page_soglasovanie.price_auto_2         = estimation_price
            estimation.page_soglasovanie.price_auto_bcp_2     = cna_expenses
            estimation.page_soglasovanie.price_zna_2          = zna
            estimation.page_soglasovanie.save()
        elif type_calculation == 'avito':
            estimation.page_soglasovanie.price_auto_3         = estimation_price
            estimation.page_soglasovanie.price_auto_bcp_3     = cna_expenses
            estimation.page_soglasovanie.price_zna_3          = zna
            estimation.page_soglasovanie.save()
    except:
        s= 1   

    price = {
        'kors_price_reception'          : kors_price_reception,
        'profit'                        : profit,
        'hub_sale_price_avg'            : hub_sale_price_avg,
        'hub_price_avg'                 : hub_price_avg,
        'zna'                           : zna,
        'zna_type'                      : zna_type,
        'estimation_price_do_kd'        : estimation_price_do_kd,
        'estimation_price'              : estimation_price,
        'zg'                            : zg,
        'kf'                            : kf,
        'kors_price_correction_sale'    : 0,
        'list_info_price'               : list_info_price,
        'array_body'                    : body_info,
        'amount_podgotovka'             : amount_podgotovka,
        'list_work_podgotovka'          : list_work_podgotovka,
        'list_work_service'             : list_work_service,
        'list_work_mcu'                 : list_work_mcu,
        'amount_sum'                    : amount_sum,
        'amount_ss'                     : amount_ss,
        'amount_mcu'                    : amount_mcu,
        'auction'                       : auction,
        'auction_comment'               : auction_comment,
        'sale'                          : price_sale,
        'price_sale'                    : price_sale,
        'price_sale_rdo'                : price_sale_rdo,
        'price_sale_kor'                : price_sale_kor,
        'cna_expenses'                  : cna_expenses,
        'zachita_ot_ubitka'             : zachita_ot_ubitka,
        'finance_price'                 : finance_price,
        'run_sum'                       : run_sum,
        'iznos_price'                   : iznos_price,
        'discount_torg'                 : discount_torg,
        'estimation_settings'           : estimation_settings
    }

    return price


def estimation_history_vin(vin, count = False):
    if vin != '':
        if count:
            return DocLO.objects.filter(vin__icontains = vin).count()
        else:
            return DocLO.objects.filter(vin__icontains = vin).order_by('-dataTime')
    return list()


def start_soglas(request, id):
    if 'status' in request.GET:
        status = int(request.GET['status'])
    rlk = DocRLK.objects.get(pk=id)
    #rlk.statusOcenka = RefStatusOcenka.objects.get(pk=status)
    if status == 2:
        rlk.staffECO1 = request.user.id
    return redirect('/eco/doc/?checkid=' + id)


def opens_info(estimation):
   return RegInteractivOcenkaHistoryOpens.objects.filter(estimation = estimation).order_by('-date_open') 


def point_in_polygon(point, polygon):
    num_vertices = len(polygon)
    x, y = point.x, point.y
    inside = False
 
    # Store the first point in the polygon and initialize the second point
    p1 = polygon[0]
 
    # Loop through each edge in the polygon
    for i in range(1, num_vertices + 1):
        # Get the next point in the polygon
        p2 = polygon[i % num_vertices]
 
        # Check if the point is above the minimum y coordinate of the edge
        if y > min(p1.y, p2.y):
            # Check if the point is below the maximum y coordinate of the edge
            if y <= max(p1.y, p2.y):
                # Check if the point is to the left of the maximum x coordinate of the edge
                if x <= max(p1.x, p2.x):
                    # Calculate the x-intersection of the line connecting the point to the edge
                    x_intersection = (y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y) + p1.x
 
                    # Check if the point is on the same line as the edge or to the left of the x-intersection
                    if p1.x == p2.x or x <= x_intersection:
                        # Flip the inside flag
                        inside = not inside
 
        # Store the current point as the first point for the next iteration
        p1 = p2
 
    # Return the value of the inside flag
    return inside


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def eco_efficiency_analysis_new(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_efficiency',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=0, minute=1, second=1, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_id = _get_int(request.GET.get('unit_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    analyst_id = _get_int(request.GET.get('analyst_id'))
    type_id = _get_int(request.GET.get('type_id'))
    status_id = _get_int(request.GET.get('status_id'))

    docs_lo     = DocLO.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end)
    docs_rlk    = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(eco = True)
    subqyery_est        = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name = 'rlk__id'))
    subqyery_eco_before = EcoAnalystSnapshot.objects.filter(role = 'before').filter(rlk_id = OuterRef(name = 'rlk__id'))
    subqyery_eco_after  = EcoAnalystSnapshot.objects.filter(role = 'after').filter(rlk_id = OuterRef(name = 'rlk__id'))
    
    docs_lo = docs_lo.annotate(
        price_after_kd          = Subquery(subqyery_est.values('page_soglasovanie__price_after_kd')[:1])).annotate(
        price_before_kd         = Subquery(subqyery_est.values('page_soglasovanie__price_before_kd')[:1])).annotate(
        before_kd               = Subquery(subqyery_eco_before.values('comparison')[:1])).annotate(
        after_kd                = Subquery(subqyery_eco_after.values('comparison')[:1])    
    )
    est_success = docs_lo.filter(active = True).count()
    est_kd      = docs_lo.filter(price_after_kd__gt = 0).count()
    est_do_kd   = docs_lo.filter(price_before_kd__gt = 0).count()

    est_success_percent = est_success / est_kd * 100
    est_kd_percent = est_kd / est_do_kd * 100

    count_before_higher = docs_lo.filter(before_kd = 1).count()
    count_before_equal  = docs_lo.filter(before_kd = 0).count()
    count_before_lower  = docs_lo.filter(before_kd = -1).count()

    count_after_higher = docs_lo.filter(after_kd = 1).count()
    count_after_equal  = docs_lo.filter(after_kd = 0).count()
    count_after_lower  = docs_lo.filter(after_kd = -1).count()

    units = RefUnit.objects.filter(buauto=True).filter(active_eco=True).exclude(name='').order_by('name')
    staffs = RefStaff.objects.exclude(name='').order_by('name')
    analysts = User.objects.filter(profiles__eco=True)
    types   = RefTypeReceptionCarsOrganization.objects.order_by('name')
    statuses = RefStatusEstimation.objects.order_by('name')

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_id': unit_id or '',
        'staff_id': staff_id or '',
        'analyst_id': analyst_id or '',
        'type_id': type_id or '',
        'status_id': status_id or '',
    }

    
    params = {
        'type': 'eco_efficiency',
        'nav_selected': 4,
        'request': request,
        'filters': filters,
        'est_success'   : est_success,
        'est_success_percent'   : est_success_percent,
        'est_kd'        : est_kd,
        'est_kd_percent'    : est_kd_percent,
        'est_do_kd'     : est_do_kd,
        'count_before_higher'   : count_before_higher,
        'count_before_equal'    : count_before_equal,
        'count_before_lower'    : count_before_lower,
        'count_after_higher'    : count_after_higher,
        'count_after_equal'     : count_after_equal,
        'count_after_lower'     : count_after_lower,
        
        
    }

    return render(request, 'lo/eco_efficiency_new.html', {'params': params})


def eco_efficiency_analysis(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_efficiency',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=0, minute=1, second=1, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_id = _get_int(request.GET.get('unit_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    analyst_id = _get_int(request.GET.get('analyst_id'))
    type_id = _get_int(request.GET.get('type_id'))
    status_id = _get_int(request.GET.get('status_id'))

    pricing_qs = EcoAnalystSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    )

    if unit_id:
        pricing_qs = pricing_qs.filter(unit_id=unit_id)
    if staff_id:
        pricing_qs = pricing_qs.filter(staff_id=staff_id)
    if analyst_id:
        pricing_qs = pricing_qs.filter(analyst_id=analyst_id)
    if type_id:
        pricing_qs = pricing_qs.filter(type_reception_id=type_id)
    if status_id:
        pricing_qs = pricing_qs.filter(status_id=status_id)

    total_count = pricing_qs.values('estimation_id').order_by('estimation_id').distinct().count()#pricing_qs.count()
    # Согласовано до КД (role='before' и has_soglasovanie=True)
    with_soglasovanie_before_count = pricing_qs.filter(role='before', has_soglasovanie=True).count()
    # Согласовано после КД (role='after' и has_soglasovanie=True)
    with_soglasovanie_after_count = pricing_qs.filter(role='after', has_soglasovanie=True).count()
    # Согласовано дистанционно (role='remote' и has_soglasovanie=True)
    with_soglasovanie_remote_count = pricing_qs.filter(role='remote').count()
    # Принято (только среди согласованных после КД: role='after', has_soglasovanie=True и accepted=True)
    with_accepted_count = pricing_qs.filter(role='after', has_soglasovanie=True, accepted=True).count()
    
    soglasovanie_percent = round((with_soglasovanie_before_count / total_count * 100), 1) if total_count > 0 else 0
    soglasovanie_after_percent = round((with_soglasovanie_after_count / with_soglasovanie_before_count * 100), 1) if with_soglasovanie_before_count > 0 else 0
    soglasovanie_remote_percent = round((with_soglasovanie_remote_count / total_count * 100), 1) if total_count > 0 else 0
    accepted_percent = round((with_accepted_count / with_soglasovanie_after_count * 100), 1) if with_soglasovanie_after_count > 0 else 0
    
    avg_time_total = pricing_qs.aggregate(avg=Avg('duration_estimation_sec'))['avg']
    avg_time_total = round(avg_time_total / 3600, 1) if avg_time_total else None

    avg_soglasovanie_time = (
        pricing_qs.filter(has_soglasovanie=True).aggregate(avg=Avg('duration_sogl_after_sec'))['avg']
    )
    avg_soglasovanie_time = round(avg_soglasovanie_time / 3600, 1) if avg_soglasovanie_time else None

    # Маркеры по согласованиям после диагностики
    price_diffs = []
    price_percent_diffs = []
    higher_count_after = lower_count_after = equal_count_after = 0
    # for price_after, auto_price in pricing_qs.filter(role='after', has_soglasovanie=True).values_list('price_after_kd', 'price_auto_selected')[:2000]:
    #     if price_after and auto_price:
    #         diff = float(price_after) - float(auto_price)
    #         price_diffs.append(diff)
    #         diff_percent = round((diff / float(auto_price)) * 100, 1) if auto_price else 0
    #         price_percent_diffs.append(diff_percent)
    #         if diff_percent > 5:  # Выше на 5% и более
    #             higher_count_after += 1
    #         elif diff_percent < 0:  # Ниже на 5% и более
    #             lower_count_after += 1
    #         else:  # В пределах ±5%
    #             equal_count_after += 1
    
    higher_count_after = pricing_qs.filter(role='after', has_soglasovanie=True, comparison = 1).count()
    lower_count_after  = pricing_qs.filter(role='after', has_soglasovanie=True, comparison = -1).count()
    equal_count_after  = pricing_qs.filter(role='after', has_soglasovanie=True, comparison = 0).count()

    higher_count_remote = pricing_qs.filter(role='remote',  comparison = 1).count()
    lower_count_remote  = pricing_qs.filter(role='remote',  comparison = -1).count()
    equal_count_remote  = pricing_qs.filter(role='remote',  comparison = 0).count()

    avg_price_diff = round(sum(price_diffs) / len(price_diffs), 0) if price_diffs else 0
    avg_price_diff_percent = round(sum(price_percent_diffs) / len(price_percent_diffs), 1) if price_percent_diffs else 0

    higher_count_before = pricing_qs.filter(role='before', comparison = 1).count()
    lower_count_before  = pricing_qs.filter(role='before', comparison = -1).count()
    equal_count_before  = pricing_qs.filter(role='before', comparison = 0).count()

    # Маркеры по согласованиям до диагностики
    # higher_count_before = lower_count_before = equal_count_before = 0
    # for price_before, auto_price in pricing_qs.filter(role='before', has_soglasovanie=True).values_list('price_before_kd', 'price_auto_selected')[:2000]:
    #     if price_before and auto_price:
    #         diff = float(price_before) - float(auto_price)
    #         diff_percent = round((diff / float(auto_price)) * 100, 1) if auto_price else 0
    #         if diff_percent > 5:  # Выше на 5% и более
    #             higher_count_before += 1
    #         elif diff_percent < 0:  # Ниже на 5% и более
    #             lower_count_before += 1
    #         else:  # В пределах ±5%
    #             equal_count_before += 1

    task_aggregate = pricing_qs.aggregate(
        total_tasks=Coalesce(Sum('tasks_total'), 0),
        closed_tasks=Coalesce(Sum('tasks_closed'), 0),
        evaluations_with_tasks=Count('estimation_id', filter=Q(tasks_total__gt=0)),
    )
    all_tasks_total = task_aggregate['total_tasks'] or 0
    all_tasks_closed = task_aggregate['closed_tasks'] or 0
    evaluations_with_tasks_count = task_aggregate['evaluations_with_tasks'] or 0
    all_tasks_open = all_tasks_total - all_tasks_closed
    avg_tasks_per_eval = round(all_tasks_total / total_count, 1) if total_count and all_tasks_total else 0
    evaluations_with_tasks_percent = (
        round((evaluations_with_tasks_count / total_count * 100), 1) if total_count else 0
    )

    analyst_qs = EcoAnalystSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    )
    if unit_id:
        analyst_qs = analyst_qs.filter(unit_id=unit_id)
    if staff_id:
        analyst_qs = analyst_qs.filter(staff_id=staff_id)
    if analyst_id:
        analyst_qs = analyst_qs.filter(analyst_id=analyst_id)
    if type_id:
        analyst_qs = analyst_qs.filter(type_reception_id=type_id)
    if status_id:
        analyst_qs = analyst_qs.filter(status_id=status_id)

    analyst_stats_raw = analyst_qs.exclude(analyst_id__isnull=True).values('analyst_id', 'analyst_name').annotate(
        total=Count('id'),
        with_soglas=Count('id', filter=Q(has_soglasovanie=True)),
        accepted=Count('id', filter=Q(accepted=True)),
        avg_duration=Avg('duration_estimation_sec'),
        tasks_total_sum=Coalesce(Sum('tasks_total'), 0),
        tasks_closed_sum=Coalesce(Sum('tasks_closed'), 0),
        evaluations_with_tasks=Count('id', filter=Q(tasks_total__gt=0)),
    )

    analyst_stats = []
    for row in analyst_stats_raw:
        count = row['total']
        if count == 0:
            continue
        avg_time = round((row['avg_duration'] or 0) / 3600, 1) if row['avg_duration'] else None
        total_tasks = row['tasks_total_sum'] or 0
        closed_tasks = row['tasks_closed_sum'] or 0
        task_stats = {
            'total_tasks': total_tasks,
            'evaluations_with_tasks': row['evaluations_with_tasks'] or 0,
            'avg_tasks_per_eval': round(total_tasks / count, 1) if total_tasks else 0,
            'closed_tasks': closed_tasks,
            'open_tasks': total_tasks - closed_tasks,
            'closed_percent': round((closed_tasks / total_tasks * 100), 1) if total_tasks else 0,
        }
        
        # Маркеры по согласованиям для аналитика
        analyst_id_st = row['analyst_id']
        analyst_before_qs = analyst_qs.filter(analyst_id=analyst_id_st, role='before', has_soglasovanie=True)
        analyst_after_qs = analyst_qs.filter(analyst_id=analyst_id_st, role='after', has_soglasovanie=True)
        analyst_remote_qs = analyst_qs.filter(analyst_id=analyst_id_st, role='remote')
        
        # До диагностики
        higher_before = lower_before = equal_before = 0
        higher_before = analyst_before_qs.filter(comparison = 1).count()
        lower_before = analyst_before_qs.filter(comparison = -1).count()
        equal_before = analyst_before_qs.filter(comparison = 0).count()
        # for price_before, auto_price in analyst_before_qs.values_list('price_before_kd', 'price_auto_selected'):
        #     if price_before and auto_price:
        #         diff = float(price_before) - float(auto_price)
        #         diff_percent = round((diff / float(auto_price)) * 100, 1) if auto_price else 0
        #         if diff_percent > 5:
        #             higher_before += 1
        #         elif diff_percent < -5:
        #             lower_before += 1
        #         else:
        #             equal_before += 1
        
        # После диагностики
        higher_after = lower_after = equal_after = 0
        higher_after = analyst_after_qs.filter(comparison = 1).count()
        lower_after = analyst_after_qs.filter(comparison = -1).count()
        equal_after = analyst_after_qs.filter(comparison = 0).count()
        
        # Дистанционная
        higher_remote = lower_remote = equal_remote = 0
        higher_remote = analyst_remote_qs.filter(comparison = 1).count()
        lower_remote = analyst_remote_qs.filter(comparison = -1).count()
        equal_remote = analyst_remote_qs.filter(comparison = 0).count()
        
        # for price_after, auto_price in analyst_after_qs.values_list('price_after_kd', 'price_auto_selected'):
        #     if price_after and auto_price:
        #         diff = float(price_after) - float(auto_price)
        #         diff_percent = round((diff / float(auto_price)) * 100, 1) if auto_price else 0
        #         if diff_percent > 5:
        #             higher_after += 1
        #         elif diff_percent < -5:
        #             lower_after += 1
        #         else:
        #             equal_after += 1
        
        analyst_stats.append(
            {
                'analyst_id': analyst_id_st,
                'name': row['analyst_name'] or '—',
                'total': count,
                'with_soglasovanie_count' : with_soglasovanie_before_count,
                'accepted_percent'      : accepted_percent,
                'with_soglasovanie': row['with_soglas'],
                'accepted': row['accepted'],
                'avg_time': avg_time,
                'conv_rate': round((row['with_soglas'] / count * 100), 1) if count else 0,
                'accept_rate': round((row['accepted'] / count * 100), 1) if count else 0,
                'task_stats': task_stats,
                'price_markers_before': {
                    'higher': higher_before,
                    'equal': equal_before,
                    'lower': lower_before,
                    'total': higher_before + equal_before + lower_before,
                },
                'price_markers_after': {
                    'higher': higher_after,
                    'equal': equal_after,
                    'lower': lower_after,
                    'total': higher_after + equal_after + lower_after,
                },
                'price_markers_remote': {
                    'higher': higher_remote,
                    'equal': equal_remote,
                    'lower': lower_remote,
                    'total': higher_remote + equal_remote + lower_remote,
                },
            }
        )

    analyst_stats = sorted(analyst_stats, key=lambda x: x['total'], reverse=True)

    monthly_data = []
    monthly_agg = (
        pricing_qs.annotate(month=TruncMonth('start_estimation'))
        .values('month')
        .order_by('month')
        .annotate(
            total=Count('estimation_id'),
            with_soglas=Count('estimation_id', filter=Q(has_soglasovanie=True)),
            accepted=Count('estimation_id', filter=Q(accepted=True)),
            avg_duration=Avg('duration_estimation_sec'),
        )
    )
    for item in monthly_agg:
        month_dt = item['month']
        monthly_data.append(
            {
                'month': month_dt.strftime('%b %Y') if month_dt else '',
                'total': item['total'],
                'with_soglasovanie': item['with_soglas'],
                'accepted': item['accepted'],
                'avg_time': round((item['avg_duration'] or 0) / 3600, 1) if item['avg_duration'] else None,
            }
        )

    units = RefUnit.objects.filter(buauto=True).filter(active_eco=True).exclude(name='').order_by('name')
    staffs = RefStaff.objects.exclude(name='').order_by('name')
    analysts = User.objects.filter(profiles__eco=True)
    types = RefTypeReceptionCarsOrganization.objects.order_by('name')
    statuses = RefStatusEstimation.objects.order_by('name')

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_id': unit_id or '',
        'staff_id': staff_id or '',
        'analyst_id': analyst_id or '',
        'type_id': type_id or '',
        'status_id': status_id or '',
    }

    monthly_data_json = json.dumps(monthly_data, ensure_ascii=False, default=str)
    
    # Вычисляем проценты для маркеров
    total_compared_after = higher_count_after + lower_count_after + equal_count_after
    total_compared_before = higher_count_before + lower_count_before + equal_count_before
    total_compared_remote = higher_count_remote + lower_count_remote + equal_count_remote

    params = {
        'type': 'eco_efficiency',
        'nav_selected': 4,
        'request': request,
        'filters': filters,
        'total_count': total_count,
        'with_soglasovanie_count': with_soglasovanie_before_count,
        'soglasovanie_percent': soglasovanie_percent,
        'with_soglasovanie_after_count': with_soglasovanie_after_count,
        'soglasovanie_after_percent': soglasovanie_after_percent,
        'with_soglasovanie_remote_count': with_soglasovanie_remote_count,
        'soglasovanie_remote_percent': soglasovanie_remote_percent,
        'with_accepted_count': with_accepted_count,
        'accepted_percent': accepted_percent,
        'avg_time_total': avg_time_total,
        'avg_soglasovanie_time': avg_soglasovanie_time,
        'price_comparison': {
            'avg_diff': avg_price_diff,
            'avg_diff_percent': avg_price_diff_percent,
            'higher_count_after': higher_count_after,
            'lower_count_after': lower_count_after,
            'equal_count_after': equal_count_after,
            'total_compared_after': total_compared_after,
            'higher_percent_after': round((higher_count_after / total_compared_after * 100), 1) if total_compared_after > 0 else 0,
            'lower_percent_after': round((lower_count_after / total_compared_after * 100), 1) if total_compared_after > 0 else 0,
            'equal_percent_after': round((equal_count_after / total_compared_after * 100), 1) if total_compared_after > 0 else 0,
            'higher_count_before': higher_count_before,
            'lower_count_before': lower_count_before,
            'equal_count_before': equal_count_before,
            'total_compared_before': total_compared_before,
            'higher_percent_before': round((higher_count_before / total_compared_before * 100), 1) if total_compared_before > 0 else 0,
            'lower_percent_before': round((lower_count_before / total_compared_before * 100), 1) if total_compared_before > 0 else 0,
            'equal_percent_before': round((equal_count_before / total_compared_before * 100), 1) if total_compared_before > 0 else 0,
            'higher_count_remote': higher_count_remote,
            'lower_count_remote': lower_count_remote,
            'equal_count_remote': equal_count_remote,
            'total_compared_remote': total_compared_remote,
            'higher_percent_remote': round((higher_count_remote / total_compared_remote * 100), 1) if total_compared_remote > 0 else 0,
            'lower_percent_remote': round((lower_count_remote / total_compared_remote * 100), 1) if total_compared_remote > 0 else 0,
            'equal_percent_remote': round((equal_count_remote / total_compared_remote * 100), 1) if total_compared_remote > 0 else 0,
        },
        'task_stats': {
            'total_tasks': all_tasks_total,
            'evaluations_with_tasks': evaluations_with_tasks_count,
            'avg_tasks_per_eval': avg_tasks_per_eval,
            'evaluations_with_tasks_percent': evaluations_with_tasks_percent,
            'closed_tasks': all_tasks_closed,
            'open_tasks': all_tasks_open,
            'closed_percent': round((all_tasks_closed / all_tasks_total * 100), 1) if all_tasks_total > 0 else 0,
        },
        'analyst_stats': analyst_stats,
        'monthly_data': monthly_data,
        'monthly_data_json': monthly_data_json,
        'units': units,
        'staffs': staffs,
        'analysts': analysts,
        'types': types,
        'statuses': statuses,
    }

    return render(request, 'lo/eco_efficiency.html', {'params': params})


def eco_analyst_detail(request, analyst_id):
    """Детальная страница по аналитику с оценками"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_analyst_detail',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = (default_end - DT.timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_id = _get_int(request.GET.get('unit_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    type_id = _get_int(request.GET.get('type_id'))
    status_id = _get_int(request.GET.get('status_id'))
    role_filter = request.GET.get('role', '')
    marker_filter = request.GET.get('marker', '')

    # Получаем аналитика
    try:
        analyst = User.objects.get(pk=analyst_id)
        analyst_name = analyst.profiles.eco_name if hasattr(analyst, 'profiles') and analyst.profiles.eco_name else analyst.get_full_name() or analyst.username
    except User.DoesNotExist:
        analyst_name = 'Неизвестный аналитик'

    # Получаем оценки аналитика
    evaluations_qs = EcoAnalystSnapshot.objects.filter(
        analyst_id=analyst_id,
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    )

    if unit_id:
        evaluations_qs = evaluations_qs.filter(unit_id=unit_id)
    if staff_id:
        evaluations_qs = evaluations_qs.filter(staff_id=staff_id)
    if type_id:
        evaluations_qs = evaluations_qs.filter(type_reception_id=type_id)
    if status_id:
        evaluations_qs = evaluations_qs.filter(status_id=status_id)
    if role_filter:
        evaluations_qs = evaluations_qs.filter(role=role_filter)
    if marker_filter:
        if marker_filter == 'higher':
            evaluations_qs = evaluations_qs.filter(comparison=1)
        elif marker_filter == 'lower':
            evaluations_qs = evaluations_qs.filter(comparison=-1)
        else:
            evaluations_qs = evaluations_qs.filter(comparison=0)

    # Пагинация
    paginator = Paginator(evaluations_qs.order_by('-start_estimation'), 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Подготовка данных для таблицы
    evaluations = []
    for eval_snapshot in page_obj:
        # Определяем маркер цены
        price_marker = None
        price_marker_class = ''
        
        if eval_snapshot.comparison == 1:
            price_marker = 'Выше'
            price_marker_class = 'text-success'
        elif eval_snapshot.comparison == -1:
            price_marker = 'Ниже'
            price_marker_class = 'text-danger'
        else:
            price_marker = 'Равно'
            price_marker_class = 'text-info'

        # if eval_snapshot.role == 'before' and eval_snapshot.price_before_kd and eval_snapshot.price_auto_selected:
        #     diff = float(eval_snapshot.price_before_kd) - float(eval_snapshot.price_auto_selected)
        #     diff_percent = round((diff / float(eval_snapshot.price_auto_selected)) * 100, 1) if eval_snapshot.price_auto_selected else 0
        #     if diff_percent > 5:
        #         price_marker = 'Выше'
        #         price_marker_class = 'text-success'
        #     elif diff_percent < -5:
        #         price_marker = 'Ниже'
        #         price_marker_class = 'text-danger'
        #     else:
        #         price_marker = 'Равно'
        #         price_marker_class = 'text-info'
        # elif eval_snapshot.role == 'after' and eval_snapshot.price_after_kd and eval_snapshot.price_auto_selected:
        #     diff = float(eval_snapshot.price_after_kd) - float(eval_snapshot.price_auto_selected)
        #     diff_percent = round((diff / float(eval_snapshot.price_auto_selected)) * 100, 1) if eval_snapshot.price_auto_selected else 0
        #     if diff_percent > 5:
        #         price_marker = 'Выше'
        #         price_marker_class = 'text-success'
        #     elif diff_percent < -5:
        #         price_marker = 'Ниже'
        #         price_marker_class = 'text-danger'
        #     else:
        #         price_marker = 'Равно'
        #         price_marker_class = 'text-info'
        # elif eval_snapshot.role == 'remote' and eval_snapshot.price_before_kd and eval_snapshot.price_auto_selected:
        #     diff = float(eval_snapshot.price_before_kd) - float(eval_snapshot.price_auto_selected)
        #     diff_percent = round((diff / float(eval_snapshot.price_auto_selected)) * 100, 1) if eval_snapshot.price_auto_selected else 0
        #     if diff_percent > 5:
        #         price_marker = 'Выше'
        #         price_marker_class = 'text-success'
        #     elif diff_percent < -5:
        #         price_marker = 'Ниже'
        #         price_marker_class = 'text-danger'
        #     else:
        #         price_marker = 'Равно'
        #         price_marker_class = 'text-info'

        # Вычисляем время в часах
        duration_estimation_hours = round((eval_snapshot.duration_estimation_sec or 0) / 3600, 1) if eval_snapshot.duration_estimation_sec else None
        duration_sogl_hours = None
        if eval_snapshot.role == 'before' and eval_snapshot.duration_sogl_before_sec:
            duration_sogl_hours = round(eval_snapshot.duration_sogl_before_sec / 3600, 1)
        elif eval_snapshot.role == 'after' and eval_snapshot.duration_sogl_after_sec:
            duration_sogl_hours = round(eval_snapshot.duration_sogl_after_sec / 3600, 1)
        role_display = 'До КД'
        if eval_snapshot.role == 'after':
            role_display = 'До КД'
        elif eval_snapshot.role == 'remote':
            role_display = 'Дистанционно'

        evaluations.append({
            'estimation_id': eval_snapshot.estimation_id,
            'rlk_id': eval_snapshot.rlk_id,
            'role': eval_snapshot.role,
            'role_display': role_display,
            'start_estimation': eval_snapshot.start_estimation,
            'end_estimation': eval_snapshot.end_estimation,
            'unit_name': eval_snapshot.unit_name,
            'staff_name': eval_snapshot.staff_name,
            'status_name': eval_snapshot.status_name,
            'has_soglasovanie': eval_snapshot.has_soglasovanie,
            'has_diagnostics': eval_snapshot.has_diagnostics,
            'accepted': eval_snapshot.accepted,
            'price_auto_selected': eval_snapshot.price_auto_selected,
            'price_before_kd': eval_snapshot.price_before_kd,
            'price_after_kd': eval_snapshot.price_after_kd,
            'duration_estimation_hours': duration_estimation_hours,
            'duration_sogl_hours': duration_sogl_hours,
            'tasks_total': eval_snapshot.tasks_total,
            'tasks_closed': eval_snapshot.tasks_closed,
            'price_marker': price_marker,
            'price_marker_class': price_marker_class,
        })

    units = RefUnit.objects.filter(buauto=True).filter(active_eco=True).exclude(name='').order_by('name')
    staffs = RefStaff.objects.exclude(name='').order_by('name')
    types = RefTypeReceptionCarsOrganization.objects.order_by('name')
    statuses = RefStatusEstimation.objects.order_by('name')

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_id': unit_id or '',
        'staff_id': staff_id or '',
        'type_id': type_id or '',
        'status_id': status_id or '',
        'role': role_filter or '',
        'marker': marker_filter or '',
    }

    params = {
        'type': 'eco_analyst_detail',
        'nav_selected': 4,
        'request': request,
        'analyst_id': analyst_id,
        'analyst_name': analyst_name,
        'filters': filters,
        'evaluations': evaluations,
        'page_obj': page_obj,
        'units': units,
        'staffs': staffs,
        'types': types,
        'statuses': statuses,
    }

    return render(request, 'lo/eco_analyst_detail.html', {'params': params})


def staff_performance_analysis(request):
    """Дашборд анализа работы оценщиков"""
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'staff_performance',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = (default_end - DT.timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_id = _get_int(request.GET.get('unit_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    type_id = _get_int(request.GET.get('type_id'))
    status_id = _get_int(request.GET.get('status_id'))

    # Базовый запрос для рабочих листов (RLK) - только trade-in через витрину
    rlk_base_qs = TradeInFunnelSnapshot.objects.filter(
        date_work_order__gte=date_start,
        date_work_order__lte=date_end,
    )

    # Базовый запрос для интерактивных оценок через витрину
    eval_base_qs = AppraiserPerformanceSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    )

    if unit_id:
        rlk_base_qs = rlk_base_qs.filter(unit_id=unit_id)
        eval_base_qs = eval_base_qs.filter(unit_id=unit_id)

    if type_id:
        # type_reception_id может быть в extra_payload или нужно использовать другую витрину
        # Пока используем фильтр через extra_payload, если там хранится type_reception_id
        eval_base_qs = eval_base_qs.filter(extra_payload__type_reception_id=type_id)

    if status_id:
        eval_base_qs = eval_base_qs.filter(status_id=status_id)

    if staff_id:
        rlk_base_qs = rlk_base_qs.filter(staff_id=staff_id)
        eval_base_qs = eval_base_qs.filter(staff_id=staff_id)

    # Получаем список всех оценщиков, которые работали в период
    staff_ids_from_rlk = set(rlk_base_qs.filter(staff_id__isnull=False).values_list('staff_id', flat=True))
    staff_ids_from_eval = set(eval_base_qs.filter(staff_id__isnull=False).values_list('staff_id', flat=True))
    all_staff_ids = list(staff_ids_from_rlk | staff_ids_from_eval)

    # Агрегируем статистику по оценщикам через витрины
    rlk_stats_by_staff = dict(
        rlk_base_qs.filter(staff_id__in=all_staff_ids)
        .values('staff_id')
        .annotate(count=Count('rlk_id'))
        .values_list('staff_id', 'count')
    )
    
    # Статистика по интерактивным оценкам через витрину
    eval_stats_qs = eval_base_qs.filter(staff_id__in=all_staff_ids)
    
    eval_stats_raw = eval_stats_qs.values('staff_id').annotate(
        total=Count('estimation_id'),
        diagnostics=Count('estimation_id', filter=Q(has_diagnostics=True)),
        accepted=Count('estimation_id', filter=Q(accepted=True)),
        with_soglas=Count('estimation_id', filter=Q(has_soglasovanie=True))
    ).values('staff_id', 'total', 'diagnostics', 'accepted', 'with_soglas')
    
    eval_stats_by_staff = {}
    for item in eval_stats_raw:
        staff_id = item['staff_id']
        eval_stats_by_staff[staff_id] = (
            item['total'],
            item['diagnostics'],
            item['accepted'],
            item['with_soglas']
        )
    
    # Получаем все оценки с временными метками для расчета среднего времени
    eval_time_data = {}
    eval_time_list = eval_base_qs.filter(
        staff_id__in=all_staff_ids,
        start_estimation__isnull=False,
        end_estimation__isnull=False
    ).values_list('staff_id', 'start_estimation', 'end_estimation')[:2000]
    
    for staff_id, start_time, end_time in eval_time_list:
        if staff_id and start_time and end_time:
            if staff_id not in eval_time_data:
                eval_time_data[staff_id] = []
            diff = (end_time - start_time).total_seconds() / 3600
            if diff >= 0:
                eval_time_data[staff_id].append(diff)
    
    # Создаем маппинг eval_id -> staff_id для быстрого поиска
    eval_to_staff_map = {}
    eval_staff_list = eval_base_qs.filter(staff_id__in=all_staff_ids).values_list('estimation_id', 'staff_id')
    for eval_id, staff_id in eval_staff_list:
        if staff_id:
            eval_to_staff_map[eval_id] = staff_id
    
    # Получаем данные по задачам из витрины
    all_eval_ids = list(eval_base_qs.values_list('estimation_id', flat=True))
    
    # Группируем задачи по оценщикам из витрины
    staff_task_stats = defaultdict(lambda: {'total': 0, 'closed': 0, 'evaluations_with_tasks': set()})
    
    task_data_from_snapshot = eval_base_qs.filter(
        staff_id__in=all_staff_ids
    ).values('staff_id', 'estimation_id', 'tasks_total', 'tasks_closed')
    
    for item in task_data_from_snapshot:
        staff_id = item['staff_id']
        eval_id = item['estimation_id']
        tasks_total = item['tasks_total'] or 0
        tasks_closed = item['tasks_closed'] or 0
        
        if staff_id:
            staff_task_stats[staff_id]['total'] += tasks_total
            staff_task_stats[staff_id]['closed'] += tasks_closed
            if tasks_total > 0:
                staff_task_stats[staff_id]['evaluations_with_tasks'].add(eval_id)
    
    # Типы поступлений по оценщикам из витрины
    # Используем InteractivePricingSnapshot для получения type_reception_id
    staff_type_stats = defaultdict(lambda: defaultdict(int))
    pricing_snapshot_qs = InteractivePricingSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
        estimation_id__in=eval_base_qs.values_list('estimation_id', flat=True)
    )
    
    if unit_id:
        pricing_snapshot_qs = pricing_snapshot_qs.filter(unit_id=unit_id)
    if staff_id:
        pricing_snapshot_qs = pricing_snapshot_qs.filter(staff_id=staff_id)
    if type_id:
        pricing_snapshot_qs = pricing_snapshot_qs.filter(type_reception_id=type_id)
    
    # Получаем type_reception_id из InteractivePricingSnapshot и маппим на staff_id
    type_data = pricing_snapshot_qs.values('estimation_id', 'type_reception_id')
    eval_to_type_map = {item['estimation_id']: item['type_reception_id'] for item in type_data}
    
    # Получаем названия типов приема
    type_names = {}
    if eval_to_type_map:
        type_ids = set(eval_to_type_map.values())
        if type_ids:
            from register.models import RefTypeReceptionCarsOrganization
            type_names = dict(RefTypeReceptionCarsOrganization.objects.filter(
                id__in=type_ids
            ).values_list('id', 'name'))
    
    # Группируем по оценщикам
    for eval_id, staff_id in eval_to_staff_map.items():
        type_reception_id = eval_to_type_map.get(eval_id)
        type_name = type_names.get(type_reception_id, 'Не указано') if type_reception_id else 'Не указано'
        staff_type_stats[staff_id][type_name] = staff_type_stats[staff_id].get(type_name, 0) + 1
    
    # Формируем финальную статистику
    staff_stats = []
    for staff in RefStaff.objects.filter(id__in=all_staff_ids).order_by('name'):
        rlk_count = rlk_stats_by_staff.get(staff.id, 0)
        eval_data = eval_stats_by_staff.get(staff.id)
        
        if not eval_data:
            eval_count = diagnostics_count = accepted_count = with_soglas_count = 0
        else:
            eval_count = eval_data[0]
            diagnostics_count = eval_data[1]
            accepted_count = eval_data[2]
            with_soglas_count = eval_data[3]
        
        # Среднее время
        time_diffs = eval_time_data.get(staff.id, [])
        avg_time = round(sum(time_diffs) / len(time_diffs), 1) if time_diffs else None
        
        # Типы поступлений
        type_stats = dict(staff_type_stats.get(staff.id, {}))
        
        # Задачи
        task_data = staff_task_stats.get(staff.id, {})
        task_stats = {
            'total': task_data.get('total', 0),
            'closed': task_data.get('closed', 0),
            'evaluations_with_tasks': len(task_data.get('evaluations_with_tasks', set())),
        }
        
        # Конверсии
        rlk_to_eval_rate = round((eval_count / rlk_count * 100), 1) if rlk_count > 0 else 0
        eval_to_diag_rate = round((diagnostics_count / eval_count * 100), 1) if eval_count > 0 else 0
        diag_to_accepted_rate = round((accepted_count / diagnostics_count * 100), 1) if diagnostics_count > 0 else 0
        overall_conversion = round((accepted_count / rlk_count * 100), 1) if rlk_count > 0 else 0
        
        if rlk_count > 0 or eval_count > 0:
            staff_stats.append({
                'staff': staff,
                'rlk_count': rlk_count,
                'eval_count': eval_count,
                'diagnostics_count': diagnostics_count,
                'accepted_count': accepted_count,
                'with_soglas_count': with_soglas_count,
                'avg_time': avg_time,
                'type_stats': type_stats,
                'task_stats': task_stats,
                'rlk_to_eval_rate': rlk_to_eval_rate,
                'eval_to_diag_rate': eval_to_diag_rate,
                'diag_to_accepted_rate': diag_to_accepted_rate,
                'overall_conversion': overall_conversion,
            })
    
    staff_stats = sorted(staff_stats, key=lambda x: x['rlk_count'], reverse=True)

    # Статистика по аналитикам
    analyst_ids = list(User.objects.filter(
        Q(profiles__eco=True) | Q(profiles__eco_visible=True)
    ).distinct().values_list('id', flat=True))
    
    analyst_stats_by_id = {}
    analyst_time_data = {}
    eval_to_analyst_map = {}
    analyst_task_stats = defaultdict(
        lambda: {'total': 0, 'closed': 0, 'evaluations_with_tasks': set(), 'task_counts': []}
    )
    
    if analyst_ids:
        # Базовый фильтр для аналитиков
        base_analyst_filter = Q(
            start_estimation__gte=date_start,
            start_estimation__lte=date_end,
        )
        
        if unit_id:
            base_analyst_filter &= (
                Q(page_documents__unit__id=unit_id)
                | Q(rlk__unit__id=unit_id)
                | Q(rlk__unit_dc__id=unit_id)
            )
        if type_id:
            base_analyst_filter &= Q(page_documents__type_reception__id=type_id)
        if status_id:
            base_analyst_filter &= Q(status__id=status_id)
        
        # Статистика по staff_eco_1 - создаем отдельный queryset
        # Базовый queryset для аналитиков через витрину
        analyst_base_qs = EcoAnalystSnapshot.objects.filter(
            start_estimation__gte=date_start,
            start_estimation__lte=date_end,
            analyst_id__in=analyst_ids
        )
        
        if unit_id:
            analyst_base_qs = analyst_base_qs.filter(unit_id=unit_id)
        if type_id:
            analyst_base_qs = analyst_base_qs.filter(type_reception_id=type_id)
        if status_id:
            analyst_base_qs = analyst_base_qs.filter(status_id=status_id)
        
        # Получаем данные по аналитикам из витрины (before)
        analyst_data_1 = analyst_base_qs.filter(role='before').values_list(
            'analyst_id', 'estimation_id', 'start_estimation', 'end_estimation',
            'has_soglasovanie', 'has_diagnostics',
            'accepted', 'status_name', 'rlk_id',
            'price_before_kd', 'price_auto_selected'
        )
        
        for (
            analyst_id,
            eval_id,
            start_time,
            end_time,
            has_soglas,
            has_diag,
            accepted,
            status_name,
            rlk_id,
            price_before_kd,
            auto_price,
        ) in analyst_data_1:
            if not analyst_id:
                continue
                
            # Инициализация
            if analyst_id not in analyst_stats_by_id:
                analyst_stats_by_id[analyst_id] = {
                    'total': 0,
                    'diagnostics': 0,
                    'accepted': 0,
                    'with_soglas': 0,
                    'roles': {
                        'before': {
                            'count': 0,
                            'price_sum': 0.0,
                            'auto_sum': 0.0,
                            'auto_count': 0,
                            'diff_sum': 0.0,
                            'above_count': 0,
                        },
                        'after': {
                            'count': 0,
                            'price_sum': 0.0,
                            'auto_sum': 0.0,
                            'auto_count': 0,
                            'diff_sum': 0.0,
                            'above_count': 0,
                        },
                    },
                }
            
            analyst_stats_by_id[analyst_id]['total'] += 1
            
            # Диагностика
            if has_diag:
                analyst_stats_by_id[analyst_id]['diagnostics'] += 1
            
            # Принято
            if accepted:
                analyst_stats_by_id[analyst_id]['accepted'] += 1
            
            # С согласованием
            if has_soglas:
                analyst_stats_by_id[analyst_id]['with_soglas'] += 1
            
            # Время
            if start_time and end_time:
                if analyst_id not in analyst_time_data:
                    analyst_time_data[analyst_id] = []
                diff = (end_time - start_time).total_seconds() / 3600
                if diff >= 0:
                    analyst_time_data[analyst_id].append(diff)

            # Ценовые показатели (до КД)
            role_stats = analyst_stats_by_id[analyst_id]['roles']['before']
            if price_before_kd:
                role_stats['count'] += 1
                role_stats['price_sum'] += float(price_before_kd)
                if auto_price and float(auto_price) > 0:
                    role_stats['auto_count'] += 1
                    role_stats['auto_sum'] += float(auto_price)
                    diff_val = float(price_before_kd) - float(auto_price)
                    role_stats['diff_sum'] += diff_val
                    if diff_val >= 0:
                        role_stats['above_count'] += 1
            
            # Маппинг для задач
            eval_to_analyst_map[eval_id] = analyst_id
        
        # Статистика по staff_eco_2 (after) - через витрину
        analyst_data_2 = analyst_base_qs.filter(role='after').values_list(
            'analyst_id', 'estimation_id', 'start_estimation', 'end_estimation',
            'has_soglasovanie', 'has_diagnostics', 'accepted', 'status_name', 'rlk_id',
            'price_after_kd', 'price_auto_selected'
        )
        
        for (
            analyst_id,
            eval_id,
            start_time,
            end_time,
            has_soglas,
            has_diag,
            accepted,
            status_name,
            rlk_id,
            price_after_kd,
            auto_price,
        ) in analyst_data_2:
            if not analyst_id:
                continue
                
            # Инициализация
            if analyst_id not in analyst_stats_by_id:
                analyst_stats_by_id[analyst_id] = {
                    'total': 0,
                    'diagnostics': 0,
                    'accepted': 0,
                    'with_soglas': 0,
                    'roles': {
                        'before': {
                            'count': 0,
                            'price_sum': 0.0,
                            'auto_sum': 0.0,
                            'auto_count': 0,
                            'diff_sum': 0.0,
                            'above_count': 0,
                        },
                        'after': {
                            'count': 0,
                            'price_sum': 0.0,
                            'auto_sum': 0.0,
                            'auto_count': 0,
                            'diff_sum': 0.0,
                            'above_count': 0,
                        },
                    },
                }
            
            analyst_stats_by_id[analyst_id]['total'] += 1
            
            # Диагностика
            if has_diag:
                analyst_stats_by_id[analyst_id]['diagnostics'] += 1
            
            # Принято
            if accepted:
                analyst_stats_by_id[analyst_id]['accepted'] += 1
            
            # С согласованием
            if has_soglas:
                analyst_stats_by_id[analyst_id]['with_soglas'] += 1
            
            # Время
            if start_time and end_time:
                if analyst_id not in analyst_time_data:
                    analyst_time_data[analyst_id] = []
                diff = (end_time - start_time).total_seconds() / 3600
                if diff >= 0:
                    analyst_time_data[analyst_id].append(diff)

            # Ценовые показатели (после КД)
            role_stats = analyst_stats_by_id[analyst_id]['roles']['after']
            if price_after_kd:
                role_stats['count'] += 1
                role_stats['price_sum'] += float(price_after_kd)
                if auto_price and float(auto_price) > 0:
                    role_stats['auto_count'] += 1
                    role_stats['auto_sum'] += float(auto_price)
                    diff_val = float(price_after_kd) - float(auto_price)
                    role_stats['diff_sum'] += diff_val
                    if diff_val >= 0:
                        role_stats['above_count'] += 1
            
            # Маппинг для задач
            eval_to_analyst_map[eval_id] = analyst_id
        
        # Задачи по аналитикам из витрины
        analyst_task_data = analyst_base_qs.values('analyst_id', 'estimation_id', 'tasks_total', 'tasks_closed')
        for item in analyst_task_data:
            analyst_id = item['analyst_id']
            eval_id = item['estimation_id']
            tasks_total = item['tasks_total'] or 0
            tasks_closed = item['tasks_closed'] or 0
            
            if analyst_id:
                analyst_task_stats[analyst_id]['total'] += tasks_total
                analyst_task_stats[analyst_id]['closed'] += tasks_closed
                if tasks_total > 0:
                    analyst_task_stats[analyst_id]['evaluations_with_tasks'].add(eval_id)
                    analyst_task_stats[analyst_id]['task_counts'].append(tasks_total)
    
    # Формируем финальную статистику по аналитикам
    analyst_stats = []
    if analyst_ids:
        for analyst in User.objects.filter(id__in=analyst_ids).select_related('profiles'):
            stats = analyst_stats_by_id.get(analyst.id, {})
            total = stats.get('total', 0)
            
            if total > 0:
                diagnostics_count = stats.get('diagnostics', 0)
                accepted_count = stats.get('accepted', 0)
                with_soglas_count = stats.get('with_soglas', 0)
                
                # Среднее время
                time_diffs = analyst_time_data.get(analyst.id, [])
                avg_time = round(sum(time_diffs) / len(time_diffs), 1) if time_diffs else None
                
                # Задачи
                task_data = analyst_task_stats.get(analyst.id, {})
                task_stats = {
                    'total': task_data.get('total', 0),
                    'closed': task_data.get('closed', 0),
                    'evaluations_with_tasks': len(task_data.get('evaluations_with_tasks', set())),
                }
                
                # Конверсии
                eval_to_diag_rate = round((diagnostics_count / total * 100), 1) if total > 0 else 0
                diag_to_accepted_rate = round((accepted_count / diagnostics_count * 100), 1) if diagnostics_count > 0 else 0
                conv_rate = round((with_soglas_count / total * 100), 1) if total > 0 else 0
                accept_rate = round((accepted_count / total * 100), 1) if total > 0 else 0
                
                analyst_stats.append({
                    'name': analyst.profiles.eco_name or analyst.get_full_name() or analyst.username,
                    'total': total,
                    'diagnostics_count': diagnostics_count,
                    'accepted_count': accepted_count,
                    'with_soglas_count': with_soglas_count,
                    'avg_time': avg_time,
                    'task_stats': task_stats,
                    'eval_to_diag_rate': eval_to_diag_rate,
                    'diag_to_accepted_rate': diag_to_accepted_rate,
                    'conv_rate': conv_rate,
                    'accept_rate': accept_rate,
                })
    
    # Сортируем по имени, затем по количеству
    analyst_stats = sorted(analyst_stats, key=lambda x: (x['name'], -x['total']))

    # Месячная динамика по всем оценщикам
    monthly_data = []
    base_month = date_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current = base_month
    
    while current <= date_end:
        month_end = (current + relativedelta(months=1)) - DT.timedelta(seconds=1)
        if month_end > date_end:
            month_end = date_end
        
        month_rlk_qs = rlk_base_qs.filter(
            date_work_order__gte=current,
            date_work_order__lte=month_end,
        )
        month_eval_qs = eval_base_qs.filter(
            start_estimation__gte=current,
            start_estimation__lte=month_end,
        )
        
        month_rlk_count = month_rlk_qs.count()
        month_eval_count = month_eval_qs.count()
        month_diagnostics_count = month_eval_qs.filter(has_diagnostics=True).count()
        month_accepted_count = month_eval_qs.filter(accepted=True).count()
        
        # Среднее время за месяц через витрину
        month_time_qs = eval_base_qs.filter(
            start_estimation__gte=current,
            start_estimation__lte=month_end,
            start_estimation__isnull=False,
            end_estimation__isnull=False
        )
        
        # Используем only() после всех фильтров, чтобы избежать конфликта
        month_time_qs = month_time_qs.only('start_estimation', 'end_estimation')[:100]
        
        time_diffs = []
        for eval in month_time_qs:
            if eval.end_estimation and eval.start_estimation:
                diff = (eval.end_estimation - eval.start_estimation).total_seconds() / 3600
                if diff >= 0:
                    time_diffs.append(diff)
        
        avg_month_time = round(sum(time_diffs) / len(time_diffs), 1) if time_diffs else None
        
        monthly_data.append({
            'month': current.strftime('%b %Y'),
            'rlk_count': month_rlk_count,
            'eval_count': month_eval_count,
            'diagnostics_count': month_diagnostics_count,
            'accepted_count': month_accepted_count,
            'avg_time': avg_month_time,
        })
        
        current = current + relativedelta(months=1)

    # Общая статистика
    total_rlk = rlk_base_qs.count()
    total_eval = eval_base_qs.count()
    total_diagnostics = eval_base_qs.filter(has_diagnostics=True).count()
    total_accepted = eval_base_qs.filter(accepted=True).count()
    
    # Распределение по типам поступлений через InteractivePricingSnapshot
    overall_type_distribution = {}
    pricing_snapshot_for_types = InteractivePricingSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
        estimation_id__in=eval_base_qs.values_list('estimation_id', flat=True)
    )
    if unit_id:
        pricing_snapshot_for_types = pricing_snapshot_for_types.filter(unit_id=unit_id)
    if staff_id:
        pricing_snapshot_for_types = pricing_snapshot_for_types.filter(staff_id=staff_id)
    
    type_dist = pricing_snapshot_for_types.values('type_reception_id').annotate(
        count=Count('estimation_id')
    )
    
    # Получаем названия типов
    type_ids = set(item['type_reception_id'] for item in type_dist if item['type_reception_id'])
    type_names_map = {}
    if type_ids:
        from register.models import RefTypeReceptionCarsOrganization
        type_names_map = dict(RefTypeReceptionCarsOrganization.objects.filter(
            id__in=type_ids
        ).values_list('id', 'name'))
    
    for item in type_dist:
        type_reception_id = item['type_reception_id']
        type_name = type_names_map.get(type_reception_id, 'Не указано') if type_reception_id else 'Не указано'
        overall_type_distribution[type_name] = item['count']

    units = RefUnit.objects.filter(buauto=True).filter(active_eco=True).exclude(name='').order_by('name')
    staffs = RefStaff.objects.exclude(name='').order_by('name')

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_id': unit_id or '',
        'staff_id': staff_id or '',
    }

    monthly_data_json = json.dumps(monthly_data, ensure_ascii=False, default=str)
    overall_type_distribution_json = json.dumps(overall_type_distribution, ensure_ascii=False)

    params = {
        'type': 'staff_performance',
        'nav_selected': 4,
        'request': request,
        'filters': filters,
        'total_rlk': total_rlk,
        'total_eval': total_eval,
        'total_diagnostics': total_diagnostics,
        'total_accepted': total_accepted,
        'staff_stats': staff_stats,
        'analyst_stats': analyst_stats,
        'monthly_data': monthly_data,
        'monthly_data_json': monthly_data_json,
        'overall_type_distribution': overall_type_distribution,
        'overall_type_distribution_json': overall_type_distribution_json,
        'units': units,
        'staffs': staffs,
    }

    return render(request, 'lo/staff_performance.html', {'params': params})


def interactive_pricing_report(request):
    """Визуальный отчет по согласованию цен интерактивных оценок"""
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'interactive_pricing_report',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = (default_end - DT.timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_id = _get_int(request.GET.get('unit_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    analyst_id = _get_int(request.GET.get('analyst_id'))

    base_qs = InteractivePricingSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    )

    if unit_id:
        base_qs = base_qs.filter(unit_id=unit_id)

    if staff_id:
        base_qs = base_qs.filter(staff_id=staff_id)

    if analyst_id:
        base_qs = base_qs.filter(Q(analyst_before_id=analyst_id) | Q(analyst_after_id=analyst_id))

    total_count = base_qs.count()

    # Статистика по аналитикам из витрины EcoAnalystSnapshot
    analyst_qs = EcoAnalystSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    )
    if unit_id:
        analyst_qs = analyst_qs.filter(unit_id=unit_id)
    if analyst_id:
        analyst_qs = analyst_qs.filter(analyst_id=analyst_id)

    before_stats = analyst_qs.filter(role='before').values('analyst_id', 'analyst_name').annotate(
        cnt=Count('estimation_id'),
        avg_diff=Avg('diff_before'),
        avg_price=Avg('price_before_kd'),
        avg_auto=Avg('price_auto_selected'),
    )
    after_stats = analyst_qs.filter(role='after').values('analyst_id', 'analyst_name').annotate(
        cnt=Count('estimation_id'),
        avg_diff=Avg('diff_after'),
        avg_price=Avg('price_after_kd'),
        avg_auto=Avg('price_auto_selected'),
    )

    analyst_stats_map = {}
    for row in before_stats:
        aid = row['analyst_id'] or 0
        analyst_stats_map[aid] = {
            'analyst_id': row['analyst_id'],
            'analyst_name': row['analyst_name'] or '—',
            'count_before': row['cnt'],
            'avg_diff_before': row['avg_diff'] or 0,
            'avg_price_before': row['avg_price'] or 0,
            'avg_auto': row['avg_auto'] or 0,
            'count_after': 0,
            'avg_diff_after': 0,
            'avg_price_after': 0,
        }
    for row in after_stats:
        aid = row['analyst_id'] or 0
        if aid not in analyst_stats_map:
            analyst_stats_map[aid] = {
                'analyst_id': row['analyst_id'],
                'analyst_name': row['analyst_name'] or '—',
                'count_before': 0,
                'avg_diff_before': 0,
                'avg_price_before': 0,
                'avg_auto': row['avg_auto'] or 0,
                'count_after': row['cnt'],
                'avg_diff_after': row['avg_diff'] or 0,
                'avg_price_after': row['avg_price'] or 0,
            }
        else:
            analyst_stats_map[aid]['count_after'] = row['cnt']
            analyst_stats_map[aid]['avg_diff_after'] = row['avg_diff'] or 0
            analyst_stats_map[aid]['avg_price_after'] = row['avg_price'] or 0
            # Обновим avg_auto, если было пусто
            if not analyst_stats_map[aid]['avg_auto']:
                analyst_stats_map[aid]['avg_auto'] = row['avg_auto'] or 0

    analyst_stats = sorted(analyst_stats_map.values(), key=lambda x: x['analyst_name'])

    aggregates = base_qs.aggregate(
        total_price_before=Coalesce(Sum('price_before_kd', output_field=FloatField()), 0.0),
        total_price_after=Coalesce(Sum('price_after_kd', output_field=FloatField()), 0.0),
        total_price_auto_1=Coalesce(Sum('price_auto_1', output_field=FloatField()), 0.0),
        total_price_auto_2=Coalesce(Sum('price_auto_2', output_field=FloatField()), 0.0),
        total_price_auto_3=Coalesce(Sum('price_auto_3', output_field=FloatField()), 0.0),
        total_price_auto_bcp=Coalesce(Sum('price_auto_bcp', output_field=FloatField()), 0.0),
        total_price_bcp=Coalesce(Sum('price_bcp', output_field=FloatField()), 0.0),
        total_price_reception=Coalesce(Sum('price_reception', output_field=FloatField()), 0.0),
        total_price_sale=Coalesce(Sum('price_sale', output_field=FloatField()), 0.0),
        total_amount_podgotovka=Coalesce(Sum('cost_podgotovka', output_field=FloatField()), 0.0),
        total_amount_ss=Coalesce(Sum('cost_ss', output_field=FloatField()), 0.0),
        total_amount_mcu=Coalesce(Sum('cost_mcu', output_field=FloatField()), 0.0),
        total_amount_recovery=Coalesce(Sum('cost_recovery', output_field=FloatField()), 0.0),
        total_amount_cost=Coalesce(Sum('cost_total', output_field=FloatField()), 0.0),
    )

    def _avg(value):
        return round(value / total_count, 1) if total_count else 0

    avg_auto_price = _avg(aggregates['total_price_auto_1'])
    avg_price_before = _avg(aggregates['total_price_before'])
    avg_price_after = _avg(aggregates['total_price_after'])
    avg_cost = _avg(aggregates['total_amount_cost'])

    summary = {
        'total_evaluations': total_count,
        'avg_price_before': avg_price_before,
        'avg_price_after': avg_price_after,
        'avg_auto_price': avg_auto_price,
        'avg_diff_before': round(avg_price_before - avg_auto_price, 1),
        'avg_diff_after': round(avg_price_after - avg_auto_price, 1),
        'avg_cost': avg_cost,
        'avg_price_reception': _avg(aggregates['total_price_reception']),
        'avg_price_sale': _avg(aggregates['total_price_sale']),
    }

    cost_breakdown = [
        {'label': 'Подготовка', 'value': aggregates['total_amount_podgotovka']},
        {'label': 'Слесарный участок', 'value': aggregates['total_amount_ss']},
        {'label': 'Кузовной участок', 'value': aggregates['total_amount_mcu']},
        {'label': 'Восстановительный ремонт', 'value': aggregates['total_amount_recovery']},
    ]

    total_cost_value = aggregates['total_amount_cost']
    for item in cost_breakdown:
        item['share'] = round((item['value'] / total_cost_value * 100), 1) if total_cost_value else 0

    per_page = 200
    page_number = _get_int(request.GET.get('page')) or 1
    paginator = Paginator(base_qs.order_by('-start_estimation'), per_page)
    page_obj = paginator.get_page(page_number)
    table_qs = page_obj.object_list

    table_data = []
    for snapshot in table_qs:
        cost_fields = {
            'podgotovka': snapshot.cost_podgotovka or 0,
            'ss': snapshot.cost_ss or 0,
            'mcu': snapshot.cost_mcu or 0,
            'recovery': snapshot.cost_recovery or 0,
        }
        table_data.append(
            {
                'id': snapshot.estimation_id,
                'start_estimation': snapshot.start_estimation,
                'unit': snapshot.unit_name or '—',
                'model': snapshot.model_name or snapshot.vin,
                'staff': snapshot.staff_name or '—',
                'analyst_before': snapshot.analyst_before_name or '—',
                'analyst_after': snapshot.analyst_after_name or '—',
                'price_before_kd': snapshot.price_before_kd or 0,
                'price_after_kd': snapshot.price_after_kd or 0,
                'price_auto_1': snapshot.price_auto_1 or 0,
                'price_auto_2': snapshot.price_auto_2 or 0,
                'price_auto_3': snapshot.price_auto_3 or 0,
                'price_auto_reference': snapshot.price_auto_selected or 0,
                'price_auto_bcp': snapshot.price_auto_bcp or 0,
                'price_bcp': snapshot.price_bcp or 0,
                'price_reception': snapshot.price_reception or 0,
                'price_sale': snapshot.price_sale or 0,
                'diff_before': snapshot.diff_before or 0,
                'diff_after': snapshot.diff_after or 0,
                'costs': cost_fields,
                'cost_total': snapshot.cost_total or 0,
                'status': snapshot.status_name or '',
            }
        )

    price_diffs = []
    price_percent_diffs = []
    higher_count = lower_count = equal_count = 0
    for price_before, auto_price in base_qs.values_list('price_before_kd', 'price_auto_selected'):
        if price_before and auto_price:
            diff = float(price_before) - float(auto_price)
            price_diffs.append(diff)
            diff_percent = round((diff / float(auto_price)) * 100, 1) if auto_price else 0
            price_percent_diffs.append(diff_percent)
            if diff > 1000:
                higher_count += 1
            elif diff < -1000:
                lower_count += 1
            else:
                equal_count += 1

    task_aggregate = base_qs.aggregate(
        total_tasks=Coalesce(Sum('tasks_total'), 0),
        closed_tasks=Coalesce(Sum('tasks_closed'), 0),
        evaluations_with_tasks=Count('estimation_id', filter=Q(tasks_total__gt=0)),
    )
    all_tasks_total = task_aggregate['total_tasks'] or 0
    all_tasks_closed = task_aggregate['closed_tasks'] or 0
    evaluations_with_tasks_count = task_aggregate['evaluations_with_tasks'] or 0
    evaluations_with_tasks_percent = (
        round((evaluations_with_tasks_count / total_count * 100), 1) if total_count else 0
    )
    avg_tasks_per_eval = (
        round(all_tasks_total / total_count, 1) if total_count and all_tasks_total else 0
    )

    units = RefUnit.objects.filter(buauto=True, active_eco=True).exclude(name='').order_by('name')
    staffs = RefStaff.objects.exclude(name='').order_by('name')
    analysts = User.objects.filter(profiles__eco=True)
    types = RefTypeReceptionCarsOrganization.objects.order_by('name')
    statuses = RefStatusEstimation.objects.order_by('name')

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_id': unit_id or '',
        'staff_id': staff_id or '',
        'analyst_id': analyst_id or '',
    }

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    base_query_string = query_params.urlencode()

    params = {
        'type': 'interactive_pricing_report',
        'nav_selected': 4,
        'request': request,
        'filters': filters,
        'summary': summary,
        'cost_breakdown': cost_breakdown,
        'table_data': table_data,
        'total_count': total_count,
        'price_comparison': {
            'avg_diff': round(sum(price_diffs) / len(price_diffs), 1) if price_diffs else 0,
            'avg_diff_percent': round(sum(price_percent_diffs) / len(price_percent_diffs), 1) if price_percent_diffs else 0,
            'higher_count': higher_count,
            'lower_count': lower_count,
            'equal_count': equal_count,
            'total_compared': len(price_diffs),
        },
        'task_stats': {
            'total_tasks': all_tasks_total,
            'evaluations_with_tasks': evaluations_with_tasks_count,
            'avg_tasks_per_eval': avg_tasks_per_eval,
            'evaluations_with_tasks_percent': evaluations_with_tasks_percent,
            'closed_tasks': all_tasks_closed,
            'open_tasks': all_tasks_total - all_tasks_closed,
            'closed_percent': round((all_tasks_closed / all_tasks_total * 100), 1) if all_tasks_total else 0,
        },
        'page_obj': page_obj,
        'paginator': paginator,
        'base_query': base_query_string,
        'units': units,
        'staffs': staffs,
        'analysts': analysts,
        'analyst_stats': analyst_stats,
    }

    return render(request, 'lo/interactive_pricing_report.html', {'params': params})


def interactive_evaluations_report(request):
    """Расширенный отчет по интерактивным оценкам и согласованию цен"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'interactive_evaluations_report',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})

    now             = (DT.datetime.now() + relativedelta(months=1)).replace(day=1) - DT.timedelta(days=1)
    default_end     = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start   = DT.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_id     = _get_int(request.GET.get('unit_id'))
    staff_id    = _get_int(request.GET.get('staff_id'))
    analyst_id  = _get_int(request.GET.get('analyst_id'))
    type_id     = _get_int(request.GET.get('type_id'))

    base_qs = InteractivePricingSnapshot.objects.filter(
        start_estimation__gte=date_start,
        start_estimation__lte=date_end,
    ).order_by('-start_estimation')

    if unit_id:
        base_qs = base_qs.filter(unit_id=unit_id)

    if staff_id:
        base_qs = base_qs.filter(staff_id=staff_id)

    if analyst_id:
        base_qs = base_qs.filter(Q(analyst_before_id=analyst_id) | Q(analyst_after_id=analyst_id))

    if type_id:
        base_qs = base_qs.filter(type_reception_id=type_id)

    total_count = base_qs.count()
    total_price_estimation_ocenshik     = base_qs.aggregate(Sum('price_reception'))['price_reception__sum'] or 0
    total_price_estimation_ocenshik_avg = base_qs.aggregate(Avg('price_reception'))['price_reception__avg'] or 0
    
    total_price_do_kd_count = base_qs.filter(price_before_kd__gte=0).count()
    total_price_do_kd       = base_qs.aggregate(Sum('price_before_kd'))['price_before_kd__sum'] or 0
    total_price_do_kd_avg   = base_qs.aggregate(Avg('price_before_kd'))['price_before_kd__avg'] or 0
    
    diff_do_kd_avg = total_price_do_kd_avg - total_price_estimation_ocenshik_avg if total_price_do_kd_avg and total_price_estimation_ocenshik_avg else 0

    total_price_after_kd_count = base_qs.filter(price_after_kd__gte=0).count()
    total_price_after_kd       = base_qs.aggregate(Sum('price_after_kd'))['price_after_kd__sum'] or 0
    total_price_after_kd_avg   = base_qs.aggregate(Avg('price_after_kd'))['price_after_kd__avg'] or 0
    diff_affter_kd_avg         = total_price_after_kd_avg - total_price_do_kd_avg if total_price_after_kd_avg and total_price_do_kd_avg else 0

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_id': unit_id or '',
        'staff_id': staff_id or '',
        'analyst_id': analyst_id or '',
        'type_id': type_id or '',
    }
    countList   = 50
    paginator   = Paginator(base_qs, countList)	
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    params = {
        'type'          : 'interactive_evaluations_report',
        'nav_selected'  : 4,
        'request'       : request,
        'filters'       : filters,
        'total_count'   : total_count,
        'total_price_estimation_ocenshik'       : total_price_estimation_ocenshik,
        'total_price_estimation_ocenshik_avg'   : total_price_estimation_ocenshik_avg,
        'total_price_do_kd' : total_price_do_kd,
        'total_price_do_kd_avg': total_price_do_kd_avg,
        'total_price_after_kd' : total_price_after_kd,
        'total_price_after_kd_avg': total_price_after_kd_avg,
        'diff_do_kd_avg'        : diff_do_kd_avg,
        'diff_affter_kd_avg'    : diff_affter_kd_avg,
        'page_obj'              : page_obj

    }

    return render(request, 'lo/interactive_evaluations_report.html', {'params': params})


def _get_op_rlk_qs(date_start, date_end, report_type, unit_source_ids, unit_ids, city_ids):
    """
    Вспомогательная функция для получения QuerySet рабочих листов ОП из DocRLK.
    Оптимизированная версия с применением фильтров и select_related для уменьшения количества запросов.
    """
    excluded_type_ids = [1,2,3, 4, 6, 7, 9, 10, 19, 21]
    op_rlk_qs = DocRLK.objects.exclude(nomer = '').exclude(type__id__in=excluded_type_ids).select_related('unit', 'unit_dc', 'unit__city', 'unit_dc__city')
    
    # Применяем фильтры по датам в зависимости от варианта отчета
    if report_type == 1:
        # Сквозной - отбор по датам событий
        op_rlk_qs = op_rlk_qs.filter(
            Q(dataTime__gte=date_start, dataTime__lte=date_end)
        )
    elif report_type == 2:
        # По рабочим листам
        op_rlk_qs = op_rlk_qs.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        )
    else:  # report_type == 3
        # По принятым - для ОП не применимо, но оставляем фильтр по дате создания
        op_rlk_qs = op_rlk_qs.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        )
    
    # Применяем фильтры по подразделениям, городам и источникам
    if unit_ids:
        op_rlk_qs = op_rlk_qs.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
    if unit_source_ids:
        names = RefUnit.objects.filter(id__in = unit_source_ids).values_list('name', flat=True)
        names_list = list()
        for name in names:
            names_list.append(name.replace('ОП ', 'ДЦ '))
        op_rlk_qs = op_rlk_qs.filter(
            Q(unit_dc__name__in=names_list) |
            Q(unit__name__in=names_list, unit_dc__isnull=True)
        )
    if city_ids:
        # Фильтруем по городам подразделений
        op_rlk_qs = op_rlk_qs.filter(
            Q(unit__city_id__in=city_ids) | Q(unit_dc__city_id__in=city_ids)
        )
    
    return op_rlk_qs


def _process_funnel_filters(date_start, date_end, report_type, unit_source_ids, unit_ids, city_ids, 
                            type_reception_ids, brand_list, staff_ids=None, analyst_ids=None, 
                            remote_filter=None, unit_source_id=None, unit_id=None, 
                            city_id=None, type_reception_id=None, brand=None, staff_id=None, analyst_id=None):
    """
    Вспомогательная функция для обработки одного набора фильтров воронки Trade-In.
    Возвращает все вычисленные данные для отображения.
    
    Параметры:
    - remote_filter: None (все), 'with' (с дистанционной оценкой), 'without' (без дистанционной оценки)
    """
    from refs.models import RefCity
    
    # Обратная совместимость с одиночными фильтрами
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if brand and brand not in brand_list:
        brand_list.append(brand)
    if staff_id and (not staff_ids or staff_id not in staff_ids):
        if staff_ids is None:
            staff_ids = []
        staff_ids.append(staff_id)
    if analyst_id and (not analyst_ids or analyst_id not in analyst_ids):
        if analyst_ids is None:
            analyst_ids = []
        analyst_ids.append(analyst_id)
    
    # Базовый QuerySet с фильтрами
    base_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры
    if unit_source_ids:
        base_qs = base_qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        base_qs = base_qs.filter(unit_id__in=unit_ids)
    if city_ids:
        base_qs = base_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        base_qs = base_qs.filter(type_reception_id__in=type_reception_ids)
    if brand_list:
        # Фильтр по списку брендов (строки)
        brand_q = Q()
        for b in brand_list:
            brand_q |= Q(brand__icontains=b)
        base_qs = base_qs.filter(brand_q)
    
    # Применяем фильтры по оценщикам (staff_id)
    if staff_ids:
        base_qs = base_qs.filter(staff_id__in=staff_ids)
    
    # Применяем фильтры по аналитикам (analyst_remote_id, analyst_before_id, analyst_after_id)
    if analyst_ids:
        analyst_q = Q()
        analyst_q |= Q(analyst_remote_id__in=analyst_ids)
        analyst_q |= Q(analyst_before_id__in=analyst_ids)
        analyst_q |= Q(analyst_after_id__in=analyst_ids)
        base_qs = base_qs.filter(analyst_q)
    
    # Определяем QuerySet в зависимости от варианта отчета
    if report_type == 1:
        # Сквозной - отбор по датам событий
        qs = base_qs.filter(
            Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
            Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
            Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
            Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
            Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
        )
        # qs = base_qs.filter(
        #     Q(date_rlk__gte=date_start, date_rlk__lte=date_end)
        #    )
    elif report_type == 2:
        # По рабочим листам
        qs = base_qs.filter(
            date_rlk__gte=date_start,
            date_rlk__lte=date_end
        )
    else:  # report_type == 3
        # По принятым
        qs = base_qs.filter(
            date_reception_success__gte=date_start,
            date_reception_success__lte=date_end
        )
    
    # Получаем данные для "Рабочие листы ОП" из DocRLK (оптимизированно)
    op_rlk_qs = _get_op_rlk_qs(date_start, date_end, report_type, unit_source_ids, unit_ids, city_ids)
    total_op_rlk = op_rlk_qs.count()
    
    # Дата для исключения некорректных дат (1.1.1)
    date_invalid = DT.date(1, 1, 1)
    
    # Вспомогательные Q-объекты для проверки валидных дат (не null и не 1.1.1)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    
    # Оптимизированный подсчет общих показателей одним запросом
    # Принятые без интерактивной оценки: date_reception_success валидна, но date_after_success отсутствует или равна 1.1.1
    reception_without_interactive = Q(valid_date_reception) & (
        Q(date_after_success__isnull=True) | Q(date_after_success=date_invalid)
    )
    
    totals_agg = qs.aggregate(
        total_rlk=Count('rlk_id', filter=valid_date_rlk),
        total_before=Count('rlk_id', filter=valid_date_before | valid_date_remote),
        total_after=Count('rlk_id', filter=valid_date_after),
        total_reception=Count('rlk_id', filter=valid_date_reception),
        total_reception_without_interactive=Count('rlk_id', filter=reception_without_interactive),
        total_taxi=Count('rlk_id', filter=Q(taxi=True)),
        total_carsharing=Count('rlk_id', filter=Q(carsharing=True)),
        total_iznos=Count('rlk_id', filter=Q(iznos=True)),
        total_auction=Count('rlk_id', filter=Q(auction=True)),
        total_no_diag=Count('rlk_id', filter=Q(diagostica=False) & valid_date_after),
        total_all=Count('rlk_id'),
    )
    
    total_op_rlk = total_op_rlk or 0  # Уже вычислено выше
    total_rlk = totals_agg['total_rlk'] or 0
    total_before = totals_agg['total_before'] or 0
    total_after = totals_agg['total_after'] or 0
    total_reception = totals_agg['total_reception'] or 0
    total_reception_without_interactive = totals_agg['total_reception_without_interactive'] or 0
    total_taxi = totals_agg['total_taxi'] or 0
    total_carsharing = totals_agg['total_carsharing'] or 0
    total_iznos = totals_agg['total_iznos'] or 0
    total_auction = totals_agg['total_auction'] or 0
    total_no_diag = totals_agg['total_no_diag'] or 0
    total_all = totals_agg['total_all'] or 0
    
    # Проценты
    conv_op_to_tradein = (total_rlk / total_op_rlk * 100) if total_op_rlk > 0 else 0
    conv_before = (total_before / total_rlk * 100) if total_rlk > 0 else 0
    conv_after = (total_after / total_before * 100) if total_before > 0 else 0
    conv_reception = (total_reception / total_after * 100) if total_after > 0 else 0
    
    taxi_pct = (total_taxi / total_all * 100) if total_all > 0 else 0
    carsharing_pct = (total_carsharing / total_all * 100) if total_all > 0 else 0
    iznos_pct = (total_iznos / total_all * 100) if total_all > 0 else 0
    auction_pct = (total_auction / total_all * 100) if total_all > 0 else 0
    no_diag_pct = (total_no_diag / total_all * 100) if total_all > 0 else 0
    
    # Статистика по типам приема
    type_reception_stats = list(qs.values('type_reception_id', 'type_reception_name').annotate(
        total=Count('rlk_id'),
        before=Count('rlk_id', filter=valid_date_before | valid_date_remote),
        after=Count('rlk_id', filter=valid_date_after),
        reception=Count('rlk_id', filter=valid_date_reception)
    ).order_by('type_reception_name'))
    
    # Для типов приема op_rlk будет 0, так как в DocRLK нет type_reception_id
    for stat in type_reception_stats:
        stat['op_rlk'] = 0  # В DocRLK нет type_reception_id
        stat['conv_op_to_tradein'] = 0
        stat['conv_before'] = (stat['before'] / stat['total'] * 100) if stat['total'] > 0 else 0
        stat['conv_after'] = (stat['after'] / stat['before'] * 100) if stat['before'] > 0 else 0
        stat['conv_reception'] = (stat['reception'] / stat['after'] * 100) if stat['after'] > 0 else 0
        if not stat['type_reception_name']:
            stat['type_reception_name'] = 'Не указан'
    
    # Итоги для статистики по типам приема
    type_reception_totals = {
        'type_reception_name': 'Итого',
        'op_rlk': total_op_rlk,  # Общее количество ОП для всех типов приема
        'total': sum(s['total'] for s in type_reception_stats),
        'before': sum(s['before'] for s in type_reception_stats),
        'after': sum(s['after'] for s in type_reception_stats),
        'reception': sum(s['reception'] for s in type_reception_stats),
    }
    type_reception_totals['conv_op_to_tradein'] = (type_reception_totals['total'] / type_reception_totals['op_rlk'] * 100) if type_reception_totals['op_rlk'] > 0 else 0
    type_reception_totals['conv_before'] = (type_reception_totals['before'] / type_reception_totals['total'] * 100) if type_reception_totals['total'] > 0 else 0
    type_reception_totals['conv_after'] = (type_reception_totals['after'] / type_reception_totals['before'] * 100) if type_reception_totals['before'] > 0 else 0
    type_reception_totals['conv_reception'] = (type_reception_totals['reception'] / type_reception_totals['after'] * 100) if type_reception_totals['after'] > 0 else 0
    
    # Статистика по ценовым группам
    price_group_stats_raw = list(qs.exclude(zg_name='').values('zg_name').annotate(
        total=Count('rlk_id'),
        before=Count('rlk_id', filter=valid_date_before | valid_date_remote),
        after=Count('rlk_id', filter=valid_date_after),
        reception=Count('rlk_id', filter=valid_date_reception)
    ))
    
    # Функция для извлечения числового значения из названия ценовой группы
    def get_price_group_order(zg_name):
        if not zg_name:
            return 9999
        numbers = zg_name.replace(' ', '').replace('+', '1')
        if numbers:
            num = int(numbers)
            if '5000+' in zg_name or '5000 +' in zg_name:
                return 5001
            return num
        return 9999
    
    # Сортируем по числовому значению
    price_group_stats = sorted(price_group_stats_raw, key=lambda x: get_price_group_order(x['zg_name']))
    
    # Для ценовых групп op_rlk будет 0, так как в DocRLK нет zg_name
    for stat in price_group_stats:
        stat['op_rlk'] = 0  # В DocRLK нет zg_name
        stat['conv_op_to_tradein'] = 0
        stat['conv_before'] = (stat['before'] / stat['total'] * 100) if stat['total'] > 0 else 0
        stat['conv_after'] = (stat['after'] / stat['before'] * 100) if stat['before'] > 0 else 0
        stat['conv_reception'] = (stat['reception'] / stat['after'] * 100) if stat['after'] > 0 else 0
    
    # Итоги для статистики по ценовым группам
    price_group_totals = {
        'zg_name': 'Итого',
        'op_rlk': total_op_rlk,  # Общее количество ОП для всех ценовых групп
        'total': sum(s['total'] for s in price_group_stats),
        'before': sum(s['before'] for s in price_group_stats),
        'after': sum(s['after'] for s in price_group_stats),
        'reception': sum(s['reception'] for s in price_group_stats),
    }
    price_group_totals['conv_op_to_tradein'] = (price_group_totals['total'] / price_group_totals['op_rlk'] * 100) if price_group_totals['op_rlk'] > 0 else 0
    price_group_totals['conv_before'] = (price_group_totals['before'] / price_group_totals['total'] * 100) if price_group_totals['total'] > 0 else 0
    price_group_totals['conv_after'] = (price_group_totals['after'] / price_group_totals['before'] * 100) if price_group_totals['before'] > 0 else 0
    price_group_totals['conv_reception'] = (price_group_totals['reception'] / price_group_totals['after'] * 100) if price_group_totals['after'] > 0 else 0
    
    # Статистика по городам
    city_stats = list(qs.exclude(city_name='').values('city_name', 'city_id').annotate(
        total=Count('rlk_id'),
        before=Count('rlk_id', filter=valid_date_before | valid_date_remote),
        after=Count('rlk_id', filter=valid_date_after),
        reception=Count('rlk_id', filter=valid_date_reception)
    ).order_by('city_name'))
    
    # Получаем статистику по городам для op_rlk из DocRLK
    from refs.models import RefCity
    op_rlk_city_stats = {}
    
    # Группируем op_rlk по городам через unit__city и unit_dc__city
    op_rlk_city_data = op_rlk_qs.values('unit__city_id', 'unit_dc__city_id').annotate(
        count=Count('id')
    )
    
    for city_stat in op_rlk_city_data:
        city_id = city_stat.get('unit__city_id') or city_stat.get('unit_dc__city_id')
        if city_id:
            if city_id not in op_rlk_city_stats:
                op_rlk_city_stats[city_id] = 0
            op_rlk_city_stats[city_id] += city_stat['count']
    
    # Добавляем op_rlk к статистике по городам
    for stat in city_stats:
        city_id = stat.get('city_id')
        stat['op_rlk'] = op_rlk_city_stats.get(city_id, 0) if city_id else 0
        stat['conv_op_to_tradein'] = (stat['total'] / stat['op_rlk'] * 100) if stat['op_rlk'] > 0 else 0
        stat['conv_before'] = (stat['before'] / stat['total'] * 100) if stat['total'] > 0 else 0
        stat['conv_after'] = (stat['after'] / stat['before'] * 100) if stat['before'] > 0 else 0
        stat['conv_reception'] = (stat['reception'] / stat['after'] * 100) if stat['after'] > 0 else 0
    
    # Итоги для статистики по городам
    city_totals = {
        'city_name': 'Итого',
        'op_rlk': total_op_rlk,
        'total': sum(s['total'] for s in city_stats),
        'before': sum(s['before'] for s in city_stats),
        'after': sum(s['after'] for s in city_stats),
        'reception': sum(s['reception'] for s in city_stats),
    }
    city_totals['conv_op_to_tradein'] = (city_totals['total'] / city_totals['op_rlk'] * 100) if city_totals['op_rlk'] > 0 else 0
    city_totals['conv_before'] = (city_totals['before'] / city_totals['total'] * 100) if city_totals['total'] > 0 else 0
    city_totals['conv_after'] = (city_totals['after'] / city_totals['before'] * 100) if city_totals['before'] > 0 else 0
    city_totals['conv_reception'] = (city_totals['reception'] / city_totals['after'] * 100) if city_totals['after'] > 0 else 0
    
    # Статистика по брендам
    brand_stats = list(qs.exclude(brand='').values('brand').annotate(
        total=Count('rlk_id'),
        before=Count('rlk_id', filter=valid_date_before | valid_date_remote),
        after=Count('rlk_id', filter=valid_date_after),
        reception=Count('rlk_id', filter=valid_date_reception)
    ).order_by('brand'))
    
    # Для брендов op_rlk будет 0, так как в DocRLK нет brand
    for stat in brand_stats:
        stat['op_rlk'] = 0  # В DocRLK нет brand
        stat['conv_op_to_tradein'] = 0
        stat['conv_before'] = (stat['before'] / stat['total'] * 100) if stat['total'] > 0 else 0
        stat['conv_after'] = (stat['after'] / stat['before'] * 100) if stat['before'] > 0 else 0
        stat['conv_reception'] = (stat['reception'] / stat['after'] * 100) if stat['after'] > 0 else 0
    
    # Итоги для статистики по брендам
    brand_totals = {
        'brand': 'Итого',
        'op_rlk': total_op_rlk,  # Общее количество ОП для всех брендов
        'total': sum(s['total'] for s in brand_stats),
        'before': sum(s['before'] for s in brand_stats),
        'after': sum(s['after'] for s in brand_stats),
        'reception': sum(s['reception'] for s in brand_stats),
    }
    brand_totals['conv_op_to_tradein'] = (brand_totals['total'] / brand_totals['op_rlk'] * 100) if brand_totals['op_rlk'] > 0 else 0
    brand_totals['conv_before'] = (brand_totals['before'] / brand_totals['total'] * 100) if brand_totals['total'] > 0 else 0
    brand_totals['conv_after'] = (brand_totals['after'] / brand_totals['before'] * 100) if brand_totals['before'] > 0 else 0
    brand_totals['conv_reception'] = (brand_totals['reception'] / brand_totals['after'] * 100) if brand_totals['after'] > 0 else 0
    
    # Статистика по оценщикам
    staff_stats = list(qs.exclude(staff_id__isnull=True).values('staff_id', 'staff_name').annotate(
        total=Count('rlk_id'),
        before=Count('rlk_id', filter=valid_date_before | valid_date_remote),
        after=Count('rlk_id', filter=valid_date_after),
        reception=Count('rlk_id', filter=valid_date_reception)
    ).order_by('staff_name'))
    
    # Для оценщиков op_rlk будет 0, так как в DocRLK нет staff_id
    for stat in staff_stats:
        stat['op_rlk'] = 0  # В DocRLK нет staff_id
        stat['conv_op_to_tradein'] = 0
        stat['conv_before'] = (stat['before'] / stat['total'] * 100) if stat['total'] > 0 else 0
        stat['conv_after'] = (stat['after'] / stat['before'] * 100) if stat['before'] > 0 else 0
        stat['conv_reception'] = (stat['reception'] / stat['after'] * 100) if stat['after'] > 0 else 0
        if not stat['staff_name']:
            stat['staff_name'] = 'Не указан'
    
    # Итоги для статистики по оценщикам
    staff_totals = {
        'staff_name': 'Итого',
        'op_rlk': total_op_rlk,  # Общее количество ОП для всех оценщиков
        'total': sum(s['total'] for s in staff_stats),
        'before': sum(s['before'] for s in staff_stats),
        'after': sum(s['after'] for s in staff_stats),
        'reception': sum(s['reception'] for s in staff_stats),
    }
    staff_totals['conv_op_to_tradein'] = (staff_totals['total'] / staff_totals['op_rlk'] * 100) if staff_totals['op_rlk'] > 0 else 0
    staff_totals['conv_before'] = (staff_totals['before'] / staff_totals['total'] * 100) if staff_totals['total'] > 0 else 0
    staff_totals['conv_after'] = (staff_totals['after'] / staff_totals['before'] * 100) if staff_totals['before'] > 0 else 0
    staff_totals['conv_reception'] = (staff_totals['reception'] / staff_totals['after'] * 100) if staff_totals['after'] > 0 else 0
    
    # График по дням
    from datetime import timedelta
    date_list = []
    current_date = date_start.date() if hasattr(date_start, 'date') else date_start
    end_date = date_end.date() if hasattr(date_end, 'date') else date_end
    
    while current_date <= end_date:
        date_list.append(current_date.strftime('%d.%m.%Y'))
        current_date += timedelta(days=1)
    
    date_fields = [
        ('date_rlk', 'rlk'),
        ('date_start_estimation', 'estimation'),
        ('date_remote_success', 'remote'),
        ('date_before_success', 'before'),
        ('date_diagnostic_success', 'diagnostic'),
        ('date_after_success', 'after'),
        ('date_reception_success', 'reception'),
    ]
    
    chart_datasets = {
        'op_rlk': [0] * len(date_list),
        'rlk': [0] * len(date_list),
        'estimation': [0] * len(date_list),
        'remote': [0] * len(date_list),
        'before': [0] * len(date_list),
        'diagnostic': [0] * len(date_list),
        'after': [0] * len(date_list),
        'reception': [0] * len(date_list),
    }
    
    # График для "Рабочие листы ОП" из DocRLK
    date_invalid_chart = DT.date(1, 1, 1)
    op_rlk_daily_counts = op_rlk_qs.annotate(
        day=TruncDate('dataTime')
    ).values('day').annotate(count=Count('id'))
    
    for item in op_rlk_daily_counts:
        if item['day']:
            day_str = item['day'].strftime('%d.%m.%Y') if hasattr(item['day'], 'strftime') else str(item['day'])
            if day_str in date_list:
                idx = date_list.index(day_str)
                chart_datasets['op_rlk'][idx] = item['count']
    
    # Графики для остальных этапов из TradeInFunnel
    for field_name, key in date_fields:
        daily_counts = qs.filter(
            **{f'{field_name}__isnull': False}
        ).exclude(
            **{field_name: date_invalid_chart}
        ).annotate(
            day=TruncDate(field_name)
        ).values('day').annotate(count=Count('rlk_id'))
        
        for item in daily_counts:
            if item['day']:
                day_str = item['day'].strftime('%d.%m.%Y') if hasattr(item['day'], 'strftime') else str(item['day'])
                if day_str in date_list:
                    idx = date_list.index(day_str)
                    chart_datasets[key][idx] = item['count']
    
    chart_data_json = json.dumps({
        'labels': date_list,
        'datasets': [
            {'label': 'РЛ ОП', 'data': chart_datasets['op_rlk'], 'borderColor': '#6366f1', 'backgroundColor': 'rgba(99, 102, 241, 0.1)'},
            {'label': 'РЛ Trade-in', 'data': chart_datasets['rlk'], 'borderColor': '#002c63', 'backgroundColor': 'rgba(0, 44, 99, 0.1)'},
            {'label': 'Оценка', 'data': chart_datasets['estimation'], 'borderColor': '#00509d', 'backgroundColor': 'rgba(0, 80, 157, 0.1)'},
            {'label': 'Дистанционно', 'data': chart_datasets['remote'], 'borderColor': '#ff8a00', 'backgroundColor': 'rgba(255, 138, 0, 0.1)'},
            {'label': 'До КД', 'data': chart_datasets['before'], 'borderColor': '#ffd500', 'backgroundColor': 'rgba(255, 213, 0, 0.1)'},
            {'label': 'Диагностика', 'data': chart_datasets['diagnostic'], 'borderColor': '#22c55e', 'backgroundColor': 'rgba(34, 197, 94, 0.1)'},
            {'label': 'После КД', 'data': chart_datasets['after'], 'borderColor': '#f97316', 'backgroundColor': 'rgba(249, 115, 22, 0.1)'},
            {'label': 'Принято', 'data': chart_datasets['reception'], 'borderColor': '#dc2626', 'backgroundColor': 'rgba(220, 38, 38, 0.1)'},
        ]
    })
    
    # Возвращаем все данные
    return {
        'totals': {
            'op_rlk': total_op_rlk,
            'rlk': total_rlk,
            'before': total_before,
            'after': total_after,
            'reception': total_reception,
            'reception_without_interactive': total_reception_without_interactive,
            'conv_op_to_tradein': conv_op_to_tradein,
            'conv_before': conv_before,
            'conv_after': conv_after,
            'conv_reception': conv_reception,
        },
        'badges': {
            'taxi': {'count': total_taxi, 'percent': taxi_pct},
            'carsharing': {'count': total_carsharing, 'percent': carsharing_pct},
            'iznos': {'count': total_iznos, 'percent': iznos_pct},
            'auction': {'count': total_auction, 'percent': auction_pct},
            'no_diag': {'count': total_no_diag, 'percent': no_diag_pct},
        },
        'type_reception_stats': type_reception_stats,
        'type_reception_totals': type_reception_totals,
        'price_group_stats': price_group_stats,
        'price_group_totals': price_group_totals,
        'city_stats': city_stats,
        'city_totals': city_totals,
        'brand_stats': brand_stats,
        'brand_totals': brand_totals,
        'staff_stats': staff_stats,
        'staff_totals': staff_totals,
        'chart_data': chart_data_json,
        'chart_datasets': chart_datasets,  # Для режима сравнения
        'chart_labels': date_list,  # Для режима сравнения
    }


def tradein_funnel_analytics(request):
    """Новая воронка Trade-In на основе модели TradeInFunnel - оптимизированная версия с поддержкой сравнения"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    # if not request.user.profiles.eco and not request.user.profiles.eco_visible  and not request.user.profiles.korsavto_settings_dc:
    #     params = {
    #         'type': 'eco_funnel',
    #         'nav_selected': 4,
    #         'request': request,
    #     }
    #     return render(request, 'errors/403.html', {'params': params})

    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)

    # Парсим основной фильтр
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    report_type = _get_int(request.GET.get('report_type', 1)) or 1
    
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    brands_str = request.GET.get('brands', '').strip()
    brand_list = [b.strip() for b in brands_str.split(',') if b.strip()] if brands_str else []
    
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    brand = request.GET.get('brand', '').strip()
    
    # Парсим новые фильтры
    staff_ids = _parse_multiple_ints(request.GET.get('staff_ids', ''))
    analyst_ids = _parse_multiple_ints(request.GET.get('analyst_ids', ''))
    remote_filter = request.GET.get('remote_filter', '').strip()  # '', 'with', 'without'
    if remote_filter not in ['with', 'without']:
        remote_filter = None
    
    # Одиночные фильтры (для обратной совместимости)
    staff_id = _get_int(request.GET.get('staff_id'))
    analyst_id = _get_int(request.GET.get('analyst_id'))
    
    # Если передан одиночный фильтр, добавляем его в множественный
    if staff_id and staff_id not in staff_ids:
        staff_ids.append(staff_id)
    if analyst_id and analyst_id not in analyst_ids:
        analyst_ids.append(analyst_id)
    
    # Обрабатываем основной фильтр
    main_data = _process_funnel_filters(
        date_start, date_end, report_type,
        unit_source_ids, unit_ids, city_ids, type_reception_ids, brand_list,
        staff_ids=staff_ids, analyst_ids=analyst_ids, remote_filter=remote_filter,
        unit_source_id=unit_source_id, unit_id=unit_id, city_id=city_id, 
        type_reception_id=type_reception_id, brand=brand, staff_id=staff_id, analyst_id=analyst_id
    )
    
    # Проверяем режим сравнения
    compare_mode = request.GET.get('compare', '') == '1'
    compare_data = None
    
    if compare_mode:
        # Парсим фильтр для сравнения
        compare_date_start = _parse_date(request.GET.get('compare_date_start', ''), default_start, is_end=False)
        compare_date_end = _parse_date(request.GET.get('compare_date_end', ''), default_end, is_end=True)
        compare_report_type = _get_int(request.GET.get('compare_report_type', 1)) or 1
        
        compare_unit_source_ids = _parse_multiple_ints(request.GET.get('compare_unit_source_ids', ''))
        compare_unit_ids = _parse_multiple_ints(request.GET.get('compare_unit_ids', ''))
        compare_city_ids = _parse_multiple_ints(request.GET.get('compare_city_ids', ''))
        compare_type_reception_ids = _parse_multiple_ints(request.GET.get('compare_type_reception_ids', ''))
        compare_brands_str = request.GET.get('compare_brands', '').strip()
        compare_brand_list = [b.strip() for b in compare_brands_str.split(',') if b.strip()] if compare_brands_str else []
        
        compare_unit_source_id = _get_int(request.GET.get('compare_unit_source_id'))
        compare_unit_id = _get_int(request.GET.get('compare_unit_id'))
        compare_city_id = _get_int(request.GET.get('compare_city_id'))
        compare_type_reception_id = _get_int(request.GET.get('compare_type_reception_id'))
        compare_brand = request.GET.get('compare_brand', '').strip()
        
        # Парсим новые фильтры для сравнения
        compare_staff_ids = _parse_multiple_ints(request.GET.get('compare_staff_ids', ''))
        compare_analyst_ids = _parse_multiple_ints(request.GET.get('compare_analyst_ids', ''))
        compare_remote_filter = request.GET.get('compare_remote_filter', '').strip()  # '', 'with', 'without'
        if compare_remote_filter not in ['with', 'without']:
            compare_remote_filter = None
        
        compare_staff_id = _get_int(request.GET.get('compare_staff_id'))
        compare_analyst_id = _get_int(request.GET.get('compare_analyst_id'))
        
        # Если передан одиночный фильтр для сравнения, добавляем его в множественный
        if compare_staff_id and compare_staff_id not in compare_staff_ids:
            compare_staff_ids.append(compare_staff_id)
        if compare_analyst_id and compare_analyst_id not in compare_analyst_ids:
            compare_analyst_ids.append(compare_analyst_id)
        
        # Обрабатываем фильтр для сравнения
        compare_data = _process_funnel_filters(
            compare_date_start, compare_date_end, compare_report_type,
            compare_unit_source_ids, compare_unit_ids, compare_city_ids, compare_type_reception_ids, compare_brand_list,
            staff_ids=compare_staff_ids, analyst_ids=compare_analyst_ids, remote_filter=compare_remote_filter,
            unit_source_id=compare_unit_source_id, unit_id=compare_unit_id, city_id=compare_city_id, 
            type_reception_id=compare_type_reception_id, brand=compare_brand, staff_id=compare_staff_id, analyst_id=compare_analyst_id
        )
    
    # Загружаем справочники для фильтров (используем основной QuerySet для получения доступных значений)
    # Создаем базовый QuerySet для получения справочников
    base_qs_for_refs = TradeInFunnel.objects.all()
    
    # Если выбраны города, фильтруем подразделения и источники по этим городам
    if city_ids:
        unit_ids_from_cities = list(base_qs_for_refs.filter(city_id__in=city_ids).exclude(unit_id__isnull=True).values_list('unit_id', flat=True).distinct())
        units = RefUnit.objects.filter(id__in=unit_ids_from_cities, buauto=True, active_eco=True).exclude(name='').order_by('name') if unit_ids_from_cities else RefUnit.objects.none()
        
        source_unit_ids = list(base_qs_for_refs.filter(city_id__in=city_ids).exclude(unit_source_id__isnull=True).values_list('unit_source_id', flat=True).distinct())
        source_units = RefUnit.objects.filter(id__in=source_unit_ids).exclude(name='').order_by('name') if source_unit_ids else RefUnit.objects.none()
    else:
        units = RefUnit.objects.filter(buauto=True, active_eco=True).exclude(name='').order_by('name')
        
        source_unit_ids = list(base_qs_for_refs.exclude(unit_source_id__isnull=True).values_list('unit_source_id', flat=True).distinct())
        source_units = RefUnit.objects.filter(id__in=source_unit_ids).exclude(name='').order_by('name') if source_unit_ids else RefUnit.objects.none()
    
    # Получаем уникальные города из TradeInFunnel
    from refs.models import RefCity
    city_ids_from_funnel = list(base_qs_for_refs.exclude(city_id__isnull=True).values_list('city_id', flat=True).distinct())
    cities = RefCity.objects.filter(id__in=city_ids_from_funnel).exclude(name='').order_by('name') if city_ids_from_funnel else RefCity.objects.none()
    
    # Получаем уникальные бренды
    brands_list = list(base_qs_for_refs.exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand'))
    
    # Получаем уникальные типы приема
    type_reception_ids_from_funnel = list(base_qs_for_refs.exclude(type_reception_id__isnull=True).values_list('type_reception_id', flat=True).distinct())
    type_receptions = RefTypeReceptionCarsOrganization.objects.filter(id__in=type_reception_ids_from_funnel).exclude(name='').order_by('name') if type_reception_ids_from_funnel else RefTypeReceptionCarsOrganization.objects.none()
    
    # Получаем уникальных оценщиков (staff)
    # Загружаем всех оценщиков для фильтра (независимо от текущих фильтров)
    from refs.models import RefStaff
    # Загружаем всех оценщиков, которые есть в TradeInFunnel, или всех, если funnel пустой
    staff_ids_from_funnel = list(base_qs_for_refs.exclude(staff_id__isnull=True).values_list('staff_id', flat=True).distinct())
    if staff_ids_from_funnel:
        staffs = RefStaff.objects.filter(id__in=staff_ids_from_funnel).exclude(name='').order_by('name')
    else:
        # Если нет данных в funnel, загружаем всех оценщиков
        staffs = RefStaff.objects.exclude(name='').order_by('name')
    
    # Получаем уникальных аналитиков (из analyst_after_id, analyst_before_id, analyst_remote_id)
    # Загружаем всех аналитиков для фильтра (независимо от текущих фильтров)
    analyst_ids_from_funnel = set()
    analyst_ids_from_funnel.update(base_qs_for_refs.exclude(analyst_after_id__isnull=True).values_list('analyst_after_id', flat=True).distinct())
    analyst_ids_from_funnel.update(base_qs_for_refs.exclude(analyst_before_id__isnull=True).values_list('analyst_before_id', flat=True).distinct())
    analyst_ids_from_funnel.update(base_qs_for_refs.exclude(analyst_remote_id__isnull=True).values_list('analyst_remote_id', flat=True).distinct())
    if analyst_ids_from_funnel:
        analysts = Profiles.objects.filter(id__in=list(analyst_ids_from_funnel)).exclude(eco_name='').order_by('eco_name')
    else:
        # Если нет данных в funnel, загружаем всех аналитиков
        # В TradeInFunnel аналитики хранятся как RefStaff (ID из RefStaff)
        analysts = Profiles.objects.filter(eco=True).order_by('eco_name')
    
    # Создаем словари для связи городов с подразделениями и источниками (для JavaScript фильтрации)
    city_unit_map = {}
    city_source_unit_map = {}
    
    city_unit_data = base_qs_for_refs.exclude(city_id__isnull=True, unit_id__isnull=True).values('city_id', 'unit_id').distinct()
    for item in city_unit_data:
        c_id = item['city_id']
        u_id = item['unit_id']
        if c_id not in city_unit_map:
            city_unit_map[c_id] = []
        if u_id not in city_unit_map[c_id]:
            city_unit_map[c_id].append(u_id)
    
    city_source_unit_data = base_qs_for_refs.exclude(city_id__isnull=True, unit_source_id__isnull=True).values('city_id', 'unit_source_id').distinct()
    for item in city_source_unit_data:
        c_id = item['city_id']
        s_id = item['unit_source_id']
        if c_id not in city_source_unit_map:
            city_source_unit_map[c_id] = []
        if s_id not in city_source_unit_map[c_id]:
            city_source_unit_map[c_id].append(s_id)
    
    # Формируем params на основе main_data
    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'filters': {
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
            'report_type': report_type,
            'unit_source_id': unit_source_id or '',
            'unit_source_ids': ','.join(map(str, unit_source_ids)) if unit_source_ids else '',
            'unit_source_ids_list': unit_source_ids,
            'unit_id': unit_id or '',
            'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
            'unit_ids_list': unit_ids,
            'city_id': city_id or '',
            'city_ids': ','.join(map(str, city_ids)) if city_ids else '',
            'city_ids_list': city_ids,
            'type_reception_id': type_reception_id or '',
            'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
            'type_reception_ids_list': type_reception_ids,
            'brand': brand,
            'brands': ','.join(brand_list) if brand_list else '',
            'brands_list': brand_list,
            'staff_id': staff_id or '',
            'staff_ids': ','.join(map(str, staff_ids)) if staff_ids else '',
            'staff_ids_list': staff_ids,
            'analyst_id': analyst_id or '',
            'analyst_ids': ','.join(map(str, analyst_ids)) if analyst_ids else '',
            'analyst_ids_list': analyst_ids,
            'remote_filter': remote_filter or '',
        },
        'units': units,
        'source_units': source_units,
        'cities': cities,
        'type_receptions': type_receptions,
        'brands': brands_list,
        'staffs': staffs,
        'analysts': analysts,
        'city_unit_map': city_unit_map,
        'city_source_unit_map': city_source_unit_map,
        'compare_mode': compare_mode,
    }
    
    # Добавляем данные из main_data
    params.update(main_data)
    
    # Добавляем данные для сравнения, если режим сравнения активен
    if compare_mode and compare_data:
        params['compare_data'] = compare_data
        params['filters'].update({
            'compare_date_start': compare_date_start.strftime('%Y-%m-%d'),
            'compare_date_end': compare_date_end.strftime('%Y-%m-%d'),
            'compare_report_type': compare_report_type,
            'compare_unit_source_ids': ','.join(map(str, compare_unit_source_ids)) if compare_unit_source_ids else '',
            'compare_unit_ids': ','.join(map(str, compare_unit_ids)) if compare_unit_ids else '',
            'compare_city_ids': ','.join(map(str, compare_city_ids)) if compare_city_ids else '',
            'compare_type_reception_ids': ','.join(map(str, compare_type_reception_ids)) if compare_type_reception_ids else '',
            'compare_brands': ','.join(compare_brand_list) if compare_brand_list else '',
            'compare_staff_ids': ','.join(map(str, compare_staff_ids)) if compare_staff_ids else '',
            'compare_staff_ids_list': compare_staff_ids or [],
            'compare_analyst_ids': ','.join(map(str, compare_analyst_ids)) if compare_analyst_ids else '',
            'compare_analyst_ids_list': compare_analyst_ids or [],
            'compare_remote_filter': compare_remote_filter or '',
        })
    
    # Все вычисления уже выполнены в _process_funnel_filters и добавлены в params через params.update(main_data)
    
    # Добавляем расчет эффективности дистанционной оценки
    # Создаем базовый QuerySet с примененными фильтрами
    date_invalid = DT.date(1, 1, 1)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    
    # Создаем QuerySet с теми же фильтрами, что и в main_data
    funnel_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры по датам в зависимости от report_type
    if report_type == 1:
        funnel_qs = funnel_qs.filter(
            Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
            Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
            Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
            Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
            Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
        )
    elif report_type == 2:
        funnel_qs = funnel_qs.filter(
            date_rlk__gte=date_start,
            date_rlk__lte=date_end
        )
    else:  # report_type == 3
        funnel_qs = funnel_qs.filter(
            date_reception_success__gte=date_start,
            date_reception_success__lte=date_end
        )
    
    # Применяем остальные фильтры
    if unit_source_ids:
        funnel_qs = funnel_qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        funnel_qs = funnel_qs.filter(unit_id__in=unit_ids)
    if city_ids:
        funnel_qs = funnel_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        funnel_qs = funnel_qs.filter(type_reception_id__in=type_reception_ids)
    if brand_list:
        brand_q = Q()
        for b in brand_list:
            brand_q |= Q(brand__icontains=b)
        funnel_qs = funnel_qs.filter(brand_q)
    if staff_ids:
        funnel_qs = funnel_qs.filter(staff_id__in=staff_ids)
    if analyst_ids:
        analyst_q = Q()
        for a_id in analyst_ids:
            analyst_q |= Q(analyst_remote_id=a_id) | Q(analyst_before_id=a_id) | Q(analyst_after_id=a_id)
        funnel_qs = funnel_qs.filter(analyst_q)
    if remote_filter == 'with':
        funnel_qs = funnel_qs.filter(valid_date_remote)
    elif remote_filter == 'without':
        funnel_qs = funnel_qs.exclude(valid_date_remote)
    
    # Подсчет эффективности дистанционной оценки
    remote_effectiveness = {
        'total_remote': funnel_qs.filter(valid_date_remote).count(),
        'got_price_before': funnel_qs.filter(valid_date_remote, valid_date_before).count(),
        'got_price_after': funnel_qs.filter(valid_date_remote, valid_date_after).count(),
        'accepted': funnel_qs.filter(valid_date_remote, valid_date_reception).count(),
    }
    
    # Проценты конверсии
    if remote_effectiveness['total_remote'] > 0:
        remote_effectiveness['conv_to_before'] = round(remote_effectiveness['got_price_before'] / remote_effectiveness['total_remote'] * 100, 1)
        remote_effectiveness['conv_to_after'] = round(remote_effectiveness['got_price_after'] / remote_effectiveness['total_remote'] * 100, 1)
        remote_effectiveness['conv_to_accepted'] = round(remote_effectiveness['accepted'] / remote_effectiveness['total_remote'] * 100, 1)
    else:
        remote_effectiveness['conv_to_before'] = 0
        remote_effectiveness['conv_to_after'] = 0
        remote_effectiveness['conv_to_accepted'] = 0
    
    params['remote_effectiveness'] = remote_effectiveness
    
    return render(request, 'lo/tradein_funnel_analytics.html', {'params': params})


def tradein_funnel_analytics_export(request):
    """Экспорт данных в Excel для блоков воронки Trade-In Analytics"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    # if not request.user.profiles.eco and not request.user.profiles.eco_visible:
    #     return HttpResponseRedirect('/')
    
    export_type = request.GET.get('export_type', '')  # op_rlk, rlk, before, after, reception, reception_price_list
    
    if export_type not in ['op_rlk', 'rlk', 'before', 'after', 'reception', 'reception_price_list']:
        return HttpResponse('Неверный тип экспорта', status=400)
    
    # Парсим параметры фильтров (аналогично tradein_funnel_analytics)
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    # Вариант отчета
    report_type = _get_int(request.GET.get('report_type', 1)) or 1
    
    # Фильтры - множественный выбор
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    brands_str = request.GET.get('brands', '').strip()
    brand_list = [b.strip() for b in brands_str.split(',') if b.strip()] if brands_str else []
    
    # Обратная совместимость с одиночными фильтрами
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    brand = request.GET.get('brand', '').strip()
    
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if brand and brand not in brand_list:
        brand_list.append(brand)
    
    # Базовый QuerySet с фильтрами
    base_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры
    if unit_source_ids:
        base_qs = base_qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        base_qs = base_qs.filter(unit_id__in=unit_ids)
    if city_ids:
        base_qs = base_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        base_qs = base_qs.filter(type_reception_id__in=type_reception_ids)
    if brand_list:
        # Фильтр по списку брендов (строки)
        brand_q = Q()
        for b in brand_list:
            brand_q |= Q(brand__icontains=b)
        base_qs = base_qs.filter(brand_q)
    
    # Определяем QuerySet в зависимости от варианта отчета
    if report_type == 1:
        # Сквозной - отбор по датам событий
        qs = base_qs.filter(
            Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
            Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
            Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
            Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
            Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
        )
    elif report_type == 2:
        # По рабочим листам
        qs = base_qs.filter(
            date_rlk__gte=date_start,
            date_rlk__lte=date_end
        )
    else:  # report_type == 3
        # По принятым
        qs = base_qs.filter(
            date_reception_success__gte=date_start,
            date_reception_success__lte=date_end
        )
    
    # Определяем QuerySet для экспорта в зависимости от типа экспорта
    date_invalid = DT.date(1, 1, 1)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    
    # Фильтруем данные в зависимости от типа экспорта
    if export_type == 'op_rlk':
        # Рабочие листы ОП - данные из DocRLK (оптимизированно)
        op_rlk_qs = _get_op_rlk_qs(date_start, date_end, report_type, unit_source_ids, unit_ids, city_ids)
        export_data = op_rlk_qs.select_related('unit', 'unit_dc').annotate(
            rlk_number=F('nomer'),
            date_rlk=F('dataTime'),
            unit_id=F('unit__id'),
            unit_name=F('unit__name'),
            unit_source_id=Case(
                When(unit_dc__isnull=False, then=F('unit_dc__id')),
                default=F('unit__id')
            ),
            unit_source_name=Case(
                When(unit_dc__isnull=False, then=F('unit_dc__name')),
                default=F('unit__name')
            ),
            vin_trade_in=F('vin_trade_in'),
            vin=Value('', output_field=CharField()),  # Для ОП VIN может быть пустым
        ).values(
            'rlk_number',
            'date_rlk',
            'vin_trade_in',
            'vin',
            'unit_id',
            'unit_name',
            'unit_source_id',
            'unit_source_name'
        ).order_by('dataTime', 'nomer')
    elif export_type == 'rlk':
        export_qs = qs.filter(valid_date_rlk)
        export_data = export_qs.values(
            'rlk_number',
            'date_rlk',
            'vin_trade_in',
            'vin',
            'unit_id',
            'unit_name',
            'unit_source_id',
            'unit_source_name'
        ).order_by('date_rlk', 'rlk_number')
    elif export_type == 'before':
        export_qs = qs.filter(valid_date_before | valid_date_remote)
        export_data = export_qs.values(
            'rlk_number',
            'date_rlk',
            'vin_trade_in',
            'vin',
            'unit_id',
            'unit_name',
            'unit_source_id',
            'unit_source_name'
        ).order_by('date_rlk', 'rlk_number')
    elif export_type == 'after':
        export_qs = qs.filter(valid_date_after)
        export_data = export_qs.values(
            'rlk_number',
            'date_rlk',
            'vin_trade_in',
            'vin',
            'unit_id',
            'unit_name',
            'unit_source_id',
            'unit_source_name'
        ).order_by('date_rlk', 'rlk_number')
    elif export_type == 'reception':
        export_qs = qs.filter(valid_date_reception)
        export_data = export_qs.values(
            'rlk_number',
            'date_rlk',
            'vin_trade_in',
            'vin',
            'unit_id',
            'unit_name',
            'unit_source_id',
            'unit_source_name'
        ).order_by('date_rlk', 'rlk_number')
    elif export_type == 'reception_price_list':
        export_qs = qs.filter(valid_date_reception)
        export_data = export_qs.values(
            'date_rlk',
            'rlk_number',
            'unit_name',
            'unit_source_name',
            'vin',
            'vin_trade_in',
            'date_reception_success',
            'lo_number'
        ).order_by('date_reception_success', 'rlk_number')
    else:
        # Если тип экспорта не распознан, возвращаем ошибку
        return HttpResponse('Неверный тип экспорта', status=400)
    
    # Создаем Excel файл
    from django.http import HttpResponse
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    if export_type == 'reception_price_list':
        filename = 'Прайс_лист.xlsx'
    elif export_type == 'op_rlk':
        filename = 'export_op_rlk.xlsx'
    else:
        filename = f'export_{export_type}.xlsx'
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb = Workbook()
    ws = wb.active
    
    if export_type == 'reception_price_list':
        ws.title = "Прайс лист"
        headers = [
            'Дата рабочего листа',
            'Номер рабочего листа',
            'Подразделение ДЦ наименование',
            'Источник наименование',
            'VIN',
            'Дата принятия',
            'Номер листа оценки'
        ]
        ws.append(headers)
        
        for item in export_data:
            vin_value = item.get('vin', '') or item.get('vin_trade_in', '')
            unit_source_display = item.get('unit_source_name', '') or item.get('unit_name', '')
            ws.append([
                item.get('date_rlk', '') if item.get('date_rlk') else '',
                item.get('rlk_number', ''),
                item.get('unit_name', ''),
                unit_source_display,
                vin_value,
                item.get('date_reception_success', '') if item.get('date_reception_success') else '',
                item.get('lo_number', ''),
            ])
    else:
        # Общие заголовки для op_rlk, rlk, before, after, reception
        headers = [
            'Номер рабочего листа',
            'Дата рабочего листа',
            'VIN Trade-In',
            'VIN',
            'ID подразделения',
            'Подразделение',
            'ID источника',
            'Источник'
        ]
        ws.append(headers)
        
        for item in export_data:
            ws.append([
                item.get('rlk_number', ''),
                item.get('date_rlk', '') if item.get('date_rlk') else '',
                item.get('vin_trade_in', '') or '',
                item.get('vin', '') or '',
                item.get('unit_id', '') or '',
                item.get('unit_name', '') or '',
                item.get('unit_source_id', '') or '',
                item.get('unit_source_name', '') or '',
            ])
    
    wb.save(response)
    return response


def tradein_funnel_analytics_detail(request):
    """Детальная информация по фильтру воронки Trade-In Analytics"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    # if not request.user.profiles.eco and not request.user.profiles.eco_visible and not request.user.profiles.korsavto_settings_dc:
    #     params = {
    #         'type': 'eco_funnel',
    #         'nav_selected': 4,
    #         'request': request,
    #     }
    #     return render(request, 'errors/403.html', {'params': params})
    
    # Тип фильтра для детальной страницы
    filter_type = request.GET.get('filter_type', '')
    
    if not filter_type:
        return HttpResponse('Не указан тип фильтра', status=400)
    
    # Парсим параметры фильтров (аналогично tradein_funnel_analytics)
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    # Вариант отчета
    report_type = _get_int(request.GET.get('report_type', 1)) or 1
    
    # Фильтры - множественный выбор
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    brands_str = request.GET.get('brands', '').strip()
    brand_list = [b.strip() for b in brands_str.split(',') if b.strip()] if brands_str else []
    
    # Обратная совместимость с одиночными фильтрами
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    brand = request.GET.get('brand', '').strip()
    
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if brand and brand not in brand_list:
        brand_list.append(brand)
    
    # Базовый QuerySet с фильтрами
    base_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры
    if unit_source_ids:
        base_qs = base_qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        base_qs = base_qs.filter(unit_id__in=unit_ids)
    if city_ids:
        base_qs = base_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        base_qs = base_qs.filter(type_reception_id__in=type_reception_ids)
    if brand_list:
        brand_q = Q()
        for b in brand_list:
            brand_q |= Q(brand__icontains=b)
        base_qs = base_qs.filter(brand_q)
    
    # Определяем QuerySet в зависимости от варианта отчета
    if report_type == 1:
        qs = base_qs.filter(
            Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
            Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
            Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
            Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
            Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
        )
    elif report_type == 2:
        qs = base_qs.filter(
            date_rlk__gte=date_start,
            date_rlk__lte=date_end
        )
    else:  # report_type == 3
        qs = base_qs.filter(
            date_reception_success__gte=date_start,
            date_reception_success__lte=date_end
        )
    
    # Дата для исключения некорректных дат (1.1.1)
    date_invalid = DT.date(1, 1, 1)
    
    # Вспомогательные Q-объекты для проверки валидных дат
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    
    # Применяем фильтр в зависимости от типа
    if filter_type == 'op_rlk':
        # Рабочие листы ОП - данные из DocRLK (оптимизированно с пагинацией на уровне QuerySet)
        op_rlk_qs = _get_op_rlk_qs(date_start, date_end, report_type, unit_source_ids, unit_ids, city_ids)
        op_rlk_qs = op_rlk_qs.select_related('unit', 'unit_dc', 'unit__city', 'unit_dc__city').order_by('-dataTime', '-id')
        
        # Пагинация на уровне QuerySet (оптимально)
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        page = request.GET.get('page', 1)
        paginator = Paginator(op_rlk_qs, 50)
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        filter_title = 'Рабочие листы ОП'
        total_count = paginator.count
        
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'filter_type': filter_type,
            'filter_title': filter_title,
            'total_count': total_count,
            'page_obj': page_obj,
            'op_rlk_data': True,  # Флаг для шаблона
            'filters': {
                'date_start': date_start.strftime('%Y-%m-%d'),
                'date_end': date_end.strftime('%Y-%m-%d'),
                'report_type': report_type,
            },
        }
        
        return render(request, 'lo/tradein_funnel_analytics_detail.html', {'params': params})
    elif filter_type == 'rlk':
        qs = qs.filter(valid_date_rlk)
        filter_title = 'Рабочие листы Trade-in'
    elif filter_type == 'before':
        qs = qs.filter(valid_date_before | valid_date_remote)
        filter_title = 'До КД / Дистанционно'
    elif filter_type == 'after':
        qs = qs.filter(valid_date_after)
        filter_title = 'После КД'
    elif filter_type == 'reception':
        qs = qs.filter(valid_date_reception)
        filter_title = 'Принято'
    elif filter_type == 'taxi':
        qs = qs.filter(taxi=True)
        filter_title = 'Такси'
    elif filter_type == 'carsharing':
        qs = qs.filter(carsharing=True)
        filter_title = 'Каршеринг'
    elif filter_type == 'iznos':
        qs = qs.filter(iznos=True)
        filter_title = 'Повышенный износ'
    elif filter_type == 'auction':
        qs = qs.filter(auction=True)
        filter_title = 'Аукцион'
    elif filter_type == 'no_diag':
        qs = qs.filter(Q(diagostica=False) & valid_date_after)
        filter_title = 'Без диагностики'
    elif filter_type == 'remote_below':
        qs = qs.filter(comparison_remote_type=-1)
        filter_title = 'Дистанционная оценка ниже авторасчета'
    elif filter_type == 'remote_equal':
        qs = qs.filter(comparison_remote_type=0)
        filter_title = 'Дистанционная оценка равна авторасчету'
    elif filter_type == 'remote_above':
        qs = qs.filter(comparison_remote_type=1)
        filter_title = 'Дистанционная оценка выше авторасчета'
    elif filter_type == 'before_below':
        qs = qs.filter(comparison_before_type=-1)
        filter_title = 'До КД ниже авторасчета'
    elif filter_type == 'before_equal':
        qs = qs.filter(comparison_before_type=0)
        filter_title = 'До КД равна авторасчету'
    elif filter_type == 'before_above':
        qs = qs.filter(comparison_before_type=1)
        filter_title = 'До КД выше авторасчета'
    elif filter_type == 'after_below':
        qs = qs.filter(comparison_after_type=-1)
        filter_title = 'После КД ниже авторасчета'
    elif filter_type == 'after_equal':
        qs = qs.filter(comparison_after_type=0)
        filter_title = 'После КД равна авторасчету'
    elif filter_type == 'after_above':
        qs = qs.filter(comparison_after_type=1)
        filter_title = 'После КД выше авторасчета'
    elif filter_type == 'rejected_before':
        # Не дошли до КД / Дистанционной оценки
        qs = qs.filter(valid_date_rlk).exclude(
            valid_date_before | valid_date_remote
        )
        filter_title = 'Не дошли до КД / Дистанционной оценки'
    elif filter_type == 'rejected_after':
        # Не дошли до после КД
        qs = qs.filter(
            valid_date_before | valid_date_remote
        ).exclude(valid_date_after)
        filter_title = 'Не дошли до после КД'
    elif filter_type == 'rejected_reception':
        # Не приняты
        qs = qs.filter(valid_date_after).exclude(valid_date_reception)
        filter_title = 'Не приняты'
    else:
        return HttpResponse('Неверный тип фильтра', status=400)
    
    # Получаем данные для отображения
    total_count = qs.count()
    
    # Пагинация
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    page = request.GET.get('page', 1)
    paginator = Paginator(qs.order_by('-rlk_id'), 50)  # Сортируем по rlk_id для стабильности
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Если page_obj пустой, но total_count > 0, переходим на первую страницу
    if not page_obj and total_count > 0:
        page_obj = paginator.page(1)
    
    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'filter_type': filter_type,
        'filter_title': filter_title,
        'total_count': total_count,
        'page_obj': page_obj,
        'filters': {
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
            'report_type': report_type,
        },
    }
    
    return render(request, 'lo/tradein_funnel_analytics_detail.html', {'params': params})
# УДАЛЕНО: функция tradein_funnel_analytics_rejected больше не используется, заменена на tradein_funnel_rejected


#История изменений
def get_versions(table, id):
	return ChangeLog.objects.filter(model = table).filter(record_id = id).order_by('changed')


def tradein_funnel_analytics_export(request):
    """Экспорт данных в Excel для блоков воронки Trade-In Analytics"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    # if not request.user.profiles.eco and not request.user.profiles.eco_visible:
    #     return HttpResponseRedirect('/')
    
    export_type = request.GET.get('export_type', '')  # op_rlk, rlk, before, after, reception, reception_price_list
    
    if export_type not in ['op_rlk', 'rlk', 'before', 'after', 'reception', 'reception_price_list']:
        return HttpResponse('Неверный тип экспорта', status=400)
    
    # Парсим параметры фильтров (аналогично tradein_funnel_analytics)
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    # Вариант отчета
    report_type = _get_int(request.GET.get('report_type', 1)) or 1
    
    # Фильтры - множественный выбор
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    brands_str = request.GET.get('brands', '').strip()
    brand_list = [b.strip() for b in brands_str.split(',') if b.strip()] if brands_str else []
    
    # Обратная совместимость с одиночными фильтрами
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    brand = request.GET.get('brand', '').strip()
    
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if brand and brand not in brand_list:
        brand_list.append(brand)
    
    # Базовый QuerySet с фильтрами
    base_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры
    if unit_source_ids:
        base_qs = base_qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        base_qs = base_qs.filter(unit_id__in=unit_ids)
    if city_ids:
        base_qs = base_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        base_qs = base_qs.filter(type_reception_id__in=type_reception_ids)
    if brand_list:
        # Фильтр по списку брендов (строки)
        brand_q = Q()
        for b in brand_list:
            brand_q |= Q(brand__icontains=b)
        base_qs = base_qs.filter(brand_q)
    
    # Определяем QuerySet в зависимости от варианта отчета
    if report_type == 1:
        # Сквозной - отбор по датам событий
        qs = base_qs.filter(
            Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
            Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
            Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
            Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
            Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
        )
    elif report_type == 2:
        # По рабочим листам
        qs = base_qs.filter(
            date_rlk__gte=date_start,
            date_rlk__lte=date_end
        )
    else:  # report_type == 3
        # По принятым
        qs = base_qs.filter(
            date_reception_success__gte=date_start,
            date_reception_success__lte=date_end
        )
    
    # Дата для исключения некорректных дат (1.1.1)
    date_invalid = DT.date(1, 1, 1)
    
    # Вспомогательные Q-объекты для проверки валидных дат (не null и не 1.1.1)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    
    # Фильтруем по типу экспорта
    if export_type == 'rlk':
        # Рабочие листы
        export_qs = qs.filter(valid_date_rlk)
    elif export_type == 'before':
        # До КД / Дистанционно
        export_qs = qs.filter(valid_date_before | valid_date_remote)
    elif export_type == 'after':
        # После КД
        export_qs = qs.filter(valid_date_after)
    elif export_type == 'reception_price_list':
        # Прайс-лист для принятых (специальный формат)
        export_qs = qs.filter(valid_date_reception)
    else:  # export_type == 'reception'
        # Принято
        export_qs = qs.filter(valid_date_reception)
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    
    # Название листа в зависимости от типа экспорта
    sheet_names = {
        'rlk': 'Рабочие листы',
        'before': 'До КД / Дистанционно',
        'after': 'После КД',
        'reception': 'Принято',
        'reception_price_list': 'Прайс лист'
    }
    ws.title = sheet_names.get(export_type, 'Экспорт')
    
    # Специальная обработка для прайс-листа
    if export_type == 'reception_price_list':
        # Получаем данные для прайс-листа
        export_data = export_qs.values(
            'date_rlk',
            'rlk_number',
            'unit_name',
            'unit_source_name',
            'vin',
            'vin_trade_in',
            'date_reception_success',
            'lo_number'
        ).order_by('date_reception_success', 'rlk_number')
        
        # Заголовки для прайс-листа
        headers = [
            'Дата',
            'Номер',
            'Подразделение ДЦ',
            'Источник',
            'VIN',
            'Дата принятия',
            'Номер листа оценки'
        ]
        ws.append(headers)
        
        # Данные для прайс-листа
        for item in export_data:
            # Используем vin, если есть, иначе vin_trade_in
            vin_value = item.get('vin', '') or item.get('vin_trade_in', '')
            # Для источника: если unit_source_name пустое, берем unit_name
            unit_source_value = item.get('unit_source_name', '') or item.get('unit_name', '')
            ws.append([
                item.get('date_rlk', '') if item.get('date_rlk') else '',
                item.get('rlk_number', ''),
                unit_source_value,
                unit_source_value,
                vin_value,
                item.get('date_reception_success', '') if item.get('date_reception_success') else '',
                item.get('lo_number', ''),
            ])
    else:
        # Стандартный экспорт для других типов
        export_data = export_qs.values(
            'rlk_number',
            'date_rlk',
            'vin_trade_in',
            'vin',
            'unit_id',
            'unit_name',
            'unit_source_id',
            'unit_source_name'
        ).order_by('date_rlk', 'rlk_number')
        
        # Заголовки
        headers = ['Номер РЛ', 'Дата РЛ', 'VIN Trade-In', 'VIN', 'Подразделение ID', 'Подразделение', 'Источник ID', 'Источник']
        ws.append(headers)
        
        # Данные
        for item in export_data:
            ws.append([
                item.get('rlk_number', ''),
                item.get('date_rlk', '') if item.get('date_rlk') else '',
                item.get('vin_trade_in', ''),
                item.get('vin', ''),
                item.get('unit_id', '') if item.get('unit_id') else '',
                item.get('unit_name', ''),
                item.get('unit_source_id', '') if item.get('unit_source_id') else '',
                item.get('unit_source_name', ''),
            ])
    
    # Формируем ответ
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    export_names = {
        'rlk': 'Рабочие_листы',
        'before': 'До_КД_Дистанционно',
        'after': 'После_КД',
        'reception': 'Принято',
        'reception_price_list': 'Прайс_лист'
    }
    
    filename = f"export_{export_names.get(export_type, export_type)}_{date_start.strftime('%Y%m%d')}_{date_end.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response


def tradein_funnel_analytics_detail(request):
    """Детальная страница с данными воронки Trade-In Analytics по выбранному критерию"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    # Тип фильтра для детальной страницы
    filter_type = request.GET.get('filter_type', '')
    
    if not filter_type:
        return HttpResponse('Не указан тип фильтра', status=400)
    
    # Парсим параметры фильтров (аналогично tradein_funnel_analytics)
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    # Вариант отчета
    report_type = _get_int(request.GET.get('report_type', 1)) or 1
    
    # Фильтры - множественный выбор
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    brands_str = request.GET.get('brands', '').strip()
    brand_list = [b.strip() for b in brands_str.split(',') if b.strip()] if brands_str else []
    
    # Обратная совместимость с одиночными фильтрами
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    brand = request.GET.get('brand', '').strip()
    
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if brand and brand not in brand_list:
        brand_list.append(brand)
    
    # Базовый QuerySet с фильтрами
    base_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры
    if unit_source_ids:
        base_qs = base_qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        base_qs = base_qs.filter(unit_id__in=unit_ids)
    if city_ids:
        base_qs = base_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        base_qs = base_qs.filter(type_reception_id__in=type_reception_ids)
    if brand_list:
        brand_q = Q()
        for b in brand_list:
            brand_q |= Q(brand__icontains=b)
        base_qs = base_qs.filter(brand_q)
    
    # Определяем QuerySet в зависимости от варианта отчета
    if report_type == 1:
        qs = base_qs.filter(
            Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
            Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
            Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
            Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
            Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
        )
    elif report_type == 2:
        qs = base_qs.filter(
            date_rlk__gte=date_start,
            date_rlk__lte=date_end
        )
    else:  # report_type == 3
        qs = base_qs.filter(
            date_reception_success__gte=date_start,
            date_reception_success__lte=date_end
        )
    # Дата для исключения некорректных дат (1.1.1)
    date_invalid = DT.date(1, 1, 1)
    
    # Вспомогательные Q-объекты для проверки валидных дат (не null и не 1.1.1)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    
    # Применяем дополнительный фильтр по типу
    filter_title = ''
    if filter_type == 'op_rlk':
        # Рабочие листы ОП - данные из DocRLK (оптимизированно с пагинацией на уровне QuerySet)
        op_rlk_qs = _get_op_rlk_qs(date_start, date_end, report_type, unit_source_ids, unit_ids, city_ids)
        op_rlk_qs = op_rlk_qs.select_related('unit', 'unit_dc', 'unit__city', 'unit_dc__city').order_by('-dataTime', '-id')
        
        # Пагинация на уровне QuerySet (оптимально)
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        page = request.GET.get('page', 1)
        paginator = Paginator(op_rlk_qs, 50)
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        filter_title = 'Рабочие листы ОП'
        total_count = paginator.count
        
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'filter_type': filter_type,
            'filter_title': filter_title,
            'total_count': total_count,
            'page_obj': page_obj,
            'op_rlk_data': True,  # Флаг для шаблона
            'filters': {
                'date_start': date_start.strftime('%Y-%m-%d'),
                'date_end': date_end.strftime('%Y-%m-%d'),
                'report_type': report_type,
            },
        }
        
        return render(request, 'lo/tradein_funnel_analytics_detail.html', {'params': params})
    elif filter_type == 'rlk':
        qs = qs.filter(valid_date_rlk)
        filter_title = 'Рабочие листы Trade-in'
    elif filter_type == 'before':
        qs = qs.filter(valid_date_before | valid_date_remote)
        filter_title = 'До КД / Дистанционно'
    elif filter_type == 'after':
        qs = qs.filter(valid_date_after)
        filter_title = 'После КД'
    elif filter_type == 'reception':
        qs = qs.filter(valid_date_reception)
        filter_title = 'Принято'
    elif filter_type == 'taxi':
        qs = qs.filter(taxi=True)
        filter_title = 'Такси'
    elif filter_type == 'carsharing':
        qs = qs.filter(carsharing=True)
        filter_title = 'Каршеринг'
    elif filter_type == 'iznos':
        qs = qs.filter(iznos=True)
        filter_title = 'Повышенный износ'
    elif filter_type == 'auction':
        qs = qs.filter(auction=True)
        filter_title = 'Аукцион'
    elif filter_type == 'no_diag':
        qs = qs.filter(Q(diagostica=False) & valid_date_after) 
        filter_title = 'Без диагностики'
    elif filter_type == 'remote_below':
        # Дистанционная оценка: date_remote_success заполнено и не равно 1,1,1
        qs = qs.filter(valid_date_remote, comparison_remote_type=-1)
        filter_title = 'Дистанционная оценка - Ниже авторасчета'
    elif filter_type == 'remote_equal':
        qs = qs.filter(valid_date_remote, comparison_remote_type=0)
        filter_title = 'Дистанционная оценка - Равно авторасчету'
    elif filter_type == 'remote_above':
        qs = qs.filter(valid_date_remote, comparison_remote_type=1)
        filter_title = 'Дистанционная оценка - Выше авторасчета'
    elif filter_type == 'before_below':
        # До КД: date_before_success указана и больше даты 1,1,1
        qs = qs.filter(valid_date_before, comparison_before_type=-1)
        filter_title = 'До КД - Ниже авторасчета'
    elif filter_type == 'before_equal':
        qs = qs.filter(valid_date_before, comparison_before_type=0)
        filter_title = 'До КД - Равно авторасчету'
    elif filter_type == 'before_above':
        qs = qs.filter(valid_date_before, comparison_before_type=1)
        filter_title = 'До КД - Выше авторасчета'
    elif filter_type == 'after_below':
        # После КД: date_after_success заполнены и не равны дате 1,1,1
        qs = qs.filter(valid_date_after, comparison_after_type=-1)
        filter_title = 'После КД - Ниже авторасчета'
    elif filter_type == 'after_equal':
        qs = qs.filter(valid_date_after, comparison_after_type=0)
        filter_title = 'После КД - Равно авторасчету'
    elif filter_type == 'after_above':
        qs = qs.filter(valid_date_after, comparison_after_type=1)
        filter_title = 'После КД - Выше авторасчета'
    elif filter_type == 'rejected_before':
        # Не дошли до КД/дистанционной оценки
        qs = qs.filter(valid_date_rlk).exclude(
            valid_date_before | valid_date_remote
        )
        filter_title = 'Не дошли до КД / Дистанционной оценки'
    elif filter_type == 'rejected_after':
        # Не дошли до после КД
        qs = qs.filter(
            valid_date_before | valid_date_remote
        ).exclude(valid_date_after)
        filter_title = 'Не дошли до после КД'
    elif filter_type == 'rejected_reception':
        # Не приняты
        qs = qs.filter(valid_date_after).exclude(
            valid_date_reception
        )
        filter_title = 'Не приняты'
    elif filter_type == 'analyst_remote':
        # Дистанционная оценка аналитика
        analyst_id = _get_int(request.GET.get('analyst_id'))
        if analyst_id:
            qs = qs.filter(analyst_remote_id=analyst_id).filter(valid_date_remote)
            filter_title = f'Дистанционная оценка аналитика (ID: {analyst_id})'
        else:
            return HttpResponse('Не указан ID аналитика', status=400)
    elif filter_type == 'analyst_before':
        # До КД аналитика
        analyst_id = _get_int(request.GET.get('analyst_id'))
        if analyst_id:
            qs = qs.filter(analyst_before_id=analyst_id).filter(valid_date_before)
            filter_title = f'До КД аналитика (ID: {analyst_id})'
        else:
            return HttpResponse('Не указан ID аналитика', status=400)
    elif filter_type == 'analyst_after':
        # После КД аналитика
        analyst_id = _get_int(request.GET.get('analyst_id'))
        if analyst_id:
            qs = qs.filter(analyst_after_id=analyst_id).filter(valid_date_after)
            filter_title = f'После КД аналитика (ID: {analyst_id})'
        else:
            return HttpResponse('Не указан ID аналитика', status=400)
    elif filter_type == 'staff_rlk':
        # Рабочие листы оценщика
        staff_id = _get_int(request.GET.get('staff_id'))
        if staff_id:
            qs = qs.filter(staff_id=staff_id).filter(valid_date_rlk)
            filter_title = f'Рабочие листы оценщика (ID: {staff_id})'
        else:
            return HttpResponse('Не указан ID оценщика', status=400)
    elif filter_type == 'staff_reception':
        # Принятые оценщиком
        staff_id = _get_int(request.GET.get('staff_id'))
        if staff_id:
            qs = qs.filter(staff_id=staff_id).filter(valid_date_reception)
            filter_title = f'Принятые оценщиком (ID: {staff_id})'
        else:
            return HttpResponse('Не указан ID оценщика', status=400)
    else:
        return HttpResponse('Неверный тип фильтра', status=400)
    
    # Получаем общее количество до пагинации
    total_count = qs.count()
    
    # Получаем данные для таблицы с сортировкой
    # Сортируем по rlk_id (всегда есть) в обратном порядке
    # Используем values() для получения всех нужных полей
    items = qs.order_by('-rlk_id')
    
    # Пагинация
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    try:
        page_number = int(request.GET.get('page', 1))
        if page_number < 1:
            page_number = 1
    except (ValueError, TypeError):
        page_number = 1
    
    paginator = Paginator(items, 50)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # Если page не является целым числом, показываем первую страницу
        page_obj = paginator.get_page(1)
    except EmptyPage:
        # Если page вне диапазона, показываем последнюю страницу
        page_obj = paginator.get_page(paginator.num_pages)
    except Exception as e:
        # В случае другой ошибки возвращаем первую страницу
        page_obj = paginator.get_page(1)
    
    # Проверяем, что page_obj содержит данные
    # Если нет, пытаемся получить данные напрямую
    if total_count > 0 and len(page_obj) == 0:
        # Пробуем получить данные без пагинации для отладки
        test_items = list(items[:5])
        # Если тестовые данные есть, значит проблема в пагинации
        # В этом случае создаем пагинатор заново
        if test_items:
            paginator = Paginator(items, 50)
            page_obj = paginator.get_page(1)
    
    # ОПТИМИЗАЦИЯ: Вычисляем цены для каждого элемента в page_obj
    # Логика: согласованная цена (ЕЦО) - price_after > 0, иначе price_before > 0, иначе price_remote
    # Авторасчет - price_auto_after > 0, иначе price_auto_before > 0, иначе price_auto_remote
    from decimal import Decimal
    for item in page_obj:
        # Согласованная цена (ЕЦО)
        if item.price_after and item.price_after > 0:
            item.agreed_price = item.price_after
        elif item.price_before and item.price_before > 0:
            item.agreed_price = item.price_before
        elif item.price_remote and item.price_remote > 0:
            item.agreed_price = item.price_remote
        else:
            item.agreed_price = None
        
        # Цена авторасчета
        if item.price_auto_after and item.price_auto_after > 0:
            item.auto_price = item.price_auto_after
        elif item.price_auto_before and item.price_auto_before > 0:
            item.auto_price = item.price_auto_before
        elif item.price_auto_remote and item.price_auto_remote > 0:
            item.auto_price = item.price_auto_remote
        else:
            item.auto_price = None
        
        # Разница в процентах
        if item.agreed_price and item.auto_price and item.auto_price > 0:
            try:
                diff_percent = ((item.agreed_price - item.auto_price) / item.auto_price) * 100
                item.price_diff_percent = diff_percent
            except:
                item.price_diff_percent = None
        else:
            item.price_diff_percent = None
    
    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'filter_type': filter_type,
        'filter_title': filter_title,
        'page_obj': page_obj,
        'total_count': total_count,
        'filters': {
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
            'report_type': report_type,
        },
    }
    
    return render(request, 'lo/tradein_funnel_analytics_detail.html', {'params': params})
# УДАЛЕНО: функция tradein_funnel_analytics_rejected больше не используется, заменена на tradein_funnel_rejected


def eco_analysts_performance(request):
    """Анализ эффективности аналитиков на основе TradeInFunnel"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    # Парсим фильтры
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    analyst_ids = _parse_multiple_ints(request.GET.get('analyst_ids', ''))
    
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    analyst_id = _get_int(request.GET.get('analyst_id'))
    
    # Обратная совместимость
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if analyst_id and analyst_id not in analyst_ids:
        analyst_ids.append(analyst_id)
    
    # Базовый QuerySet
    base_qs = TradeInFunnel.objects.all()
    
    # QuerySet для справочников (без фильтров по источникам и подразделениям)
    refs_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры по датам (сквозной отчет)
    qs = base_qs.filter(
        Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
        Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
        Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
        Q(date_after_success__gte=date_start, date_after_success__lte=date_end)
    )
    
    if unit_source_ids:
        qs = qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        qs = qs.filter(unit_id__in=unit_ids)
    if city_ids:
        qs = qs.filter(city_id__in=city_ids)
        refs_qs = refs_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        qs = qs.filter(type_reception_id__in=type_reception_ids)
        refs_qs = refs_qs.filter(type_reception_id__in=type_reception_ids)
    if analyst_ids:
        qs = qs.filter(
            Q(analyst_remote_id__in=analyst_ids) |
            Q(analyst_before_id__in=analyst_ids) |
            Q(analyst_after_id__in=analyst_ids)
        )
    
    # Дата для исключения некорректных дат (1.1.1)
    date_invalid = DT.date(1, 1, 1)
    
    # Вспомогательные Q-объекты для проверки валидных дат
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    
    # Получаем всех уникальных аналитиков
    analyst_ids_remote = set(qs.exclude(analyst_remote_id__isnull=True).values_list('analyst_remote_id', flat=True).distinct())
    analyst_ids_before = set(qs.exclude(analyst_before_id__isnull=True).values_list('analyst_before_id', flat=True).distinct())
    analyst_ids_after = set(qs.exclude(analyst_after_id__isnull=True).values_list('analyst_after_id', flat=True).distinct())
    all_analyst_ids_set = analyst_ids_remote | analyst_ids_before | analyst_ids_after
    
    analyst_stats = []
    
    for analyst_id_val in all_analyst_ids_set:
        if analyst_id_val is None or analyst_id_val == 0:
            continue
        
        # Получаем имя аналитика
        analyst_name = None
        analyst_name_obj = qs.filter(
            Q(analyst_remote_id=analyst_id_val) | Q(analyst_before_id=analyst_id_val) | Q(analyst_after_id=analyst_id_val)
        ).exclude(
            Q(analyst_remote_name='') & Q(analyst_before_name='') & Q(analyst_after_name='')
        ).first()
        
        if analyst_name_obj:
            if analyst_name_obj.analyst_remote_id == analyst_id_val and analyst_name_obj.analyst_remote_name:
                analyst_name = analyst_name_obj.analyst_remote_name
            elif analyst_name_obj.analyst_before_id == analyst_id_val and analyst_name_obj.analyst_before_name:
                analyst_name = analyst_name_obj.analyst_before_name
            elif analyst_name_obj.analyst_after_id == analyst_id_val and analyst_name_obj.analyst_after_name:
                analyst_name = analyst_name_obj.analyst_after_name
        
        if not analyst_name:
            analyst_name = f'Аналитик #{analyst_id_val}'
        
        # Фильтруем по аналитику
        analyst_qs = qs.filter(
            Q(analyst_remote_id=analyst_id_val) | Q(analyst_before_id=analyst_id_val) | Q(analyst_after_id=analyst_id_val)
        )
        
        # Подсчеты для дистанционной оценки
        remote_qs = analyst_qs.filter(Q(analyst_remote_id=analyst_id_val) & valid_date_remote)
        remote_count = remote_qs.count()
        remote_below = remote_qs.filter(comparison_remote_type=-1).count()
        remote_equal = remote_qs.filter(comparison_remote_type=0).count()
        remote_above = remote_qs.filter(comparison_remote_type=1).count()
        remote_avg_price = remote_qs.aggregate(avg=Avg('price_remote'))['avg'] or 0
        remote_avg_auto = remote_qs.aggregate(avg=Avg('price_auto_remote'))['avg'] or 0
        
        # Подсчеты для до КД
        before_qs = analyst_qs.filter(Q(analyst_before_id=analyst_id_val) & valid_date_before)
        before_count = before_qs.count()
        before_below = before_qs.filter(comparison_before_type=-1).count()
        before_equal = before_qs.filter(comparison_before_type=0).count()
        before_above = before_qs.filter(comparison_before_type=1).count()
        before_avg_price = before_qs.aggregate(avg=Avg('price_before'))['avg'] or 0
        before_avg_auto = before_qs.aggregate(avg=Avg('price_auto_before'))['avg'] or 0
        
        # Подсчеты для после КД
        after_qs = analyst_qs.filter(Q(analyst_after_id=analyst_id_val) & valid_date_after)
        after_count = after_qs.count()
        after_below = after_qs.filter(comparison_after_type=-1).count()
        after_equal = after_qs.filter(comparison_after_type=0).count()
        after_above = after_qs.filter(comparison_after_type=1).count()
        after_avg_price = after_qs.aggregate(avg=Avg('price_after'))['avg'] or 0
        after_avg_auto = after_qs.aggregate(avg=Avg('price_auto_after'))['avg'] or 0
        
        # Общее количество оценок
        total_estimations = remote_count + before_count + after_count
        
        # Статистика по подразделениям
        units_stats = list(analyst_qs.exclude(unit_id__isnull=True).values('unit_id', 'unit_name').annotate(
            count=Count('rlk_id', distinct=True)
        ).order_by('-count')[:10])
        
        # Статистика по типам приема
        type_reception_stats = list(analyst_qs.exclude(type_reception_id__isnull=True).values('type_reception_id', 'type_reception_name').annotate(
            count=Count('rlk_id', distinct=True)
        ).order_by('-count')[:10])
        
        analyst_stats.append({
            'analyst_id': analyst_id_val,
            'analyst_name': analyst_name,
            'total_estimations': total_estimations,
            'remote': {
                'count': remote_count,
                'below': remote_below,
                'equal': remote_equal,
                'above': remote_above,
                'avg_price': remote_avg_price,
                'avg_auto': remote_avg_auto,
            },
            'before': {
                'count': before_count,
                'below': before_below,
                'equal': before_equal,
                'above': before_above,
                'avg_price': before_avg_price,
                'avg_auto': before_avg_auto,
            },
            'after': {
                'count': after_count,
                'below': after_below,
                'equal': after_equal,
                'above': after_above,
                'avg_price': after_avg_price,
                'avg_auto': after_avg_auto,
            },
            'units_stats': units_stats,
            'type_reception_stats': type_reception_stats,
        })
    
    # Сортируем по общему количеству оценок
    analyst_stats.sort(key=lambda x: x['total_estimations'], reverse=True)
    
    # Общие показатели (суммируем по всем аналитикам)
    total_estimations_all = sum(s['total_estimations'] for s in analyst_stats)
    total_remote_all = sum(s['remote']['count'] for s in analyst_stats)
    total_before_all = sum(s['before']['count'] for s in analyst_stats)
    total_after_all = sum(s['after']['count'] for s in analyst_stats)
    
    # Подсчитываем общее количество принятых автомобилей с учетом фильтров
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    total_reception_all = qs.filter(valid_date_reception).count()
    
    # Общие показатели дистанционной оценки
    remote_below_all = sum(s['remote']['below'] for s in analyst_stats)
    remote_equal_all = sum(s['remote']['equal'] for s in analyst_stats)
    remote_above_all = sum(s['remote']['above'] for s in analyst_stats)
    remote_total_comparison = remote_below_all + remote_equal_all + remote_above_all
    
    # Средние цены для дистанционной оценки (взвешенные)
    remote_price_sum = sum(s['remote']['avg_price'] * s['remote']['count'] for s in analyst_stats if s['remote']['count'] > 0)
    remote_auto_sum = sum(s['remote']['avg_auto'] * s['remote']['count'] for s in analyst_stats if s['remote']['count'] > 0)
    remote_avg_price_all = (remote_price_sum / total_remote_all) if total_remote_all > 0 else 0
    remote_avg_auto_all = (remote_auto_sum / total_remote_all) if total_remote_all > 0 else 0
    
    # Общие показатели для до КД
    before_below_all = sum(s['before']['below'] for s in analyst_stats)
    before_equal_all = sum(s['before']['equal'] for s in analyst_stats)
    before_above_all = sum(s['before']['above'] for s in analyst_stats)
    before_total_comparison = before_below_all + before_equal_all + before_above_all
    
    # Общие показатели для после КД
    after_below_all = sum(s['after']['below'] for s in analyst_stats)
    after_equal_all = sum(s['after']['equal'] for s in analyst_stats)
    after_above_all = sum(s['after']['above'] for s in analyst_stats)
    after_total_comparison = after_below_all + after_equal_all + after_above_all
    
    # Вычисляем дополнительные показатели для сравнения с авторасчетом
    # Для дистанционной оценки: сколько дошли до цены "до КД" и сколько принято
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    
    # Для каждой группы (below, equal, above) в дистанционной оценке
    remote_below_qs = qs.filter(valid_date_remote, comparison_remote_type=-1)
    remote_below_to_before = remote_below_qs.filter(valid_date_before).count()
    remote_below_to_before_pct = (remote_below_to_before / remote_below_all * 100) if remote_below_all > 0 else 0
    remote_below_to_before_pct_from_total = (remote_below_to_before / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    remote_below_to_reception = remote_below_qs.filter(valid_date_reception).count()
    remote_below_to_reception_pct = (remote_below_to_reception / remote_below_all * 100) if remote_below_all > 0 else 0
    remote_below_to_reception_pct_from_total = (remote_below_to_reception / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    
    remote_equal_qs = qs.filter(valid_date_remote, comparison_remote_type=0)
    remote_equal_to_before = remote_equal_qs.filter(valid_date_before).count()
    remote_equal_to_before_pct = (remote_equal_to_before / remote_equal_all * 100) if remote_equal_all > 0 else 0
    remote_equal_to_before_pct_from_total = (remote_equal_to_before / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    remote_equal_to_reception = remote_equal_qs.filter(valid_date_reception).count()
    remote_equal_to_reception_pct = (remote_equal_to_reception / remote_equal_all * 100) if remote_equal_all > 0 else 0
    remote_equal_to_reception_pct_from_total = (remote_equal_to_reception / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    
    remote_above_qs = qs.filter(valid_date_remote, comparison_remote_type=1)
    remote_above_to_before = remote_above_qs.filter(valid_date_before).count()
    remote_above_to_before_pct = (remote_above_to_before / remote_above_all * 100) if remote_above_all > 0 else 0
    remote_above_to_before_pct_from_total = (remote_above_to_before / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    remote_above_to_reception = remote_above_qs.filter(valid_date_reception).count()
    remote_above_to_reception_pct = (remote_above_to_reception / remote_above_all * 100) if remote_above_all > 0 else 0
    remote_above_to_reception_pct_from_total = (remote_above_to_reception / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    
    # Для каждой группы (below, equal, above) в "До КД"
    before_below_qs = qs.filter(valid_date_before, comparison_before_type=-1)
    before_below_to_after = before_below_qs.filter(valid_date_after).count()
    before_below_to_after_pct = (before_below_to_after / before_below_all * 100) if before_below_all > 0 else 0
    before_below_to_after_pct_from_total = (before_below_to_after / before_total_comparison * 100) if before_total_comparison > 0 else 0
    before_below_to_reception = before_below_qs.filter(valid_date_reception).count()
    before_below_to_reception_pct = (before_below_to_reception / before_below_all * 100) if before_below_all > 0 else 0
    before_below_to_reception_pct_from_total = (before_below_to_reception / before_total_comparison * 100) if before_total_comparison > 0 else 0
    
    before_equal_qs = qs.filter(valid_date_before, comparison_before_type=0)
    before_equal_to_after = before_equal_qs.filter(valid_date_after).count()
    before_equal_to_after_pct = (before_equal_to_after / before_equal_all * 100) if before_equal_all > 0 else 0
    before_equal_to_after_pct_from_total = (before_equal_to_after / before_total_comparison * 100) if before_total_comparison > 0 else 0
    before_equal_to_reception = before_equal_qs.filter(valid_date_reception).count()
    before_equal_to_reception_pct = (before_equal_to_reception / before_equal_all * 100) if before_equal_all > 0 else 0
    before_equal_to_reception_pct_from_total = (before_equal_to_reception / before_total_comparison * 100) if before_total_comparison > 0 else 0
    
    before_above_qs = qs.filter(valid_date_before, comparison_before_type=1)
    before_above_to_after = before_above_qs.filter(valid_date_after).count()
    before_above_to_after_pct = (before_above_to_after / before_above_all * 100) if before_above_all > 0 else 0
    before_above_to_after_pct_from_total = (before_above_to_after / before_total_comparison * 100) if before_total_comparison > 0 else 0
    before_above_to_reception = before_above_qs.filter(valid_date_reception).count()
    before_above_to_reception_pct = (before_above_to_reception / before_above_all * 100) if before_above_all > 0 else 0
    before_above_to_reception_pct_from_total = (before_above_to_reception / before_total_comparison * 100) if before_total_comparison > 0 else 0
    
    # Для каждой группы (below, equal, above) в "После КД"
    after_below_qs = qs.filter(valid_date_after, comparison_after_type=-1)
    after_below_to_reception = after_below_qs.filter(valid_date_reception).count()
    after_below_to_reception_pct = (after_below_to_reception / after_below_all * 100) if after_below_all > 0 else 0
    after_below_to_reception_pct_from_total = (after_below_to_reception / after_total_comparison * 100) if after_total_comparison > 0 else 0
    
    after_equal_qs = qs.filter(valid_date_after, comparison_after_type=0)
    after_equal_to_reception = after_equal_qs.filter(valid_date_reception).count()
    after_equal_to_reception_pct = (after_equal_to_reception / after_equal_all * 100) if after_equal_all > 0 else 0
    after_equal_to_reception_pct_from_total = (after_equal_to_reception / after_total_comparison * 100) if after_total_comparison > 0 else 0
    
    after_above_qs = qs.filter(valid_date_after, comparison_after_type=1)
    after_above_to_reception = after_above_qs.filter(valid_date_reception).count()
    after_above_to_reception_pct = (after_above_to_reception / after_above_all * 100) if after_above_all > 0 else 0
    after_above_to_reception_pct_from_total = (after_above_to_reception / after_total_comparison * 100) if after_total_comparison > 0 else 0
    
    # Проценты для сравнения с авторасчетом
    remote_below_pct = (remote_below_all / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    remote_equal_pct = (remote_equal_all / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    remote_above_pct = (remote_above_all / remote_total_comparison * 100) if remote_total_comparison > 0 else 0
    before_below_pct = (before_below_all / before_total_comparison * 100) if before_total_comparison > 0 else 0
    before_equal_pct = (before_equal_all / before_total_comparison * 100) if before_total_comparison > 0 else 0
    before_above_pct = (before_above_all / before_total_comparison * 100) if before_total_comparison > 0 else 0
    after_below_pct = (after_below_all / after_total_comparison * 100) if after_total_comparison > 0 else 0
    after_equal_pct = (after_equal_all / after_total_comparison * 100) if after_total_comparison > 0 else 0
    after_above_pct = (after_above_all / after_total_comparison * 100) if after_total_comparison > 0 else 0
    
    # Загружаем справочники для фильтров
    from refs.models import RefCity, RefStaff
    units = RefUnit.objects.filter(buauto=True, active_eco=True).exclude(name='').order_by('name')
    
    # Получаем источники из refs_qs
    source_unit_ids = list(refs_qs.exclude(unit_source_id__isnull=True).values_list('unit_source_id', flat=True).distinct())
    source_units = RefUnit.objects.filter(id__in=source_unit_ids).exclude(name='').order_by('name') if source_unit_ids else RefUnit.objects.none()
    
    city_ids_from_funnel = list(refs_qs.exclude(city_id__isnull=True).values_list('city_id', flat=True).distinct())
    cities = RefCity.objects.filter(id__in=city_ids_from_funnel).exclude(name='').order_by('name') if city_ids_from_funnel else RefCity.objects.none()
    type_reception_ids_from_funnel = list(refs_qs.exclude(type_reception_id__isnull=True).values_list('type_reception_id', flat=True).distinct())
    type_receptions = RefTypeReceptionCarsOrganization.objects.filter(id__in=type_reception_ids_from_funnel).exclude(name='').order_by('name') if type_reception_ids_from_funnel else RefTypeReceptionCarsOrganization.objects.none()
    
    # Получаем всех аналитиков для фильтра
    all_analyst_ids_list = list(all_analyst_ids_set)
    analysts = RefStaff.objects.filter(id__in=all_analyst_ids_list).exclude(name='').order_by('name') if all_analyst_ids_list else RefStaff.objects.none()
    
    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'analyst_stats': analyst_stats,
        'totals': {
            'total_estimations': total_estimations_all,
            'total_remote': total_remote_all,
            'total_before': total_before_all,
            'total_after': total_after_all,
            'total_reception': total_reception_all,
        },
        'remote_totals': {
            'total': total_remote_all,
            'below': remote_below_all,
            'equal': remote_equal_all,
            'above': remote_above_all,
            'total_comparison': remote_total_comparison,
            'avg_price': remote_avg_price_all,
            'avg_auto': remote_avg_auto_all,
        },
        'before_totals': {
            'total': total_before_all,
            'below': before_below_all,
            'equal': before_equal_all,
            'above': before_above_all,
            'total_comparison': before_total_comparison,
        },
        'after_totals': {
            'total': total_after_all,
            'below': after_below_all,
            'equal': after_equal_all,
            'above': after_above_all,
            'total_comparison': after_total_comparison,
        },
        'badges': {
            'remote_comparison': {
                'below': {
                    'count': remote_below_all, 
                    'percent': remote_below_pct,
                    'to_before': {'count': remote_below_to_before, 'percent': remote_below_to_before_pct, 'percent_from_total': remote_below_to_before_pct_from_total},
                    'to_reception': {'count': remote_below_to_reception, 'percent': remote_below_to_reception_pct, 'percent_from_total': remote_below_to_reception_pct_from_total}
                },
                'equal': {
                    'count': remote_equal_all, 
                    'percent': remote_equal_pct,
                    'to_before': {'count': remote_equal_to_before, 'percent': remote_equal_to_before_pct, 'percent_from_total': remote_equal_to_before_pct_from_total},
                    'to_reception': {'count': remote_equal_to_reception, 'percent': remote_equal_to_reception_pct, 'percent_from_total': remote_equal_to_reception_pct_from_total}
                },
                'above': {
                    'count': remote_above_all, 
                    'percent': remote_above_pct,
                    'to_before': {'count': remote_above_to_before, 'percent': remote_above_to_before_pct, 'percent_from_total': remote_above_to_before_pct_from_total},
                    'to_reception': {'count': remote_above_to_reception, 'percent': remote_above_to_reception_pct, 'percent_from_total': remote_above_to_reception_pct_from_total}
                },
                'total': remote_total_comparison,
            },
            'before_comparison': {
                'below': {
                    'count': before_below_all, 
                    'percent': before_below_pct,
                    'to_after': {'count': before_below_to_after, 'percent': before_below_to_after_pct, 'percent_from_total': before_below_to_after_pct_from_total},
                    'to_reception': {'count': before_below_to_reception, 'percent': before_below_to_reception_pct, 'percent_from_total': before_below_to_reception_pct_from_total}
                },
                'equal': {
                    'count': before_equal_all, 
                    'percent': before_equal_pct,
                    'to_after': {'count': before_equal_to_after, 'percent': before_equal_to_after_pct, 'percent_from_total': before_equal_to_after_pct_from_total},
                    'to_reception': {'count': before_equal_to_reception, 'percent': before_equal_to_reception_pct, 'percent_from_total': before_equal_to_reception_pct_from_total}
                },
                'above': {
                    'count': before_above_all, 
                    'percent': before_above_pct,
                    'to_after': {'count': before_above_to_after, 'percent': before_above_to_after_pct, 'percent_from_total': before_above_to_after_pct_from_total},
                    'to_reception': {'count': before_above_to_reception, 'percent': before_above_to_reception_pct, 'percent_from_total': before_above_to_reception_pct_from_total}
                },
                'total': before_total_comparison,
            },
            'after_comparison': {
                'below': {
                    'count': after_below_all, 
                    'percent': after_below_pct,
                    'to_reception': {'count': after_below_to_reception, 'percent': after_below_to_reception_pct, 'percent_from_total': after_below_to_reception_pct_from_total}
                },
                'equal': {
                    'count': after_equal_all, 
                    'percent': after_equal_pct,
                    'to_reception': {'count': after_equal_to_reception, 'percent': after_equal_to_reception_pct, 'percent_from_total': after_equal_to_reception_pct_from_total}
                },
                'above': {
                    'count': after_above_all, 
                    'percent': after_above_pct,
                    'to_reception': {'count': after_above_to_reception, 'percent': after_above_to_reception_pct, 'percent_from_total': after_above_to_reception_pct_from_total}
                },
                'total': after_total_comparison,
            },
        },
        'filters': {
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
            'unit_source_ids': ','.join(map(str, unit_source_ids)) if unit_source_ids else '',
            'unit_source_ids_list': unit_source_ids,
            'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
            'unit_ids_list': unit_ids,
            'city_ids': ','.join(map(str, city_ids)) if city_ids else '',
            'city_ids_list': city_ids,
            'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
            'type_reception_ids_list': type_reception_ids,
            'analyst_ids': ','.join(map(str, analyst_ids)) if analyst_ids else '',
            'analyst_ids_list': analyst_ids,
        },
        'units': units,
        'source_units': source_units,
        'cities': cities,
        'type_receptions': type_receptions,
        'analysts': analysts,
    }
    
    return render(request, 'lo/eco_analysts_performance.html', {'params': params})


def eco_appraisers_performance(request):
    """Анализ эффективности оценщиков на основе TradeInFunnel"""
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=1, minute=0, second=0, microsecond=0)
    
    # Парсим фильтры
    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)
    
    unit_source_ids = _parse_multiple_ints(request.GET.get('unit_source_ids', ''))
    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    city_ids = _parse_multiple_ints(request.GET.get('city_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    staff_ids = _parse_multiple_ints(request.GET.get('staff_ids', ''))
    
    unit_source_id = _get_int(request.GET.get('unit_source_id'))
    unit_id = _get_int(request.GET.get('unit_id'))
    city_id = _get_int(request.GET.get('city_id'))
    type_reception_id = _get_int(request.GET.get('type_reception_id'))
    staff_id = _get_int(request.GET.get('staff_id'))
    
    # Обратная совместимость
    if unit_source_id and unit_source_id not in unit_source_ids:
        unit_source_ids.append(unit_source_id)
    if unit_id and unit_id not in unit_ids:
        unit_ids.append(unit_id)
    if city_id and city_id not in city_ids:
        city_ids.append(city_id)
    if type_reception_id and type_reception_id not in type_reception_ids:
        type_reception_ids.append(type_reception_id)
    if staff_id and staff_id not in staff_ids:
        staff_ids.append(staff_id)
    
    # Базовый QuerySet
    base_qs = TradeInFunnel.objects.all()
    
    # QuerySet для справочников (без фильтров по источникам и подразделениям)
    refs_qs = TradeInFunnel.objects.all()
    
    # Применяем фильтры по датам (сквозной отчет)
    qs = base_qs.filter(
        Q(date_rlk__gte=date_start, date_rlk__lte=date_end) |
        Q(date_remote_success__gte=date_start, date_remote_success__lte=date_end) |
        Q(date_before_success__gte=date_start, date_before_success__lte=date_end) |
        Q(date_after_success__gte=date_start, date_after_success__lte=date_end) |
        Q(date_reception_success__gte=date_start, date_reception_success__lte=date_end)
    )
    
    if unit_source_ids:
        qs = qs.filter(unit_source_id__in=unit_source_ids)
    if unit_ids:
        qs = qs.filter(unit_id__in=unit_ids)
    if city_ids:
        qs = qs.filter(city_id__in=city_ids)
        refs_qs = refs_qs.filter(city_id__in=city_ids)
    if type_reception_ids:
        qs = qs.filter(type_reception_id__in=type_reception_ids)
        refs_qs = refs_qs.filter(type_reception_id__in=type_reception_ids)
    if staff_ids:
        qs = qs.filter(staff_id__in=staff_ids)
    
    # Дата для исключения некорректных дат (1.1.1)
    date_invalid = DT.date(1, 1, 1)
    
    # Вспомогательные Q-объекты для проверки валидных дат
    valid_date_rlk = Q(date_rlk__isnull=False) & ~Q(date_rlk=date_invalid)
    valid_date_remote = Q(date_remote_success__isnull=False) & ~Q(date_remote_success=date_invalid)
    valid_date_before = Q(date_before_success__isnull=False) & ~Q(date_before_success=date_invalid)
    valid_date_after = Q(date_after_success__isnull=False) & ~Q(date_after_success=date_invalid)
    valid_date_reception = Q(date_reception_success__isnull=False) & ~Q(date_reception_success=date_invalid)
    
    # Получаем всех уникальных оценщиков
    staff_ids_list = list(qs.exclude(staff_id__isnull=True).values_list('staff_id', flat=True).distinct())
    
    staff_stats = []
    
    for staff_id_val in staff_ids_list:
        if staff_id_val is None:
            continue
        
        # Фильтруем по оценщику
        staff_qs = qs.filter(staff_id=staff_id_val)
        
        # Получаем имя оценщика
        staff_name_obj = staff_qs.exclude(staff_name='').first()
        staff_name = staff_name_obj.staff_name if staff_name_obj else f'Оценщик #{staff_id_val}'
        
        # Подсчеты
        total_rlk = staff_qs.filter(valid_date_rlk).count()
        total_before = staff_qs.filter(valid_date_before | valid_date_remote).count()
        total_after = staff_qs.filter(valid_date_after).count()
        total_reception = staff_qs.filter(valid_date_reception).count()
        
        # Конверсии
        conv_before = (total_before / total_rlk * 100) if total_rlk > 0 else 0
        conv_after = (total_after / total_before * 100) if total_before > 0 else 0
        conv_reception = (total_reception / total_after * 100) if total_after > 0 else 0
        
        # Средние цены
        avg_price_reception = staff_qs.filter(valid_date_reception).aggregate(avg=Avg('price_reception_staff'))['avg'] or 0
        avg_price_sale = staff_qs.filter(valid_date_reception).aggregate(avg=Avg('price_sale_staff'))['avg'] or 0
        
        # Статистика по подразделениям
        units_stats = list(staff_qs.exclude(unit_id__isnull=True).values('unit_id', 'unit_name').annotate(
            count=Count('rlk_id', distinct=True)
        ).order_by('-count')[:10])
        
        # Статистика по типам приема
        type_reception_stats = list(staff_qs.exclude(type_reception_id__isnull=True).values('type_reception_id', 'type_reception_name').annotate(
            count=Count('rlk_id', distinct=True)
        ).order_by('-count')[:10])
        
        # Статистика по брендам
        brand_stats = list(staff_qs.exclude(brand='').values('brand').annotate(
            count=Count('rlk_id', distinct=True)
        ).order_by('-count')[:10])
        
        # Среднее время на складе
        avg_hours_stock = staff_qs.filter(valid_date_reception).aggregate(avg=Avg('hours_stock'))['avg'] or 0
        
        staff_stats.append({
            'staff_id': staff_id_val,
            'staff_name': staff_name,
            'total_rlk': total_rlk,
            'total_before': total_before,
            'total_after': total_after,
            'total_reception': total_reception,
            'conv_before': conv_before,
            'conv_after': conv_after,
            'conv_reception': conv_reception,
            'avg_price_reception': avg_price_reception,
            'avg_price_sale': avg_price_sale,
            'avg_hours_stock': avg_hours_stock,
            'units_stats': units_stats,
            'type_reception_stats': type_reception_stats,
            'brand_stats': brand_stats,
        })
    
    # Сортируем по имени оценщика (алфавит)
    staff_stats.sort(key=lambda x: x.get('staff_name', '').lower())
    
    # Загружаем справочники для фильтров
    from refs.models import RefCity, RefStaff
    units = RefUnit.objects.filter(buauto=True, active_eco=True).exclude(name='').order_by('name')
    
    # Получаем источники из refs_qs
    source_unit_ids = list(refs_qs.exclude(unit_source_id__isnull=True).values_list('unit_source_id', flat=True).distinct())
    source_units = RefUnit.objects.filter(id__in=source_unit_ids).exclude(name='').order_by('name') if source_unit_ids else RefUnit.objects.none()
    
    city_ids_from_funnel = list(refs_qs.exclude(city_id__isnull=True).values_list('city_id', flat=True).distinct())
    cities = RefCity.objects.filter(id__in=city_ids_from_funnel).exclude(name='').order_by('name') if city_ids_from_funnel else RefCity.objects.none()
    type_reception_ids_from_funnel = list(refs_qs.exclude(type_reception_id__isnull=True).values_list('type_reception_id', flat=True).distinct())
    type_receptions = RefTypeReceptionCarsOrganization.objects.filter(id__in=type_reception_ids_from_funnel).exclude(name='').order_by('name') if type_reception_ids_from_funnel else RefTypeReceptionCarsOrganization.objects.none()
    
    # Получаем всех оценщиков из refs_qs для фильтра (отсортированных по алфавиту)
    staff_ids_from_funnel = list(refs_qs.exclude(staff_id__isnull=True).values_list('staff_id', flat=True).distinct())
    staffs = RefStaff.objects.filter(id__in=staff_ids_from_funnel).exclude(name='').order_by('name') if staff_ids_from_funnel else RefStaff.objects.none()
    
    params = {
        'type': 'eco_funnel',
        'nav_selected': 4,
        'staff_stats': staff_stats,
        'filters': {
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
            'unit_source_ids': ','.join(map(str, unit_source_ids)) if unit_source_ids else '',
            'unit_source_ids_list': unit_source_ids,
            'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
            'unit_ids_list': unit_ids,
            'city_ids': ','.join(map(str, city_ids)) if city_ids else '',
            'city_ids_list': city_ids,
            'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
            'type_reception_ids_list': type_reception_ids,
            'staff_ids': ','.join(map(str, staff_ids)) if staff_ids else '',
            'staff_ids_list': staff_ids,
        },
        'units': units,
        'source_units': source_units,
        'cities': cities,
        'type_receptions': type_receptions,
        'staffs': staffs,
    }
    
    return render(request, 'lo/eco_appraisers_performance.html', {'params': params})


#История изменений
def get_versions(table, id):
	return ChangeLog.objects.filter(model = table).filter(record_id = id).order_by('changed')