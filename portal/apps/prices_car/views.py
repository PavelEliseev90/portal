import calendar
import os
from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Min
from documents.models import DocCarAgreement, DocZN, DocCarShipment
from refs.models import AutoruMark, AutoruModel, RefStagePrice, RefUnit
from .models import PriceCarBrand, BrandKM, PriceCarKmDiscount, PriceCarStageKM, CarCalculations
from .calculations_table import (
    CALC_LIST_SORT_FIELDS,
    build_columns_settings,
    build_table_columns,
    export_cell_value,
    save_user_table_columns,
)


def _prev_month_first(month_date: date) -> date:
    """Первый день календарного месяца, предшествующего month_date."""
    if month_date.month == 1:
        return date(month_date.year - 1, 12, 1)
    return date(month_date.year, month_date.month - 1, 1)


_RU_MONTHS_NOM = (
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
)


def _month_first_from_str(month_str: str):
    """Парсит YYYY-MM в date первого числа или None."""
    month_str = (month_str or '').strip()
    if not month_str:
        return None
    try:
        parts = month_str.split('-')
        if len(parts) < 2:
            raise ValueError
        year, month = int(parts[0]), int(parts[1])
        return date(year, month, 1)
    except (ValueError, IndexError):
        return None


def _shift_month_first(month_date: date, delta: int) -> date:
    """Сдвиг на delta месяцев от первого числа month_date."""
    y, m = month_date.year, month_date.month + delta
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return date(y, m, 1)


def _month_title_ru(month_date: date) -> str:
    return '%s %s' % (_RU_MONTHS_NOM[month_date.month - 1], month_date.year)


def _redirect_settings(month_str: str = None):
    url = reverse('prices_car:settings')
    if month_str:
        url = '%s?month=%s' % (url, month_str)
    return redirect(url)


@login_required
def index(request):
    """Управление ценообразованием новых — главная страница с блоками."""
    return render(request, 'prices_car/index.html', {'params': {}})


@login_required
def director_dashboard(request):
    """Директор ГК: та же логика и шаблон, что /cars/director/, открыто из раздела ценообразования."""
    from avtosalon.views import gk_director_dashboard
    return gk_director_dashboard(request)


@login_required
def brands_get_models(request):
    """AJAX: модели по выбранным маркам (для форм брендов, калькуляций и т.п.)."""
    mark_ids = request.GET.getlist('mark_ids[]') or request.GET.getlist('mark_ids')
    search = (request.GET.get('search') or '').strip()
    if not mark_ids:
        return JsonResponse({'models': []})
    try:
        mark_ids_int = [int(mid) for mid in mark_ids if mid]
        if not mark_ids_int:
            return JsonResponse({'models': []})
        models = (
            AutoruModel.objects.filter(mark_id__in=mark_ids_int)
            .select_related('mark')
            .only('id', 'name', 'mark')
            .order_by('mark__name', 'name')
        )
        if search:
            models = models.filter(name__icontains=search)
        models = models[:500]
        return JsonResponse({
            'models': [{'id': m.id, 'name': m.name, 'mark_name': m.mark.name} for m in models]
        })
    except (ValueError, TypeError):
        return JsonResponse({'models': []})


