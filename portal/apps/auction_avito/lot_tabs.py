"""Контекст вкладок карточки лота Аукцион Авито: склад, продажи, оценки."""

from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from avtosalon.models import AvtohubModifications
from refs.models import (
    AutoruMark,
    AutoruModel,
    AutoruModification,
    RefCarsOrganization,
    RefUnit,
)
from register.models import RegInteractivOcenkaRLK

TAB_PAGE_SIZE = 25


def vehicle_condition_dict(is_new=None, label=None):
    """Маркер «Новый» / «С пробегом» для таблиц склада и продаж."""
    if is_new is True:
        return {'is_new': True, 'label': 'Новый'}
    if is_new is False:
        return {'is_new': False, 'label': 'С пробегом'}
    return {'is_new': None, 'label': label or '—'}


def condition_from_postuplenie(postuplenie, *, default_new=True):
    """
    Тип АМ по полю Postuplenie (Cumulative).
    Пустое значение в кумулятиве новых считаем «Новый», если default_new.
    """
    s = (postuplenie or '').strip().lower()
    if not s:
        return vehicle_condition_dict(is_new=True if default_new else None)
    if any(x in s for x in ('пробег', 'б/у', 'бу', 'подерж', 'асп', 'trade')):
        return vehicle_condition_dict(is_new=False)
    if 'нов' in s:
        return vehicle_condition_dict(is_new=True)
    return vehicle_condition_dict(label=(postuplenie or '').strip()[:40] or '—')


def default_two_months_period():
    """С 1-го числа прошлого месяца по сегодня."""
    now = timezone.now()
    first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_prev = first_this_month - timedelta(seconds=1)
    date_from = last_prev.replace(day=1).date()
    date_to = now.date()
    return date_from, date_to


