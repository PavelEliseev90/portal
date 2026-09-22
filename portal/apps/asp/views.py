from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from asp.models import ReportSavedFilter
from asp.report_common import VIEW_COOKIE, VIEW_COOKIE_MAX_AGE, preferred_view_from_cookie
from asp.report_table import (
    COLUMNS_COOKIE_MAX_AGE,
    REPORTS,
    attach_table_ui,
    columns_cookie_value,
    cookie_name,
    normalize_columns,
)
from asp.saved_filters import (
    resolve_report_get,
    saved_filters_for_template,
    snapshot_filter_data,
)

ASP_VARIANT_TEMPLATES = {
    '1': 'asp/asp.html',
    '2': 'asp/asp_bento.html',
    '3': 'asp/asp_command.html',
    '4': 'asp/asp_22c.html',
}

REPORT_KEY_BY_TYPE = {
    'asp_cumulative_margin': 'margin',
    'asp_stock_report': 'stock',
    'asp_accepted_report': 'accepted',
}


def asp(request):
    variant = (request.GET.get('v') or '1').strip()
    if variant not in ASP_VARIANT_TEMPLATES:
        variant = '1'
    template = ASP_VARIANT_TEMPLATES[variant]
    params = {
        'type': 'asp',
        'asp_variant': variant,
    }
    return render(request, template, {'params': params})


def _redirect_with_default_view(request):
    """Режим всегда в URL; без view — берём из cookie или main."""
    preferred = preferred_view_from_cookie(request.COOKIES.get(VIEW_COOKIE))
    q = request.GET.copy()
    if isinstance(q, QueryDict):
        q = q.copy()
    q['view'] = preferred
    target = f'{request.path}?{q.urlencode()}'
    return redirect(target)


def _ajax_or_report(request, build_report, build_details, export_fn, template_name, report_type):
    ajax = (request.GET.get('ajax') or '').strip()
    export = (request.GET.get('export') or '').strip().lower()
    report_key = REPORT_KEY_BY_TYPE.get(report_type, 'margin')
    report_get = resolve_report_get(request, report_key)

    # Режим просмотра фиксируем в URL (удобно шарить ссылку / обновлять страницу)
    if 'view' not in request.GET and ajax != 'details' and export not in ('xlsx', 'excel', '1'):
        return _redirect_with_default_view(request)

    if ajax == 'details':
        try:
            payload = build_details(report_get)
            return JsonResponse(payload, encoder=DjangoJSONEncoder)
        except Exception as exc:
            return JsonResponse({'ok': False, 'error': str(exc), 'rows': []}, status=500)

    if export in ('xlsx', 'excel', '1'):
        return export_fn(report_get, request=request)

    report = build_report(report_get)
    attach_table_ui(report, request, report_key)
    active_saved = (request.GET.get('saved_filter') or report_get.get('saved_filter') or '').strip()
    report['report_key'] = report_key
    report['saved_filters'] = saved_filters_for_template(
        request.user, report_key, active_id=active_saved,
    )
    filters = report.get('filters')
    if isinstance(filters, dict):
        filters['saved_filter'] = active_saved
    params = {
        'type': report_type,
        'nav_selected': 4,
        **report,
    }
    response = render(request, template_name, {'params': params})
    view = report.get('view') or 'main'
    response.set_cookie(
        VIEW_COOKIE,
        view,
        max_age=VIEW_COOKIE_MAX_AGE,
        samesite='Lax',
    )
    return response


@login_required
def cumulative_margin_report(request):
    from asp.cumulative_margin_report import build_cumulative_margin_report, build_group_details
    from asp.excel_export import export_margin_xlsx

    return _ajax_or_report(
        request,
        build_cumulative_margin_report,
        build_group_details,
        export_margin_xlsx,
        'asp/cumulative_margin_report.html',
        'asp_cumulative_margin',
    )


@login_required
def stock_report(request):
    from asp.excel_export import export_stock_xlsx
    from asp.stock_report import build_stock_report, build_group_details

    return _ajax_or_report(
        request,
        build_stock_report,
        build_group_details,
        export_stock_xlsx,
        'asp/stock_report.html',
        'asp_stock_report',
    )


@login_required
def accepted_report(request):
    from asp.accepted_report import build_accepted_report, build_group_details
    from asp.excel_export import export_accepted_xlsx

    return _ajax_or_report(
        request,
        build_accepted_report,
        build_group_details,
        export_accepted_xlsx,
        'asp/accepted_report.html',
        'asp_accepted_report',
    )


@login_required
@require_POST
def report_columns_save(request):
    """Сохранение состава/порядка столбцов отчёта (cookie, как персональная настройка)."""
    import json

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)

    report_key = (payload.get('report_key') or '').strip()
    if report_key not in REPORTS and report_key != 'deal_calc_approval':
        return JsonResponse({'error': 'Неизвестный отчёт'}, status=400)

    columns = payload.get('columns')
    if not isinstance(columns, list):
        return JsonResponse({'error': 'Передайте массив columns'}, status=400)

    normalized = normalize_columns(report_key, columns)
    if not normalized:
        return JsonResponse({'error': 'Выберите хотя бы один столбец'}, status=400)

    response = JsonResponse({'ok': True, 'columns': normalized})
    response.set_cookie(
        cookie_name(report_key),
        columns_cookie_value(normalized),
        max_age=COLUMNS_COOKIE_MAX_AGE,
        samesite='Lax',
    )
    return response


@login_required
@require_POST
def report_saved_filter_save(request):
    """Создать / обновить сохранённый фильтр текущего отчёта."""
    import json

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Некорректный JSON'}, status=400)

    report_key = (payload.get('report_key') or '').strip()
    if report_key not in REPORTS:
        return JsonResponse({'ok': False, 'error': 'Неизвестный отчёт'}, status=400)

    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Укажите название'}, status=400)
    if len(name) > 200:
        return JsonResponse({'ok': False, 'error': 'Слишком длинное название'}, status=400)

    filter_data = payload.get('filter_data')
    if filter_data is None:
        filter_data = snapshot_filter_data(request.GET)
    if not isinstance(filter_data, dict):
        return JsonResponse({'ok': False, 'error': 'filter_data должен быть объектом'}, status=400)

    is_shared = bool(payload.get('is_shared'))
    if is_shared and not (request.user.is_staff or request.user.is_superuser):
        is_shared = False

    obj, created = ReportSavedFilter.objects.update_or_create(
        user=request.user,
        report_key=report_key,
        name=name,
        defaults={
            'filter_data': filter_data,
            'is_shared': is_shared,
        },
    )
    return JsonResponse({
        'ok': True,
        'id': obj.pk,
        'created': created,
        'message': 'Фильтр сохранён' if created else 'Фильтр обновлён',
    })


@login_required
@require_POST
def report_saved_filter_delete(request, filter_id):
    """Удалить свой (или любой — для superuser) сохранённый фильтр."""
    qs = ReportSavedFilter.objects.filter(pk=filter_id)
    if not request.user.is_superuser:
        qs = qs.filter(user=request.user)
    obj = qs.first()
    if obj is None:
        return JsonResponse({'ok': False, 'error': 'Фильтр не найден'}, status=404)
    obj.delete()
    return JsonResponse({'ok': True, 'message': 'Фильтр удалён'})
