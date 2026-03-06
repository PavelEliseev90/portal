from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError

from refs.models import AutoruMark, AutoruModel, RefStagePrice
from .models import PriceCarBrand, BrandKM, PriceCarKmDiscount, PriceCarStageKM


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
def brands_list(request):
    """Настройки брендов: список, добавление и редактирование."""
    brands = PriceCarBrand.objects.prefetch_related('marks', 'models_included').order_by('name')
    marks_avtosalon = AutoruMark.objects.filter(avtosalon=True).order_by('name')
    models_all = AutoruModel.objects.select_related('mark').order_by('mark__name', 'name')

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
            'models_all': models_all,
            'brand_edit': brand_edit,
        },
    })


@login_required
def settings_page(request):
    """Страница настроек: км по брендам на месяц (BrandKM)."""
    brands = PriceCarBrand.objects.order_by('name')
    items = BrandKM.objects.select_related('brand').order_by('-month', 'brand')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(BrandKM, pk=pk)
                obj.delete()
                messages.success(request, 'Запись удалена.')
            return redirect('prices_car:settings')

        if action == 'add':
            brand_id = request.POST.get('brand')
            month_str = request.POST.get('month', '').strip()
            km_str = request.POST.get('km', '0').strip()
            km_index_rdo_str = request.POST.get('km_index_rdo', '').strip().replace(',', '.')
            if not brand_id or not month_str:
                messages.error(request, 'Укажите бренд и месяц.')
                return redirect('prices_car:settings')
            try:
                km = int(km_str) if km_str else 0
                if km < 0:
                    km = 0
            except ValueError:
                km = 0
            try:
                km_index_rdo = float(km_index_rdo_str) if km_index_rdo_str else None
            except ValueError:
                km_index_rdo = None
            try:
                parts = month_str.split('-')
                if len(parts) >= 2:
                    year, month = int(parts[0]), int(parts[1])
                    month_date = date(year, month, 1)
                else:
                    messages.error(request, 'Неверный формат месяца (нужен ГГГГ-ММ).')
                    return redirect('prices_car:settings')
            except (ValueError, IndexError):
                messages.error(request, 'Неверный формат месяца.')
                return redirect('prices_car:settings')

            if not PriceCarBrand.objects.filter(pk=brand_id).exists():
                messages.error(request, 'Выберите бренд из списка.')
                return redirect('prices_car:settings')

            defaults = {'km': km, 'km_index_rdo': km_index_rdo}
            obj, created = BrandKM.objects.update_or_create(
                brand_id=brand_id,
                month=month_date,
                defaults=defaults,
            )
            if created:
                messages.success(request, 'Запись добавлена.')
            else:
                messages.success(request, 'Запись обновлена.')
            return redirect('prices_car:settings')

    return render(request, 'prices_car/settings.html', {
        'params': {
            'brands': brands,
            'items': items,
        },
    })


@login_required
def stage_km_page(request):
    """Индексы Км по этапам УС: этап установки цены + месяц + значение индекса."""
    stages = RefStagePrice.objects.order_by('name')
    items = PriceCarStageKM.objects.select_related('stage').order_by('-month', 'stage')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(PriceCarStageKM, pk=pk)
                obj.delete()
                messages.success(request, 'Запись удалена.')
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
            return redirect('prices_car:stage_km')

    return render(request, 'prices_car/stage_km.html', {
        'params': {
            'stages': stages,
            'items': items,
        },
    })


@login_required
def discount_km_page(request):
    """Управление дисконтом Км: процент изменения минимального Км по бренду/модели/модификации/комплектации/году, срок в рамках месяца."""
    from refs.models import AutoruModification, AutoruComplectation

    discount_edit = None
    brands = PriceCarBrand.objects.order_by('name')
    models_all = AutoruModel.objects.select_related('mark').order_by('mark__name', 'name')
    modifications_all = AutoruModification.objects.select_related('model__mark').order_by('model__mark__name', 'model__name', 'name')
    complectations_all = AutoruComplectation.objects.select_related('modification__model__mark').order_by('modification__model__mark__name', 'modification__name', 'name')
    items = PriceCarKmDiscount.objects.select_related(
        'brand', 'model', 'model__mark', 'modification', 'complectation'
    ).order_by('-date_from', 'brand')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'delete':
            pk = request.POST.get('id')
            if pk:
                obj = get_object_or_404(PriceCarKmDiscount, pk=pk)
                obj.delete()
                messages.success(request, 'Запись удалена.')
            return redirect('prices_car:discount_km')

        if action in ('add', 'edit'):
            pk = request.POST.get('id') if action == 'edit' else None
            brand_id = request.POST.get('brand')
            if not brand_id:
                messages.error(request, 'Укажите бренд.')
                return redirect('prices_car:discount_km')
            try:
                discount_percent = float(request.POST.get('discount_percent', '0').replace(',', '.'))
            except ValueError:
                messages.error(request, 'Неверное значение процента.')
                return redirect('prices_car:discount_km')
            date_from_str = request.POST.get('date_from', '').strip()
            date_to_str = request.POST.get('date_to', '').strip()
            if not date_from_str or not date_to_str:
                messages.error(request, 'Укажите срок действия (с и по).')
                return redirect('prices_car:discount_km')
            try:
                date_from = date.fromisoformat(date_from_str)
                date_to = date.fromisoformat(date_to_str)
            except ValueError:
                messages.error(request, 'Неверный формат даты (нужен ГГГГ-ММ-ДД).')
                return redirect('prices_car:discount_km')

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
                return redirect('prices_car:discount_km')
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
            'models_all': models_all,
            'modifications_all': modifications_all,
            'complectations_all': complectations_all,
            'items': items,
            'discount_edit': discount_edit,
        },
    })
