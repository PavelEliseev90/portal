from django.contrib import admin

from .models import (
    DamageType,
    EstimationPlanLine,
    EstimationPlanPackage,
    EstimationPlanSnapshot,
    EstimationPreparationTransfer,
    EstimationRule,
    EstimationRuleCondition,
    EstimationRulePackage,
    LegacyWorkMapping,
    PreparationMaterialProfile,
    PreparationPart,
    PreparationPartCompatibility,
    PreparationService,
    PreparationServiceOffering,
    PreparationServiceProvider,
    PreparationWorkPackage,
    PreparationWorkPackageLine,
    SchemeElement,
    SchemeElementPolygon,
)


@admin.register(LegacyWorkMapping)
class LegacyWorkMappingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'legacy_work',
        'target_work',
        'review_status',
        'is_active',
        'updated_at',
    )
    list_filter = ('review_status', 'is_active')
    search_fields = (
        'legacy_work__name',
        'legacy_work__name_group',
        'target_work__name',
        'target_work__code',
        'comment',
    )
    raw_id_fields = ('legacy_work',)
    autocomplete_fields = ('target_work',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('legacy_work_id',)


@admin.register(PreparationMaterialProfile)
class PreparationMaterialProfileAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'material',
        'category',
        'manufacturer',
        'article',
        'process_loss_percent',
        'is_active',
        'sort_order',
    )
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'material__name', 'material__code', 'manufacturer', 'article')
    autocomplete_fields = ('material',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'code')


class PreparationPartCompatibilityInline(admin.TabularInline):
    model = PreparationPartCompatibility
    extra = 0
    autocomplete_fields = ('mark', 'model')
    raw_id_fields = ('type_body',)
    fields = (
        'type_body',
        'mark',
        'model',
        'year_from',
        'year_to',
        'notes',
        'is_active',
    )


@admin.register(PreparationPart)
class PreparationPartAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'category',
        'oem_number',
        'manufacturer',
        'kind',
        'is_active',
        'sort_order',
    )
    list_filter = ('kind', 'is_active', 'category')
    search_fields = ('code', 'name', 'oem_number', 'manufacturer', 'category')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'code')
    inlines = [PreparationPartCompatibilityInline]


@admin.register(PreparationPartCompatibility)
class PreparationPartCompatibilityAdmin(admin.ModelAdmin):
    list_display = (
        'part',
        'type_body',
        'mark',
        'model',
        'year_from',
        'year_to',
        'is_active',
    )
    list_filter = ('is_active',)
    search_fields = (
        'part__code',
        'part__name',
        'type_body__name',
        'mark__name',
        'model__name',
        'notes',
    )
    autocomplete_fields = ('part', 'mark', 'model')
    raw_id_fields = ('type_body',)
    readonly_fields = ('created_at', 'updated_at')


class PreparationServiceOfferingInline(admin.TabularInline):
    model = PreparationServiceOffering
    extra = 0
    autocomplete_fields = ('provider',)
    fields = (
        'code',
        'provider',
        'sla_hours',
        'includes_works',
        'includes_materials',
        'includes_parts',
        'valid_from',
        'valid_to',
        'is_active',
        'sort_order',
    )


@admin.register(PreparationService)
class PreparationServiceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active', 'sort_order')
    list_filter = ('is_active', 'category')
    search_fields = ('code', 'name', 'category', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'code')
    inlines = [PreparationServiceOfferingInline]


@admin.register(PreparationServiceProvider)
class PreparationServiceProviderAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'inn',
        'contract_number',
        'contract_valid_from',
        'contract_valid_to',
        'is_active',
        'sort_order',
    )
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'legal_name', 'inn', 'contract_number', 'contacts')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'code')


