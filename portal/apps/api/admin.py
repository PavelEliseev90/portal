from django.contrib import admin
from .models import Exchange1CErrorLog


@admin.register(Exchange1CErrorLog)
class Exchange1CErrorLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_create', 'exchange_type', 'error_preview', 'data_preview')
    list_filter = ('exchange_type', 'date_create')
    search_fields = ('exchange_type', 'error_description', 'data')
    readonly_fields = ('date_create', 'exchange_type', 'data', 'error_description')
    date_hierarchy = 'date_create'

    def error_preview(self, obj):
        text = obj.error_description or ''
        return text[:120] + ('…' if len(text) > 120 else '')

    error_preview.short_description = 'Ошибка'

    def data_preview(self, obj):
        text = obj.data or ''
        return text[:80] + ('…' if len(text) > 80 else '')

    data_preview.short_description = 'Данные'

    def has_add_permission(self, request):
        return False
