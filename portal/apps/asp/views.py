from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse, QueryDict
from django.shortcuts import redirect, render

from asp.report_common import VIEW_COOKIE, VIEW_COOKIE_MAX_AGE, preferred_view_from_cookie

ASP_VARIANT_TEMPLATES = {
    '1': 'asp/asp.html',
    '2': 'asp/asp_bento.html',
    '3': 'asp/asp_command.html',
    '4': 'asp/asp_22c.html',
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

    # Режим просмотра фиксируем в URL (удобно шарить ссылку / обновлять страницу)
    if 'view' not in request.GET and ajax != 'details' and export not in ('xlsx', 'excel', '1'):
        return _redirect_with_default_view(request)

    if ajax == 'details':
        try:
            payload = build_details(request.GET)
            return JsonResponse(payload, encoder=DjangoJSONEncoder)
        except Exception as exc:
            return JsonResponse({'ok': False, 'error': str(exc), 'rows': []}, status=500)

    if export in ('xlsx', 'excel', '1'):
        return export_fn(request.GET)

    report = build_report(request.GET)
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
