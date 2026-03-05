# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta

from .models import PageViewLog


def _staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def pageview_dashboard(request):
    """Дашборд логов просмотров: уникальные пользователи за период, кол-во просмотров, топ страниц, фильтр по пользователю и по странице."""
    # Период по умолчанию — последние 30 дней
    today = timezone.now().date()
    default_end = today
    default_start = today - timedelta(days=30)
    date_start = request.GET.get('date_start') or str(default_start)
    date_end = request.GET.get('date_end') or str(default_end)
    user_id = request.GET.get('user_id', '').strip()
    path_search = request.GET.get('path_search', '').strip()
    only_anonymous = request.GET.get('only_anonymous') == '1'
    device_type = request.GET.get('device_type', '').strip()

    try:
        ds = timezone.datetime.strptime(date_start, '%Y-%m-%d').date()
        de = timezone.datetime.strptime(date_end, '%Y-%m-%d').date()
        if ds > de:
            ds, de = de, ds
        date_start, date_end = ds, de
    except (ValueError, TypeError):
        ds = default_start
        de = default_end
        date_start, date_end = ds, de

    # Базовый queryset за период (включительно день окончания)
    next_day = date_end + timedelta(days=1)
    qs = PageViewLog.objects.filter(
        created__date__gte=date_start,
        created__date__lt=next_day,
    )

    if user_id:
        try:
            qs = qs.filter(user_id=int(user_id))
        except ValueError:
            pass
    if path_search:
        qs = qs.filter(Q(path__icontains=path_search) | Q(path_full__icontains=path_search))
    if only_anonymous:
        qs = qs.filter(user__isnull=True)
    if device_type:
        qs = qs.filter(device_type=device_type)

    # ——— Агрегаты по отфильтрованному qs (один запрос) ———
    agg = qs.aggregate(
        total_views=Count('id'),
        unique_users=Count('user', distinct=True),
        unique_sessions=Count('session_key', distinct=True, filter=Q(user__isnull=True)),
    )
    total_views = agg['total_views'] or 0
    unique_users = agg['unique_users'] or 0
    unique_sessions = agg['unique_sessions'] or 0
    # Уникальные «посетители»: авторизованные по user + анонимы по session_key
    unique_visitors = unique_users + unique_sessions

    # Топ страниц (по path, без query) — отдельный запрос
    top_paths = (
        qs.values('path')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:50]
    )
    # Разбивка по устройствам
    device_breakdown = (
        qs.values('device_type')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
    )

    # Список пользователей, у которых есть логи в периоде (для фильтра)
    users_with_logs = (
        PageViewLog.objects.filter(created__date__gte=date_start, created__date__lt=next_day)
        .filter(user__isnull=False)
        .values_list('user_id', 'user__username')
        .distinct()
    )
    users_list = list(users_with_logs)

    # Таблица логов с пагинацией
    per_page = min(int(request.GET.get('per_page', 50)), 200)
    paginator = Paginator(qs.select_related('user').order_by('-created'), per_page)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    get_copy = request.GET.copy()
    if 'page' in get_copy:
        get_copy.pop('page')
    query_without_page = get_copy.urlencode()

    device_type_choices = [
        ('', '— все —'),
        ('pc', 'ПК'),
        ('mobile', 'Мобильный'),
        ('tablet', 'Планшет'),
        ('bot', 'Бот'),
        ('unknown', 'Неизвестно'),
    ]
    params = {
        'date_start': date_start,
        'date_end': date_end,
        'user_id': user_id,
        'path_search': path_search,
        'only_anonymous': only_anonymous,
        'device_type': device_type,
        'device_type_choices': device_type_choices,
        'total_views': total_views,
        'unique_visitors': unique_visitors,
        'unique_users': unique_users,
        'unique_sessions': unique_sessions,
        'top_paths': top_paths,
        'device_breakdown': device_breakdown,
        'users_list': users_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'query_without_page': query_without_page,
    }
    return render(request, 'changelog/pageview_dashboard.html', {'params': params})
