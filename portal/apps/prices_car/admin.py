from django.contrib import admin
from .models import PriceCarBrand, BrandKM, PriceCarKmDiscount, PriceCarStageKM


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
    list_display = ('brand', 'month', 'km', 'km_index_rdo')
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
