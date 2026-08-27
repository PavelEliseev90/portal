from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from documents.models import DocCarAgreement
from refs.models import RefUnit

from .models import CalculatedCumulativeData, IndicatorKVP

CUMULATIVE_SEND_BATCH_LIMIT = 200
CUMULATIVE_FLAG_BATCH_LIMIT = 5000


_AGREEMENT_DETAIL_FIELDS = (
    ('nomer', 'Номер'),
    ('dataTime', 'Дата'),
    ('active', 'Проведен'),
    ('unit', 'Подразделение'),
    ('organization', 'Организация'),
    ('client', 'Клиент'),
    ('clientName', 'Наименование клиента'),
    ('staff', 'Менеджер'),
    ('cars', 'Автомобиль'),
    ('amount', 'Сумма продажи'),
    ('cost_price', 'Себестоимость'),
    ('outlay', 'Расходы на АМ'),
    ('discountAmount', 'Скидка итог'),
    ('discountAmountTorg', 'Скидка торг'),
    ('discountAmountTradeIN', 'Скидка трейдин'),
    ('run', 'Пробег'),
    ('owners', 'Владельцев'),
    ('typeSale', 'Тип продажи'),
    ('bu_wheels_est', 'Расчетные данные бу шины'),
    ('bu_wheels_actual', 'Фактические данные бу шины'),
    ('kso_est', 'Расчетные данные ксо'),
    ('kso_actual', 'Фактические данные ксо'),
    ('cm_est', 'КМ расчетный'),
    ('cm_actual', 'КМ фактический'),
    ('cm_goal', 'КМ целевой'),
    ('check_estimated', 'Правило расчетное выполнено'),
    ('check_actual', 'Правило фактическое выполнено'),
    ('check_text', 'Правило'),
    ('rlk', 'РЛК'),
    ('lo', 'Лист оценки'),
    ('uin', 'uin'),
)


def _parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _agreement_field_rows(agreement):
    """Основные поля соглашения для детальной карточки."""
    if not agreement:
        return []
    rows = []
    for field_name, label in _AGREEMENT_DETAIL_FIELDS:
        try:
            value = getattr(agreement, field_name, None)
        except Exception:
            continue
        if value is None or value == '':
            display = '—'
        elif hasattr(value, 'pk'):
            display = str(value)
        elif isinstance(value, bool):
            display = 'Да' if value else 'Нет'
        elif isinstance(value, datetime):
            display = timezone.localtime(value).strftime('%d.%m.%Y %H:%M') if timezone.is_aware(value) else value.strftime('%d.%m.%Y %H:%M')
        elif isinstance(value, float):
            display = f'{value:,.2f}'.replace(',', ' ')
        else:
            display = str(value)
        rows.append({
            'name': field_name,
            'label': label,
            'value': display,
        })
    return rows


def _today():
    now = timezone.now()
    if timezone.is_aware(now):
        return timezone.localtime(now).date()
    return now.date()


def _default_list_dates():
    today = _today()
    return today.replace(day=1), today


def cumulative_1c_target(agreement):
    """Куда слать: Альфа-Авто (unit.ib.alfa) или КорсАвто."""
    from task_manager.views import resolve_agreement_cumulative_1c_target
    _url, code, name = resolve_agreement_cumulative_1c_target(agreement)
    return code, name


def attach_cumulative_1c_target(item):
    code, name = cumulative_1c_target(getattr(item, 'agreement', None))
    item.target = code
    item.target_name = name
    return item


def cumulative_unsent_qs():
    return CalculatedCumulativeData.objects.filter(send_1c=False).select_related(
        'agreement',
        'agreement__unit',
        'agreement__unit__ib',
        'agreement__cars',
        'indicatorKVP',
    ).order_by('-agreement__dataTime', '-id')


def cumulative_hub_counts():
    qs = CalculatedCumulativeData.objects.filter(send_1c=False)
    alfa_q = Q(agreement__unit__ib__alfa=True)
    return {
        'cumulative_unsent': qs.count(),
        'cumulative_unsent_alfa': qs.filter(alfa_q).count(),
        'cumulative_unsent_kors': qs.exclude(alfa_q).count(),
    }


def send_cumulative_item(item):
    from task_manager.views import send_agreement_cumulative_to_1c

    result = send_agreement_cumulative_to_1c(item)
    agreement = getattr(item, 'agreement', None)
    nomer = (agreement.nomer if agreement else '') or ''
    vin = ''
    if agreement and getattr(agreement, 'cars', None):
        vin = agreement.cars.vin or ''
    indicator = getattr(item.indicatorKVP, 'name', '') or ''
    title = ' · '.join(p for p in (nomer, indicator) if p) or f'#{item.pk}'
    return {
        'id': item.pk,
        'title': title,
        'agreement_id': getattr(agreement, 'pk', None),
        'vin': vin,
        'ok': bool(result.get('ok')),
        'status_code': result.get('status_code'),
        'text': (result.get('text') or '')[:500],
        'error': result.get('error'),
        'target': result.get('target'),
        'target_name': result.get('target_name'),
    }


