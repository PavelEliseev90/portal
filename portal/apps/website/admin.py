from django.contrib import admin
from .models import ImProduct, ImSyncLog


@admin.register(ImProduct)
class ImProductAdmin(admin.ModelAdmin):
    list_display = ('nomenclature_code', 'nomenclature', 'article', 'price_value', 'photo_count', 'status_text', 'synced_at')
    search_fields = ('nomenclature', 'article', 'nomenclature_code')
    list_filter = ('status_text', 'manufacturer')


@admin.register(ImSyncLog)
class ImSyncLogAdmin(admin.ModelAdmin):
    list_display = ('started_at', 'sync_type', 'status', 'items_total', 'items_ok', 'items_failed', 'response_code')
    list_filter = ('sync_type', 'status')
