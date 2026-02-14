from django.contrib import admin
from .models import (
    RefClassifiedsPlatform,
    ClassifiedsExportConfig,
    ClassifiedsFieldMapping,
    ClassifiedsExportHistory,
    ClassifiedsExportLog,
)


@admin.register(RefClassifiedsPlatform)
class RefClassifiedsPlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('sort_order', 'name')


class ClassifiedsFieldMappingInline(admin.TabularInline):
    model = ClassifiedsFieldMapping
    extra = 1
    fields = ('car_field', 'platform_field', 'default_value', 'transform_function', 'is_required', 'sort_order')


@admin.register(ClassifiedsExportConfig)
class ClassifiedsExportConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'unit', 'status', 'is_active', 'auto_export', 'date_create')
    list_filter = ('status', 'is_active', 'auto_export', 'platform', 'unit')
    search_fields = ('name', 'platform__name', 'unit__name')
    filter_horizontal = ('filter_units', 'filter_statuses')
    inlines = [ClassifiedsFieldMappingInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'platform', 'unit', 'type_exchange', 'status', 'is_active', 'comment')
        }),
        ('Настройки файла', {
            'fields': ('file_name_template', 'file_path')
        }),
        ('Автоматизация', {
            'fields': ('auto_export', 'schedule_cron')
        }),
        ('Фильтры автомобилей', {
            'fields': ('filter_units', 'filter_statuses', 'filter_is_new', 
                      'filter_min_price', 'filter_max_price', 'filter_min_year', 'filter_max_year',
                      'filter_marks', 'filter_exclude_vin', 'max_cars_per_export',
                      'include_reserved', 'include_sold')
        }),
        ('Настройки XML', {
            'fields': ('xml_settings',)
        }),
        ('Метаданные', {
            'fields': ('user_create', 'user_update', 'date_create', 'date_update')
        }),
    )
    readonly_fields = ('date_create', 'date_update')


class ClassifiedsExportLogInline(admin.TabularInline):
    model = ClassifiedsExportLog
    extra = 0
    readonly_fields = ('car', 'status', 'error_message', 'date_create')
    can_delete = False


@admin.register(ClassifiedsExportHistory)
class ClassifiedsExportHistoryAdmin(admin.ModelAdmin):
    list_display = ('config', 'status', 'cars_count', 'cars_exported', 'cars_skipped', 
                   'date_start', 'date_end', 'is_manual')
    list_filter = ('status', 'is_manual', 'date_start', 'config')
    search_fields = ('config__name', 'file_name', 'error_message')
    readonly_fields = ('date_start', 'date_end', 'cars_count', 'cars_exported', 
                      'cars_skipped', 'cars_errors', 'file_size')
    inlines = [ClassifiedsExportLogInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('config', 'status', 'user', 'is_manual')
        }),
        ('Результаты', {
            'fields': ('cars_count', 'cars_exported', 'cars_skipped', 'cars_errors')
        }),
        ('Файлы', {
            'fields': ('file_path', 'file_name', 'file_size')
        }),
        ('Детали', {
            'fields': ('error_message', 'export_details')
        }),
        ('Временные метки', {
            'fields': ('date_start', 'date_end')
        }),
    )


@admin.register(ClassifiedsExportLog)
class ClassifiedsExportLogAdmin(admin.ModelAdmin):
    list_display = ('export_history', 'car', 'status', 'date_create')
    list_filter = ('status', 'date_create', 'export_history')
    search_fields = ('car__vin', 'car__mark', 'car__model', 'error_message')
    readonly_fields = ('date_create',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('export_history', 'car', 'status')
        }),
        ('Детали', {
            'fields': ('error_message', 'xml_data')
        }),
        ('Временная метка', {
            'fields': ('date_create',)
        }),
    )

