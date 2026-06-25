from django.contrib import admin
from .models import IndicatorKVP, CalculatedCumulativeData


@admin.register(IndicatorKVP)
class IndicatorKVPAdmin(admin.ModelAdmin):
    list_display = ('name', 'bu_wheels', 'osago', 'kasko', 'credit', 'gap', 'life',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(CalculatedCumulativeData)
class CalculatedCumulativeDataAdmin(admin.ModelAdmin):
    list_display = ('agreement', 'indicatorKVP', 'amount', 'author', 'send_1c', 'comment',)
    list_filter = ('indicatorKVP', 'send_1c',)
    raw_id_fields = ('agreement', 'indicatorKVP', )
    search_fields = ('agreement__nomer',)
    ordering = ('-agreement__dataTime',)
