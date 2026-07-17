from django.contrib import admin
from .models import (
    RefCarPreparationStage, RefCarPreparationWork, RefCarPreparationStatus,
    CarPreparation, CarPreparationPackage, CarPreparationWorkItem, CarPreparationPhoto,
    CarPreparationChecklist, CarPreparationTemplate, CarPreparationTemplateWork,
    CarPreparationHistory, CarPreparationNotification,
    CarPreparationWorkSchedule, CarPreparationCalendar, CarPreparationResource,
    RefPreparationMaterial, PreparationMaterialStock, PreparationMaterialMovement,
    PlannedMaterialConsumption,
    RefRepairZone,     WorkOrderTemplate, WorkOrderTemplateWork,
    WorkOrder, WorkOrderItem, WorkOrderItemPhoto, WorkOrderItemMaterial,
)


@admin.register(RefCarPreparationStage)
class RefCarPreparationStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'sort_order', 'required', 'is_active']
    list_filter = ['is_active', 'required']
    search_fields = ['name', 'code']
    ordering = ['sort_order']


@admin.register(RefCarPreparationWork)
class RefCarPreparationWorkAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'stage', 'sort_order', 'default_required', 'is_active']
    list_filter = ['stage', 'is_active', 'default_required']
    search_fields = ['name', 'code', 'description']
    ordering = ['stage__sort_order', 'sort_order']


@admin.register(RefCarPreparationStatus)
class RefCarPreparationStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color', 'is_final', 'can_edit']
    list_filter = ['is_final', 'can_edit']
    search_fields = ['name', 'code']


class CarPreparationWorkItemInline(admin.TabularInline):
    model = CarPreparationWorkItem
    extra = 0
    fields = ['preparation_package', 'work', 'status', 'performer', 'actual_time', 'cost', 'comment']
    raw_id_fields = ['preparation_package']
    readonly_fields = []


class CarPreparationPhotoInline(admin.TabularInline):
    model = CarPreparationPhoto
    extra = 0
    fields = ['photo', 'description', 'date_created', 'created_by']
    readonly_fields = ['date_created']
    max_num = 10


class CarPreparationPackageInline(admin.TabularInline):
    model = CarPreparationPackage
    extra = 0
    fields = [
        'code', 'name', 'route_type', 'repair_zone', 'status',
        'is_confirmed', 'planned_time', 'cost', 'sort_order',
    ]
    raw_id_fields = ['repair_zone', 'source_package']
    show_change_link = True


@admin.register(CarPreparationPackage)
class CarPreparationPackageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'preparation', 'name', 'code', 'route_type', 'repair_zone',
        'status', 'is_confirmed', 'planned_time', 'cost',
    ]
    list_filter = ['status', 'route_type', 'is_confirmed']
    search_fields = ['name', 'code', 'preparation__car__vin']
    raw_id_fields = ['preparation', 'source_package', 'repair_zone']
    inlines = [CarPreparationWorkItemInline]


@admin.register(CarPreparation)
class CarPreparationAdmin(admin.ModelAdmin):
    list_display = ['id', 'car', 'unit', 'status', 'current_stage', 'responsible', 
                   'date_start', 'date_planned_end', 'progress_percent', 'date_created']
    list_filter = ['status', 'unit', 'current_stage', 'mobile_created', 'date_start']
    search_fields = ['car__vin', 'car__name', 'qr_code', 'responsible__name']
    readonly_fields = ['date_created', 'date_updated', 'progress_percent', 'qr_code']
    inlines = [CarPreparationPackageInline, CarPreparationWorkItemInline, CarPreparationPhotoInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('car', 'unit', 'status', 'current_stage')
        }),
        ('Даты', {
            'fields': ('date_start', 'date_planned_end', 'date_end', 
                      'date_created', 'date_updated')
        }),
        ('Ответственные', {
            'fields': ('responsible', 'inspector')
        }),
        ('Комментарии', {
            'fields': ('comment_initial', 'comment_final', 'quality_notes')
        }),
        ('Мобильность', {
            'fields': ('qr_code', 'mobile_created', 'mobile_last_sync')
        }),
        ('Прогресс', {
            'fields': ('progress_percent',)
        }),
    )


