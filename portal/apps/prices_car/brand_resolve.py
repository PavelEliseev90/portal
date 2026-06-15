"""Сопоставление автомобиля с брендом ценообразования PriceCarBrand."""

from .models import PriceCarBrand


def resolve_price_car_brand_for_car(car):
    """
    Подобрать PriceCarBrand для автомобиля.

    - models_included задан — модель авто должна быть в списке;
    - models_included пуст — подходят все модели выбранных марок.

    При нескольких совпадениях приоритет у бренда с явным включением модели.
    """
    if not car or not getattr(car, 'modification_autoru_id', None):
        return None

    mark = car.modification_autoru.model.mark
    model = car.modification_autoru.model
    candidates = list(
        PriceCarBrand.objects.filter(marks=mark)
        .prefetch_related('models_included')
        .order_by('pk')
    )
    if not candidates:
        return None

    explicit_match = None
    generic_match = None
    for brand in candidates:
        included_ids = {m.pk for m in brand.models_included.all()}
        if included_ids:
            if model.pk in included_ids:
                explicit_match = brand
        else:
            generic_match = brand

    return explicit_match or generic_match