def _list_filter_values(request):
    params = request.GET
    date_from = _parse_date(params.get('date_from', ''))
    date_to = _parse_date(params.get('date_to', ''))
    agreement_nomer = params.get('agreement_nomer', '').strip()
    vin = params.get('vin', '').strip()
    unit_ids = params.getlist('unit')
    indicator_ids = params.getlist('indicator')
    send_1c_filter = params.get('send_1c', '').strip()
    target_filter = params.get('target', '').strip()

    has_explicit_filters = any([
        params.get('date_from', '').strip(),
        params.get('date_to', '').strip(),
        agreement_nomer,
        vin,
        unit_ids,
        indicator_ids,
        send_1c_filter,
        target_filter,
        params.get('page', '').strip(),
    ])
    if not has_explicit_filters:
        date_from, date_to = _default_list_dates()

    return {
        'date_from': date_from,
        'date_to': date_to,
        'agreement_nomer': agreement_nomer,
        'vin': vin,
        'unit_ids': unit_ids,
        'indicator_ids': indicator_ids,
        'send_1c': send_1c_filter,
        'target': target_filter,
    }


def _filtered_cumulative_qs(filters, *, apply_send_filter=True):
    qs = CalculatedCumulativeData.objects.select_related(
        'agreement',
        'agreement__unit',
        'agreement__unit__ib',
        'agreement__cars',
        'indicatorKVP',
    )
    date_from = filters.get('date_from')
    date_to = filters.get('date_to')
    if date_from:
        qs = qs.filter(agreement__dataTime__date__gte=date_from)
    if date_to:
        qs = qs.filter(agreement__dataTime__date__lte=date_to)
    if filters.get('agreement_nomer'):
        qs = qs.filter(agreement__nomer__icontains=filters['agreement_nomer'])
    if filters.get('vin'):
        qs = qs.filter(
            Q(agreement__cars__vin__icontains=filters['vin'])
            | Q(agreement__cars__vin2__icontains=filters['vin'])
        ).distinct()
    if filters.get('unit_ids'):
        qs = qs.filter(agreement__unit_id__in=filters['unit_ids'])
    if filters.get('indicator_ids'):
        qs = qs.filter(indicatorKVP_id__in=filters['indicator_ids'])
    if apply_send_filter:
        if filters.get('send_1c') == '1':
            qs = qs.filter(send_1c=True)
        elif filters.get('send_1c') == '0':
            qs = qs.filter(send_1c=False)
    target = filters.get('target')
    if target == 'alfa':
        qs = qs.filter(agreement__unit__ib__alfa=True)
    elif target == 'kors':
        qs = qs.filter(
            Q(agreement__unit__ib__alfa=False)
            | Q(agreement__unit__ib__isnull=True)
            | Q(agreement__unit__isnull=True)
        )
    return qs.order_by('-agreement__dataTime', '-id')


@login_required
def cumulative_list(request):
    filters = _list_filter_values(request)
    qs = _filtered_cumulative_qs(filters)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    for item in page_obj.object_list:
        attach_cumulative_1c_target(item)

    units = RefUnit.objects.filter(buauto=True).order_by('name')
    indicators = IndicatorKVP.objects.all().order_by('name')

    date_from_str = filters['date_from'].strftime('%Y-%m-%d') if filters['date_from'] else ''
    date_to_str = filters['date_to'].strftime('%Y-%m-%d') if filters['date_to'] else ''
    unsent_count = _filtered_cumulative_qs(filters, apply_send_filter=False).filter(send_1c=False).count()
    send_results = request.session.pop('cumulative_send_1c_results', None)

    context = {
        'page_obj': page_obj,
        'items': page_obj,
        'units': units,
        'indicators': indicators,
        'filters': {
            'date_from': request.GET.get('date_from', '') or date_from_str,
            'date_to': request.GET.get('date_to', '') or date_to_str,
            'agreement_nomer': filters['agreement_nomer'],
            'vin': filters['vin'],
            'unit': filters['unit_ids'],
            'unit_ids_list': [
                int(v) for v in filters['unit_ids'] if str(v).strip().isdigit()
            ],
            'indicator': filters['indicator_ids'],
            'indicator_ids_list': [
                int(v) for v in filters['indicator_ids'] if str(v).strip().isdigit()
            ],
            'send_1c': filters['send_1c'],
            'target': filters['target'],
        },
        'filtered_count': paginator.count,
        'unsent_count': unsent_count,
        'send_limit': CUMULATIVE_SEND_BATCH_LIMIT,
        'flag_limit': CUMULATIVE_FLAG_BATCH_LIMIT,
        'send_results': send_results or [],
        'query_string': request.GET.urlencode(),
    }
    return render(request, 'prices_car_bu/cumulative_list.html', context)


