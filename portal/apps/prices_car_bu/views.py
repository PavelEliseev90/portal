from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from documents.models import DocCarAgreement
from refs.models import RefUnit

from .models import CalculatedCumulativeData, IndicatorKVP


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


def _default_list_dates():
    today = timezone.localdate()
    return today.replace(day=1), today


@login_required
def cumulative_list(request):
    qs = CalculatedCumulativeData.objects.select_related(
        'agreement',
        'agreement__unit',
        'agreement__cars',
        'indicatorKVP',
    )

    date_from = _parse_date(request.GET.get('date_from', ''))
    date_to = _parse_date(request.GET.get('date_to', ''))
    agreement_nomer = request.GET.get('agreement_nomer', '').strip()
    vin = request.GET.get('vin', '').strip()
    unit_ids = request.GET.getlist('unit')
    indicator_ids = request.GET.getlist('indicator')
    send_1c_filter = request.GET.get('send_1c', '').strip()

    has_explicit_filters = any([
        request.GET.get('date_from', '').strip(),
        request.GET.get('date_to', '').strip(),
        agreement_nomer,
        vin,
        unit_ids,
        indicator_ids,
        send_1c_filter,
        request.GET.get('page', '').strip(),
    ])
    if not has_explicit_filters:
        date_from, date_to = _default_list_dates()

    if date_from:
        qs = qs.filter(agreement__dataTime__date__gte=date_from)
    if date_to:
        qs = qs.filter(agreement__dataTime__date__lte=date_to)
    if agreement_nomer:
        qs = qs.filter(agreement__nomer__icontains=agreement_nomer)
    if vin:
        qs = qs.filter(
            Q(agreement__cars__vin__icontains=vin)
            | Q(agreement__cars__vin2__icontains=vin)
        ).distinct()
    if unit_ids:
        qs = qs.filter(agreement__unit_id__in=unit_ids)
    if indicator_ids:
        qs = qs.filter(indicatorKVP_id__in=indicator_ids)
    if send_1c_filter == '1':
        qs = qs.filter(send_1c=True)
    elif send_1c_filter == '0':
        qs = qs.filter(send_1c=False)

    qs = qs.order_by('-agreement__dataTime', '-id')

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    units = RefUnit.objects.filter(buauto=True).order_by('name')
    indicators = IndicatorKVP.objects.all().order_by('name')

    date_from_str = date_from.strftime('%Y-%m-%d') if date_from else ''
    date_to_str = date_to.strftime('%Y-%m-%d') if date_to else ''

    context = {
        'page_obj': page_obj,
        'items': page_obj,
        'units': units,
        'indicators': indicators,
        'filters': {
            'date_from': request.GET.get('date_from', '') or date_from_str,
            'date_to': request.GET.get('date_to', '') or date_to_str,
            'agreement_nomer': agreement_nomer,
            'vin': vin,
            'unit': unit_ids,
            'indicator': indicator_ids,
            'send_1c': send_1c_filter,
        },
        'filtered_count': paginator.count,
    }
    return render(request, 'prices_car_bu/cumulative_list.html', context)


@login_required
def cumulative_detail(request, pk):
    item = get_object_or_404(
        CalculatedCumulativeData.objects.select_related(
            'agreement',
            'agreement__unit',
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

    context = {
        'item': item,
        'agreement': agreement,
        'agreement_rows': agreement_rows,
        'same_agreement_items': same_agreement_items,
    }
    return render(request, 'prices_car_bu/cumulative_detail.html', context)


@login_required
def cumulative_send_1c(request, pk):
    from task_manager.views import send_agreement_cumulative_to_1c

    item = get_object_or_404(
        CalculatedCumulativeData.objects.select_related(
            'agreement__unit__ib',
            'indicatorKVP',
        ),
        pk=pk,
    )
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('prices_car_bu:cumulative_detail', args=[pk]))

    result = send_agreement_cumulative_to_1c(item)
    if result.get('ok'):
        messages.success(request, 'Данные отправлены в 1С.')
    else:
        messages.error(
            request,
            'Не удалось отправить в 1С: {}'.format(result.get('error') or 'ошибка'),
        )
    return HttpResponseRedirect(reverse('prices_car_bu:cumulative_detail', args=[pk]))


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



    
