"""Фоновые задачи MyKors — отдельная очередь, не блокирует портал."""
from background_task import background


@background(queue='mykors_sync')
def export_stock_cars_task(force=False, limit=0, car_id=0):
    """
    Фоновая выгрузка стока в MyKors.
    Запускать через process_tasks --queue mykors_sync
    """
    from mykors.export_cars import export_stock_cars

    export_stock_cars(
        force=bool(force),
        limit=int(limit) if limit else None,
        car_id=int(car_id) if car_id else None,
    )


@background(queue='mykors_sync')
def export_staff_task(limit=0, user_id=0):
    """
    Фоновая выгрузка сотрудников в MyKors.
    Запускать через process_tasks --queue mykors_sync
    """
    from mykors.export_staff import export_staff

    export_staff(
        limit=int(limit) if limit else None,
        user_id=int(user_id) if user_id else None,
    )


@background(queue='mykors_sync')
def export_work_orders_task(limit=0, uin=''):
    """
    Фоновая выгрузка заказ-нарядов в MyKors.
    Запускать через process_tasks --queue mykors_sync
    """
    from mykors.export_work_orders import export_work_orders

    export_work_orders(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_work_orders_ka_task(limit=0, uin=''):
    """Фоновая выгрузка заказ-нарядов КорсАвто в MyKors."""
    from mykors.export_work_orders_ka import export_work_orders_ka

    export_work_orders_ka(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_services_ka_task(limit=0, uin=''):
    """Фоновая выгрузка поступлений услуг КорсАвто в MyKors."""
    from mykors.export_services_ka import export_services_ka

    export_services_ka(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_service_requests_task(limit=0, uin=''):
    """Фоновая выгрузка заявок на ремонт в MyKors."""
    from mykors.export_service_requests import export_service_requests

    export_service_requests(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_worksheets_task(limit=0, uin=''):
    """Фоновая выгрузка рабочих листов в MyKors."""
    from mykors.export_worksheets import export_worksheets

    export_worksheets(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_evaluations_task(limit=0, uin=''):
    """Фоновая выгрузка листов оценок в MyKors."""
    from mykors.export_evaluations import export_evaluations

    export_evaluations(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_car_agreements_task(limit=0, uin=''):
    """Фоновая выгрузка соглашений в MyKors."""
    from mykors.export_car_agreements import export_car_agreements

    export_car_agreements(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_car_shipments_task(limit=0, uin=''):
    """Фоновая выгрузка отгрузок в MyKors."""
    from mykors.export_car_shipments import export_car_shipments

    export_car_shipments(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


@background(queue='mykors_sync')
def export_sms_task(limit=0, uin=''):
    """Фоновая выгрузка СМС в MyKors."""
    from mykors.export_sms import export_sms

    export_sms(
        limit=int(limit) if limit else None,
        uin=uin or None,
    )