@login_required
def brands_list(request):
    """Настройки брендов: список, добавление и редактирование."""
    brands = PriceCarBrand.objects.prefetch_related('marks', 'models_included').order_by('name')
    marks_avtosalon = AutoruMark.objects.filter(avtosalon=True).only('id', 'name').order_by('name')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(PriceCarBrand, pk=pk)
                obj.delete()
                messages.success(request, 'Бренд удалён.')
            return redirect('prices_car:brands')

        if action in ('add', 'edit'):
            pk = request.POST.get('id') if action == 'edit' else None
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, 'Укажите название бренда.')
                return redirect('prices_car:brands')
            mark_ids = request.POST.getlist('marks')
            model_ids = request.POST.getlist('models_included')

            if pk:
                brand = get_object_or_404(PriceCarBrand, pk=pk)
                brand.name = name
                brand.save()
            else:
                brand = PriceCarBrand.objects.create(name=name)

            brand.marks.set(AutoruMark.objects.filter(pk__in=mark_ids) if mark_ids else [])
            brand.models_included.set(AutoruModel.objects.filter(pk__in=model_ids) if model_ids else [])
            messages.success(request, 'Бренд сохранён.')
            return redirect('prices_car:brands')

    edit_id = request.GET.get('edit')
    brand_edit = None
    if edit_id:
        brand_edit = PriceCarBrand.objects.filter(pk=edit_id).prefetch_related('marks', 'models_included').first()

    return render(request, 'prices_car/brands.html', {
        'params': {
            'brands': brands,
            'marks_avtosalon': marks_avtosalon,
            'brand_edit': brand_edit,
        },
    })


@login_required
def settings_km_preview(request):
    """JSON: для выбранного месяца — км прошлого месяца и текущие км по каждому бренду."""
    month_str = request.GET.get('month', '').strip()
    if not month_str:
        return JsonResponse({'error': 'Укажите месяц'}, status=400)
    try:
        parts = month_str.split('-')
        if len(parts) < 2:
            raise ValueError
        year, month = int(parts[0]), int(parts[1])
        month_date = date(year, month, 1)
    except (ValueError, IndexError):
        return JsonResponse({'error': 'Неверный формат месяца'}, status=400)

    prev_month = _prev_month_first(month_date)
    brands = list(PriceCarBrand.objects.order_by('name').values('id', 'name'))

    prev_kms = {
        x['brand_id']: x['km']
        for x in BrandKM.objects.filter(month=prev_month).values('brand_id', 'km')
    }
    curr_kms = {
        x['brand_id']: x['km']
        for x in BrandKM.objects.filter(month=month_date).values('brand_id', 'km')
    }

    out = []
    for b in brands:
        bid = b['id']
        out.append({
            'id': bid,
            'name': b['name'],
            'prev_km': prev_kms.get(bid),
            'current_km': curr_kms.get(bid),
        })

    return JsonResponse({
        'prev_month_label': prev_month.strftime('%Y-%m'),
        'month_label': month_date.strftime('%Y-%m'),
        'brands': out,
    })


@login_required
def settings_page(request):
    """Страница настроек: км по брендам на месяц (BrandKM)."""
    brands = PriceCarBrand.objects.order_by('name')

    today = timezone.now().date()
    calendar_month = date(today.year, today.month, 1)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(BrandKM, pk=pk)
                obj.delete()
                messages.success(request, 'Запись удалена.')
            return_month = request.POST.get('return_month', '').strip()
            if _month_first_from_str(return_month):
                return _redirect_settings(return_month)
            return _redirect_settings()

        if action == 'bulk_save':
            month_str = request.POST.get('month', '').strip()
            if not month_str:
                messages.error(request, 'Укажите месяц.')
                return _redirect_settings()
            try:
                parts = month_str.split('-')
                if len(parts) < 2:
                    raise ValueError
                year, month = int(parts[0]), int(parts[1])
                month_date = date(year, month, 1)
            except (ValueError, IndexError):
                messages.error(request, 'Неверный формат месяца (нужен ГГГГ-ММ).')
                return _redirect_settings()

            brand_ids = list(PriceCarBrand.objects.values_list('id', flat=True))
            if not brand_ids:
                messages.warning(request, 'Нет брендов для сохранения.')
                return _redirect_settings(month_str)

            def _parse_nonneg_int(raw):
                raw = (raw or '').strip().replace(' ', '').replace('\u00a0', '')
                if not raw:
                    return 0
                try:
                    val = int(raw)
                    return val if val >= 0 else 0
                except ValueError:
                    return 0

            with transaction.atomic():
                for bid in brand_ids:
                    km = _parse_nonneg_int(request.POST.get('km_%s' % bid))
                    km_min_dc = _parse_nonneg_int(request.POST.get('km_min_dc_%s' % bid))
                    BrandKM.objects.update_or_create(
                        brand_id=bid,
                        month=month_date,
                        defaults={'km': km, 'km_min_dc': km_min_dc},
                    )

            messages.success(
                request,
                'Сохранены КМ по всем брендам на %s.' % month_date.strftime('%Y-%m'),
            )
            return _redirect_settings(month_date.strftime('%Y-%m'))

    month_str_get = request.GET.get('month', '').strip()
    filter_month_date = _month_first_from_str(month_str_get)
    if filter_month_date is None:
        filter_month_date = calendar_month
    filter_month_str = filter_month_date.strftime('%Y-%m')

    items = BrandKM.objects.select_related('brand').filter(
        month=filter_month_date,
    ).order_by('brand__name')

    return render(request, 'prices_car/settings.html', {
        'params': {
            'brands': brands,
            'items': items,
            'default_month': filter_month_str,
            'filter_month': filter_month_str,
            'filter_month_title': _month_title_ru(filter_month_date),
            'prev_month': _shift_month_first(filter_month_date, -1).strftime('%Y-%m'),
            'next_month': _shift_month_first(filter_month_date, 1).strftime('%Y-%m'),
            'is_filter_calendar_month': filter_month_date == calendar_month,
        },
    })


