"""Контекст вкладок карточки лота Аукцион Авито: склад, продажи, оценки."""

from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from refs.models import AutoruMark, AutoruModel, AutoruModification, RefCarsOrganization, RefUnit
from register.models import RegInteractivOcenkaRLK

TAB_PAGE_SIZE = 25


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


def resolve_autoru_models(vehicle):
    if not vehicle:
        return None
    brand = (getattr(vehicle, 'brand_name', None) or '').strip()
    model_name = (getattr(vehicle, 'model_name', None) or '').strip()
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
    if model_name:
        models_qs = models_qs.filter(
            Q(name__icontains=model_name)
            | Q(nameHuman__icontains=model_name)
            | Q(nameEn__icontains=model_name)
        )
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

    return {
        'mark': mark,
        'brand_name': brand,
        'model_name': model_name,
        'models': models,
        'model_ids': model_ids,
    }


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
    }


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


def lot_sales_page(model_ids, date_from, date_to, page=1):
    if not model_ids:
        return [], 0, None

    mod_ids = _modification_id_sites(model_ids)
    if not mod_ids:
        return [], 0, None

    from powerbi.models import Cumulative

    q = Cumulative.objects.filter(
        TipProdazhi='Розница',
        DataProdazhi__gte=date_from,
        DataProdazhi__lte=date_to,
        SebestoimostPoDokumentu__gt=0,
        IDModifikatsii__in=mod_ids,
    ).order_by('-DataProdazhi')

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
            'VyruchkaZaAvto': row.VyruchkaZaAvto,
            'PodrazdelenieDTs': row.PodrazdelenieDTs,
            'TipProdazhi': row.TipProdazhi,
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
):
    qs = _estimation_base_qs(model_ctx, brand_name, model_name)
    if qs is None:
        return [], 0, None, []

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

    qs = qs.order_by('-estimation__start_estimation')
    unit_choices = estimation_unit_choices(model_ctx, brand_name, model_name)

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
