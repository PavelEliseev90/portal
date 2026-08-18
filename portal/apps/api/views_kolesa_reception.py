"""API приёмки второго комплекта колёс для базы БУ колес."""
import json
from datetime import datetime

from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http.response import JsonResponse
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view

from eco.reception import build_kolesa_reception_send_payload
from register.models import RegInteractivOcenkaKolesaReception


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


def _parse_bool_param(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ('1', 'true', 'yes', 'да', 'sent', 'отправлен', 'отправлено'):
        return True
    if text in ('0', 'false', 'no', 'нет', 'not_sent', 'неотправлен', 'неотправлено'):
        return False
    raise ValueError('Некорректное значение send_wheels_ib: %r' % value)


def _parse_date(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_accept_datetime(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value

    parsed = parse_datetime(str(value).strip())
    if parsed is not None:
        return parsed

    parsed_date = parse_date(str(value).strip())
    if parsed_date is not None:
        return datetime.combine(parsed_date, datetime.min.time())

    text = str(value).strip()
    for fmt in (
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%d.%m.%Y',
        '%d.%m.%Y %H:%M:%S',
    ):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue

    raise ValueError('Некорректная дата: %r' % value)


def _parse_document_number(value):
    if value is None:
        return None
    text = str(value).strip()
    return text[:64] if text else None


def _kolesa_reception_queryset():
    return (
        RegInteractivOcenkaKolesaReception.objects
        .select_related(
            'rlk',
            'estimation',
            'estimation__page_kolesa',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
            'mark_tyre', 'width_tyre', 'profil_tyre', 'radius', 'sezon',
            'disk_type', 'et_disk', 'dia_disk', 'psd_disk', 'user',
        )
        .filter(estimation__page_kolesa__kolesa2_estimation=1)
        .order_by('-date', '-id')
    )


def _car_label(estimation):
    if estimation is None:
        return ''
    if estimation.modification_id and estimation.modification:
        mod = estimation.modification
        if mod.model_id and mod.model:
            mark = mod.model.mark.name if mod.model.mark_id else ''
            return f'{mark} {mod.model.name} {mod.name}'.strip()
    parts = [estimation.mark_name, estimation.model_name, estimation.modification_name]
    label = ' '.join(p for p in parts if p)
    return label or estimation.vin or estimation.number_body or ''


def _serialize_list_row(reception, include_data=False, request=None):
    estimation = reception.estimation
    rlk = reception.rlk
    row = {
        'id': reception.pk,
        'KolesaReceptionId': reception.pk,
        'send_wheels_ib': bool(reception.send_wheels_ib),
        'send_wheels_ib_date': reception.send_wheels_ib_date,
        'send_wheels_ib_number': reception.send_wheels_ib_number or '',
        'date': reception.date,
        'estimation_id': estimation.pk if estimation else None,
        'EstimationId': estimation.pk if estimation else None,
        'vin': (estimation.vin or estimation.number_body or '') if estimation else '',
        'car_label': _car_label(estimation),
        'rlk_id': rlk.pk if rlk else None,
        'rlk_number': rlk.nomer if rlk else '',
        'rlk_uin': rlk.uin if rlk else '',
        'count_disk': reception.count_disk or 0,
        'count_tyre': reception.count_tyre or 0,
    }
    if include_data:
        row['data'] = build_kolesa_reception_send_payload(reception, request=request)
    return row


def _json_response(payload, http_status=status.HTTP_200_OK):
    return JsonResponse(payload, status=http_status, safe=False, encoder=DjangoJSONEncoder)


def _apply_list_filters(qs, request):
    send_param = (
        request.GET.get('send_wheels_ib')
        or request.GET.get('sent')
        or request.GET.get('send')
    )
    if send_param is not None and str(send_param).strip() != '':
        try:
            sent = _parse_bool_param(send_param)
        except ValueError as exc:
            return None, str(exc)
        if sent:
            qs = qs.filter(send_wheels_ib=True)
        else:
            qs = qs.filter(Q(send_wheels_ib=False) | Q(send_wheels_ib__isnull=True))

    date_from = _parse_date(request.GET.get('date_from', ''))
    date_to = _parse_date(request.GET.get('date_to', ''))
    if date_from:
        qs = qs.filter(date__date__gte=date_from)
    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    vin = (request.GET.get('vin') or '').strip()
    if vin:
        qs = qs.filter(
            Q(estimation__vin__icontains=vin)
            | Q(estimation__number_body__icontains=vin)
        )

    rlk_number = (request.GET.get('rlk') or request.GET.get('rlk_number') or '').strip()
    if rlk_number:
        qs = qs.filter(rlk__nomer__icontains=rlk_number)

    rlk_uin = (request.GET.get('rlk_uin') or request.GET.get('Uin') or request.GET.get('uin') or '').strip()
    if rlk_uin:
        qs = qs.filter(rlk__uin=rlk_uin)

    reception_id = (request.GET.get('id') or request.GET.get('KolesaReceptionId') or '').strip()
    if reception_id.isdigit():
        qs = qs.filter(pk=int(reception_id))

    return qs, None


@api_view(['GET'])
def kolesa_reception_list(request):
    """
    Список приёмок второго комплекта колёс.

    GET-параметры:
    - send_wheels_ib / sent / send: 1|0|true|false|sent|not_sent
    - date_from, date_to (YYYY-MM-DD или DD.MM.YYYY)
    - vin, rlk / rlk_number, rlk_uin / Uin, id / KolesaReceptionId
    - page (default 1), page_size (default 50, max 200)
    - with_data=1 — полный JSON (Rlk, Lo, KolesaReception, ...) в каждой строке
    """
    qs = _kolesa_reception_queryset()
    qs, filter_error = _apply_list_filters(qs, request)
    if filter_error:
        return _json_response({'ok': False, 'error': filter_error}, status.HTTP_400_BAD_REQUEST)

    try:
        page_size = min(max(int(request.GET.get('page_size', 50) or 50), 1), 200)
    except (TypeError, ValueError):
        page_size = 50
    try:
        page_num = max(int(request.GET.get('page', 1) or 1), 1)
    except (TypeError, ValueError):
        page_num = 1

    include_data = (request.GET.get('with_data') or '').strip().lower() in ('1', 'true', 'yes')
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page_num)

    items = [
        _serialize_list_row(row, include_data=include_data, request=request)
        for row in page_obj.object_list
    ]

    not_sent_count = qs.filter(Q(send_wheels_ib=False) | Q(send_wheels_ib__isnull=True)).count()
    sent_count = qs.filter(send_wheels_ib=True).count()

    return _json_response({
        'ok': True,
        'count': paginator.count,
        'page': page_obj.number,
        'page_size': page_size,
        'pages': paginator.num_pages,
        'not_sent_count': not_sent_count,
        'sent_count': sent_count,
        'items': items,
    })


@api_view(['GET'])
def kolesa_reception_detail(request, reception_id):
    """Полный JSON по одной приёмке 2КК."""
    reception = (
        _kolesa_reception_queryset()
        .filter(pk=reception_id)
        .first()
    )
    if reception is None:
        return _json_response(
            {'ok': False, 'error': 'Приёмка не найдена', 'id': reception_id},
            status.HTTP_404_NOT_FOUND,
        )

    payload = build_kolesa_reception_send_payload(reception, request=request)
    payload['ok'] = True
    payload['send_wheels_ib'] = bool(reception.send_wheels_ib)
    payload['send_wheels_ib_date'] = reception.send_wheels_ib_date
    payload['send_wheels_ib_number'] = reception.send_wheels_ib_number or ''
    return _json_response(payload)


def _field_from_payload(data, *keys):
    for key in keys:
        if key in data and data[key] not in (None, ''):
            return data[key]
    return None


def _normalize_accept_item(data):
    if not isinstance(data, dict):
        raise ValueError('Ожидается JSON-объект')

    reception_id = _field_from_payload(
        data,
        'id', 'KolesaReceptionId', 'kolesa_reception_id',
    )
    rlk_uin = _field_from_payload(data, 'rlk_uin', 'Uin', 'uin')

    if reception_id is not None:
        text = str(reception_id).strip()
        if not text.isdigit():
            raise ValueError('Некорректный id приёмки: %r' % reception_id)
        reception_id = int(text)
    elif rlk_uin:
        reception = (
            _kolesa_reception_queryset()
            .filter(rlk__uin=str(rlk_uin).strip())
            .first()
        )
        if reception is None:
            raise ValueError('Приёмка не найдена для rlk_uin=%r' % rlk_uin)
        reception_id = reception.pk
    else:
        raise ValueError('Укажите id, KolesaReceptionId или rlk_uin')

    raw_date = _field_from_payload(
        data,
        'date', 'Дата', 'send_wheels_ib_date', 'document_date',
    )
    raw_number = _field_from_payload(
        data,
        'number', 'Номер', 'nomer', 'document_number', 'send_wheels_ib_number',
    )

    accept_date = None
    if raw_date is not None:
        accept_date = _parse_accept_datetime(raw_date)

    accept_number = _parse_document_number(raw_number)

    return {
        'id': reception_id,
        'send_wheels_ib_date': accept_date,
        'send_wheels_ib_number': accept_number,
    }


def _extract_accept_items(data):
    if not isinstance(data, dict):
        raise ValueError('Ожидается JSON-объект')

    if 'items' in data and isinstance(data['items'], list):
        if not data['items']:
            raise ValueError('Список items пуст')
        return [_normalize_accept_item(item) for item in data['items']]

    if 'ids' in data and isinstance(data['ids'], (list, tuple)):
        raw_date = _field_from_payload(
            data,
            'date', 'Дата', 'send_wheels_ib_date', 'document_date',
        )
        raw_number = _field_from_payload(
            data,
            'number', 'Номер', 'nomer', 'document_number', 'send_wheels_ib_number',
        )
        accept_date = _parse_accept_datetime(raw_date) if raw_date is not None else None
        accept_number = _parse_document_number(raw_number)
        items = []
        for value in data['ids']:
            text = str(value).strip()
            if not text.isdigit():
                raise ValueError('Некорректный id приёмки: %r' % value)
            items.append({
                'id': int(text),
                'send_wheels_ib_date': accept_date,
                'send_wheels_ib_number': accept_number,
            })
        return items

    return [_normalize_accept_item(data)]


def _apply_accept(reception, accept_date, accept_number):
    already_sent = bool(reception.send_wheels_ib)
    update_fields = []

    if not already_sent:
        reception.send_wheels_ib = True
        update_fields.append('send_wheels_ib')

    if accept_date is not None:
        reception.send_wheels_ib_date = accept_date
        update_fields.append('send_wheels_ib_date')

    if accept_number is not None:
        reception.send_wheels_ib_number = accept_number
        update_fields.append('send_wheels_ib_number')

    if update_fields:
        reception.save(update_fields=update_fields)

    return already_sent


@api_view(['POST'])
def kolesa_reception_accept(request):
    """
    Подтверждение приёмки в базе БУ колёс (send_wheels_ib=True).

    Тело:
    {"id": 43, "date": "2026-08-18", "number": "00001234"}
    {"id": 43, "Дата": "18.08.2026", "Номер": "00001234"}
    {"ids": [43, 44], "date": "2026-08-18", "number": "00001234"}
    {"items": [{"id": 43, "date": "...", "number": "..."}]}
    """
    try:
        data = _parse_request_json(request)
    except (ValueError, json.JSONDecodeError) as exc:
        return _json_response(
            {'ok': False, 'error': 'Ошибка разбора JSON: %s' % exc},
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        accept_items = _extract_accept_items(data)
    except ValueError as exc:
        return _json_response({'ok': False, 'error': str(exc)}, status.HTTP_400_BAD_REQUEST)

    accepted = []
    errors = []

    for item in accept_items:
        reception_id = item['id']
        reception = _kolesa_reception_queryset().filter(pk=reception_id).first()
        if reception is None:
            errors.append({'id': reception_id, 'error': 'Приёмка не найдена'})
            continue

        already_sent = _apply_accept(
            reception,
            item.get('send_wheels_ib_date'),
            item.get('send_wheels_ib_number'),
        )

        accepted.append({
            'id': reception.pk,
            'KolesaReceptionId': reception.pk,
            'send_wheels_ib': True,
            'send_wheels_ib_date': reception.send_wheels_ib_date,
            'send_wheels_ib_number': reception.send_wheels_ib_number or '',
            'already_sent': already_sent,
            'message': 'Принято' if not already_sent else 'Уже было принято ранее',
        })

    if not accepted and errors:
        return _json_response(
            {'ok': False, 'accepted': accepted, 'errors': errors},
            status.HTTP_404_NOT_FOUND,
        )

    return _json_response({
        'ok': True,
        'message': 'Принято',
        'accepted': accepted,
        'errors': errors,
    })
