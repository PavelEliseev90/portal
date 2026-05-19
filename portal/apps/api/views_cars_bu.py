from datetime import datetime

from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from django.db.models import (
    OuterRef,
    Subquery,
    Exists,
    Value,
    CharField,
    FloatField,
)
from django.db.models.functions import Coalesce

from prices_car_bu.models import CalculatedCumulativeData, IndicatorKVP
from documents.models import DocCarAgreement, DocCarShipment


def _annotate_cumulative_by_indicators(queryset, indicators):
    """Для каждого показателя КВП — amount, author, comment (0 / '' если записи нет)."""
    for indicator in indicators:
        calc_qs = CalculatedCumulativeData.objects.filter(
            agreement_id=OuterRef('pk'),
            indicatorKVP_id=indicator.pk,
        )
        prefix = f'cumulative_{indicator.pk}'
        queryset = queryset.annotate(
            **{
                f'{prefix}_amount': Coalesce(
                    Subquery(calc_qs.values('amount')[:1]),
                    Value(0.0),
                    output_field=FloatField(),
                ),
                f'{prefix}_author': Coalesce(
                    Subquery(calc_qs.values('author')[:1]),
                    Value(''),
                    output_field=CharField(),
                ),
                f'{prefix}_comment': Coalesce(
                    Subquery(calc_qs.values('comment')[:1]),
                    Value(''),
                    output_field=CharField(),
                ),
            }
        )
    return queryset


def _agreement_value_fields(indicators):
    fields = [
        'id',
        'uin',
        'nomer',
        'dataTime',
        'clientName',
        'unit__name',
        'has_shipment',
    ]
    for indicator in indicators:
        prefix = f'cumulative_{indicator.pk}'
        fields.extend([
            f'{prefix}_amount',
            f'{prefix}_author',
            f'{prefix}_comment',
        ])
    return fields


def _cumulative_rows_from_values(row, indicators):
    rows = []
    for indicator in indicators:
        prefix = f'cumulative_{indicator.pk}'
        rows.append({
            'indicatorKVP': {
                'id': indicator.pk,
                'name': indicator.name or '',
            },
            'amount': row.get(f'{prefix}_amount') or 0,
            'author': row.get(f'{prefix}_author') or '',
            'comment': row.get(f'{prefix}_comment') or '',
        })
    return rows


def _serialize_agreement_row(row, indicators):
    data_time = row.get('dataTime')
    return {
        'id': row['id'],
        'uin': row.get('uin') or '',
        'nomer': row.get('nomer') or '',
        'dataTime': data_time.isoformat() if data_time else None,
        'unit_name': row.get('unit__name') or '',
        'client_name': row.get('clientName') or '',
        'has_shipment': row['has_shipment'],
        'cumulative_data': _cumulative_rows_from_values(row, indicators),
    }


@api_view(['GET'])
def calculated_cumulative_data(request):
    indicators = list(IndicatorKVP.objects.order_by('name'))

    agreements = DocCarAgreement.objects.filter(unit__buauto=True, active=True)

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
        agreements = agreements.filter(client__name__icontains=customer)

    city = request.GET.get('city', '')
    if city:
        agreements = agreements.filter(client__city__name__icontains=city)

    agreements = agreements.annotate(
        has_shipment=Exists(
            DocCarShipment.objects.filter(agreement_id=OuterRef('pk'))
        ),
    )
    agreements = _annotate_cumulative_by_indicators(agreements, indicators)
    agreement_rows = agreements.order_by('-dataTime').values(
        *_agreement_value_fields(indicators)
    )

    answer = {
        'ok': True,
        'agreements': [
            _serialize_agreement_row(row, indicators)
            for row in agreement_rows
        ],
    }

    return JsonResponse(answer, status=status.HTTP_200_OK, safe=False)
