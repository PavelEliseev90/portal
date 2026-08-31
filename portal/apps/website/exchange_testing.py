"""Тестирование обменов с 1С: сбор payload, выбор ИБ, отправка."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests
from django.core.serializers.json import DjangoJSONEncoder

from eco.reception import (
    build_reception_1c_payload,
    estimation_has_kolesa2,
    get_kolesa_reception_or_none,
    get_reception_or_none,
    queue_estimation_for_1c,
)
from prices_car_bu.models import CalculatedCumulativeData
from refs.models import RefIb
from register.models import (
    RegInteractivOcenka,
    RegInteractivOcenkaKolesaReception,
    RegInteractivOcenkaRLK,
    RegSwapKors,
)
from task_manager.views import (
    AUTOPRICING_EXPORT_1C_TYPE,
    build_agreement_cumulative_1c_payload,
    build_estimation_1c_payload,
    build_kolesa_reception_send_payload,
    resolve_agreement_cumulative_1c_target,
    resolve_estimation_1c_url,
    resolve_ib_1c_hs_url,
    send_agreement_cumulative_to_1c,
    send_kolesa_reception_to_1c,
    url_hs_alfa_auto,
    url_hs_kors_auto,
    url_hs_wheels_bu,
)

IB_PRESETS = (
    ('auto', 'Авто (из контекста записи)'),
    ('kors', 'КорсАвто — zbusiness'),
    ('alfa', 'Альфа-Авто — ralfa01'),
    ('wheels', 'БУ шин — rwheels2024'),
    ('km_car', 'KMCar — ralfa01/?type=KMCar (basic auth)'),
)

URL_KM_CAR = 'http://k01srv1c10/ralfa01/hs/mb/?type=KMCar'
KM_CAR_HTTP_AUTH = ('reglament', 'aliluj24')
KM_CAR_BATCH_PREVIEW_LIMIT = 20


def _json_dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder, default=str)


def _http_result(response) -> dict:
    try:
        text = (response.text or '')[:4000]
    except Exception:
        text = ''
    status_code = response.status_code
    return {
        'ok': 200 <= status_code < 300,
        'status_code': status_code,
        'text': text,
        'error': None if 200 <= status_code < 300 else f'HTTP {status_code}',
    }


def post_exchange_payload(
    url: str,
    payload: dict,
    timeout: int = 60,
    auth=None,
) -> dict:
    if not url:
        return {'ok': False, 'status_code': None, 'text': '', 'error': 'URL не задан'}
    try:
        response = requests.post(url, json=payload, timeout=timeout, auth=auth)
        return _http_result(response)
    except requests.RequestException as exc:
        return {'ok': False, 'status_code': None, 'text': '', 'error': str(exc)}


@dataclass
class ExchangeScenario:
    key: str
    title: str
    description: str
    payload: dict | None = None
    payload_json: str = ''
    endpoint_url: str = ''
    endpoint_auto_url: str = ''
    endpoint_kind: str = ''
    can_send: bool = True
    can_queue: bool = False
    can_delete: bool = False
    error: str = ''
    meta: dict = field(default_factory=dict)


def list_ib_options():
    """Пресеты + активные информационные базы."""
    options = [{'value': code, 'label': label, 'group': 'preset'} for code, label in IB_PRESETS]
    for ib in RefIb.objects.filter(active=True).order_by('name'):
        url = resolve_ib_1c_hs_url(ib)
        suffix = f' — {url}' if url else ' — URL не задан'
        options.append({
            'value': f'ib:{ib.pk}',
            'label': f'{ib.name}{suffix}',
            'group': 'ib',
            'ib_id': ib.pk,
        })
    return options


def resolve_ib_target(ib_target: str, auto_url: str = '', auto_kind: str = '') -> tuple[str, str]:
    """
  Возвращает (url, kind_label).
  ib_target: auto | kors | alfa | wheels | ib:<id>
    """
    ib_target = (ib_target or 'auto').strip()
    if ib_target == 'auto':
        return auto_url or '', auto_kind or 'auto'
    if ib_target == 'kors':
        return url_hs_kors_auto, 'kors'
    if ib_target == 'alfa':
        return url_hs_alfa_auto, 'alfa'
    if ib_target == 'wheels':
        return url_hs_wheels_bu, 'wheels'
    if ib_target == 'km_car':
        return URL_KM_CAR, 'km_car'
    if ib_target.startswith('ib:'):
        try:
            ib_id = int(ib_target.split(':', 1)[1])
        except (TypeError, ValueError):
            return '', 'ib:invalid'
        ib = RefIb.objects.filter(pk=ib_id).first()
        if ib is None:
            return '', f'ib:{ib_id}:not_found'
        url = resolve_ib_1c_hs_url(ib)
        kind = f'ib:{ib.pk}'
        if ib.alfa:
            kind = f'ib:{ib.pk}:alfa'
        return url or '', kind
    return auto_url or '', auto_kind or ib_target


def _auto_url_for_unit(unit) -> tuple[str, str]:
    if unit is None:
        return url_hs_kors_auto, 'kors'
    ib = getattr(unit, 'ib', None)
    if ib is not None and getattr(ib, 'alfa', False):
        return url_hs_alfa_auto, 'alfa'
    if ib is not None:
        url = resolve_ib_1c_hs_url(ib)
        if url:
            return url, f'ib:{ib.pk}'
    return url_hs_kors_auto, 'kors'


def _find_unit(unit_id: str):
    if not unit_id:
        return None
    from refs.models import RefUnit
    return RefUnit.objects.select_related('ib').filter(pk=int(unit_id)).first()


def _find_calc(calc_id: str):
    if not calc_id:
        return None
    from prices_car.models import CarCalculations
    return (
        CarCalculations.objects
        .select_related('unit', 'unit__ib', 'rlk', 'car')
        .filter(pk=int(calc_id))
        .first()
    )


def _find_km_car(km_id: str):
    if not km_id:
        return None
    from prices_car.models import KMCar
    return (
        KMCar.objects
        .select_related('car')
        .filter(pk=int(km_id))
        .first()
    )


def _find_avito_offer(offer_id: str):
    if not offer_id:
        return None
    from auction_avito.models import AvitoLotOffer
    return (
        AvitoLotOffer.objects
        .select_related(
            'lot', 'lot__venue', 'lot__venue__unit', 'lot__venue__unit__ib',
            'lot__vehicle_avito', 'lot__vehicle_autohub', 'account',
        )
        .filter(pk=int(offer_id))
        .first()
    )


def build_matrix_auction_payload() -> dict:
    from register.models import SettingsMatrixAuction

    settings_matrix = SettingsMatrixAuction.objects.get(pk=1)
    rows = []
    for cg_label, prefix in (
        ('200', '200'),
        ('400', '400'),
        ('700', '700'),
        ('1 200', '1200'),
        ('2 000', '2000'),
        ('3 000', '3000'),
        ('5 000', '5000'),
        ('5 000+', '5001'),
    ):
        rows.append({
            'ЦГ': cg_label,
            'БазоваяНаценка': getattr(settings_matrix, f'charge_bcp_{prefix}'),
            'МинимальныйКМ': getattr(settings_matrix, f'min_km_{prefix}'),
            'УмеренноеСнижение': getattr(settings_matrix, f'charge_km_stage_1_{prefix}'),
            'СреднееСнижение': getattr(settings_matrix, f'charge_km_stage_2_{prefix}'),
            'ЗначительноеСнижение': getattr(settings_matrix, f'charge_km_stage_3_{prefix}'),
        })
    return {'Type': 'matrix', 'Settings': rows}


def build_matrix_scenarios(ib_target: str) -> list[ExchangeScenario]:
    try:
        payload = build_matrix_auction_payload()
    except Exception as exc:
        return [ExchangeScenario(
            key='matrix',
            title='Type = matrix',
            description='Матрица БЦП аукциона',
            error=str(exc),
            can_send=False,
        )]

    payload_json = _json_dumps(payload)
    scenarios = []
    targets = []
    if ib_target == 'auto':
        targets = [
            ('matrix_kors', url_hs_kors_auto, 'kors', 'КорсАвто'),
            ('matrix_alfa', url_hs_alfa_auto, 'alfa', 'Альфа-Авто'),
        ]
    else:
        url, kind = resolve_ib_target(ib_target, url_hs_kors_auto, 'kors')
        targets = [('matrix', url, kind, kind)]

    for key, url, kind, label in targets:
        scenarios.append(ExchangeScenario(
            key=key,
            title=f'Type = matrix → {label}',
            description='Матрица наценок БЦП аукциона (SettingsMatrixAuction pk=1). '
                        'В проде уходит в Корс и Альфу одновременно.',
            payload=payload,
            payload_json=payload_json,
            endpoint_url=url,
            endpoint_auto_url=url_hs_kors_auto,
            endpoint_kind=kind,
        ))
    return scenarios


def build_settings_dc_scenarios(unit, ib_target: str) -> list[ExchangeScenario]:
    if unit is None:
        return []
    from refs.unit_settings_1c import build_unit_settings_dc_payload

    auto_url, auto_kind = _auto_url_for_unit(unit)
    endpoint_url, endpoint_kind = resolve_ib_target(ib_target, auto_url, auto_kind)
    try:
        payload = {
            'Type': 'settings_dc',
            'Settings': build_unit_settings_dc_payload(unit),
        }
        return [ExchangeScenario(
            key='settings_dc',
            title='Type = settings_dc',
            description=f'Настройки подразделения «{unit.name}» для 1С',
            payload=payload,
            payload_json=_json_dumps(payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=auto_url,
            endpoint_kind=endpoint_kind,
            meta={'unit_id': unit.pk},
        )]
    except Exception as exc:
        return [ExchangeScenario(
            key='settings_dc',
            title='Type = settings_dc',
            description='Настройки подразделения',
            error=str(exc),
            can_send=False,
        )]


def build_change_kp_scenarios(calc, ib_target: str) -> list[ExchangeScenario]:
    if calc is None:
        return []
    from avtosalon.deal_calc_approval import (
        URL_HS_ALFA_AUTO,
        build_calculation_soglasovanie_1c_payload,
    )

    auto_url = URL_HS_ALFA_AUTO
    endpoint_url, endpoint_kind = resolve_ib_target(ib_target, auto_url, 'alfa')
    try:
        payload = build_calculation_soglasovanie_1c_payload(calc)
        return [ExchangeScenario(
            key='change_kp',
            title='Type = ChangeKP',
            description=f'Статус согласования КП #{calc.pk} ({calc.number or "без номера"})',
            payload=payload,
            payload_json=_json_dumps(payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=auto_url,
            endpoint_kind=endpoint_kind,
            meta={'calc_id': calc.pk},
        )]
    except Exception as exc:
        return [ExchangeScenario(
            key='change_kp',
            title='Type = ChangeKP',
            description='Согласование КП',
            error=str(exc),
            can_send=False,
        )]


def _km_car_item_dict(km) -> dict:
    return {
        'VIN': km.car.vin,
        'Comment': km.car.vin,
        'KM': km.km,
        'Date': km.date.strftime('%Y-%m-%dT%H:%M:%S%z'),
    }


def build_km_car_scenarios(km_row, ib_target: str, batch: bool = False) -> list[ExchangeScenario]:
    from prices_car.models import KMCar

    if ib_target == 'auto':
        endpoint_url, endpoint_kind = URL_KM_CAR, 'km_car'
    else:
        endpoint_url, endpoint_kind = resolve_ib_target(ib_target, URL_KM_CAR, 'km_car')

    auth_meta = {'http_auth': KM_CAR_HTTP_AUTH, 'timeout': 180}

    if batch:
        km_list = list(KMCar.objects.select_related('car').order_by('-date')[:KM_CAR_BATCH_PREVIEW_LIMIT])
        cars = [_km_car_item_dict(km) for km in km_list]
        payload = {'Type': 'KMCar', 'Cars': cars}
        return [ExchangeScenario(
            key='km_car_batch',
            title='Type = KMCar (пакет)',
            description=f'Пакет КМ: превью {len(cars)} последних записей '
                        f'(в проде до 5000). Basic auth.',
            payload=payload,
            payload_json=_json_dumps(payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=URL_KM_CAR,
            endpoint_kind=endpoint_kind,
            meta=auth_meta,
        )]

    if km_row is None:
        return []
    payload = {'Type': 'KMCar', 'Cars': [_km_car_item_dict(km_row)]}
    vin = getattr(km_row.car, 'vin', '') or '—'
    return [ExchangeScenario(
        key='km_car',
        title='Type = KMCar',
        description=f'КМ автомобиля VIN {vin}, значение {km_row.km}',
        payload=payload,
        payload_json=_json_dumps(payload),
        endpoint_url=endpoint_url,
        endpoint_auto_url=URL_KM_CAR,
        endpoint_kind=endpoint_kind,
        meta={**auth_meta, 'km_id': km_row.pk},
    )]


def build_avito_worksheet_scenarios(offer, ib_target: str) -> list[ExchangeScenario]:
    if offer is None:
        return []
    from auction_avito.services.win_rlk import (
        CREATE_AVITO_WORKSHEET_TYPE,
        build_create_avito_worksheet_payload,
        hs_url_for_unit,
        resolve_win_rlk_unit,
    )

    unit = resolve_win_rlk_unit(offer)
    auto_url = hs_url_for_unit(unit) if unit is not None else url_hs_kors_auto
    auto_kind = 'alfa' if unit and getattr(getattr(unit, 'ib', None), 'alfa', False) else 'kors'
    endpoint_url, endpoint_kind = resolve_ib_target(ib_target, auto_url or url_hs_kors_auto, auto_kind)
    try:
        payload = build_create_avito_worksheet_payload(offer, unit)
        lot_id = getattr(offer.lot, 'lot_id', None) if offer.lot_id else None
        return [ExchangeScenario(
            key='create_avito_worksheet',
            title=f'Type = {CREATE_AVITO_WORKSHEET_TYPE}',
            description=f'Создание РЛ по выигрышу аукциона Авито: offer #{offer.pk}, '
                        f'lotOfferId={offer.lot_offer_id}, lot={lot_id}',
            payload=payload,
            payload_json=_json_dumps(payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=auto_url or '',
            endpoint_kind=endpoint_kind,
            meta={'offer_id': offer.pk},
        )]
    except Exception as exc:
        return [ExchangeScenario(
            key='create_avito_worksheet',
            title='Type = CreateAvitoWorksheet',
            description='Аукцион Авито',
            error=str(exc),
            can_send=False,
        )]


def _auto_url_for_rlk(rlk) -> tuple[str, str]:
    if rlk is None:
        return url_hs_kors_auto, 'kors'
    return resolve_estimation_1c_url(rlk)


def _auto_url_for_agreement(agreement) -> tuple[str, str]:
    url, kind, _name = resolve_agreement_cumulative_1c_target(agreement)
    return url, kind


def _find_interactiv_rlk(estimation_id: str, rlk_id: str):
    qs = RegInteractivOcenkaRLK.objects.select_related(
        'rlk', 'rlk__unit', 'rlk__unit__ib', 'rlk__unit_dc', 'rlk__unit_dc__ib',
        'estimation', 'estimation__page_kolesa', 'page_soglasovanie', 'page_reception',
    )
    if estimation_id:
        interactiv_rlk = qs.filter(estimation_id=int(estimation_id)).first()
        if interactiv_rlk is None:
            estimation = RegInteractivOcenka.objects.filter(pk=int(estimation_id)).select_related(
                'rlk', 'page_kolesa',
            ).first()
            if estimation is not None:
                interactiv_rlk = qs.filter(rlk=estimation.rlk, estimation=estimation).first()
        return interactiv_rlk
    if rlk_id:
        return qs.filter(rlk_id=int(rlk_id)).order_by('-id').first()
    return None


def _find_kolesa_reception(reception_id: str, estimation_id: str):
    if reception_id:
        return (
            RegInteractivOcenkaKolesaReception.objects
            .select_related('estimation', 'rlk', 'rlk__unit', 'user')
            .filter(pk=int(reception_id))
            .first()
        )
    if estimation_id:
        return (
            RegInteractivOcenkaKolesaReception.objects
            .select_related('estimation', 'rlk', 'rlk__unit', 'user')
            .filter(estimation_id=int(estimation_id))
            .order_by('-id')
            .first()
        )
    return None


def _find_cumulative(cumulative_id: str):
    if not cumulative_id:
        return None
    return (
        CalculatedCumulativeData.objects
        .select_related('agreement', 'agreement__unit', 'agreement__unit__ib', 'agreement__cars', 'indicatorKVP')
        .filter(pk=int(cumulative_id))
        .first()
    )


def _wheels_endpoint(ib_target: str) -> tuple[str, str]:
    auto_url = url_hs_wheels_bu
    if ib_target == 'auto':
        return auto_url, 'wheels'
    return resolve_ib_target(ib_target, auto_url, 'wheels')


def build_estimation_scenarios(interactiv_rlk, ib_target: str = 'auto', request=None) -> list[ExchangeScenario]:
    scenarios: list[ExchangeScenario] = []
    if interactiv_rlk is None:
        return scenarios

    estimation = interactiv_rlk.estimation
    rlk = interactiv_rlk.rlk
    auto_url, auto_kind = _auto_url_for_rlk(rlk)
    endpoint_url, endpoint_kind = resolve_ib_target(ib_target, auto_url, auto_kind)

    # Type=estimation
    try:
        est_payload = build_estimation_1c_payload(interactiv_rlk)
        scenarios.append(ExchangeScenario(
            key='estimation',
            title='Type = estimation',
            description='Полная интерактивная оценка (HasKolesa2, Reception, 2КК)',
            payload=est_payload,
            payload_json=_json_dumps(est_payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=auto_url,
            endpoint_kind=endpoint_kind,
            can_queue=True,
        ))
    except Exception as exc:
        scenarios.append(ExchangeScenario(
            key='estimation',
            title='Type = estimation',
            description='Полная интерактивная оценка',
            error=str(exc),
            can_send=False,
        ))

    # Type=reception
    reception = get_reception_or_none(interactiv_rlk)
    if reception is not None:
        try:
            rec_payload = build_reception_1c_payload(interactiv_rlk, reception)
            scenarios.append(ExchangeScenario(
                key='reception',
                title='Type = reception',
                description='Приём автомобиля (refresh_data=reception1c)',
                payload=rec_payload,
                payload_json=_json_dumps(rec_payload),
                endpoint_url=endpoint_url,
                endpoint_auto_url=auto_url,
                endpoint_kind=endpoint_kind,
            ))
        except Exception as exc:
            scenarios.append(ExchangeScenario(
                key='reception',
                title='Type = reception',
                description='Приём автомобиля',
                error=str(exc),
                can_send=False,
            ))

    # Type=kolesa_reception
    kolesa_reception = get_kolesa_reception_or_none(estimation)
    if kolesa_reception is not None:
        wheels_url, wheels_kind = _wheels_endpoint(ib_target)
        try:
            k_payload = build_kolesa_reception_send_payload(kolesa_reception, request=request)
            k_payload['Type'] = 'kolesa_reception'
            scenarios.append(ExchangeScenario(
                key='kolesa_reception',
                title='Type = kolesa_reception',
                description='Приёмка второго комплекта колёс → БУ шин',
                payload=k_payload,
                payload_json=_json_dumps(k_payload),
                endpoint_url=wheels_url,
                endpoint_auto_url=url_hs_wheels_bu,
                endpoint_kind=wheels_kind,
                meta={'reception_id': kolesa_reception.pk},
            ))
        except Exception as exc:
            scenarios.append(ExchangeScenario(
                key='kolesa_reception',
                title='Type = kolesa_reception',
                description='Приёмка 2КК',
                error=str(exc),
                can_send=False,
            ))

    return scenarios


def build_kolesa_only_scenarios(reception, ib_target: str = 'auto', request=None) -> list[ExchangeScenario]:
    if reception is None:
        return []
    endpoint_url, endpoint_kind = _wheels_endpoint(ib_target)
    try:
        payload = build_kolesa_reception_send_payload(reception, request=request)
        payload['Type'] = 'kolesa_reception'
        return [ExchangeScenario(
            key='kolesa_reception',
            title='Type = kolesa_reception',
            description='Приёмка второго комплекта колёс → БУ шин',
            payload=payload,
            payload_json=_json_dumps(payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=url_hs_wheels_bu,
            endpoint_kind=endpoint_kind,
            meta={'reception_id': reception.pk},
        )]
    except Exception as exc:
        return [ExchangeScenario(
            key='kolesa_reception',
            title='Type = kolesa_reception',
            description='Приёмка 2КК',
            error=str(exc),
            can_send=False,
        )]


def build_cumulative_scenarios(row, ib_target: str = 'auto', delete: bool = False) -> list[ExchangeScenario]:
    if row is None:
        return []
    agreement = row.agreement
    auto_url, auto_kind = _auto_url_for_agreement(agreement)
    endpoint_url, endpoint_kind = resolve_ib_target(ib_target, auto_url, auto_kind)
    try:
        payload = build_agreement_cumulative_1c_payload(row, delete=delete)
        title = 'Type = agreement_cumulative (удаление)' if delete else 'Type = agreement_cumulative'
        desc = 'Расчётные данные кумулятива по соглашению'
        if delete:
            desc += ' — Delete=true'
        indicator = getattr(row.indicatorKVP, 'name', '') or '—'
        return [ExchangeScenario(
            key='cumulative_delete' if delete else 'cumulative',
            title=title,
            description=f'{desc}. Показатель: {indicator}, сумма: {row.amount}',
            payload=payload,
            payload_json=_json_dumps(payload),
            endpoint_url=endpoint_url,
            endpoint_auto_url=auto_url,
            endpoint_kind=endpoint_kind,
            can_queue=False,
            can_delete=not delete,
            meta={
                'cumulative_id': row.pk,
                'agreement_uin': (agreement.uin or '') if agreement else '',
                'send_1c': row.send_1c,
            },
        )]
    except Exception as exc:
        return [ExchangeScenario(
            key='cumulative',
            title='Type = agreement_cumulative',
            description='Кумулятив',
            error=str(exc),
            can_send=False,
        )]


def build_autopricing_scenario(ib_target: str) -> list[ExchangeScenario]:
    """Триггер автопереоценки — только Type, без тела данных."""
    ib = None
    auto_url = ''
    auto_kind = ''
    if ib_target.startswith('ib:'):
        try:
            ib_id = int(ib_target.split(':', 1)[1])
            ib = RefIb.objects.filter(pk=ib_id).first()
            auto_url = resolve_ib_1c_hs_url(ib) if ib else ''
            auto_kind = f'ib:{ib_id}'
        except (TypeError, ValueError):
            pass
    elif ib_target == 'alfa':
        auto_url, auto_kind = url_hs_alfa_auto, 'alfa'
    elif ib_target == 'kors':
        auto_url, auto_kind = url_hs_kors_auto, 'kors'
    elif ib_target == 'wheels':
        auto_url, auto_kind = url_hs_wheels_bu, 'wheels'

    endpoint_url, endpoint_kind = resolve_ib_target(ib_target, auto_url, auto_kind)
    payload = {'Type': AUTOPRICING_EXPORT_1C_TYPE}
    return [ExchangeScenario(
        key='auto_repricing_export',
        title=f'Type = {AUTOPRICING_EXPORT_1C_TYPE}',
        description='Запуск автопереоценки и выгрузки на сайт в 1С (без тела данных)',
        payload=payload,
        payload_json=_json_dumps(payload),
        endpoint_url=endpoint_url,
        endpoint_auto_url=auto_url,
        endpoint_kind=endpoint_kind,
        can_queue=False,
    )]


def _send_scenario(sc: ExchangeScenario) -> dict:
    if sc.error or not sc.can_send:
        return {'ok': False, 'error': sc.error or 'Отправка недоступна'}
    url = sc.endpoint_url or sc.endpoint_auto_url
    if not url:
        return {'ok': False, 'error': 'Endpoint URL не определён'}
    return post_exchange_payload(
        url,
        sc.payload or {},
        timeout=sc.meta.get('timeout', 60),
        auth=sc.meta.get('http_auth'),
    )


def build_context_info(mode: str, **kwargs) -> dict | None:
    if mode == 'estimation':
        interactiv_rlk = kwargs.get('interactiv_rlk')
        if interactiv_rlk is None:
            return None
        estimation = interactiv_rlk.estimation
        rlk = interactiv_rlk.rlk
        return {
            'mode': mode,
            'estimation_id': estimation.pk if estimation else None,
            'rlk_id': rlk.pk if rlk else None,
            'rlk_nomer': getattr(rlk, 'nomer', '') if rlk else '',
            'vin': getattr(estimation, 'vin', '') if estimation else '',
            'unit': (
                getattr(getattr(rlk, 'unit', None), 'name', '')
                or getattr(getattr(rlk, 'unit_dc', None), 'name', '')
            ),
            'has_kolesa2': estimation_has_kolesa2(estimation),
            'has_kolesa_reception': get_kolesa_reception_or_none(estimation) is not None,
            'has_reception': get_reception_or_none(interactiv_rlk) is not None,
        }
    if mode == 'kolesa':
        reception = kwargs.get('reception')
        if reception is None:
            return None
        est = reception.estimation
        return {
            'mode': mode,
            'reception_id': reception.pk,
            'estimation_id': est.pk if est else None,
            'vin': (est.vin or est.number_body or '') if est else '',
            'unit': getattr(getattr(reception.rlk, 'unit', None), 'name', '') if reception.rlk_id else '',
            'sent': bool(reception.send_wheels_ib),
        }
    if mode == 'cumulative':
        row = kwargs.get('cumulative')
        if row is None:
            return None
        agreement = row.agreement
        return {
            'mode': mode,
            'cumulative_id': row.pk,
            'agreement_id': agreement.pk if agreement else None,
            'agreement_nomer': getattr(agreement, 'nomer', '') if agreement else '',
            'agreement_uin': (agreement.uin or '') if agreement else '',
            'indicator': getattr(row.indicatorKVP, 'name', '') if row.indicatorKVP_id else '',
            'amount': row.amount,
            'send_1c': row.send_1c,
            'unit': getattr(getattr(agreement, 'unit', None), 'name', '') if agreement else '',
        }
    if mode == 'autopricing':
        return {'mode': mode, 'ib_target': kwargs.get('ib_target', '')}
    if mode == 'settings_dc':
        unit = kwargs.get('unit')
        if unit is None:
            return None
        return {
            'mode': mode,
            'unit_id': unit.pk,
            'unit_name': unit.name,
            'ib_name': getattr(getattr(unit, 'ib', None), 'name', '') or '—',
        }
    if mode == 'matrix':
        return {'mode': mode, 'note': 'Матрица SettingsMatrixAuction pk=1'}
    if mode == 'change_kp':
        calc = kwargs.get('calc')
        if calc is None:
            return None
        return {
            'mode': mode,
            'calc_id': calc.pk,
            'number': calc.number or '—',
            'uin': calc.uin or '—',
            'unit': getattr(calc.unit, 'name', '') if calc.unit_id else '—',
            'amount': calc.amount,
        }
    if mode == 'km_car':
        km_row = kwargs.get('km_row')
        batch = kwargs.get('batch', False)
        if batch:
            return {'mode': mode, 'batch': True, 'preview_limit': KM_CAR_BATCH_PREVIEW_LIMIT}
        if km_row is None:
            return None
        return {
            'mode': mode,
            'km_id': km_row.pk,
            'vin': getattr(km_row.car, 'vin', '') if km_row.car_id else '—',
            'km': km_row.km,
            'date': km_row.date,
        }
    if mode == 'avito':
        offer = kwargs.get('offer')
        if offer is None:
            return None
        lot = offer.lot
        return {
            'mode': mode,
            'offer_id': offer.pk,
            'lot_offer_id': offer.lot_offer_id,
            'lot_id': getattr(lot, 'lot_id', None) if lot else None,
            'bid': offer.bid,
            'venue': getattr(getattr(lot, 'venue', None), 'name', '') if lot else '',
        }
    return None


def fetch_queue_rows(estimation_id: int | None):
    if not estimation_id:
        return []
    return list(
        RegSwapKors.objects.filter(estimation_id=estimation_id).order_by('-id')[:20].values(
            'id', 'status_code', 'status', 'comment', 'date', 'status_date',
        )
    )


def handle_send_action(
    action: str,
    *,
    ib_target: str,
    interactiv_rlk=None,
    reception=None,
    cumulative=None,
    unit=None,
    calc=None,
    km_row=None,
    offer=None,
    km_batch: bool = False,
    scenario_key: str,
    mark_cumulative_sent: bool,
    request=None,
) -> dict:
    """Выполнить отправку по ключу сценария."""
    if action == 'queue_estimation':
        estimation = interactiv_rlk.estimation if interactiv_rlk else None
        if estimation is None:
            return {'ok': False, 'error': 'Оценка не найдена'}
        queue_estimation_for_1c(estimation, comment='exchange_testing')
        return {'ok': True, 'message': 'Добавлено в очередь RegSwapKors (status_code=60)'}

    if scenario_key in ('matrix', 'matrix_kors', 'matrix_alfa'):
        for sc in build_matrix_scenarios(ib_target):
            if sc.key == scenario_key:
                return _send_scenario(sc)
        return {'ok': False, 'error': f'Сценарий {scenario_key} недоступен'}

    if scenario_key == 'settings_dc' and unit is not None:
        scenarios = build_settings_dc_scenarios(unit, ib_target)
        return _send_scenario(scenarios[0]) if scenarios else {'ok': False, 'error': 'Сценарий не найден'}

    if scenario_key == 'change_kp' and calc is not None:
        scenarios = build_change_kp_scenarios(calc, ib_target)
        return _send_scenario(scenarios[0]) if scenarios else {'ok': False, 'error': 'Сценарий не найден'}

    if scenario_key in ('km_car', 'km_car_batch'):
        scenarios = build_km_car_scenarios(km_row, ib_target, batch=km_batch or scenario_key == 'km_car_batch')
        sc_map = {s.key: s for s in scenarios}
        sc = sc_map.get(scenario_key)
        return _send_scenario(sc) if sc else {'ok': False, 'error': 'Сценарий KMCar не найден'}

    if scenario_key == 'create_avito_worksheet' and offer is not None:
        scenarios = build_avito_worksheet_scenarios(offer, ib_target)
        return _send_scenario(scenarios[0]) if scenarios else {'ok': False, 'error': 'Сценарий не найден'}

    if scenario_key == 'kolesa_reception' and reception is not None:
        scenarios = build_kolesa_only_scenarios(reception, ib_target, request=request)
        if not scenarios or scenarios[0].error:
            return {'ok': False, 'error': scenarios[0].error if scenarios else 'Сценарий не найден'}
        sc = scenarios[0]
        if ib_target != 'auto' and sc.endpoint_url:
            result = post_exchange_payload(sc.endpoint_url, sc.payload or {})
            return result
        return send_kolesa_reception_to_1c(reception, request=request)

    if scenario_key in ('cumulative', 'cumulative_delete') and cumulative is not None:
        delete = scenario_key == 'cumulative_delete'
        scenarios = build_cumulative_scenarios(cumulative, ib_target, delete=delete)
        if not scenarios or scenarios[0].error:
            return {'ok': False, 'error': scenarios[0].error if scenarios else 'Сценарий не найден'}
        sc = scenarios[0]
        url = sc.endpoint_url or sc.endpoint_auto_url
        if delete:
            from task_manager.views import delete_agreement_cumulative_from_1c
            if ib_target != 'auto' and url:
                result = post_exchange_payload(url, sc.payload or {})
            else:
                result = delete_agreement_cumulative_from_1c(cumulative)
            return result
        return send_agreement_cumulative_to_1c(
            cumulative,
            url=url if ib_target != 'auto' else None,
            mark_sent=mark_cumulative_sent,
        )

    if interactiv_rlk is not None:
        scenarios = build_estimation_scenarios(interactiv_rlk, ib_target, request=request)
        sc_map = {s.key: s for s in scenarios}
        sc = sc_map.get(scenario_key)
        if sc is None or sc.error:
            return {'ok': False, 'error': sc.error if sc else f'Сценарий {scenario_key} недоступен'}
        return _send_scenario(sc)

    if scenario_key == 'auto_repricing_export':
        scenarios = build_autopricing_scenario(ib_target)
        if not scenarios:
            return {'ok': False, 'error': 'Сценарий не найден'}
        return _send_scenario(scenarios[0])

    return {'ok': False, 'error': 'Неизвестное действие'}


def process_exchange_testing_request(request) -> dict[str, Any]:
    """Основная точка входа для view board_exchange_testing."""
    mode = (request.GET.get('mode') or request.POST.get('mode') or 'estimation').strip()
    ib_target = (request.GET.get('ib_target') or request.POST.get('ib_target') or 'auto').strip()
    estimation_id = (request.GET.get('estimation_id') or request.POST.get('estimation_id') or '').strip()
    rlk_id = (request.GET.get('rlk_id') or request.POST.get('rlk_id') or '').strip()
    reception_id = (request.GET.get('reception_id') or request.POST.get('reception_id') or '').strip()
    cumulative_id = (request.GET.get('cumulative_id') or request.POST.get('cumulative_id') or '').strip()
    unit_id = (request.GET.get('unit_id') or request.POST.get('unit_id') or '').strip()
    calc_id = (request.GET.get('calc_id') or request.POST.get('calc_id') or '').strip()
    km_id = (request.GET.get('km_id') or request.POST.get('km_id') or '').strip()
    offer_id = (request.GET.get('offer_id') or request.POST.get('offer_id') or '').strip()
    km_batch = (request.GET.get('km_batch') or request.POST.get('km_batch') or '') == '1'
    action = (request.POST.get('action') or '').strip()
    scenario_key = (request.POST.get('scenario_key') or '').strip()
    mark_cumulative_sent = request.POST.get('mark_cumulative_sent') == '1'

    params: dict[str, Any] = {
        'mode': mode,
        'ib_target': ib_target,
        'estimation_id': estimation_id,
        'rlk_id': rlk_id,
        'reception_id': reception_id,
        'cumulative_id': cumulative_id,
        'unit_id': unit_id,
        'calc_id': calc_id,
        'km_id': km_id,
        'offer_id': offer_id,
        'km_batch': km_batch,
        'ib_options': list_ib_options(),
        'error': '',
        'info': None,
        'scenarios': [],
        'queue_rows': [],
        'send_result': None,
        'action_message': '',
    }

    interactiv_rlk = None
    reception = None
    cumulative = None
    unit = None
    calc = None
    km_row = None
    offer = None

    try:
        if mode == 'estimation':
            if estimation_id or rlk_id:
                interactiv_rlk = _find_interactiv_rlk(estimation_id, rlk_id)
                if interactiv_rlk is None:
                    params['error'] = 'Оценка / РЛК не найдены'
                else:
                    params['estimation_id'] = str(interactiv_rlk.estimation_id or estimation_id)
                    params['rlk_id'] = str(interactiv_rlk.rlk_id or rlk_id)
                    params['info'] = build_context_info('estimation', interactiv_rlk=interactiv_rlk)
                    params['scenarios'] = build_estimation_scenarios(interactiv_rlk, ib_target, request=request)
                    params['queue_rows'] = fetch_queue_rows(interactiv_rlk.estimation_id)

        elif mode == 'kolesa':
            if reception_id or estimation_id:
                reception = _find_kolesa_reception(reception_id, estimation_id)
                if reception is None:
                    params['error'] = 'Приёмка 2КК не найдена'
                else:
                    params['reception_id'] = str(reception.pk)
                    if reception.estimation_id:
                        params['estimation_id'] = str(reception.estimation_id)
                    params['info'] = build_context_info('kolesa', reception=reception)
                    params['scenarios'] = build_kolesa_only_scenarios(reception, ib_target, request=request)

        elif mode == 'cumulative':
            if cumulative_id:
                cumulative = _find_cumulative(cumulative_id)
                if cumulative is None:
                    params['error'] = 'Запись кумулятива не найдена'
                else:
                    params['info'] = build_context_info('cumulative', cumulative=cumulative)
                    params['scenarios'] = (
                        build_cumulative_scenarios(cumulative, ib_target, delete=False)
                        + build_cumulative_scenarios(cumulative, ib_target, delete=True)
                    )

        elif mode == 'matrix':
            params['info'] = build_context_info('matrix')
            params['scenarios'] = build_matrix_scenarios(ib_target)

        elif mode == 'autopricing':
            params['info'] = build_context_info('autopricing', ib_target=ib_target)
            params['scenarios'] = build_autopricing_scenario(ib_target)

        elif mode == 'settings_dc':
            if unit_id:
                unit = _find_unit(unit_id)
                if unit is None:
                    params['error'] = 'Подразделение не найдено'
                else:
                    params['info'] = build_context_info('settings_dc', unit=unit)
                    params['scenarios'] = build_settings_dc_scenarios(unit, ib_target)

        elif mode == 'change_kp':
            if calc_id:
                calc = _find_calc(calc_id)
                if calc is None:
                    params['error'] = 'Калькуляция КП не найдена'
                else:
                    params['info'] = build_context_info('change_kp', calc=calc)
                    params['scenarios'] = build_change_kp_scenarios(calc, ib_target)

        elif mode == 'km_car':
            if km_batch:
                params['info'] = build_context_info('km_car', batch=True)
                params['scenarios'] = build_km_car_scenarios(None, ib_target, batch=True)
            elif km_id:
                km_row = _find_km_car(km_id)
                if km_row is None:
                    params['error'] = 'Запись KMCar не найдена'
                else:
                    params['info'] = build_context_info('km_car', km_row=km_row)
                    params['scenarios'] = build_km_car_scenarios(km_row, ib_target, batch=False)

        elif mode == 'avito':
            if offer_id:
                offer = _find_avito_offer(offer_id)
                if offer is None:
                    params['error'] = 'Оффер Авито не найден'
                else:
                    params['info'] = build_context_info('avito', offer=offer)
                    params['scenarios'] = build_avito_worksheet_scenarios(offer, ib_target)

        else:
            params['error'] = f'Неизвестный режим: {mode}'

    except (TypeError, ValueError):
        params['error'] = 'Некорректный id'
        return params

    if request.method == 'POST' and action:
        if action == 'queue_estimation' and interactiv_rlk is not None:
            result = handle_send_action('queue_estimation', ib_target=ib_target, interactiv_rlk=interactiv_rlk)
            params['action_message'] = result.get('message', '')
            params['send_result'] = result
            if interactiv_rlk.estimation_id:
                params['queue_rows'] = fetch_queue_rows(interactiv_rlk.estimation_id)
        elif action == 'send' and scenario_key:
            result = handle_send_action(
                'send',
                ib_target=ib_target,
                interactiv_rlk=interactiv_rlk,
                reception=reception or (get_kolesa_reception_or_none(interactiv_rlk.estimation) if interactiv_rlk else None),
                cumulative=cumulative,
                unit=unit,
                calc=calc,
                km_row=km_row,
                offer=offer,
                km_batch=km_batch,
                scenario_key=scenario_key,
                mark_cumulative_sent=mark_cumulative_sent,
                request=request,
            )
            params['send_result'] = result
            if interactiv_rlk and interactiv_rlk.estimation_id:
                params['queue_rows'] = fetch_queue_rows(interactiv_rlk.estimation_id)
            if cumulative is not None and scenario_key == 'cumulative' and result.get('ok'):
                cumulative.refresh_from_db(fields=['send_1c'])
                if params.get('info'):
                    params['info']['send_1c'] = cumulative.send_1c

    return params