@admin.register(CarPreparationWorkItem)
class CarPreparationWorkItemAdmin(admin.ModelAdmin):
    list_display = ['preparation', 'preparation_package', 'work', 'is_confirmed', 'status', 'performer', 
                   'actual_time', 'cost', 'date_start', 'date_end']
    list_filter = ['is_confirmed', 'status', 'quality', 'mobile_updated']
    search_fields = ['preparation__car__vin', 'work__name', 'performer__name', 'preparation_package__name']
    raw_id_fields = ['preparation', 'preparation_package', 'work', 'performer', 'confirmed_by']
    readonly_fields = ['mobile_updated_at', 'confirmed_at']


@admin.register(CarPreparationPhoto)
class CarPreparationPhotoAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'preparation', 'created_by', 'date_created']
    list_filter = ['date_created']
    search_fields = ['preparation__car__vin', 'description']
    readonly_fields = ['date_created']


@admin.register(CarPreparationChecklist)
class CarPreparationChecklistAdmin(admin.ModelAdmin):
    list_display = ['preparation', 'overall_quality', 'checked_by', 
                   'date_checked', 'approved', 'approved_by']
    list_filter = ['approved', 'exterior_checked', 'interior_checked', 
                  'technical_checked', 'documents_checked']
    search_fields = ['preparation__car__vin']
    readonly_fields = ['date_checked', 'date_approved']


class CarPreparationTemplateWorkInline(admin.TabularInline):
    model = CarPreparationTemplateWork
    extra = 0
    fields = ['work', 'is_required', 'planned_time', 'default_cost', 'sort_order']


@admin.register(CarPreparationTemplate)
class CarPreparationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'car_type', 'is_active', 'is_default', 'date_created']
    list_filter = ['is_active', 'is_default', 'unit', 'car_type']
    search_fields = ['name', 'description']
    filter_horizontal = ['stages']
    inlines = [CarPreparationTemplateWorkInline]
    readonly_fields = ['date_created']


@admin.register(CarPreparationHistory)
class CarPreparationHistoryAdmin(admin.ModelAdmin):
    list_display = ['preparation', 'action', 'field_name', 'user', 'date']
    list_filter = ['action', 'date']
    search_fields = ['preparation__car__vin', 'action', 'comment']
    readonly_fields = ['date']
    ordering = ['-date']


@admin.register(CarPreparationNotification)
class CarPreparationNotificationAdmin(admin.ModelAdmin):
    list_display = ['preparation', 'work_item', 'notification_type', 'priority', 
                   'recipient', 'sent', 'read', 'auto_created', 'date_created']
    list_filter = ['notification_type', 'priority', 'sent', 'read', 'auto_created',
                  'channel_email', 'channel_push', 'channel_sms']
    search_fields = ['preparation__car__vin', 'message', 'recipient__name']
    readonly_fields = ['date_created', 'date_sent', 'date_read']
    date_hierarchy = 'date_created'


@admin.register(CarPreparationWorkSchedule)
class CarPreparationWorkScheduleAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'planned_performer', 'planned_start', 'planned_end',
                   'priority', 'planning_status', 'blocks_time']
    list_filter = ['planning_status', 'priority', 'blocks_time', 'auto_scheduled']
    search_fields = ['work_item__work__name', 'planned_performer__name']
    readonly_fields = ['date_created', 'date_updated']
    date_hierarchy = 'planned_start'


@admin.register(CarPreparationCalendar)
class CarPreparationCalendarAdmin(admin.ModelAdmin):
    list_display = ['unit', 'date', 'total_preparations', 'active_preparations',
                   'performers_count', 'total_work_hours', 'get_utilization_percent']
    list_filter = ['unit', 'date']
    search_fields = ['unit__name']
    readonly_fields = ['date_updated']
    date_hierarchy = 'date'
    
    def get_utilization_percent(self, obj):
        return f"{obj.get_utilization_percent()}%"
    get_utilization_percent.short_description = 'Загрузка'


@admin.register(CarPreparationResource)
class CarPreparationResourceAdmin(admin.ModelAdmin):
    list_display = ['resource_type', 'performer', 'name', 'unit', 'is_active',
                   'max_concurrent_works']
    list_filter = ['resource_type', 'unit', 'is_active']
    search_fields = ['name', 'code', 'performer__name']


@admin.register(RefPreparationMaterial)
class RefPreparationMaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'uom', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(PreparationMaterialStock)
class PreparationMaterialStockAdmin(admin.ModelAdmin):
    list_display = ['unit', 'material', 'qty_on_hand', 'min_qty', 'max_qty', 'date_updated']
    list_filter = ['unit', 'material']
    search_fields = ['material__name', 'material__code']