@login_required
def cumulative_detail(request, pk):
    item = get_object_or_404(
        CalculatedCumulativeData.objects.select_related(
            'agreement',
            'agreement__unit',
            'agreement__unit__ib',
            'agreement__cars',
            'agreement__staff',
            'agreement__client',
            'agreement__organization',
            'agreement__rlk',
            'agreement__lo',
            'indicatorKVP',
        ),
        pk=pk,
    )
    agreement = item.agreement
    agreement_rows = _agreement_field_rows(agreement)
    same_agreement_items = []
    if agreement:
        same_agreement_items = list(
            CalculatedCumulativeData.objects.filter(
                agreement=agreement,
            ).select_related('indicatorKVP').order_by('indicatorKVP__name')
        )

    attach_cumulative_1c_target(item)
    context = {
        'item': item,
        'agreement': agreement,
        'agreement_rows': agreement_rows,
        'same_agreement_items': same_agreement_items,
    }
    return render(request, 'prices_car_bu/cumulative_detail.html', context)


def _cumulative_list_redirect(request):
    url = reverse('prices_car_bu:cumulative_list')
    query = request.GET.urlencode()
    if query:
        return HttpResponseRedirect(f'{url}?{query}')
    return HttpResponseRedirect(url)


@login_required
def cumulative_send_1c(request, pk):
    item = get_object_or_404(
        CalculatedCumulativeData.objects.select_related(
            'agreement__unit__ib',
            'agreement__cars',
            'indicatorKVP',
        ),
        pk=pk,
    )
    next_url = request.POST.get('next') or reverse('prices_car_bu:cumulative_detail', args=[pk])
    if request.method != 'POST':
        return HttpResponseRedirect(next_url)

    result = send_cumulative_item(item)
    target_name = result.get('target_name') or '1С'
    if result.get('ok'):
        messages.success(request, 'Данные отправлены в {}.'.format(target_name))
    else:
        messages.error(
            request,
            'Не удалось отправить в {}: {}'.format(
                target_name,
                result.get('error') or 'ошибка',
            ),
        )
    return HttpResponseRedirect(next_url)


@login_required
@require_POST
def cumulative_send_1c_batch(request):
    """Массовая отправка неотправленных записей по текущему фильтру списка (макс. 200)."""
    filters = _list_filter_values(request)
    qs = _filtered_cumulative_qs(filters, apply_send_filter=False).filter(send_1c=False)
    results = []
    for item in list(qs[:CUMULATIVE_SEND_BATCH_LIMIT]):
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

    request.session['cumulative_send_1c_results'] = results
    ok_n = sum(1 for r in results if r.get('ok'))
    fail_n = len(results) - ok_n
    if results:
        messages.info(
            request,
            'Отправка расчётных КВП: успешно {}, ошибок {} (детали ниже).'.format(ok_n, fail_n),
        )
    else:
        messages.warning(request, 'Нет неотправленных записей по текущему фильтру.')
    return _cumulative_list_redirect(request)


@login_required
@require_POST
def cumulative_set_send_1c_flag(request):
    """
    Массово проставить признак send_1c по текущему фильтру списка
    (без реальной отправки/удаления в 1С).
    """
    action = (request.POST.get('action') or '').strip()
    if action not in ('mark_sent', 'mark_unsent'):
        messages.error(request, 'Неизвестное действие.')
        return _cumulative_list_redirect(request)

    filters = _list_filter_values(request)
    qs = _filtered_cumulative_qs(filters)
    total = qs.count()
    if total == 0:
        messages.warning(request, 'Нет записей по текущему фильтру.')
        return _cumulative_list_redirect(request)
    if total > CUMULATIVE_FLAG_BATCH_LIMIT:
        messages.error(
            request,
            'Слишком много записей ({}). Сузьте фильтр (лимит {}).'.format(
                total,
                CUMULATIVE_FLAG_BATCH_LIMIT,
            ),
        )
        return _cumulative_list_redirect(request)

    new_value = action == 'mark_sent'
    updated = qs.update(send_1c=new_value)
    if new_value:
        messages.success(
            request,
            'По текущему фильтру помечено как отправленные: {}.'.format(updated),
        )
    else:
        messages.success(
            request,
            'По текущему фильтру помечено как не отправленные: {}.'.format(updated),
        )
    return _cumulative_list_redirect(request)


@login_required
def cumulative_delete(request, pk):
    from task_manager.views import delete_agreement_cumulative_from_1c

    item = get_object_or_404(
        CalculatedCumulativeData.objects.select_related(
            'agreement__unit__ib',
            'indicatorKVP',
        ),
        pk=pk,
    )
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('prices_car_bu:cumulative_detail', args=[pk]))

    if item.send_1c:
        result = delete_agreement_cumulative_from_1c(item)
        if not result.get('ok'):
            messages.error(
                request,
                'Не удалось удалить в 1С: {}'.format(result.get('error') or 'ошибка'),
            )
            return HttpResponseRedirect(reverse('prices_car_bu:cumulative_detail', args=[pk]))

    item.delete()
    messages.success(request, 'Запись расчётных данных кумулятива удалена.')
    return HttpResponseRedirect(reverse('prices_car_bu:cumulative_list'))



    
