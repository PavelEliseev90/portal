# -*- coding: utf-8 -*-
import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta

from api.models import Exchange1CErrorLog
from refs.models import RefCarsOrganization, RefStore


def _staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _parse_date_range(request, default_days=30):
    today = timezone.now().date()
    default_end = today
    default_start = today - timedelta(days=default_days)
    date_start = request.GET.get('date_start') or request.POST.get('date_start') or str(default_start)
    date_end = request.GET.get('date_end') or request.POST.get('date_end') or str(default_end)
    try:
        ds = timezone.datetime.strptime(date_start, '%Y-%m-%d').date()
        de = timezone.datetime.strptime(date_end, '%Y-%m-%d').date()
        if ds > de:
            ds, de = de, ds
        return ds, de
    except (ValueError, TypeError):
        return default_start, default_end


def _exchange_errors_counts():
    since_24h = timezone.now() - timedelta(hours=24)
    return {
        'exchange_errors_24h': Exchange1CErrorLog.objects.filter(date_create__gte=since_24h).count(),
        'exchange_errors_total': Exchange1CErrorLog.objects.count(),
    }


def _exchange_errors_queryset(date_start, date_end, exchange_type=''):
    next_day = date_end + timedelta(days=1)
    qs = Exchange1CErrorLog.objects.filter(
        date_create__date__gte=date_start,
        date_create__date__lt=next_day,
    )
    if exchange_type:
        qs = qs.filter(exchange_type=exchange_type)
    return qs


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def hub(request):
    """Главная панель мониторинга."""
    params = {
        'type': 'monitoring_hub',
        **_exchange_errors_counts(),
    }
    return render(request, 'monitoring/hub.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def exchange_errors_list(request):
    """Список ошибок обмена с 1С."""
    date_start, date_end = _parse_date_range(request)
    exchange_type = request.GET.get('exchange_type', '').strip()
    qs = _exchange_errors_queryset(date_start, date_end, exchange_type)

    type_choices = (
        Exchange1CErrorLog.objects.order_by('exchange_type')
        .values_list('exchange_type', flat=True)
        .distinct()
    )

    stats_by_type = (
        qs.values('exchange_type')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
    )

    per_page = min(int(request.GET.get('per_page', 50)), 100)
    paginator = Paginator(qs.order_by('-date_create'), per_page)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    get_copy = request.GET.copy()
    if 'page' in get_copy:
        get_copy.pop('page')
    query_without_page = get_copy.urlencode()

    params = {
        'type': 'monitoring_exchange',
        'date_start': date_start,
        'date_end': date_end,
        'date_start_str': date_start.strftime('%Y-%m-%d'),
        'date_end_str': date_end.strftime('%Y-%m-%d'),
        'exchange_type': exchange_type,
        'type_choices': list(type_choices),
        'stats_by_type': stats_by_type,
        'total_count': qs.count(),
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'query_without_page': query_without_page,
        'purged_count': request.GET.get('purged'),
        **_exchange_errors_counts(),
    }
    return render(request, 'monitoring/exchange_errors_list.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
@require_POST
def exchange_errors_purge(request):
    """Удаление ошибок обмена за выбранный период."""
    date_start, date_end = _parse_date_range(request)
    exchange_type = request.POST.get('exchange_type', '').strip()
    qs = _exchange_errors_queryset(date_start, date_end, exchange_type)
    deleted_count, _ = qs.delete()

    query = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'purged': deleted_count,
    }
    if exchange_type:
        query['exchange_type'] = exchange_type
    return redirect(f"{reverse('monitoring:exchange_errors_list')}?{urlencode(query)}")


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def exchange_errors_detail(request, pk):
    """Подробный просмотр ошибки обмена."""
    obj = get_object_or_404(Exchange1CErrorLog, pk=pk)
    data_pretty = obj.data
    try:
        parsed = json.loads(obj.data)
        data_pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        pass

    params = {
        'type': 'monitoring_exchange',
        'object': obj,
        'data_pretty': data_pretty,
    }
    return render(request, 'monitoring/exchange_errors_detail.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def stores_list(request):
    """Управление стоянками: список и количество авто в наличии."""
    q = (request.GET.get('q') or '').strip()
    only_with_cars = request.GET.get('only_with_cars') == '1'

    cars_in_stock_sq = (
        RefCarsOrganization.objects.filter(store=OuterRef('pk'), quantity__gt=0)
        .order_by()
        .values('store')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1]
    )
    qs = RefStore.objects.select_related('city', 'unit').annotate(
        cars_in_stock=Coalesce(Subquery(cars_in_stock_sq, output_field=IntegerField()), 0),
    ).order_by('name', 'id')

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(name_dop__icontains=q)
            | Q(name_site__icontains=q)
            | Q(adress__icontains=q)
            | Q(uin__icontains=q)
            | Q(city__name__icontains=q)
            | Q(unit__name__icontains=q)
        )
    if only_with_cars:
        qs = qs.filter(cars_in_stock__gt=0)

    per_page = min(int(request.GET.get('per_page', 50) or 50), 100)
    paginator = Paginator(qs, per_page)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    get_copy = request.GET.copy()
    if 'page' in get_copy:
        get_copy.pop('page')
    query_without_page = get_copy.urlencode()

    params = {
        'type': 'monitoring_stores',
        'q': q,
        'only_with_cars': only_with_cars,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'query_without_page': query_without_page,
        'total_count': paginator.count,
        'cleared_count': request.GET.get('cleared'),
        'cleared_store': request.GET.get('store'),
    }
    return render(request, 'monitoring/stores_list.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
@require_POST
def stores_clear_stock(request, pk):
    """Обнулить наличие (quantity=0) у всех автомобилей стоянки."""
    store = get_object_or_404(RefStore, pk=pk)
    updated = RefCarsOrganization.objects.filter(
        store=store,
        quantity__gt=0,
    ).update(quantity=0)

    messages.success(
        request,
        f'Стоянка «{store}»: в «отсутствуют» переведено автомобилей: {updated}.',
    )
    query = {
        'cleared': updated,
        'store': store.name or str(store.pk),
    }
    q = (request.POST.get('q') or '').strip()
    if q:
        query['q'] = q
    if request.POST.get('only_with_cars') == '1':
        query['only_with_cars'] = '1'
    return redirect(f"{reverse('monitoring:stores_list')}?{urlencode(query)}")