def _match_ref_stage_for_block(stages_list, block_key):
    """Сопоставляет этап УС из справочника с одним из фиксированных блоков на странице."""
    for s in stages_list:
        n = (s.name or '').strip().lower()
        if block_key == 'test_price':
            if ('тест' in n and 'прайс' in n) or n in ('тест - прайс', 'тест-прайс'):
                return s
        elif block_key == 'rdo':
            if n == 'рдо' or n.startswith('рдо '):
                return s
        elif block_key == 'correction':
            if 'коррекц' in n:
                return s
        elif block_key == 'txt':
            if 'тхт' in n:
                return s
    return None


def _stage_km_blocks(stages_queryset):
    """Четыре карточки: последний индекс по этапу и период (месяц)."""
    stages_list = list(stages_queryset)
    specs = (
        ('test_price', 'Тест - прайс'),
        ('rdo', 'РДО'),
        ('correction', 'Коррекция'),
        ('txt', 'ТХТ'),
    )
    out = []
    for key, title in specs:
        stage = _match_ref_stage_for_block(stages_list, key)
        latest = None
        if stage:
            latest = (
                PriceCarStageKM.objects.filter(stage=stage)
                .select_related('stage')
                .order_by('-month')
                .first()
            )
        out.append({
            'key': key,
            'title': title,
            'stage': stage,
            'stage_id': stage.id if stage else None,
            'latest': latest,
        })
    return out


