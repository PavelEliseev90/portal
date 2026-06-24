"""Создание и отправка экспресс-лота аукциона из интерактивной оценки."""
import datetime as dt
import json

from django.db import transaction
from django.utils import timezone

from documents.models import DocLO
from refs.models import Auction, AuctionStructure, RefCarsOrganization, RefTypeSaleCarsOrganization
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


def get_or_create_express_car(interactiv_rlk, estimation, client_price, start_price):
    lo = DocLO.objects.filter(rlk=interactiv_rlk.rlk).first()
    car = None
    if lo:
        car = RefCarsOrganization.objects.filter(lo=lo).first()
    if car:
        car.price = int(client_price or 0)
        car.bcp = int(start_price or 0)
        if not car.store_id:
            car.store = _resolve_store(interactiv_rlk)
        car.save(update_fields=['price', 'bcp', 'store'])
        return car

    type_sale, _ = RefTypeSaleCarsOrganization.objects.get_or_create(name='Аукцион')
    car = RefCarsOrganization(
        organization=interactiv_rlk.organization,
        unit=interactiv_rlk.unit,
        store=_resolve_store(interactiv_rlk),
        lo=lo,
        vin=(estimation.vin or '')[:18],
        year=estimation.year or 0,
        run=_resolve_run(estimation),
        modification_autoru=estimation.modification,
        complectation_autoru=estimation.complectation,
        type_sale=type_sale,
        type_reception=interactiv_rlk.type_reception,
        quantity=1,
        price=int(client_price or 0),
        bcp=int(start_price or 0),
        is_new=False,
        description_op='Экспресс-лот из интерактивной оценки',
    )
    if estimation.modification_id:
        mod = estimation.modification
        try:
            car.mark = mod.model.mark.name
            car.model = mod.model.name
            car.modification = mod.name
        except Exception:
            pass
    elif estimation.mark_name:
        car.mark = estimation.mark_name
        car.model = estimation.model_name or ''
        car.modification = estimation.modification_name or ''
    car.save()
    return car


def build_auction_structure(auction, car, interactiv_rlk, estimation):
    soglasovanie = interactiv_rlk.page_soglasovanie
    diagnostic = ''
    if soglasovanie and soglasovanie.comment_diagnostica:
        diagnostic = soglasovanie.comment_diagnostica

    photos = _collect_photo_lists(estimation.id)
    structure, _ = AuctionStructure.objects.get_or_create(
        auction=auction,
        car=car,
        defaults={'description': 'Экспресс-лот · VIN {}'.format(estimation.vin or '—')},
    )
    structure.description = 'Экспресс-лот · VIN {}'.format(estimation.vin or '—')
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


@transaction.atomic
def create_and_send_express_auction(
    interactiv_rlk,
    estimation,
    user,
    client_price,
    date_start,
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
        description='Экспресс-лот · ЕЦО · VIN {}'.format(estimation.vin or '—'),
        is_express=True,
    )
    auction.save()

    build_auction_structure(auction, car, interactiv_rlk, estimation)

    from task_manager.views import send_auction

    send_auction(auction)

    auction.refresh_from_db()
    soglasovanie.auction_client_price = matrix_info['client_price']
    soglasovanie.auction_start_price = matrix_info['auction_start_price']
    soglasovanie.express_auction = auction
    soglasovanie.save(update_fields=[
        'auction_client_price',
        'auction_start_price',
        'express_auction',
    ])

    return auction, matrix_info
