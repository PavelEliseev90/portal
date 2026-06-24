"""Создание и отправка экспресс-лота аукциона из интерактивной оценки."""
import datetime as dt
import json

from django.db import transaction
from django.utils import timezone

from documents.models import DocLO
from refs.models import Auction, AuctionStructure, RefCarsOrganization, RefTypeSaleCarsOrganization
from refs.price_groups import resolve_price_group_by_amount
from register.auction_matrix import charge_bcp_for_price


class ExpressAuctionError(Exception):
    pass


def _format_works(estimation_id):
    from task_manager.views import list_work

    items = list_work(estimation_id)
    if not items:
        return ''
    return '\n'.join(item.get('name', '') for item in items if item.get('name'))


def _collect_photo_lists(estimation_id):
    from task_manager.views import (
        get_url_image_osmotr,
        get_url_int,
    )

    vnesh = get_url_int(estimation_id, 'vnesh_car_all') or []
    pered = get_url_image_osmotr(estimation_id, 'vnesh_car_osmotr_pered')
    if pered and pered != '/media/nophoto.png' and pered not in vnesh:
        vnesh = [pered] + list(vnesh)

    return {
        'files_car': json.dumps(vnesh, ensure_ascii=False),
        'files_salon': json.dumps(get_url_int(estimation_id, 'salon') or [], ensure_ascii=False),
        'files_damages': json.dumps(get_url_int(estimation_id, 'damage') or [], ensure_ascii=False),
        'files_kolesa': json.dumps(get_url_int(estimation_id, 'wheel') or [], ensure_ascii=False),
        'files_diagnostic': json.dumps(get_url_int(estimation_id, 'diagnostic') or [], ensure_ascii=False),
        'files_shema': json.dumps([], ensure_ascii=False),
        'files_glav': pered if pered and pered != '/media/nophoto.png' else (vnesh[0] if vnesh else ''),
    }


def _resolve_store(interactiv_rlk):
    if interactiv_rlk.store_id:
        return interactiv_rlk.store
    lo = DocLO.objects.filter(rlk=interactiv_rlk.rlk).first()
    if lo and lo.store_id:
        return lo.store
    if interactiv_rlk.unit_id:
        from refs.models import RefStore
        store = RefStore.objects.filter(
            unit_id=interactiv_rlk.unit_id,
            active_eco=True,
        ).first()
        if store:
            return store
    return None


def _resolve_run(estimation):
    if estimation.page_salon_id and estimation.page_salon.run:
        return int(estimation.page_salon.run)
    if estimation.page_remote_id and estimation.page_remote.run:
        return int(estimation.page_remote.run)
    return 0


def _format_rub(amount):
    return '{:,.0f}'.format(int(amount or 0)).replace(',', ' ')


def build_express_auction_description(estimation, matrix_info, date_start, custom_text=None):
    """Описание лота для документа аукциона (старт, цены, VIN)."""
    custom_text = (custom_text or '').strip()
    if custom_text:
        return custom_text[:12500]

    lines = [
        'Экспресс-лот из интерактивной оценки',
        'VIN: {}'.format(estimation.vin or '—'),
    ]
    if date_start:
        local_dt = timezone.localtime(date_start) if timezone.is_aware(date_start) else date_start
        lines.append('Старт аукциона: {}'.format(local_dt.strftime('%d.%m.%Y %H:%M')))
    lines.append('Цена клиента: {} ₽'.format(_format_rub(matrix_info.get('client_price'))))
    lines.append('Наценка по матрице: {} ₽'.format(_format_rub(matrix_info.get('matrix_charge'))))
    lines.append('Стартовая цена: {} ₽'.format(_format_rub(matrix_info.get('auction_start_price'))))
    price_group = matrix_info.get('price_group')
    if price_group:
        lines.append('Ценовая группа: {}'.format(price_group))
    return '\n'.join(lines)[:12500]


def _get_or_create_lo_for_express(interactiv_rlk, estimation):
    """Лист оценки для связи карточки авто с РЛК (нужно для dop_info и slug)."""
    rlk = interactiv_rlk.rlk
    lo = DocLO.objects.filter(rlk=rlk).first()
    if lo is None:
        lo = DocLO(rlk=rlk)

    rlk_uin = (rlk.uin or '').strip() if rlk else ''
    if not lo.uin:
        lo.uin = rlk_uin or 'express-rlk-{}'.format(interactiv_rlk.pk)

    lo.vin = (estimation.vin or lo.vin or '')[:21]
    lo.year = estimation.year or lo.year or 0
    lo.run = _resolve_run(estimation)
    if interactiv_rlk.organization_id:
        lo.organization = interactiv_rlk.organization
    if interactiv_rlk.unit_id:
        lo.unit = interactiv_rlk.unit
    store = _resolve_store(interactiv_rlk)
    if store:
        lo.store = store
    if interactiv_rlk.type_reception_id:
        lo.type_reception = interactiv_rlk.type_reception
    if estimation.modification_id:
        lo.modification_autoru = estimation.modification
    if estimation.complectation_id:
        lo.complectation_autoru = estimation.complectation
    if rlk and rlk.nomer and not lo.nomer:
        lo.nomer = rlk.nomer
    if estimation.page_documents_id and estimation.page_documents.plate_number:
        lo.carsGRZ = estimation.page_documents.plate_number
    lo.save()
    return lo