@admin.register(PreparationMaterialMovement)
class PreparationMaterialMovementAdmin(admin.ModelAdmin):
    list_display = ['date', 'unit', 'material', 'qty', 'movement_type', 'work_item', 'user']
    list_filter = ['movement_type', 'unit', 'material', 'date']
    search_fields = ['material__name', 'material__code', 'comment']
    date_hierarchy = 'date'


@admin.register(PlannedMaterialConsumption)
class PlannedMaterialConsumptionAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'material', 'qty_planned', 'qty_reserved', 'reserved', 'date_created']
    list_filter = ['reserved', 'material']
    search_fields = ['work_item__work__name', 'material__name', 'material__code']
    date_hierarchy = 'date_created'


# ===========================================
# АДМИНКА ДЛЯ СИСТЕМЫ ЗАКАЗ-НАРЯДОВ
# ===========================================

@admin.register(RefRepairZone)
class RefRepairZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'unit', 'is_active', 'sort_order']
    list_filter = ['is_active', 'unit']
    search_fields = ['name', 'code', 'description']
    filter_horizontal = ['assigned_staff']
    ordering = ['sort_order', 'name']


class WorkOrderTemplateWorkInline(admin.TabularInline):
    model = WorkOrderTemplateWork
    extra = 0
    fields = ['work', 'is_required', 'estimated_time', 'sort_order']
    ordering = ['sort_order']


@admin.register(WorkOrderTemplate)
class WorkOrderTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'unit', 'estimated_duration_minutes', 'is_active', 'is_default', 'date_created']
    list_filter = ['is_active', 'is_default', 'unit']
    search_fields = ['name', 'code', 'description']
    inlines = [WorkOrderTemplateWorkInline]
    readonly_fields = ['date_created', 'date_updated']


class WorkOrderItemInline(admin.TabularInline):
    model = WorkOrderItem
    extra = 0
    fields = ['work', 'status', 'performer', 'planned_start', 'planned_end', 'actual_start', 'actual_end', 'sort_order']
    readonly_fields = ['actual_start', 'actual_end']
    ordering = ['sort_order']


class WorkOrderItemPhotoInline(admin.TabularInline):
    model = WorkOrderItemPhoto
    extra = 0
    fields = ['photo', 'description', 'created_by', 'date_created']
    readonly_fields = ['date_created']
    max_num = 10


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ['number', 'car', 'title', 'status', 'repair_zone', 'planned_start', 
                   'actual_start', 'responsible', 'date_created']
    list_filter = ['status', 'repair_zone', 'template', 'date_created']
    search_fields = ['number', 'title', 'car__vin', 'car__name', 'description']
    readonly_fields = ['number', 'date_created', 'date_updated']
    inlines = [WorkOrderItemInline]
    date_hierarchy = 'date_created'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('number', 'car', 'preparation', 'template', 'title', 'description')
        }),
        ('Планирование', {
            'fields': ('repair_zone', 'planned_start', 'planned_end', 'status')
        }),
        ('Выполнение', {
            'fields': ('actual_start', 'actual_end', 'responsible')
        }),
        ('Системные', {
            'fields': ('created_by', 'date_created', 'date_updated')
        }),
    )


@admin.register(WorkOrderItem)
class WorkOrderItemAdmin(admin.ModelAdmin):
    list_display = ['work_order', 'work', 'status', 'performer', 'planned_start', 
                   'actual_start', 'actual_end', 'sort_order']
    list_filter = ['status', 'work_order__status']
    search_fields = ['work_order__number', 'work__name', 'performer__name', 'comment']
    readonly_fields = ['date_created', 'date_updated']
    inlines = [WorkOrderItemPhotoInline]
    date_hierarchy = 'date_created'


@admin.register(WorkOrderItemPhoto)
class WorkOrderItemPhotoAdmin(admin.ModelAdmin):
    list_display = ['work_order_item', 'description', 'created_by', 'date_created']
    list_filter = ['date_created']
    search_fields = ['work_order_item__work__name', 'description']
    readonly_fields = ['date_created']
    date_hierarchy = 'date_created'


@admin.register(WorkOrderItemMaterial)
class WorkOrderItemMaterialAdmin(admin.ModelAdmin):
    list_display = ['work_order_item', 'material', 'quantity', 'unit_price', 'total_price', 'date_created']
    list_filter = ['material', 'date_created']
    search_fields = ['work_order_item__work__name', 'material__name', 'comment']
    readonly_fields = ['total_price', 'date_created']
    date_hierarchy = 'date_created'

