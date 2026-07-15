from django.contrib import admin

from mykors.models import MykorsCarSyncState


@admin.register(MykorsCarSyncState)
class MykorsCarSyncStateAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'car_id', 'vin', 'remote_id', 'last_ok',
        'last_http_status', 'last_synced_at', 'updated_at',
    )
    list_filter = ('last_ok',)
    search_fields = ('vin', 'car_id')
    readonly_fields = (
        'car_id', 'vin', 'payload_hash', 'remote_id',
        'last_synced_at', 'last_ok', 'last_http_status',
        'last_error', 'created_at', 'updated_at',
    )
    ordering = ('-updated_at',)
