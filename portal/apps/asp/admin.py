from django.contrib import admin

from asp.models import ReportSavedFilter


@admin.register(ReportSavedFilter)
class ReportSavedFilterAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_key', 'user', 'is_shared', 'order', 'date_updated')
    list_filter = ('report_key', 'is_shared')
    search_fields = ('name', 'user__username', 'user__email')
    raw_id_fields = ('user',)