@admin.register(PreparationServiceOffering)
class PreparationServiceOfferingAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'service',
        'provider',
        'sla_hours',
        'includes_works',
        'includes_materials',
        'includes_parts',
        'valid_from',
        'valid_to',
        'is_active',
    )
    list_filter = (
        'is_active',
        'includes_works',
        'includes_materials',
        'includes_parts',
    )
    search_fields = (
        'code',
        'service__code',
        'service__name',
        'provider__code',
        'provider__name',
        'package_description',
    )
    autocomplete_fields = ('service', 'provider')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'code')


class PreparationWorkPackageLineInline(admin.TabularInline):
    model = PreparationWorkPackageLine
    extra = 0
    autocomplete_fields = ('work', 'material', 'part', 'service', 'service_offering')
    fields = (
        'line_type',
        'work',
        'material',
        'part',
        'service',
        'service_offering',
        'quantity',
        'norm_hours',
        'unit_cost',
        'is_required',
        'scope',
        'coverage_key',
        'parent_coverage_key',
        'sort_order',
        'is_active',
    )


@admin.register(PreparationWorkPackage)
class PreparationWorkPackageAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'section',
        'route_type',
        'default_repair_zone',
        'estimation_reduction_amount',
        'status',
        'is_active',
        'sort_order',
    )
    list_filter = ('section', 'route_type', 'status', 'is_active')
    search_fields = ('code', 'name', 'description')
    raw_id_fields = ('default_repair_zone',)
    autocomplete_fields = ('default_service_offering',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('sort_order', 'code')
    inlines = [PreparationWorkPackageLineInline]


@admin.register(PreparationWorkPackageLine)
class PreparationWorkPackageLineAdmin(admin.ModelAdmin):
    list_display = (
        'package',
        'line_type',
        'work',
        'material',
        'part',
        'service',
        'quantity',
        'norm_hours',
        'coverage_key',
        'is_active',
        'sort_order',
    )
    list_filter = ('line_type', 'scope', 'is_active')
    search_fields = (
        'package__code',
        'package__name',
        'coverage_key',
        'parent_coverage_key',
        'notes',
    )
    autocomplete_fields = ('package', 'work', 'material', 'part', 'service', 'service_offering')
    readonly_fields = ('created_at', 'updated_at')


class EstimationPlanLineInline(admin.TabularInline):
    model = EstimationPlanLine
    extra = 0
    autocomplete_fields = ('work', 'material', 'part', 'service', 'service_offering')
    raw_id_fields = ('source_package_line', 'preparation_work_item', 'plan_package')
    fields = (
        'plan_package',
        'line_type',
        'section',
        'name',
        'work',
        'material',
        'part',
        'service',
        'service_offering',
        'quantity',
        'norm_hours',
        'planned_minutes',
        'cost',
        'coverage_key',
        'parent_coverage_key',
        'preparation_work_item',
        'sort_order',
    )
    readonly_fields = ('preparation_work_item',)


class EstimationPlanPackageInline(admin.TabularInline):
    model = EstimationPlanPackage
    extra = 0
    autocomplete_fields = ('work_package', 'service_offering')
    raw_id_fields = ('repair_zone',)
    fields = (
        'work_package',
        'code',
        'name',
        'route_type',
        'repair_zone',
        'service_offering',
        'total_norm_hours',
        'total_cost',
        'sort_order',
    )
    show_change_link = True


@admin.register(EstimationPlanSnapshot)
class EstimationPlanSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'estimation',
        'revision',
        'status',
        'vin',
        'unit',
        'preparation',
        'total_norm_hours',
        'total_cost',
        'transferred_at',
    )
    list_filter = ('status', 'source')
    search_fields = ('vin', 'estimation__vin', 'notes')
    raw_id_fields = ('estimation', 'rlk', 'car', 'unit', 'preparation')
    readonly_fields = ('created_at', 'updated_at', 'transferred_at', 'approved_at')
    inlines = [EstimationPlanPackageInline, EstimationPlanLineInline]