@login_required
def stage_km_page(request):
    """Индексы Км по этапам УС: этап установки цены + месяц + значение индекса."""
    stages = RefStagePrice.objects.order_by('name')
    items_qs = PriceCarStageKM.objects.select_related('stage').order_by('-month', 'stage')

    paginator = Paginator(items_qs, 10)
    page_number = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(PriceCarStageKM, pk=pk)
                obj.delete()
                messages.success(request, 'Запись удалена.')
            rp = request.POST.get('return_page', '').strip()
            url = reverse('prices_car:stage_km')
            if rp.isdigit():
                return redirect('%s?page=%s' % (url, rp))
            return redirect('prices_car:stage_km')

        if action == 'add':
            stage_id = request.POST.get('stage')
            month_str = request.POST.get('month', '').strip()
            km_index_str = request.POST.get('km_index', '0').strip().replace(',', '.')
            if not stage_id or not month_str:
                messages.error(request, 'Укажите этап УС и месяц.')
                return redirect('prices_car:stage_km')
            try:
                km_index = float(km_index_str) if km_index_str else 0
            except ValueError:
                km_index = 0
            try:
                parts = month_str.split('-')
                if len(parts) >= 2:
                    year, month = int(parts[0]), int(parts[1])
                    month_date = date(year, month, 1)
                else:
                    messages.error(request, 'Неверный формат месяца (нужен ГГГГ-ММ).')
                    return redirect('prices_car:stage_km')
            except (ValueError, IndexError):
                messages.error(request, 'Неверный формат месяца.')
                return redirect('prices_car:stage_km')

            if not RefStagePrice.objects.filter(pk=stage_id).exists():
                messages.error(request, 'Выберите этап из списка.')
                return redirect('prices_car:stage_km')

            obj, created = PriceCarStageKM.objects.update_or_create(
                stage_id=stage_id,
                month=month_date,
                defaults={'km_index': km_index},
            )
            if created:
                messages.success(request, 'Запись добавлена.')
            else:
                messages.success(request, 'Запись обновлена.')
            rp = request.POST.get('return_page', '').strip()
            url = reverse('prices_car:stage_km')
            if rp.isdigit():
                return redirect('%s?page=%s' % (url, rp))
            return redirect('prices_car:stage_km')

    today = timezone.now().date()
    default_month = date(today.year, today.month, 1).strftime('%Y-%m')

    return render(request, 'prices_car/stage_km.html', {
        'params': {
            'stages': stages,
            'items': page_obj,
            'page_obj': page_obj,
            'stage_blocks': _stage_km_blocks(stages),
            'default_month': default_month,
        },
    })


@login_required
def discount_get_models(request):
    """AJAX: модели по выбранному бренду (PriceCarBrand)."""
    from django.http import JsonResponse
    brand_id = request.GET.get('brand_id', '').strip()
    if not brand_id:
        return JsonResponse({'models': []})
    try:
        brand = PriceCarBrand.objects.prefetch_related('marks', 'models_included').get(pk=int(brand_id))
        if brand.models_included.exists():
            models = brand.models_included.select_related('mark').order_by('mark__name', 'name')
        else:
            models = AutoruModel.objects.filter(mark__in=brand.marks.all()).select_related('mark').order_by('mark__name', 'name')
        models = list(models[:500])
        return JsonResponse({'models': [{'id': m.id, 'name': m.name, 'mark_name': m.mark.name} for m in models]})
    except (ValueError, PriceCarBrand.DoesNotExist):
        return JsonResponse({'models': []})


@login_required
def discount_get_modifications(request):
    """AJAX: модификации по выбранной модели."""
    from django.http import JsonResponse
    from refs.models import AutoruModification
    model_id = request.GET.get('model_id', '').strip()
    if not model_id:
        return JsonResponse({'modifications': []})
    try:
        mods = AutoruModification.objects.filter(model_id=int(model_id)).select_related('model').order_by('name')[:500]
        return JsonResponse({'modifications': [{'id': m.id, 'name': m.name, 'model_name': m.model.name} for m in mods]})
    except (ValueError, TypeError):
        return JsonResponse({'modifications': []})


@login_required
def discount_get_complectations(request):
    """AJAX: комплектации по выбранной модификации."""
    from django.http import JsonResponse
    from refs.models import AutoruComplectation
    modification_id = request.GET.get('modification_id', '').strip()
    if not modification_id:
        return JsonResponse({'complectations': []})
    try:
        comps = AutoruComplectation.objects.filter(modification_id=int(modification_id)).select_related('modification').order_by('name')[:500]
        return JsonResponse({'complectations': [{'id': c.id, 'name': c.name, 'modification_name': c.modification.name} for c in comps]})
    except (ValueError, TypeError):
        return JsonResponse({'complectations': []})


def _redirect_discount_km(request):
    """Сохраняет query-строку фильтров после POST."""
    rq = request.POST.get('return_query', '').strip()
    url = reverse('prices_car:discount_km')
    if rq:
        return redirect('%s?%s' % (url, rq))
    return redirect(url)


def _parse_iso_date(s):
    s = (s or '').strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


