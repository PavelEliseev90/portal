from datetime import datetime

from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from django.db.models import Exists, Max, OuterRef, Q, Value
from django.db.models.functions import Coalesce
import json

from django.db import transaction

from prices_car_bu.models import CalculatedCumulativeData, IndicatorKVP
from documents.models import DocCarAgreement, DocCarShipment
from refs.models import RefUnit, RefCity
from task_manager.views import send_agreement_cumulative_to_1c

# Поля из 1С → показатель IndicatorKVP (режим ОПФУ)
_KSO_PAYLOAD = (
    ('КВРасчетнаяОСАГО', 'КВРасчетнаяОСАГОКомментарий', 'osago', {'osago': True}),
    ('КВРасчетнаяКаско', 'КВРасчетнаяКаскоКомментарий', 'kasko', {'kasko': True}),
    ('КВРасчетнаяКредит', 'КВРасчетнаяКредитКомментарий', 'credit', {'credit': True}),
    ('КВРасчетнаяЖизнь', 'КВРасчетнаяЖизньКомментарий', 'life', {'life': True}),
    ('КВРасчетнаяГАП', 'КВРасчетнаяГАПКомментарий', 'gap', {'gap': True}),
)


@api_view(['GET'])
def calculated_cumulative_data(request):
    agreements = DocCarAgreement.objects.filter(unit__bu_auto=True, active=True)

    now = datetime.now()
    date_start = request.GET.get('date_start', '').strip()
    if not date_start:
        date_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    date_end = request.GET.get('date_end', '').strip()
    if not date_end:
        date_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    agreements = agreements.filter(dataTime__gte=date_start, dataTime__lte=date_end)

    unit_name = request.GET.get('unit_name', '')
    if unit_name:
        agreements = agreements.filter(unit__name__icontains=unit_name)

    number = request.GET.get('number', '')
    if number:
        agreements = agreements.filter(nomer__icontains=number)

    customer = request.GET.get('customer', '')
    if customer:
        agreements = agreements.filter(customer__name__icontains=customer)

    city = request.GET.get('city', '')
    if city:
        agreements = agreements.filter(client__city__name__icontains=city)

    q_bu_wheels = Q(calculatedcumulativedata__indicatorKVP__bu_wheels=True)
    q_osago = Q(calculatedcumulativedata__indicatorKVP__osago=True)
    q_kasko = Q(calculatedcumulativedata__indicatorKVP__kasko=True)
    q_credit = Q(calculatedcumulativedata__indicatorKVP__credit=True)
    q_gap = Q(calculatedcumulativedata__indicatorKVP__gap=True)
    q_life = Q(calculatedcumulativedata__indicatorKVP__life=True)

    q_bu_kso = (
        Q(indicatorKVP__osago=True)
        | Q(indicatorKVP__kasko=True)
        | Q(indicatorKVP__credit=True)
        | Q(indicatorKVP__gap=True)
        | Q(indicatorKVP__life=True)
    )

    agreements = agreements.annotate(
        has_shipment=Exists(
            DocCarShipment.objects.filter(agreement_id=OuterRef('pk')),
        ),
        has_bu_wheels=Exists(
            CalculatedCumulativeData.objects.filter(
                agreement_id=OuterRef('pk'),
                indicatorKVP__bu_wheels=True,
            ),
        ),
        has_bu_kso=Exists(
            CalculatedCumulativeData.objects.filter(
                agreement_id=OuterRef('pk'),
            ).filter(q_bu_kso),
        ),
        bu_wheels_amount=Coalesce(
            Max('calculatedcumulativedata__amount', filter=q_bu_wheels),
            Value(0.0),
        ),
        bu_wheels_author=Coalesce(
            Max('calculatedcumulativedata__author', filter=q_bu_wheels),
            Value(''),
        ),
        bu_wheels_comment=Coalesce(
            Max('calculatedcumulativedata__comment', filter=q_bu_wheels),
            Value(''),
        ),
        osago_amount=Coalesce(
            Max('calculatedcumulativedata__amount', filter=q_osago),
            Value(0.0),
        ),
        osago_author=Coalesce(
            Max('calculatedcumulativedata__author', filter=q_osago),
            Value(''),
        ),
        osago_comment=Coalesce(
            Max('calculatedcumulativedata__comment', filter=q_osago),
            Value(''),
        ),
        kasko_amount=Coalesce(
            Max('calculatedcumulativedata__amount', filter=q_kasko),
            Value(0.0),
        ),
        kasko_author=Coalesce(
            Max('calculatedcumulativedata__author', filter=q_kasko),
            Value(''),
        ),
        kasko_comment=Coalesce(
            Max('calculatedcumulativedata__comment', filter=q_kasko),
            Value(''),
        ),
        credit_amount=Coalesce(
            Max('calculatedcumulativedata__amount', filter=q_credit),
            Value(0.0),
        ),
        credit_author=Coalesce(
            Max('calculatedcumulativedata__author', filter=q_credit),
            Value(''),
        ),
        credit_comment=Coalesce(
            Max('calculatedcumulativedata__comment', filter=q_credit),
            Value(''),
        ),
        gap_amount=Coalesce(
            Max('calculatedcumulativedata__amount', filter=q_gap),
            Value(0.0),
        ),
        gap_author=Coalesce(
            Max('calculatedcumulativedata__author', filter=q_gap),
            Value(''),
        ),
        gap_comment=Coalesce(
            Max('calculatedcumulativedata__comment', filter=q_gap),
            Value(''),
        ),
        life_amount=Coalesce(
            Max('calculatedcumulativedata__amount', filter=q_life),
            Value(0.0),
        ),
        life_author=Coalesce(
            Max('calculatedcumulativedata__author', filter=q_life),
            Value(''),
        ),
        life_comment=Coalesce(
            Max('calculatedcumulativedata__comment', filter=q_life),
            Value(''),
        ),
    )

    agreement_rows = agreements.order_by('-dataTime').values(
        'id',
        'uin',
        'nomer',
        'dataTime',
        'client__name',
        'unit__name',
        'date_planed_sale',
        'staff__name',
        'amount',
        'lo__carsGRZ',
        'lo__run',
        'lo__year',
        'lo__vin',
        'lo__modification_autoru__model__mark__name',
        'lo__modification_autoru__model__name',
        'lo__modification_autoru__name',
        'has_shipment',
        'has_bu_wheels',
        'has_bu_kso',
        'bu_wheels_amount',
        'bu_wheels_author',
        'bu_wheels_comment',
        'osago_amount',
        'osago_author',
        'osago_comment',
        'kasko_amount',
        'kasko_author',
        'kasko_comment',
        'credit_amount',
        'credit_author',
        'credit_comment',
        'gap_amount',
        'gap_author',
        'gap_comment',
        'life_amount',
        'life_author',
        'life_comment',
    )
    
    units = RefUnit.objects.filter(buauto=True).filter(name__icontains = 'КорсАвто').values_list('name', flat=True).order_by('name')
    citys = RefCity.objects.values_list('name', flat=True).order_by('name')

    answer = {
        'ok': True,
        'units': list(units),
        'citys': list(citys),
        'agreements': list(agreement_rows),
    }

    return JsonResponse(answer, status=status.HTTP_200_OK, safe=False)

