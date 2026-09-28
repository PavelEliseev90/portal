"""HMAC HTTP-клиент MyKors API."""
import hashlib
import hmac
import logging
import time
from typing import Optional, Union
from urllib.parse import urlparse

import requests

from mykors import conf

logger = logging.getLogger(__name__)

CAR_INGEST_PATH = '/api/portal/v1/cars/ingest/'
CARS_LIST_PATH = '/api/portal/v1/cars/'
STAFF_INGEST_PATH = '/api/portal/v1/staff/ingest/'
USER_INGEST_PATH = STAFF_INGEST_PATH
WORK_ORDER_INGEST_PATH = '/api/portal/v1/work-orders/ingest/'
WORK_ORDER_KA_INGEST_PATH = '/api/portal/v1/work-orders-ka/ingest/'
SERVICES_KA_INGEST_PATH = '/api/portal/v1/services-ka/ingest/'
SERVICE_REQUEST_INGEST_PATH = '/api/portal/v1/service-requests/ingest/'
WORKSHEET_INGEST_PATH = '/api/portal/v1/worksheets/ingest/'
EVALUATION_INGEST_PATH = '/api/portal/v1/evaluations/ingest/'
AGREEMENT_INGEST_PATH = '/api/portal/v1/agreements/ingest/'
SHIPMENT_INGEST_PATH = '/api/portal/v1/shipments/ingest/'
SMS_INGEST_PATH = '/api/portal/v1/sms/ingest/'


class MykorsClientError(Exception):
    def __init__(self, message, status_code=None, body=''):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def sign_request(method: str, path: str, body: bytes) -> tuple:
    """
    message = "{timestamp}.{METHOD}.{PATH}." + RAW_BODY
    signature = hex(HMAC-SHA256(secret, message))
    """
    ts = str(int(time.time()))
    message = f'{ts}.{method.upper()}.{path}.'.encode('utf-8') + (body or b'')
    signature = hmac.new(
        conf.api_secret().encode('utf-8'),
        message,
        hashlib.sha256,
    ).hexdigest()
    return ts, signature


def _auth_headers(method: str, path: str, body: bytes) -> dict:
    ts, signature = sign_request(method, path, body)
    return {
        'X-API-Key': conf.api_key(),
        'X-Timestamp': ts,
        'X-Signature': signature,
    }


def request(
    method: str,
    path: str,
    *,
    body: bytes = b'',
    params: Optional[dict] = None,
    content_type: Optional[str] = None,
):
    """Подписанный запрос к MyKors. PATH без query."""
    if not conf.is_enabled():
        raise MykorsClientError('MyKors integration is disabled or keys are empty')

    url = conf.api_base_url() + path
    headers = _auth_headers(method, path, body)
    if content_type:
        headers['Content-Type'] = content_type

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=body if body else None,
            headers=headers,
            timeout=conf.request_timeout(),
        )
    except requests.RequestException as exc:
        logger.warning('MyKors request failed %s %s: %s', method, path, exc)
        raise MykorsClientError(str(exc)) from exc

    return response


def ingest_car(payload: dict) -> dict:
    """
    POST /api/portal/v1/cars/ingest/
    Возвращает dict: ok, created, status_code, body, remote_id
    """
    import json

    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    response = request(
        'POST',
        CAR_INGEST_PATH,
        body=body,
        content_type='application/json',
    )
    text = (response.text or '')[:2000]
    data = {}
    try:
        data = response.json()
    except Exception:
        pass

    ok = response.status_code in (200, 201)
    if not ok:
        logger.warning(
            'MyKors ingest failed vin=%s status=%s body=%s',
            payload.get('vin'),
            response.status_code,
            text[:300],
        )
    return {
        'ok': ok,
        'created': bool(data.get('created')) if ok else False,
        'status_code': response.status_code,
        'body': text,
        'remote_id': data.get('id'),
        'data': data,
    }


def ingest_staff(payload: dict) -> dict:
    """
    POST /api/portal/v1/staff/ingest/
    Возвращает dict: ok, created, status_code, body, remote_id, data.
    """
    import json

    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    response = request(
        'POST',
        STAFF_INGEST_PATH,
        body=body,
        content_type='application/json',
    )
    text = (response.text or '')[:2000]
    data = {}
    try:
        data = response.json()
    except Exception:
        pass

    ok = response.status_code in (200, 201)
    if not ok:
        logger.warning(
            'MyKors staff ingest failed portal_user_id=%s username=%s status=%s body=%s',
            payload.get('portal_user_id'),
            payload.get('username'),
            response.status_code,
            text[:300],
        )
    return {
        'ok': ok,
        'created': bool(data.get('created')) if ok else False,
        'status_code': response.status_code,
        'body': text,
        'remote_id': data.get('id'),
        'data': data,
    }


def ingest_user(payload: dict) -> dict:
    """Алиас для обратной совместимости."""
    return ingest_staff(payload)


def ingest_work_order(payload: Union[dict, list]) -> dict:
    """
    POST /api/portal/v1/work-orders/ingest/
    Возвращает dict: ok, created, status_code, body, remote_id, data.
    """
    return _ingest_json(WORK_ORDER_INGEST_PATH, payload, 'work_order')


def _ingest_json(path: str, payload: Union[dict, list], label: str = '') -> dict:
    import json
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    response = request('POST', path, body=body, content_type='application/json')
    text = (response.text or '')[:2000]
    data = {}
    try:
        data = response.json()
    except Exception:
        pass
    ok = response.status_code in (200, 201)
    if not ok:
        identifier = payload.get('uin') if isinstance(payload, dict) else f'count={len(payload)}'
        logger.warning('MyKors %s ingest failed identifier=%s status=%s body=%s', label, identifier, response.status_code, text[:300])
    return {
        'ok': ok,
        'created': bool(data.get('created')) if ok else False,
        'status_code': response.status_code,
        'body': text,
        'remote_id': data.get('id'),
        'data': data,
    }


def ingest_work_order_ka(payload: Union[dict, list]) -> dict:
    return _ingest_json(WORK_ORDER_KA_INGEST_PATH, payload, 'work_order_ka')


def ingest_services_ka(payload: Union[dict, list]) -> dict:
    return _ingest_json(SERVICES_KA_INGEST_PATH, payload, 'services_ka')


def ingest_service_request(payload: Union[dict, list]) -> dict:
    return _ingest_json(SERVICE_REQUEST_INGEST_PATH, payload, 'service_request')


def ingest_worksheet(payload: Union[dict, list]) -> dict:
    return _ingest_json(WORKSHEET_INGEST_PATH, payload, 'worksheet')


def ingest_evaluation(payload: Union[dict, list]) -> dict:
    return _ingest_json(EVALUATION_INGEST_PATH, payload, 'evaluation')


def ingest_car_agreement(payload: Union[dict, list]) -> dict:
    return _ingest_json(AGREEMENT_INGEST_PATH, payload, 'car_agreement')


def ingest_car_shipment(payload: Union[dict, list]) -> dict:
    return _ingest_json(SHIPMENT_INGEST_PATH, payload, 'car_shipment')


def ingest_sms(payload: Union[dict, list]) -> dict:
    return _ingest_json(SMS_INGEST_PATH, payload, 'sms')


def get_cars(params: Optional[dict] = None):
    """GET /api/portal/v1/cars/ — для тестов/будущего pull."""
    return request('GET', CARS_LIST_PATH, params=params or {})


def path_from_url(url: str) -> str:
    """Из полного next-URL берём только path (без query) для подписи."""
    return urlparse(url).path