@login_required
def discount_km_page(request):
    """Управление дисконтом Км: процент изменения минимального Км по бренду/модели/модификации/комплектации/году, срок в рамках месяца."""
    discount_edit = None
    brands = PriceCarBrand.objects.only('id', 'name').order_by('name')
    today = timezone.now().date()

    get_params = request.GET.copy()
    get_params.pop('edit', None)
    filter_query = get_params.urlencode()

    qs = PriceCarKmDiscount.objects.select_related(
        'brand', 'model', 'model__mark', 'modification', 'complectation'
    )

    f_brand = request.GET.get('f_brand', '').strip()
    if f_brand:
        try:
            qs = qs.filter(brand_id=int(f_brand))
        except ValueError:
            pass

    df_min = _parse_iso_date(request.GET.get('df_min'))
    df_max = _parse_iso_date(request.GET.get('df_max'))
    if df_min:
        qs = qs.filter(date_from__gte=df_min)
    if df_max:
        qs = qs.filter(date_from__lte=df_max)

    dt_min = _parse_iso_date(request.GET.get('dt_min'))
    dt_max = _parse_iso_date(request.GET.get('dt_max'))
    if dt_min:
        qs = qs.filter(date_to__gte=dt_min)
    if dt_max:
        qs = qs.filter(date_to__lte=dt_max)

    pct_min_str = request.GET.get('pct_min', '').strip()
    pct_max_str = request.GET.get('pct_max', '').strip()
    if pct_min_str:
        try:
            qs = qs.filter(discount_percent__gte=float(pct_min_str.replace(',', '.')))
        except ValueError:
            pass
    if pct_max_str:
        try:
            qs = qs.filter(discount_percent__lte=float(pct_max_str.replace(',', '.')))
        except ValueError:
            pass

    items = qs.order_by('-date_from', 'brand')

    filtr = {
        'f_brand': f_brand,
        'df_min': request.GET.get('df_min', '').strip(),
        'df_max': request.GET.get('df_max', '').strip(),
        'dt_min': request.GET.get('dt_min', '').strip(),
        'dt_max': request.GET.get('dt_max', '').strip(),
        'pct_min': pct_min_str,
        'pct_max': pct_max_str,
    }

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(PriceCarKmDiscount, pk=pk)
                obj.delete()
                messages.success(request, 'Запись удалена.')
            return _redirect_discount_km(request)

        if action in ('add', 'edit'):
            pk = request.POST.get('id') if action == 'edit' else None
            brand_id = request.POST.get('brand')
            if not brand_id:
                messages.error(request, 'Укажите бренд.')
                return _redirect_discount_km(request)
            try:
                discount_percent = float(request.POST.get('discount_percent', '0').replace(',', '.'))
            except ValueError:
                messages.error(request, 'Неверное значение процента.')
                return _redirect_discount_km(request)
            date_from_str = request.POST.get('date_from', '').strip()
            date_to_str = request.POST.get('date_to', '').strip()
            if not date_from_str or not date_to_str:
                messages.error(request, 'Укажите срок действия (с и по).')
                return _redirect_discount_km(request)
            try:
                date_from = date.fromisoformat(date_from_str)
                date_to = date.fromisoformat(date_to_str)
            except ValueError:
                messages.error(request, 'Неверный формат даты (нужен ГГГГ-ММ-ДД).')
                return _redirect_discount_km(request)

            model_id = request.POST.get('model') or None
            modification_id = request.POST.get('modification') or None
            complectation_id = request.POST.get('complectation') or None
            year_val = request.POST.get('year', '').strip()
            try:
                year = int(year_val) if year_val else None
            except ValueError:
                year = None

            if pk:
                obj = get_object_or_404(PriceCarKmDiscount, pk=pk)
                obj.brand_id = brand_id
                obj.model_id = model_id
                obj.modification_id = modification_id
                obj.complectation_id = complectation_id
                obj.year = year
                obj.discount_percent = discount_percent
                obj.date_from = date_from
                obj.date_to = date_to
            else:
                obj = PriceCarKmDiscount(
                    brand_id=brand_id,
                    model_id=model_id,
                    modification_id=modification_id,
                    complectation_id=complectation_id,
                    year=year,
                    discount_percent=discount_percent,
                    date_from=date_from,
                    date_to=date_to,
                )
            try:
                obj.save()
                messages.success(request, 'Запись сохранена.')
                return _redirect_discount_km(request)
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, msgs in e.message_dict.items():
                        for msg in msgs:
                            messages.error(request, '{}: {}'.format(field, msg))
                else:
                    messages.error(request, str(e))
                discount_edit = obj

    edit_id = request.GET.get('edit')
    if edit_id and discount_edit is None:
        discount_edit = PriceCarKmDiscount.objects.filter(pk=edit_id).select_related(
            'brand', 'model', 'modification', 'complectation'
        ).first()

    return render(request, 'prices_car/discount_km.html', {
        'params': {
            'brands': brands,
            'items': items,
            'discount_edit': discount_edit,
            'today': today,
            'filter_query': filter_query,
            'filtr': filtr,
        },
    })