def _parse_request_json(request):
    if getattr(request, 'data', None):
        return request.data
    raw = request.body.decode('utf-8') if request.body else ''
    if not raw.strip():
        raise ValueError('Пустое тело запроса')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(raw.replace("'", '"'))


def _is_opfu(value):
    if value is True or value == 1:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'да', 'yes', 'истина')
    return False


def _to_float(value):
    if value is None or value == '':
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError('Некорректная сумма: %r' % value)


def _to_str(value):
    if value is None:
        return ''
    return str(value).strip()


def _get_agreement(data):
    agreement_id = data.get('agreement_id') or data.get('id')
    if agreement_id is not None and str(agreement_id).strip() != '':
        return DocCarAgreement.objects.get(pk=agreement_id)

    uin = data.get('uin') or data.get('Uin') or data.get('agreement_uin')
    if uin:
        return DocCarAgreement.objects.get(uin=uin)

    raise DocCarAgreement.DoesNotExist()


def _upsert_cumulative(agreement, indicator_filter, amount, author, comment):
   
    indicator = IndicatorKVP.objects.filter(**indicator_filter).first()
    if indicator is None:
        raise ValueError(
            'Показатель КВП не найден в справочнике: %s' % indicator_filter
        )

    obj, created = CalculatedCumulativeData.objects.update_or_create(
        agreement=agreement,
        indicatorKVP=indicator,
        defaults={
            'amount': amount,
            'author': author,
            'comment': comment,
            'send_1c': False,
        },
    )
    return obj, created