def _apply_lo_fields(car, lo, interactiv_rlk=None):
    if lo is None:
        return
    car.lo = lo
    if lo.uin:
        car.lo_uin = lo.uin
    if lo.nomer:
        car.lo_link_number = lo.nomer
    elif interactiv_rlk and interactiv_rlk.rlk and interactiv_rlk.rlk.nomer:
        car.lo_link_number = interactiv_rlk.rlk.nomer
    if lo.dataTime:
        car.lo_link_date = lo.dataTime


def _build_car_name(estimation):
    if estimation.modification_id:
        mod = estimation.modification
        try:
            name = '{} {} {}'.format(
                mod.model.mark.name,
                mod.model.name,
                mod.name,
            ).strip()
            if estimation.complectation_id:
                name = '{} {}'.format(name, estimation.complectation.name).strip()
            return name
        except Exception:
            pass
    if estimation.mark_name:
        return '{} {} {}'.format(
            estimation.mark_name,
            estimation.model_name or '',
            estimation.modification_name or '',
        ).strip()
    return ''


def _apply_car_identity(car, estimation):
    if estimation.modification_id:
        car.modification_autoru = estimation.modification
    if estimation.complectation_id:
        car.complectation_autoru = estimation.complectation

    if estimation.modification_id:
        mod = estimation.modification
        try:
            car.mark = mod.model.mark.name
            car.model = mod.model.name
            car.modification = mod.name
            if mod.engineVolume:
                car.engine_volume = float(mod.engineVolume)
            if mod.enginePower:
                car.engine_power = float(mod.enginePower)
            if mod.typeBody_id and not car.type_body_id:
                car.type_body = mod.typeBody
            if mod.typeEngine_id and not car.type_engine_id:
                car.type_engine = mod.typeEngine
            if mod.typeGear_id and not car.type_gear_id:
                car.type_gear = mod.typeGear
        except Exception:
            pass
    elif estimation.mark_name:
        car.mark = estimation.mark_name
        car.model = estimation.model_name or ''
        car.modification = estimation.modification_name or ''

    if estimation.type_body_id:
        car.type_body = estimation.type_body
    if estimation.type_engine_id:
        car.type_engine = estimation.type_engine
    if estimation.type_gear_id:
        car.type_gear = estimation.type_gear

    if estimation.page_documents_id:
        docs = estimation.page_documents
        if docs.plate_number:
            car.plate_number = docs.plate_number
        if docs.pts_color:
            car.color = docs.pts_color
        if docs.count_owners is not None:
            car.owners = docs.count_owners
        if docs.count_key is not None:
            car.keys = docs.count_key

    car_name = _build_car_name(estimation)
    if car_name:
        car.name = car_name


def _apply_express_car_prices(car, client_price, start_price):
    client_price = int(client_price or 0)
    start_price = int(start_price or 0)
    car.cost_price = client_price
    car.price = start_price
    car.bcp = start_price
    price_group = resolve_price_group_by_amount(client_price)
    if price_group:
        car.group_price = price_group


def _ensure_car_slug(car):
    if car.slug and len(car.slug) >= 8:
        return
    car.slug = ''
    car.save()