@admin.register(EstimationPlanPackage)
class EstimationPlanPackageAdmin(admin.ModelAdmin):
    list_display = (
        'snapshot',
        'name',
        'code',
        'route_type',
        'repair_zone',
        'total_norm_hours',
        'total_cost',
        'preparation_package',
        'sort_order',
    )
    list_filter = ('route_type',)
    search_fields = ('name', 'code', 'snapshot__vin')
    autocomplete_fields = ('work_package', 'service_offering')
    raw_id_fields = ('snapshot', 'repair_zone', 'preparation_package')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [EstimationPlanLineInline]


@admin.register(EstimationPlanLine)
class EstimationPlanLineAdmin(admin.ModelAdmin):
    list_display = (
        'snapshot',
        'plan_package',
        'line_type',
        'section',
        'name',
        'work',
        'material',
        'quantity',
        'norm_hours',
        'cost',
        'preparation_work_item',
    )
    list_filter = ('line_type', 'section')
    search_fields = ('name', 'coverage_key', 'snapshot__vin')
    autocomplete_fields = ('work', 'material', 'part', 'service', 'service_offering')
    raw_id_fields = ('snapshot', 'plan_package', 'source_package_line', 'preparation_work_item')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EstimationPreparationTransfer)
class EstimationPreparationTransferAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'snapshot',
        'preparation',
        'status',
        'created_packages',
        'created_work_items',
        'updated_work_items',
        'created_materials',
        'skipped_lines',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('snapshot__vin', 'error_message')
    raw_id_fields = ('snapshot', 'preparation')
    readonly_fields = (
        'created_at',
        'updated_at',
        'created_packages',
        'created_work_items',
        'updated_work_items',
        'created_materials',
        'skipped_lines',
        'error_message',
        'details',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SchemeElement)
class SchemeElementAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'section', 'is_active', 'sort_order')
    list_filter = ('section', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SchemeElementPolygon)
class SchemeElementPolygonAdmin(admin.ModelAdmin):
    list_display = ('element', 'info_body', 'is_active')
    list_filter = ('is_active',)
    autocomplete_fields = ('element',)
    raw_id_fields = ('info_body',)


@admin.register(DamageType)
class DamageTypeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'section', 'legacy_label', 'severity',
        'requires_photo', 'is_active', 'sort_order',
    )
    list_filter = ('section', 'requires_photo', 'is_active')
    search_fields = ('code', 'name', 'legacy_label')
    ordering = ('sort_order', 'name')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('requires_photo', 'is_active', 'sort_order')


class EstimationRulePackageInline(admin.TabularInline):
    model = EstimationRulePackage
    extra = 1
    autocomplete_fields = ('package',)
    fields = ('package', 'fixed_cost', 'sort_order', 'is_active')


class EstimationRuleConditionInline(admin.TabularInline):
    model = EstimationRuleCondition
    extra = 0
    autocomplete_fields = ('damage_type_ref',)
    fields = (
        'sort_order', 'join_op', 'field', 'damage_type_ref',
        'operator', 'value', 'is_active',
    )


@admin.register(EstimationRule)
class EstimationRuleAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'priority', 'status', 'section',
        'element', 'damage_type_ref',
        'windshield_heat', 'windshield_projection',
        'cleaning_level', 'salon_type',
        'diagnostic_system', 'diagnostic_status',
        'hour_rate', 'is_active',
    )
    list_filter = (
        'status', 'is_active', 'section', 'exclusive_group',
        'windshield_heat', 'windshield_projection',
        'cleaning_level', 'salon_type',
        'diagnostic_system', 'diagnostic_status',
    )
    search_fields = ('code', 'name', 'element_code', 'damage_type', 'body_type')
    autocomplete_fields = ('element', 'damage_type_ref')
    filter_horizontal = ('body_types',)
    inlines = [EstimationRuleConditionInline, EstimationRulePackageInline]
    readonly_fields = ('created_at', 'updated_at', 'element_code', 'damage_type', 'body_type')


@admin.register(EstimationRulePackage)
class EstimationRulePackageAdmin(admin.ModelAdmin):
    list_display = ('rule', 'package', 'fixed_cost', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    autocomplete_fields = ('rule', 'package')