def _resolve_calc_list_order(order_by: str) -> str:
    default = '-date'
    order_by = (order_by or '').strip()
    if not order_by:
        return default
    desc = order_by.startswith('-')
    field = order_by.lstrip('-')
    db_field = CALC_LIST_SORT_FIELDS.get(field)
    if not db_field:
        return default
    return ('-' if desc else '') + db_field


def _parse_int_id_list(values):
    ids = []
    for raw in values:
        if str(raw).isdigit():
            val = int(raw)
            if val not in ids:
                ids.append(val)
    return ids


def _current_month_period():
    """Первый и последний день текущего календарного месяца."""
    today = timezone.now().date()
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    return first_day, last_day


def _build_calculations_list_queryset(request):
    """Фильтры и queryset калькуляций (список и выгрузка)."""
    date_start = (request.GET.get('date_start') or '').strip()
    date_end = (request.GET.get('date_end') or '').strip()
    if not date_start and not date_end:
        month_start, month_end = _current_month_period()
        date_start = month_start.isoformat()
        date_end = month_end.isoformat()
    vin = (request.GET.get('vin') or '').strip()
    unit_ids = _parse_int_id_list(
        request.GET.getlist('unit[]') + request.GET.getlist('unit_ids')
    )
    mark_ids = _parse_int_id_list(
        request.GET.getlist('mark[]') + request.GET.getlist('mark_ids')
    )
    model_ids = _parse_int_id_list(request.GET.getlist('model[]'))
    agreement_filters = set(request.GET.getlist('agreement_filter'))
    shipment_filters = set(request.GET.getlist('shipment_filter'))
    order_by = _resolve_calc_list_order(request.GET.get('order_by'))

    agreement_qs = (
        DocCarAgreement.objects.filter(rlk_id=OuterRef('rlk_id'), active=True)
        .order_by('-dataTime')
    )
    shipment_qs = (
        DocCarShipment.objects.filter(rlk_id=OuterRef('rlk_id'), active=True)
        .order_by('-dataTime')
    )
    objects = CarCalculations.objects.select_related(
        'rlk', 'rlk__customer', 'unit', 'car', 'author', 'staff',
    ).annotate(
        agreement_pk=Subquery(agreement_qs.values('pk')[:1]),
        agreement_nomer=Subquery(agreement_qs.values('nomer')[:1]),
        shipment_pk=Subquery(shipment_qs.values('pk')[:1]),
        shipment_nomer=Subquery(shipment_qs.values('nomer')[:1]),
    )

    if date_start:
        try:
            objects = objects.filter(date__date__gte=date.fromisoformat(date_start))
        except ValueError:
            pass
    if date_end:
        try:
            objects = objects.filter(date__date__lte=date.fromisoformat(date_end))
        except ValueError:
            pass
    if vin:
        objects = objects.filter(car__vin__icontains=vin)
    if unit_ids:
        objects = objects.filter(unit_id__in=unit_ids)
    if mark_ids:
        objects = objects.filter(car__modification_autoru__model__mark__id__in=mark_ids)
    if model_ids:
        objects = objects.filter(car__modification_autoru__model__id__in=model_ids)

    if agreement_filters == {'yes'}:
        objects = objects.filter(agreement_pk__isnull=False)
    elif agreement_filters == {'no'}:
        objects = objects.filter(agreement_pk__isnull=True)

    if shipment_filters == {'yes'}:
        objects = objects.filter(shipment_pk__isnull=False)
    elif shipment_filters == {'no'}:
        objects = objects.filter(shipment_pk__isnull=True)

    filtr = {
        'date_start': date_start,
        'date_end': date_end,
        'vin': vin,
        'filter_unit': unit_ids,
        'filter_mark': mark_ids,
        'filter_model': model_ids,
        'agreement_filter': list(agreement_filters),
        'shipment_filter': list(shipment_filters),
        'order_by': request.GET.get('order_by') or '-date',
    }
    return objects.order_by(order_by, '-pk'), filtr