def get_or_create_express_car(interactiv_rlk, estimation, client_price, start_price):
    lo = _get_or_create_lo_for_express(interactiv_rlk, estimation)
    car = RefCarsOrganization.objects.filter(lo=lo).first()
    if car is None and estimation.vin:
        car = RefCarsOrganization.objects.filter(
            lo_uin=lo.uin,
            vin=(estimation.vin or '')[:18],
        ).first()

    type_sale, _ = RefTypeSaleCarsOrganization.objects.get_or_create(name='Аукцион')

    if car:
        _apply_express_car_prices(car, client_price, start_price)
        if not car.store_id:
            car.store = _resolve_store(interactiv_rlk)
        _apply_lo_fields(car, lo, interactiv_rlk)
        _apply_car_identity(car, estimation)
        if not car.type_sale_id:
            car.type_sale = type_sale
        if car.quantity is None or car.quantity <= 0:
            car.quantity = 1
        car.save()
        _ensure_car_slug(car)
        return car

    car = RefCarsOrganization(
        organization=interactiv_rlk.organization,
        unit=interactiv_rlk.unit,
        store=_resolve_store(interactiv_rlk),
        vin=(estimation.vin or '')[:18],
        year=estimation.year or 0,
        run=_resolve_run(estimation),
        modification_autoru=estimation.modification,
        complectation_autoru=estimation.complectation,
        type_sale=type_sale,
        type_reception=interactiv_rlk.type_reception,
        quantity=1,
        is_new=False,
        description_op='Экспресс-лот из интерактивной оценки',
    )
    _apply_lo_fields(car, lo, interactiv_rlk)
    _apply_car_identity(car, estimation)
    _apply_express_car_prices(car, client_price, start_price)
    car.save()
    _ensure_car_slug(car)
    return car


def get_express_estimation_for_auction(auction):
    soglasovanie = auction.express_estimations.first()
    if soglasovanie is None:
        return None
    from register.models import RegInteractivOcenkaRLK

    rlk = RegInteractivOcenkaRLK.objects.filter(
        estimation__page_soglasovanie_id=soglasovanie.pk,
    ).select_related('estimation').first()
    if rlk is None:
        rlk = RegInteractivOcenkaRLK.objects.filter(
            page_soglasovanie_id=soglasovanie.pk,
        ).select_related('estimation').first()
    if rlk is None or rlk.estimation_id is None:
        return None
    return rlk.estimation, rlk


def build_express_dop_info_for_car(car, estimation, interactiv_rlk=None):
    """Доп. данные авто для портала аукциона (mark/model, фото из ЕЦО)."""
    from task_manager.views import (
        get_url_image_osmotr,
        get_url_image_salon,
        get_url_images,
        get_url_int,
        list_work,
    )

    mark_name = model_name = modification_name = ''
    if car.modification_autoru_id:
        mod = car.modification_autoru
        try:
            mark_name = mod.model.mark.name
            model_name = mod.model.name
            modification_name = mod.name
        except Exception:
            pass
    elif estimation.modification_id:
        mod = estimation.modification
        try:
            mark_name = mod.model.mark.name
            model_name = mod.model.name
            modification_name = mod.name
        except Exception:
            pass
    else:
        mark_name = car.mark or estimation.mark_name or ''
        model_name = car.model or estimation.model_name or ''
        modification_name = car.modification or estimation.modification_name or ''

    diagnostika = ''
    if interactiv_rlk and interactiv_rlk.page_soglasovanie:
        diagnostika = interactiv_rlk.page_soglasovanie.comment_diagnostica or ''

    pered = get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_pered')
    url = pered if pered and pered != '/media/nophoto.png' else ''
    if not url:
        try:
            images = get_url_images(car.slug)
            if isinstance(images, list) and images:
                url = images[0]
            elif images:
                url = images
        except Exception:
            url = ''
    if not url:
        vnesh = get_url_int(estimation.id, 'vnesh_car_all') or []
        url = vnesh[0] if vnesh else '/media/nophoto.png'

    group_id = car.group_price_id if car.group_price_id else None

    return {
        'vin': car.vin,
        'slug': car.slug,
        'year': car.year,
        'price': car.price,
        'run': car.run,
        'days_in_stok': car.days_in_stok,
        'outlay': car.outlay,
        'cost_price': car.cost_price,
        'bcp': car.bcp,
        'description_op': car.description_op,
        'description_podgotovka': car.description_podgotovka,
        'int_ocenka_diagnostika': diagnostika,
        'int_ocenka_work': list_work(estimation.id),
        'int_ocenka_id': interactiv_rlk.id if interactiv_rlk else None,
        'int_ocenka_url_salon_all': get_url_int(estimation.id, 'salon'),
        'int_ocenka_url_wheel': get_url_int(estimation.id, 'wheel'),
        'int_ocenka_url_diagnostic': get_url_int(estimation.id, 'diagnostic'),
        'int_ocenka_url_salon': get_url_image_salon(estimation.id, 'osmotr_salon'),
        'int_ocenka_url_pered': get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_pered'),
        'int_ocenka_url_zad': get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_zad'),
        'int_ocenka_url_up': get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_up'),
        'int_ocenka_url_right': get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_pass'),
        'int_ocenka_url_left': get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_vod'),
        'int_ocenka_url_vnesh': get_url_int(estimation.id, 'vnesh_car_all'),
        'int_ocenka_url_damage': get_url_int(estimation.id, 'damage'),
        'price_moderate': 0,
        'price_medium': 0,
        'price_significant': 0,
        'market_price': 0,
        'autoteka_web': estimation.avtoteka_web or '',
        'group': group_id,
        'type_sale_name': car.type_sale.name if car.type_sale_id else 'Аукцион',
        'type_reception_name': car.type_reception.name if car.type_reception_id else '',
        'stage_price_name': car.stage_price.name if car.stage_price_id else '',
        'status_name': car.status.name if car.status_id else '',
        'mark_name': mark_name,
        'model_name': model_name,
        'modification_name': modification_name,
        'url': url,
    }


