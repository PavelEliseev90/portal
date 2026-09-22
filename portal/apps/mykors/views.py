import hashlib
import hmac
import json
import time

from django.conf import settings
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from online.models import Online_doc
from refs.models import RefCars, RefCustomer, RefUnit


def _authenticate(request):
    api_key = getattr(settings, 'MYKORS_INGEST_API_KEY', '')
    secret = getattr(settings, 'MYKORS_INGEST_API_SECRET', '')
    timestamp = request.headers.get('X-Timestamp', '')
    signature = request.headers.get('X-Signature', '')

    if not api_key or not secret or request.headers.get('X-API-Key') != api_key:
        return JsonResponse({'error': 'Invalid API key'}, status=403)
    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid X-Timestamp'}, status=401)
    if abs(time.time() - timestamp_value) > 300:
        return JsonResponse({'error': 'Expired request'}, status=401)

    message = f'{timestamp}.{request.method}.{request.path}.'.encode() + request.body
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return JsonResponse({'error': 'Invalid signature'}, status=403)
    return None


def _upsert_unit(data):
    if not isinstance(data, dict) or not data.get('uin'):
        raise ValueError('unit.uin is required')
    unit, _ = RefUnit.objects.update_or_create(
        uin=str(data['uin']),
        defaults={
            'name': data.get('name', ''),
            'name_dop': data.get('name_dop', ''),
            'adress': data.get('adress', ''),
            'phone': data.get('phone', ''),
            'email': data.get('email', ''),
            'buauto': bool(data.get('buauto', False)),
        },
    )
    return unit


def _upsert_customer(data, name, phone):
    data = data if isinstance(data, dict) else {}
    customer_uin = str(data.get('uin', '')).strip()
    customer_phone = str(data.get('phoneNorm') or phone).strip()
    if customer_uin:
        lookup = {'uin': customer_uin}
    elif customer_phone:
        lookup = {'phoneNorm': customer_phone}
    else:
        raise ValueError('clientPhone is required')
    customer, _ = RefCustomer.objects.update_or_create(
        **lookup,
        defaults={
            'name': data.get('name') or name,
            'full_name': data.get('full_name', ''),
            'phoneNorm': customer_phone,
            'email': data.get('email', ''),
        },
    )
    return customer


def _upsert_car(data):
    if not isinstance(data, dict) or not data.get('vin'):
        return None
    vin = str(data['vin'])[:18]
    car, _ = RefCars.objects.update_or_create(
        vin=vin,
        defaults={
            'vin2': data.get('vin2', ''),
            'name': data.get('name', ''),
            'year': str(data.get('year', '') or ''),
            'mark': data.get('mark', ''),
            'model': data.get('model', ''),
            'modification': data.get('modification', ''),
        },
    )
    return car


@csrf_exempt
@require_POST
def ingest_online_doc(request):
    auth_error = _authenticate(request)
    if auth_error:
        return auth_error

    try:
        data = json.loads(request.body or '{}')
        uid = str(data.get('uid', '')).strip()
        client_name = str(data.get('clientName', '')).strip()
        client_phone = str(data.get('clientPhone', '')).strip()
        if not uid or not client_name or not client_phone:
            raise ValueError('uid, clientName and clientPhone are required')

        unit = _upsert_unit(data.get('unit'))
        customer = _upsert_customer(data.get('customer'), client_name, client_phone)
        car = _upsert_car(data.get('cars'))
        values = {
            'clientName': client_name,
            'clientPhone': client_phone,
            'customer': customer,
            'unit': unit,
            'cars': car,
            'call': bool(data.get('call', False)),
            'unitRecord': _upsert_unit(data['unitRecord']) if data.get('unitRecord') else unit,
        }
        for field in ('dataTimeCreate', 'dataTimeRecord'):
            if data.get(field):
                parsed = parse_datetime(str(data[field]))
                if parsed is None:
                    raise ValueError(f'Invalid {field}')
                values[field] = parsed

        doc, created = Online_doc.objects.update_or_create(uid=uid, defaults=values)
        return JsonResponse(
            {'id': doc.pk, 'uid': doc.uid, 'created': created},
            status=201 if created else 200,
        )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)