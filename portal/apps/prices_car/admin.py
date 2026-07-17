from django.contrib import admin
from .models import (
    BrandKM,
    CarCalculations,
    CarCalculationsTypeDetail,
    CarCalculationUkApproval,
    KMCar,
    PriceCarBrand,
    PriceCarKmDiscount,
    PriceCarStageKM,
)

@admin.register(CarCalculations)
class CarCalculationsAdmin(admin.ModelAdmin):
    list_display = ('date', 'number', 'active', 'car', 'kvp', 'km_raschet', 'amount', 'unit', 'price', 'comment',)
    list_filter = ('unit', )
    raw_id_fields = ('rlk', 'unit', 'staff', 'author', 'user', 'car', )
    search_fields = ('rlk__nomer',)
    ordering = ('-date',)


@admin.register(CarCalculationUkApproval)
class CarCalculationUkApprovalAdmin(admin.ModelAdmin):
    list_display = (
        'approved_at', 'rlk', 'car', 'approved_kvp',
        'approved_by', 'calculation',
    )
    list_filter = ('approved_at',)
    raw_id_fields = ('rlk', 'car', 'approved_by', 'calculation')
    search_fields = (
        'rlk__nomer', 'car__vin', 'calculation__number',
        'approved_by__username',
    )
    ordering = ('approved_kvp', '-approved_at')
    readonly_fields = (
        'approved_at', 'rlk', 'car', 'approved_kvp',
        'approved_by', 'calculation', 'comment', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ('GET', 'HEAD', 'OPTIONS')

    def has_delete_permission(self, request, obj=None):
        return False


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
    list_display = ('brand', 'month', 'km', 'km_min_dc', 'allow_dc_transfers')
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


@admin.register(CarCalculationsTypeDetail)
class CarCalculationsTypeDetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_trade_in')
    list_filter = ('is_trade_in',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(KMCar)
class KMCarAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'car', 'km', 'type_km', 'km_manual',
        'km_auto_k', 'km_auto_k_tradein', 'km_auto_1', 'km_auto_2', 'km_auto_3',
    )
    list_filter = ('date',)
    raw_id_fields = ('car',)
    search_fields = ('car__vin', 'car__name', 'car__slug')
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('km',)
