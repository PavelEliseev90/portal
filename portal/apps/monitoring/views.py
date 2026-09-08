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
from prices_car_bu.views import (
    CUMULATIVE_SEND_BATCH_LIMIT,
    attach_cumulative_1c_target,
    cumulative_hub_counts,
    cumulative_unsent_qs,
    send_cumulative_item,
)


def _staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _cars_no_modification_qs(store_id=None, unit_id=None):
    """Авто в наличии без привязки modification_autoru."""
    qs = (
        RefCarsOrganization.objects.filter(quantity__gt=0, modification_autoru__isnull=True)
        .select_related('store', 'unit', 'status', 'type_sale')
        .order_by('-date_refresh', '-id')
    )
    if store_id:
        qs = qs.filter(store_id=store_id)
    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    return qs


def cars_no_modification_count(store_id=None, unit_id=None):
    return _cars_no_modification_qs(store_id=store_id, unit_id=unit_id).count()


def stores_hub_counts():
    return {
        'cars_no_modification_total': cars_no_modification_count(),
    }


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
        **cumulative_hub_counts(),
        **stores_hub_counts(),
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
    only_no_modification = request.GET.get('only_no_modification') == '1'

    cars_in_stock_sq = (
        RefCarsOrganization.objects.filter(store=OuterRef('pk'), quantity__gt=0)
        .order_by()
        .values('store')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1]
    )
    cars_no_modification_sq = (
        RefCarsOrganization.objects.filter(
            store=OuterRef('pk'),
            quantity__gt=0,
            modification_autoru__isnull=True,
        )
        .order_by()
        .values('store')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1]
    )
    qs = RefStore.objects.select_related('city', 'unit').annotate(
        cars_in_stock=Coalesce(Subquery(cars_in_stock_sq, output_field=IntegerField()), 0),
        cars_no_modification=Coalesce(
            Subquery(cars_no_modification_sq, output_field=IntegerField()), 0,
        ),
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
    if only_no_modification:
        qs = qs.filter(cars_no_modification__gt=0)

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
        'only_no_modification': only_no_modification,
        'cars_no_modification_total': cars_no_modification_count(),
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
def cars_no_modification_list(request, store_pk=None):
    """Детальный список авто в наличии без modification_autoru."""
    q = (request.GET.get('q') or '').strip()
    store = None
    if store_pk is not None:
        store = get_object_or_404(RefStore.objects.select_related('city', 'unit'), pk=store_pk)

    qs = _cars_no_modification_qs(store_id=store.pk if store else None)
    if q:
        qs = qs.filter(
            Q(vin__icontains=q)
            | Q(name__icontains=q)
            | Q(slug__icontains=q)
            | Q(plate_number__icontains=q)
            | Q(mark__icontains=q)
            | Q(model__icontains=q)
            | Q(modification__icontains=q)
            | Q(store__name__icontains=q)
            | Q(unit__name__icontains=q)
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
        'type': 'monitoring_cars_no_modification',
        'q': q,
        'store': store,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'query_without_page': query_without_page,
        'total_count': paginator.count,
        'cars_no_modification_total': cars_no_modification_count(),
    }
    return render(request, 'monitoring/cars_no_modification_list.html', {'params': params})


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
                сars_organization__quantity__gt=0,
                сars_organization__is_new=False,
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
            RefCarsOrganization.objects.filter(quantity__gt=0, is_new=False)
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


def _cumulative_send_qs(target=''):
    qs = cumulative_unsent_qs()
    if target == 'alfa':
        qs = qs.filter(agreement__unit__ib__alfa=True)
    elif target == 'kors':
        qs = qs.filter(
            Q(agreement__unit__ib__alfa=False)
            | Q(agreement__unit__ib__isnull=True)
            | Q(agreement__unit__isnull=True)
        )
    return qs


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def cumulative_send_list(request):
    """Очередь неотправленного расчётного КВП: Альфа-Авто / КорсАвто."""
    target = (request.GET.get('target') or '').strip()
    if target not in ('', 'alfa', 'kors'):
        target = ''
    qs = _cumulative_send_qs(target)

    per_page = min(int(request.GET.get('per_page', 50) or 50), 100)
    paginator = Paginator(qs, per_page)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    for item in page_obj.object_list:
        attach_cumulative_1c_target(item)

    get_copy = request.GET.copy()
    if 'page' in get_copy:
        get_copy.pop('page')
    query_without_page = get_copy.urlencode()

    send_results = request.session.pop('monitoring_cumulative_send_results', None)
    counts = cumulative_hub_counts()

    params = {
        'type': 'monitoring_cumulative_send',
        'target': target,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'query_without_page': query_without_page,
        'total_count': paginator.count,
        'send_limit': CUMULATIVE_SEND_BATCH_LIMIT,
        'send_results': send_results or [],
        **counts,
    }
    return render(request, 'monitoring/cumulative_send.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
@require_POST
def cumulative_send(request):
    """Отправить одну или все (до 200) неотправленные записи расчётного КВП."""
    target = (request.POST.get('target') or '').strip()
    if target not in ('', 'alfa', 'kors'):
        target = ''
    item_id = (request.POST.get('id') or '').strip()
    send_all = request.POST.get('send_all') == '1'
    results = []

    if send_all:
        for item in list(_cumulative_send_qs(target)[:CUMULATIVE_SEND_BATCH_LIMIT]):
            try:
                item.refresh_from_db()
            except Exception:
                continue
            if item.send_1c:
                continue
            try:
                results.append(send_cumulative_item(item))
            except Exception as exc:
                results.append({
                    'id': item.pk,
                    'title': f'#{item.pk}',
                    'ok': False,
                    'status_code': None,
                    'text': '',
                    'error': str(exc),
                    'target': None,
                    'target_name': None,
                })
    elif item_id:
        try:
            pk = int(item_id)
        except (TypeError, ValueError):
            pk = None
        if pk is not None:
            from prices_car_bu.models import CalculatedCumulativeData
            item = CalculatedCumulativeData.objects.select_related(
                'agreement__unit__ib',
                'agreement__cars',
                'indicatorKVP',
            ).filter(pk=pk).first()
            if item is None:
                results.append({
                    'id': pk,
                    'title': f'#{pk}',
                    'ok': False,
                    'status_code': None,
                    'text': '',
                    'error': 'Запись не найдена',
                    'target': None,
                    'target_name': None,
                })
            else:
                try:
                    results.append(send_cumulative_item(item))
                except Exception as exc:
                    results.append({
                        'id': pk,
                        'title': f'#{pk}',
                        'ok': False,
                        'status_code': None,
                        'text': '',
                        'error': str(exc),
                        'target': None,
                        'target_name': None,
                    })

    request.session['monitoring_cumulative_send_results'] = results
    ok_n = sum(1 for r in results if r.get('ok'))
    fail_n = len(results) - ok_n
    if results:
        messages.info(
            request,
            'Отправка расчётных КВП: успешно {}, ошибок {} (детали ниже).'.format(ok_n, fail_n),
        )
    query = {}
    if target:
        query['target'] = target
    url = reverse('monitoring:cumulative_send_list')
    if query:
        return redirect(f'{url}?{urlencode(query)}')
    return redirect(url)


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def cars_delete_search(request):
    """Поиск автомобиля организации для удаления вместе со связанными записями."""
    from .car_delete import related_total, search_organization_cars

    q = (request.GET.get('q') or '').strip()
    cars = search_organization_cars(q) if q else []
    rows = []
    for car in cars:
        rows.append({
            'car': car,
            'related_total': related_total(car),
        })
    params = {
        'type': 'monitoring_cars_delete',
        'q': q,
        'rows': rows,
        'found': len(rows),
    }
    return render(request, 'monitoring/cars_delete.html', {'params': params})


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def cars_delete_preview(request, pk):
    """Показать связанные объекты и удалить автомобиль организации."""
    from .car_delete import delete_organization_car, inspect_car_relations

    car = get_object_or_404(
        RefCarsOrganization.objects.select_related('unit', 'store', 'lo', 'organization'),
        pk=pk,
    )

    if request.method == 'POST':
        if request.POST.get('confirm') != '1' or str(request.POST.get('car_id')) != str(car.pk):
            messages.error(request, 'Подтвердите удаление: отметьте галочку.')
            return redirect('monitoring:cars_delete_preview', pk=car.pk)
        try:
            result = delete_organization_car(car, user=request.user)
        except Exception as exc:
            messages.error(request, f'Не удалось удалить: {exc}')
            return redirect('monitoring:cars_delete_preview', pk=pk)
        messages.success(
            request,
            'Удалён автомобиль id={pk} VIN {vin}: связанных записей {n}.'.format(
                pk=result['pk'],
                vin=result['vin'] or '—',
                n=result['related_total'],
            ),
        )
        q = (result['vin'] or '').strip()
        url = reverse('monitoring:cars_delete_search')
        if q:
            return redirect(f'{url}?q={q}')
        return redirect(url)

    relations = inspect_car_relations(car)
    params = {
        'type': 'monitoring_cars_delete',
        'car': car,
        'relations': relations,
    }
    return render(request, 'monitoring/cars_delete_preview.html', {'params': params})
