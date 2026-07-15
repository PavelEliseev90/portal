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
