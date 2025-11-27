from django.contrib import admin

from .models import InteractivePricingSnapshot


@admin.register(InteractivePricingSnapshot)
class InteractivePricingSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'estimation_id',
        'start_estimation',
        'unit_name',
        'staff_name',
        'analyst_before_name',
        'analyst_after_name',
        'price_before_kd',
        'price_after_kd',
        'price_auto_selected',
        'cost_total',
    )
    list_filter = ('unit_name', 'status_name')
    search_fields = ('estimation_id', 'staff_name', 'analyst_before_name', 'analyst_after_name', 'model_name', 'vin')

