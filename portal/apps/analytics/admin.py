from django.contrib import admin

from .models import (
    AppraiserPerformanceSnapshot,
    EcoAnalystSnapshot,
    InteractivePricingSnapshot,
    TradeInFunnelSnapshot,
    TradeInFunnel,
)


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


@admin.register(EcoAnalystSnapshot)
class EcoAnalystSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'estimation_id',
        'role',
        'start_estimation',
        'analyst_name',
        'unit_name',
        'has_soglasovanie',
        'has_diagnostics',
        'accepted',
        'price_auto_selected',
        'price_before_kd',
        'price_after_kd',
        'diff_after',
    )
    list_filter = ('role', 'has_soglasovanie', 'has_diagnostics', 'accepted')
    search_fields = ('estimation_id', 'analyst_name', 'staff_name', 'unit_name')


@admin.register(AppraiserPerformanceSnapshot)
class AppraiserPerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'estimation_id',
        'staff_name',
        'unit_name',
        'worksheet_created_at',
        'price_offer',
        'price_agreed',
        'price_reception',
        'price_sale',
        'cost_total',
    )
    list_filter = ('unit_name', 'accepted')
    search_fields = ('estimation_id', 'staff_name', 'unit_name', 'status_name')


@admin.register(TradeInFunnelSnapshot)
class TradeInFunnelSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'rlk_id',
        'unit_name',
        'staff_name',
        'stage',
        'date_work_order',
        'date_evaluation',
        'date_acceptance',
        'date_sale',
        'price_agreed_after',
        'price_sale',
    )
    list_filter = ('stage', 'unit_name')
    search_fields = ('rlk_id', 'staff_name', 'unit_name', 'worksheet_number')


@admin.register(TradeInFunnel)
class TradeInFunnelAdmin(admin.ModelAdmin):
    list_display = (
        'rlk_id',
        'vin',
        'unit_name',
        'brand',
        'unit_source_name',
        'staff_name',
        'stage',        
    )
    search_fields = ('rlk_id', 'vin', 'staff_name', 'unit_name', )
