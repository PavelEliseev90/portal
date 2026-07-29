# -*- coding: utf-8 -*-
from datetime import datetime, time as dt_time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from .models import PageViewLog

DEFAULT_PERIOD_DAYS = 7
MAX_PERIOD_DAYS = 31
MAX_TOP_PATHS = 30
MAX_USERS_IN_FILTER = 300
LIST_FIELDS = (
    'id', 'created', 'user_id', 'session_key', 'device_type',
    'path', 'path_full', 'method', 'status_code',
)


def _staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _parse_period(request):
    today = timezone.now().date()
    default_end = today
    default_start = today - timedelta(days=DEFAULT_PERIOD_DAYS)
    date_start_raw = request.GET.get('date_start') or str(default_start)
    date_end_raw = request.GET.get('date_end') or str(default_end)

    try:
        date_start = timezone.datetime.strptime(date_start_raw, '%Y-%m-%d').date()
        date_end = timezone.datetime.strptime(date_end_raw, '%Y-%m-%d').date()
        if date_start > date_end:
            date_start, date_end = date_end, date_start
    except (ValueError, TypeError):
        date_start = default_start
        date_end = default_end

    period_capped = False
    if (date_end - date_start).days > MAX_PERIOD_DAYS:
        date_end = date_start + timedelta(days=MAX_PERIOD_DAYS)
        period_capped = True

    return date_start, date_end, period_capped


def _period_bounds(date_start, date_end):
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(date_start, dt_time.min), tz)
    end_dt = timezone.make_aware(
        datetime.combine(date_end + timedelta(days=1), dt_time.min),
        tz,
    )
    return start_dt, end_dt


def _paginate_without_count(qs, page_num, per_page):
    page_num = max(1, int(page_num or 1))
    per_page = max(1, min(int(per_page or 25), 100))
    offset = (page_num - 1) * per_page
    rows = list(qs[offset:offset + per_page + 1])
    has_next = len(rows) > per_page
    if has_next:
        rows = rows[:per_page]
    return rows, page_num, per_page, has_next, page_num > 1


@login_required
@user_passes_test(_staff_required, login_url='/login/')
def pageview_dashboard(request):
    """Дашборд логов просмотров: агрегаты, топ страниц, последние записи."""
    date_start, date_end, period_capped = _parse_period(request)
    start_dt, end_dt = _period_bounds(date_start, date_end)

    user_id = request.GET.get('user_id', '').strip()
    path_search = request.GET.get('path_search', '').strip()
    only_anonymous = request.GET.get('only_anonymous') == '1'
    device_type = request.GET.get('device_type', '').strip()

    qs = PageViewLog.objects.filter(created__gte=start_dt, created__lt=end_dt)

    if user_id:
        try:
            qs = qs.filter(user_id=int(user_id))
        except ValueError:
            pass
    if path_search and len(path_search) >= 2:
        qs = qs.filter(Q(path__icontains=path_search) | Q(path_full__icontains=path_search))
    if only_anonymous:
        qs = qs.filter(user__isnull=True)
    if device_type:
        qs = qs.filter(device_type=device_type)

    agg = qs.aggregate(
        total_views=Count('id'),
        unique_users=Count('user', distinct=True),
        unique_sessions=Count('session_key', distinct=True, filter=Q(user__isnull=True)),
    )
    total_views = agg['total_views'] or 0
    unique_users = agg['unique_users'] or 0
    unique_sessions = agg['unique_sessions'] or 0
    unique_visitors = unique_users + unique_sessions

    top_paths = list(
        qs.values('path')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:MAX_TOP_PATHS]
    )
    device_breakdown = list(
        qs.values('device_type')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
    )

    user_ids = (
        PageViewLog.objects.filter(
            created__gte=start_dt,
            created__lt=end_dt,
            user_id__isnull=False,
        )
        .values_list('user_id', flat=True)
        .distinct()[:MAX_USERS_IN_FILTER]
    )
    users_list = list(
        get_user_model().objects.filter(id__in=user_ids)
        .order_by('username')
        .values_list('id', 'username')
    )

    page_num = request.GET.get('page', 1)
    per_page = min(int(request.GET.get('per_page', 25)), 100)
    page_rows, page_num, per_page, has_next, has_previous = _paginate_without_count(
        qs.select_related('user').only(*LIST_FIELDS).order_by('-created', '-id'),
        page_num,
        per_page,
    )

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
        'period_capped': period_capped,
        'max_period_days': MAX_PERIOD_DAYS,
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
        'page_rows': page_rows,
        'page_num': page_num,
        'per_page': per_page,
        'has_next': has_next,
        'has_previous': has_previous,
        'query_without_page': query_without_page,
    }
    return render(request, 'changelog/pageview_dashboard.html', {'params': params})