def _validate_auction_before_send(auction):
    structures = list(auction.cars().select_related('car'))
    if not structures:
        raise ExpressAuctionError('Лот не содержит автомобилей — отправка отменена.')
    for row in structures:
        if row.car_id is None:
            raise ExpressAuctionError('В составе лота отсутствует автомобиль.')
        if not (row.car.slug or '').strip():
            raise ExpressAuctionError('У автомобиля не сформирован идентификатор — отправка отменена.')


def build_auction_structure(auction, car, interactiv_rlk, estimation):
    soglasovanie = interactiv_rlk.page_soglasovanie
    diagnostic = ''
    if soglasovanie and soglasovanie.comment_diagnostica:
        diagnostic = soglasovanie.comment_diagnostica

    photos = _collect_photo_lists(estimation.id)
    car_description = auction.description or 'Экспресс-лот · VIN {}'.format(estimation.vin or '—')
    structure, _ = AuctionStructure.objects.get_or_create(
        auction=auction,
        car=car,
        defaults={'description': car_description},
    )
    structure.description = car_description
    structure.diagnostic = diagnostic
    structure.works = _format_works(estimation.id)
    structure.op = ''
    structure.podgotovka = ''
    structure.autoteka_prev = bool((estimation.avtoteka_web or '').strip())
    structure.success = True
    structure.files_car = photos['files_car']
    structure.files_salon = photos['files_salon']
    structure.files_damages = photos['files_damages']
    structure.files_kolesa = photos['files_kolesa']
    structure.files_diagnostic = photos['files_diagnostic']
    structure.files_shema = photos['files_shema']
    structure.files_glav = photos['files_glav'] or ''
    structure.save()
    return structure


def create_and_send_express_auction(
    interactiv_rlk,
    estimation,
    user,
    client_price,
    date_start,
    lot_description=None,
):
    """
    Создать экспресс-лот и отправить на auction.kors-group.ru.
    Возвращает (auction, matrix_info).
    """
    soglasovanie = interactiv_rlk.page_soglasovanie
    if soglasovanie is None:
        raise ExpressAuctionError('Не заполнена страница согласования.')

    if soglasovanie.express_auction_id:
        existing = soglasovanie.express_auction
        if existing and not (existing.rejection_reason or '').strip():
            raise ExpressAuctionError(
                'По этой оценке уже создан экспресс-лот №{}.'.format(
                    existing.pk_auction or existing.uid,
                )
            )

    matrix_info = charge_bcp_for_price(client_price)
    if matrix_info['client_price'] <= 0:
        raise ExpressAuctionError('Укажите цену клиента больше нуля.')

    store = _resolve_store(interactiv_rlk)
    if store is None:
        raise ExpressAuctionError('Не указана стоянка в оценке.')

    if date_start is None:
        date_start = timezone.now() + dt.timedelta(hours=1)
    elif timezone.is_naive(date_start):
        date_start = timezone.make_aware(date_start, timezone.get_current_timezone())

    lot_description = build_express_auction_description(
        estimation,
        matrix_info,
        date_start,
        custom_text=lot_description,
    )

    auction_uid = None
    with transaction.atomic():
        car = get_or_create_express_car(
            interactiv_rlk,
            estimation,
            matrix_info['client_price'],
            matrix_info['auction_start_price'],
        )

        auction = Auction(
            user=user,
            store=store,
            start_price=matrix_info['auction_start_price'],
            dateStart=date_start,
            description=lot_description,
            is_express=True,
        )
        auction.save()

        build_auction_structure(auction, car, interactiv_rlk, estimation)

        soglasovanie.auction_client_price = matrix_info['client_price']
        soglasovanie.auction_start_price = matrix_info['auction_start_price']
        soglasovanie.express_auction = auction
        soglasovanie.save(update_fields=[
            'auction_client_price',
            'auction_start_price',
            'express_auction',
        ])
        auction_uid = auction.uid

    from task_manager.views import send_auction

    auction = Auction.objects.get(uid=auction_uid)
    _validate_auction_before_send(auction)
    send_auction(auction)
    auction.refresh_from_db()

    return auction, matrix_info
