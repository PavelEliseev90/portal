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
from refs.models import RefCarsOrganization, RefCarsOrganizationFiles, RefStore

from .cars_photos import (
    cars_photos_hub_counts,
    cleanup_photo_queue,
    enqueue_pending_photo_retries,
)


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
        **cars_photos_hub_counts(),
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


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def cars_photos_list(request):
    """Фото автомобилей организации: не загружены / очередь / повтор."""
    tab = request.GET.get('tab', 'no_photos')
    q = (request.GET.get('q') or '').strip()

    if tab == 'pending_files':
        qs = (
            RefCarsOrganizationFiles.objects.filter(
                Q(file='') | Q(file__isnull=True),
            )
            .exclude(url='')
            .select_related('сars_organization', 'сars_organization__unit', 'сars_organization__store')
            .order_by('-date', '-id')
        )
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(url__icontains=q)
                | Q(сars_organization__vin__icontains=q)
                | Q(сars_organization__name__icontains=q)
            )
    else:
        tab = 'no_photos'
        qs = (
            RefCarsOrganization.objects.filter(quantity__gt=0)
            .annotate(
                downloaded=Count(
                    'refcarsorganizationfiles',
                    filter=Q(refcarsorganizationfiles__file__gt=''),
                    distinct=True,
                ),
            )
            .filter(downloaded=0)
            .select_related('unit', 'store')
            .order_by('-date_refresh', '-id')
        )
        if q:
            qs = qs.filter(
                Q(vin__icontains=q)
                | Q(name__icontains=q)
                | Q(slug__icontains=q)
                | Q(plate_number__icontains=q)
            )

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
        'type': 'monitoring_cars_photos',
        'tab': tab,
        'q': q,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'query_without_page': query_without_page,
        'total_count': paginator.count,
        'retried': request.GET.get('retried'),
        **cars_photos_hub_counts(),
    }
    return render(request, 'monitoring/cars_photos_list.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
@require_POST
def cars_photos_retry(request, pk):
    """Поставить в очередь повторную загрузку фото авто по сохранённым URL."""
    from api.tasks_cars import retry_pending_photos_async

    car = get_object_or_404(RefCarsOrganization, pk=pk)
    pending = RefCarsOrganizationFiles.objects.filter(сars_organization=car).filter(
        Q(file='') | Q(file__isnull=True),
    ).exclude(url='').count()

    if pending:
        retry_pending_photos_async(car.pk, remove_existing_tasks=True)
        messages.info(request, f'Авто {car.vin or car.slug}: в очередь на повтор — {pending} фото.')
    else:
        messages.warning(request, f'Авто {car.vin or car.slug}: нет URL для повторной загрузки.')

    query = {'tab': request.POST.get('tab', 'no_photos')}
    q = (request.POST.get('q') or '').strip()
    if q:
        query['q'] = q
    return redirect(f"{reverse('monitoring:cars_photos_list')}?{urlencode(query)}")


@login_required
@user_passes_test(_staff_required, login_url='/login/')
@require_POST
def cars_photos_cleanup(request):
    """Сброс зависших lock, удаление failed и дубликатов в очереди фото."""
    result = cleanup_photo_queue(dedupe=True, delete_failed=True)
    messages.success(
        request,
        'Очередь фото: снято lock — {released}, удалено failed — {failed_deleted}, '
        'дубликатов — {duplicates_deleted}.'.format(**result),
    )
    query = {'tab': request.POST.get('tab', 'no_photos')}
    q = (request.POST.get('q') or '').strip()
    if q:
        query['q'] = q
    return redirect(f"{reverse('monitoring:cars_photos_list')}?{urlencode(query)}")


@login_required
@user_passes_test(_staff_required, login_url='/login/')
@require_POST
def cars_photos_enqueue_retries(request):
    """Поставить в очередь повторную загрузку по URL из БД (до 500 авто)."""
    limit = min(int(request.POST.get('limit', 500) or 500), 2000)
    queued = enqueue_pending_photo_retries(limit=limit)
    messages.info(
        request,
        f'В очередь refresh_cars_photos поставлено авто для повтора: {queued} '
        f'(лимит {limit}). Убедитесь, что воркер process_tasks запущен.',
    )
    query = {'tab': request.POST.get('tab', 'pending_files')}
    q = (request.POST.get('q') or '').strip()
    if q:
        query['q'] = q
    return redirect(f"{reverse('monitoring:cars_photos_list')}?{urlencode(query)}")
