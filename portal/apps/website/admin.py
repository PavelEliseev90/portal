from django.contrib import admin
from .models import ImProduct, ImProductPhoto, ImProductUserActivity, ImSyncLog


@admin.register(ImProduct)
class ImProductAdmin(admin.ModelAdmin):
    list_display = ('nomenclature_code', 'nomenclature', 'article', 'price_value', 'photo_count', 'status_text', 'synced_at')
    search_fields = ('nomenclature', 'article', 'nomenclature_code')
    list_filter = ('status_text', 'manufacturer')


@admin.register(ImProductPhoto)
class ImProductPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'upload_1c_status', 'source_url', 'sort_order', 'created_at')
    list_filter = ('upload_1c_status',)
    search_fields = ('product__nomenclature_code', 'source_url')
    raw_id_fields = ('product',)


@admin.register(ImSyncLog)
class ImSyncLogAdmin(admin.ModelAdmin):
    list_display = ('started_at', 'sync_type', 'status', 'items_total', 'items_ok', 'items_failed', 'response_code')
    list_filter = ('sync_type', 'status')


@admin.register(ImProductUserActivity)
class ImProductUserActivityAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'product', 'action', 'photo')
    list_filter = ('action', 'created_at')
    search_fields = ('product__nomenclature_code', 'product__nomenclature', 'user__username')
    raw_id_fields = ('user', 'product', 'photo')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