@login_required
def calculations_list(request):

    select_units = RefUnit.objects.filter(buauto=False, ib__active=True).filter(name__istartswith='дц').order_by('name')
    select_marks = AutoruMark.objects.only('id', 'name').order_by('name')

    objects, filtr = _build_calculations_list_queryset(request)

    paginator = Paginator(objects, 25)
    page_number = request.GET.get('page') or 1

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'prices_car/calculations_list.html', {
        'params': {
            'objects': page_obj,
            'filtr': filtr,
            'select_units': select_units,
            'select_marks': select_marks,
            'table_columns': build_table_columns(request.user),
            'columns_settings': build_columns_settings(request.user),
        },
    })


@login_required
def calculations_list_columns_save(request):
    """Сохранение персонального порядка и состава столбцов таблицы."""
    import json

    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)

    columns = payload.get('columns')
    if not isinstance(columns, list):
        return JsonResponse({'error': 'Передайте массив columns'}, status=400)
    try:
        saved = save_user_table_columns(request.user, columns)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse({
        'ok': True,
        'columns': saved,
    })


@login_required
def calculations_list_export(request):
    """Выгрузка отфильтрованного списка калькуляций в Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    objects, _filtr = _build_calculations_list_queryset(request)
    table_columns = build_table_columns(request.user)
    headers = [col['label_export'] for col in table_columns]

    wb = Workbook()
    ws = wb.active
    ws.title = 'Калькуляции'
    ws.append(headers)

    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    column_keys = [col['key'] for col in table_columns]
    for item in objects.iterator(chunk_size=500):
        ws.append([export_cell_value(item, key) for key in column_keys])

    for col in range(1, len(headers) + 1):
        column_letter = get_column_letter(col)
        max_length = 0
        for cell in ws[column_letter]:
            try:
                if cell.value is not None and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    filename = 'calculations_%s.xlsx' % datetime.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    wb.save(response)
    return response


def _presentation_root():
    return os.path.join(settings.BASE_DIR, 'docs', 'presentation')


@login_required
def presentation_page(request):
    """HTML-презентация: ценообразование новых АМ и калькуляции."""
    path = os.path.join(_presentation_root(), 'cenoobrazovanie-kalkulyacii.html')
    if not os.path.isfile(path):
        raise Http404
    with open(path, encoding='utf-8') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/html; charset=utf-8')


@login_required
def presentation_asset(request, asset):
    """Статические файлы презентации (скриншоты)."""
    asset = asset.replace('\\', '/').lstrip('/')
    if '..' in asset.split('/'):
        raise Http404
    if not asset.startswith('screenshots/'):
        raise Http404
    path = os.path.join(_presentation_root(), asset)
    if not os.path.isfile(path):
        raise Http404
    content_type = 'image/svg+xml' if path.endswith('.svg') else 'application/octet-stream'
    return FileResponse(open(path, 'rb'), content_type=content_type)  # noqa: SIM115