def parse_date_param(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def resolve_period(date_from_raw, date_to_raw):
    default_from, default_to = default_two_months_period()
    date_from = parse_date_param(date_from_raw) or default_from
    date_to = parse_date_param(date_to_raw) or default_to
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _vehicle_model_name_variants(vehicle):
    """Варианты названия модели: с поколением (Sportage + IV → Sportage, IV)."""
    model_name = (getattr(vehicle, 'model_name', None) or '').strip()
    generation = (getattr(vehicle, 'generation_name', None) or '').strip()
    if not model_name:
        return []
    variants = []
    if generation:
        variants.extend([
            f'{model_name}, {generation}',
            f'{model_name} {generation}',
        ])
    variants.append(model_name)
    seen = set()
    result = []
    for v in variants:
        key = v.lower()
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def resolve_autoru_models(vehicle, *, include_model_choices=True):
    if not vehicle:
        return None
    brand = (getattr(vehicle, 'brand_name', None) or '').strip()
    model_variants = _vehicle_model_name_variants(vehicle)
    model_name = model_variants[-1] if model_variants else ''
    if not brand:
        return None

    mark = AutoruMark.objects.filter(
        Q(name__iexact=brand) | Q(nameEn__iexact=brand)
    ).first()
    if not mark:
        mark = AutoruMark.objects.filter(name__icontains=brand).first()
    if not mark:
        return {
            'mark': None,
            'brand_name': brand,
            'model_name': model_name,
            'models': [],
            'model_ids': [],
        }

    models_qs = AutoruModel.objects.filter(mark=mark)
    if model_variants:
        q = Q()
        for variant in model_variants:
            q |= (
                Q(name__icontains=variant)
                | Q(nameHuman__icontains=variant)
                | Q(nameEn__icontains=variant)
            )
        models_qs = models_qs.filter(q)
    model_ids = list(models_qs.values_list('id', flat=True)[:80])
    models = []
    if include_model_choices:
        models_qs = models_qs.order_by('name')[:80]
        models = [
            {'id': m.id, 'label': m.nameHuman or m.name}
            for m in models_qs
        ]
        model_ids = [m['id'] for m in models]
        if not model_ids and model_name:
            models_qs = AutoruModel.objects.filter(mark=mark).order_by('name')[:80]
            models = [{'id': m.id, 'label': m.nameHuman or m.name} for m in models_qs]
            model_ids = [m['id'] for m in models]
    elif not model_ids and model_name:
        model_ids = list(
            AutoruModel.objects.filter(mark=mark).values_list('id', flat=True)[:80]
        )

    return {
        'mark': mark,
        'brand_name': brand,
        'model_name': model_name,
        'models': models,
        'model_ids': model_ids,
    }


def build_avito_mod_to_model_ids_map():
    """Связь Avito modification_id → AutoruModel PK по автомобилям на складе."""
    mapping = {}
    rows = (
        RefCarsOrganization.objects.filter(
            modification_avito__isnull=False,
            modification_autoru__isnull=False,
        )
        .values_list('modification_avito__avito_id', 'modification_autoru__model_id')
        .distinct()
    )
    for avito_id, model_id in rows:
        if avito_id and model_id:
            mapping.setdefault(avito_id, set()).add(model_id)
    return mapping


def build_autohub_mod_to_model_ids_map(autohub_mod_ids):
    """Связь Autohub modificationID → AutoruModel PK через avtohubModifications."""
    mapping = {mid: set() for mid in autohub_mod_ids if mid}
    if not mapping:
        return mapping

    ah_by_id = {
        row.id_avtohub: row.autoruId
        for row in AvtohubModifications.objects.filter(id_avtohub__in=mapping.keys())
        if row.autoruId
    }
    autoru_ids = set(ah_by_id.values())
    if not autoru_ids:
        return mapping

    mod_by_autoru = {}
    for mod in AutoruModification.objects.filter(
        Q(idSite__in=autoru_ids) | Q(idSiteTech__in=autoru_ids)
    ).only('idSite', 'idSiteTech', 'model_id'):
        if not mod.model_id:
            continue
        for aid in (mod.idSite, mod.idSiteTech):
            if aid:
                mod_by_autoru.setdefault(aid, set()).add(mod.model_id)

    for ah_id, autoru_id in ah_by_id.items():
        mapping[ah_id].update(mod_by_autoru.get(autoru_id, ()))
    return mapping


def resolve_lot_autoru_model_ids(lot, *, avito_mod_map=None, autohub_mod_map=None):
    """
    AutoruModel PK для сопоставления лота с сегментами продаж БУ.

    Порядок: Autohub modificationID → Avito modification_id (склад) → текст каталога Avito.
    """
    vehicle_avito = getattr(lot, 'vehicle_avito', None)
    vehicle_autohub = getattr(lot, 'vehicle_autohub', None)
    model_ids = []
    seen = set()

    def _add(ids):
        for mid in ids:
            if mid and mid not in seen:
                seen.add(mid)
                model_ids.append(mid)

    autohub_mod_id = getattr(vehicle_autohub, 'modification_id', None) if vehicle_autohub else None
    if autohub_mod_id and autohub_mod_map is not None:
        _add(autohub_mod_map.get(autohub_mod_id, ()))

    avito_mod_id = getattr(vehicle_avito, 'modification_id', None) if vehicle_avito else None
    if avito_mod_id and avito_mod_map is not None:
        _add(avito_mod_map.get(avito_mod_id, ()))

    if vehicle_avito:
        ctx = resolve_autoru_models(vehicle_avito, include_model_choices=False)
        if ctx:
            _add(ctx.get('model_ids') or [])

    return model_ids


def _stock_queryset(model_ids, model_filter_id=None):
    if not model_ids:
        return RefCarsOrganization.objects.none()
    ids = model_ids
    if model_filter_id:
        try:
            mid = int(model_filter_id)
            if mid in model_ids:
                ids = [mid]
        except (TypeError, ValueError):
            pass
    return (
        RefCarsOrganization.objects.filter(
            quantity__gt=0,
            modification_autoru__isnull=False,
            modification_autoru__model_id__in=ids,
        )
        .select_related(
            'modification_autoru',
            'modification_autoru__model',
            'modification_autoru__model__mark',
            'modification_autoru__typeBody',
            'modification_autoru__typeGear',
            'status',
            'store',
            'store__city',
            'unit',
            'type_sale',
            'stage_price',
            'evaluation',
            'type_drive',
            'complectation_autoru',
        )
        .order_by('-date_create')
    )


def _car_to_stock_row(car):
    mod = car.modification_autoru
    return {
        'car': car,
        'slug': car.slug,
        'vin': car.vin,
        'name': car.name or f'{car.mark} {car.model}',
        'year': car.year,
        'run': car.run,
        'price': car.price,
        'cost_price': car.cost_price,
        'days_in_stok': car.days_in_stok,
        'quantity': car.quantity,
        'unit': car.unit.name if car.unit_id else '—',
        'store': car.store.name if car.store_id else '—',
        'city': car.store.city.name if car.store_id and car.store.city_id else '',
        'status': car.status.name if car.status_id else '—',
        'evaluation': car.evaluation.name if car.evaluation_id else '—',
        'stage': car.stage_price.name if car.stage_price_id else '—',
        'modification': mod.name if mod else '—',
        'model': mod.model.name if mod and mod.model_id else '—',
        'mark': mod.model.mark.name if mod and mod.model_id and mod.model.mark_id else '—',
        'complectation': (
            car.complectation_autoru.name
            if car.complectation_autoru_id
            else '—'
        ),
        'body': mod.typeBody.name if mod and mod.typeBody_id else '—',
        'gear': mod.typeGear.name if mod and mod.typeGear_id else '—',
        'drive': car.type_drive.name if car.type_drive_id else '—',
        'color': car.color or '—',
        'owners': car.owners,
        'bcp': car.bcp,
        'condition': vehicle_condition_dict(is_new=bool(car.is_new)),
    }


def lot_stock_count(model_ids, model_filter_id=None):
    return _stock_queryset(model_ids, model_filter_id).count()


def lot_stock_page(model_ids, model_filter_id=None, page=1):
    qs = _stock_queryset(model_ids, model_filter_id)
    paginator = Paginator(qs, TAB_PAGE_SIZE)
    page_obj = paginator.get_page(page)
    rows = [_car_to_stock_row(car) for car in page_obj.object_list]
    return rows, paginator.count, page_obj


def _modification_id_sites(model_ids):
    return [
        x
        for x in AutoruModification.objects.filter(model_id__in=model_ids).values_list(
            'idSite', flat=True
        )
        if x
    ]


def _sales_queryset(model_ids, date_from, date_to):
    mod_ids = _modification_id_sites(model_ids)
    if not mod_ids:
        return None
    from powerbi.models import Cumulative

    return Cumulative.objects.filter(
        TipProdazhi='Розница',
        DataProdazhi__gte=date_from,
        DataProdazhi__lte=date_to,
        SebestoimostPoDokumentu__gt=0,
        IDModifikatsii__in=mod_ids,
    )


def lot_sales_count(model_ids, date_from, date_to):
    q = _sales_queryset(model_ids, date_from, date_to)
    return q.count() if q is not None else 0


def lot_sales_page(model_ids, date_from, date_to, page=1):
    if not model_ids:
        return [], 0, None

    q = _sales_queryset(model_ids, date_from, date_to)
    if q is None:
        return [], 0, None
    q = q.order_by('-DataProdazhi')

    paginator = Paginator(q, TAB_PAGE_SIZE)
    page_obj = paginator.get_page(page)
    rows = []
    for row in page_obj.object_list:
        data = {
            'DataProdazhi': row.DataProdazhi,
            'Marka': row.Marka,
            'Model': row.Model,
            'Modifikatsiya': row.Modifikatsiya,
            'VIN': row.VIN,
            'Postuplenie': row.Postuplenie,
            'VyruchkaZaAvto': row.VyruchkaZaAvto,
            'PodrazdelenieDTs': row.PodrazdelenieDTs,
            'TipProdazhi': row.TipProdazhi,
            'condition': condition_from_postuplenie(row.Postuplenie),
            'SummaMarzhiBezNDS': row.SummaMarzhiBezNDS,
            'VPOPFU': row.VPOPFU,
            'SummaTreydInPoPlanu': row.SummaTreydInPoPlanu,
            'ValovayaPribylZChShiny': row.ValovayaPribylZChShiny,
            'SummaRabot': row.SummaRabot,
            'ValovayaPribylZCh': row.ValovayaPribylZCh,
            'SummaGosreg': row.SummaGosreg,
        }
        data['margin'] = sum(
            x or 0
            for x in (
                data.get('SummaMarzhiBezNDS'),
                data.get('VPOPFU'),
                data.get('SummaTreydInPoPlanu'),
                data.get('ValovayaPribylZChShiny'),
                data.get('SummaRabot'),
                data.get('ValovayaPribylZCh'),
                data.get('SummaGosreg'),
            )
        )
        rows.append(data)
    return rows, paginator.count, page_obj


def _estimation_base_qs(model_ctx, brand_name='', model_name=''):
    qs = (
        RegInteractivOcenkaRLK.objects.exclude(status_id=8)
        .filter(estimation__isnull=False)
        .select_related(
            'status',
            'unit',
            'filial',
            'rlk',
            'estimation',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
            'page_soglasovanie',
        )
    )
    if model_ctx and model_ctx.get('model_ids'):
        qs = qs.filter(
            estimation__modification__model_id__in=model_ctx['model_ids']
        )
    elif brand_name or model_name:
        if brand_name:
            qs = qs.filter(
                Q(estimation__modification__model__mark__name__icontains=brand_name)
                | Q(estimation__mark_name__icontains=brand_name)
            )
        if model_name:
            qs = qs.filter(
                Q(estimation__modification__model__name__icontains=model_name)
                | Q(estimation__model_name__icontains=model_name)
            )
    else:
        return None
    return qs


def _estimation_filtered_qs(
    model_ctx,
    brand_name='',
    model_name='',
    date_from=None,
    date_to=None,
    unit_id=None,
):
    qs = _estimation_base_qs(model_ctx, brand_name, model_name)
    if qs is None:
        return None
    if date_from and date_to:
        qs = qs.filter(
            Q(
                estimation__start_estimation__date__gte=date_from,
                estimation__start_estimation__date__lte=date_to,
            )
            | Q(
                estimation__end_estimation__date__gte=date_from,
                estimation__end_estimation__date__lte=date_to,
            )
        )
    if unit_id:
        try:
            qs = qs.filter(unit_id=int(unit_id))
        except (TypeError, ValueError):
            pass
    return qs


def lot_estimation_count(
    model_ctx,
    brand_name='',
    model_name='',
    date_from=None,
    date_to=None,
    unit_id=None,
):
    qs = _estimation_filtered_qs(
        model_ctx, brand_name, model_name, date_from, date_to, unit_id,
    )
    return qs.count() if qs is not None else 0


def estimation_unit_choices(model_ctx, brand_name='', model_name=''):
    qs = _estimation_base_qs(model_ctx, brand_name, model_name)
    if qs is None:
        return []
    unit_ids = qs.exclude(unit_id__isnull=True).values_list('unit_id', flat=True).distinct()
    return list(
        RefUnit.objects.filter(id__in=unit_ids).order_by('name').values('id', 'name')
    )


def lot_estimation_page(
    model_ctx,
    brand_name='',
    model_name='',
    date_from=None,
    date_to=None,
    unit_id=None,
    page=1,
    *,
    load_unit_choices=False,
):
    qs = _estimation_filtered_qs(
        model_ctx, brand_name, model_name, date_from, date_to, unit_id,
    )
    if qs is None:
        return [], 0, None, []

    qs = qs.order_by('-estimation__start_estimation')
    unit_choices = (
        estimation_unit_choices(model_ctx, brand_name, model_name)
        if load_unit_choices
        else []
    )

    paginator = Paginator(qs, TAB_PAGE_SIZE)
    page_obj = paginator.get_page(page)
    rows = []
    for rlk_est in page_obj.object_list:
        est = rlk_est.estimation
        mod = est.modification if est else None
        sog = rlk_est.page_soglasovanie
        rows.append({
            'rlk_est': rlk_est,
            'rlk_id': rlk_est.rlk_id,
            'rlk_nomer': rlk_est.rlk.nomer if rlk_est.rlk_id else '—',
            'status': rlk_est.status.name if rlk_est.status_id else '—',
            'unit': rlk_est.unit.name if rlk_est.unit_id else '—',
            'filial': rlk_est.filial.name if rlk_est.filial_id else '—',
            'vin': est.vin if est else '',
            'year': est.year if est else '',
            'mark': (
                mod.model.mark.name
                if mod and mod.model_id and mod.model.mark_id
                else (est.mark_name if est else '')
            ),
            'model': mod.model.name if mod and mod.model_id else (est.model_name if est else ''),
            'modification': mod.name if mod else (est.modification_name if est else ''),
            'start': est.start_estimation if est else None,
            'end': est.end_estimation if est else None,
            'price_before_kd': sog.price_before_kd if sog else None,
            'price_after_kd': sog.price_after_kd if sog else None,
        })
    return rows, paginator.count, page_obj, unit_choices
