from django.contrib import admin
from .models import CarCalculations, PriceCarBrand, BrandKM, PriceCarKmDiscount, PriceCarStageKM, KMCar

@admin.register(CarCalculations)
class CarCalculationsAdmin(admin.ModelAdmin):
    list_display = ('date', 'number', 'car', 'kvp', 'km_raschet', 'amount', 'unit', 'price', 'comment',)
    list_filter = ('unit', )
    raw_id_fields = ('rlk', 'unit', 'staff', 'author', 'user', 'car', )
    search_fields = ('rlk__nomer',)
    ordering = ('-date',)


@admin.register(PriceCarKmDiscount)
class PriceCarKmDiscountAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'modification', 'complectation', 'year', 'discount_percent', 'date_from', 'date_to')
    list_filter = ('brand', 'date_from')
    search_fields = ('brand__name',)
    ordering = ('-date_from', 'brand')


@admin.register(PriceCarBrand)
class PriceCarBrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('marks', 'models_included')


@admin.register(BrandKM)
class BrandKMAdmin(admin.ModelAdmin):
    list_display = ('brand', 'month', 'km', 'km_min_dc')
    list_filter = ('brand', 'month')
    search_fields = ('brand__name',)
    date_hierarchy = 'month'
    ordering = ('-month', 'brand')


@admin.register(PriceCarStageKM)
class PriceCarStageKMAdmin(admin.ModelAdmin):
    list_display = ('stage', 'month', 'km_index')
    list_filter = ('stage', 'month')
    search_fields = ('stage__name',)
    date_hierarchy = 'month'
    ordering = ('-month', 'stage')


@admin.register(KMCar)
class KMCarAdmin(admin.ModelAdmin):
    list_display = ('date', 'car', 'km', 'type_km', 'km_manual', 'km_auto_1', 'km_auto_2', 'km_auto_3')
    list_filter = ('date',)
    raw_id_fields = ('car',)
    search_fields = ('car__vin', 'car__name', 'car__slug')
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('km',)