def _send_cumulative_row(obj, created):
    """Отправка в 1С после commit. Ошибка 1С не откатывает сохранение."""
    row = CalculatedCumulativeData.objects.select_related(
        'agreement__unit__ib',
        'indicatorKVP',
    ).get(pk=obj.pk)
    send_result = send_agreement_cumulative_to_1c(row)
    indicator = row.indicatorKVP
    return {
        'indicator': (indicator.name if indicator else '') or '',
        'id': obj.pk,
        'created': created,
        'amount': obj.amount,
        'send_1c': send_result.get('ok', False),
        'target': send_result.get('target'),
        'target_name': send_result.get('target_name'),
        'status_code': send_result.get('status_code'),
        'error': send_result.get('error'),
    }


@api_view(['POST'])
def calculated_cumulative_data_create_or_edit(request):
    
    try:
        data = _parse_request_json(request)
    except (ValueError, json.JSONDecodeError) as exc:
        return JsonResponse(
            {'ok': False, 'error': 'Ошибка разбора JSON: %s' % exc},
            status=status.HTTP_400_BAD_REQUEST,
            safe=False,
        )

    try:
        agreement = _get_agreement(data)
    except DocCarAgreement.DoesNotExist:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Соглашение не найдено. Укажите корректный agreement_id или uin.',
            },
            status=status.HTTP_404_NOT_FOUND,
            safe=False,
        )
    except (TypeError, ValueError) as exc:
        return JsonResponse(
            {'ok': False, 'error': str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
            safe=False,
        )

    author = _to_str(data.get('Автор') or data.get('author'))
    is_opfu = _is_opfu(data.get('ОПФУ', data.get('opfu')))

    saved = []
    pending = []
    errors = []

    try:
        with transaction.atomic():
            if is_opfu:
                for amount_key, comment_key, code, indicator_filter in _KSO_PAYLOAD:
                    try:
                        obj, created = _upsert_cumulative(
                            agreement,
                            indicator_filter,
                            _to_float(data.get(amount_key)),
                            author,
                            _to_str(data.get(comment_key)),
                        )
                        pending.append((obj, created))
                    except ValueError as exc:
                        errors.append({
                            'indicator': code,
                            'field': amount_key,
                            'message': str(exc),
                        })
            else:
                try:
                    obj, created = _upsert_cumulative(
                        agreement,
                        {'bu_wheels': True},
                        _to_float(data.get('КВРасчетнаяБуРезина')),
                        author,
                        _to_str(data.get('КВРасчетнаяБуРезинаКомментарий', '')),
                    )
                    pending.append((obj, created))
                except ValueError as exc:
                    errors.append({
                        'indicator': 'bu_wheels',
                        'field': 'КВРасчетнаяБуРезина',
                        'message': str(exc),
                    })

            if errors:
                raise ValueError('Не все показатели сохранены')

    except ValueError:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Ошибка сохранения расчётных данных',
                'mode': 'opfu' if is_opfu else 'bu_wheels',
                'agreement_id': agreement.pk,
                'saved': saved,
                'errors': errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
            safe=False,
        )
    except Exception as exc:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Непредвиденная ошибка: %s' % exc,
                'agreement_id': agreement.pk,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            safe=False,
        )

    for obj, created in pending:
        saved.append(_send_cumulative_row(obj, created))

    return JsonResponse(
        {
            'ok': True,
            'message': 'Расчётные данные успешно сохранены',
            'mode': 'opfu' if is_opfu else 'bu_wheels',
            'agreement_id': agreement.pk,
            'saved': saved,
        },
        status=status.HTTP_200_OK,
        safe=False,
    )