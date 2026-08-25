from django.contrib import admin
from .models import RegInfoRefreshEstimationCarsExpress, RegRefCarsOrganizationsCalculationPrice, RegEstimationBalanceStaffEco, RegRefCarsOrganizationsPrice, RegEstimationRefCarsOrganizations, RegEstimationBalanceUnit, RegPodgotovkaWork, RegInfoBody, RegEstimationsSettings, RegPrices, RegSwapKors, RegInteractivOcenkaHistoryOpens, RegInteractivOcenkaEmailPush, RegInteractivOcenkaProverki, RegInteractivOcenkaSoglasovanie, RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive ,RegInteractivOcenkaComplectnost, RegInteractivOcenkaVnesh, RegDashboardError, RegInteractivOcenkaSalon, RegRegInteractivOcenkaFiles, RegInteractivOcenka, RegViewsCarsOrganization, SettingsRegPrices, TaskRegPrices, RegInfoRefreshCatalog, RegInteractivOcenkaDocument, RegUnitMonthlyPlan, RegInteractivOcenkaRLK, RegInteractivOcenkaKolesaReception, DiagnosticReferenceCategory, DiagnosticReferenceItem, DiagnosticReferenceSelection, BodyRefReplace, BodyTypeGroup, RegInteractivOcenkaPrice


@admin.register(RegInfoRefreshEstimationCarsExpress)
class RegInfoRefreshEstimationCarsExpressAdmin(admin.ModelAdmin):
    list_display    = ('date', 'date_end', 'count_all', 'count_success', 'count_error',)
    

@admin.register(RegEstimationBalanceStaffEco)
class RegEstimationBalanceStaffEcoAdmin(admin.ModelAdmin):
    list_display    = ('date', 'staff', 'estimation', 'shipment', 'amount',)
    raw_id_fields   = ('staff', 'estimation', 'shipment')


@admin.register(RegRefCarsOrganizationsCalculationPrice)
class RegRefCarsOrganizationsCalculationPriceAdmin(admin.ModelAdmin):
    list_display    = ('date', 'car', 'price', 'evaluation', 'rule',)
    raw_id_fields   = ('car', )
    search_fields   = ('car__vin',)
    

@admin.register(RegRefCarsOrganizationsPrice)
class RegRefCarsOrganizationsPriceAdmin(admin.ModelAdmin):
    list_display    = ('date', 'car', 'price',)
    raw_id_fields   = ('car', )
    search_fields   = ('car__vin',)


@admin.register(RegEstimationRefCarsOrganizations)
class RegEstimationRefCarsOrganizationsAdmin(admin.ModelAdmin):
    list_display    = ('date', 'car', 'avg_price', 'avg_days', 'position', 'price', 'error', )
    raw_id_fields   = ('car', )
    search_fields   = ('car__vin',)
    list_filter     = ('date',)


@admin.register(RegEstimationBalanceUnit)
class RegEstimationBalanceUnitAdmin(admin.ModelAdmin):
    list_display    = ('date', 'unit', 'estimation', 'shipment', 'amount',)
    raw_id_fields   = ('unit', 'estimation', 'shipment')


@admin.register(RegInfoBody)
class RegInfoBodyAdmin(admin.ModelAdmin):
    list_display    = ('type_body', 'side', 'body_element', 'body_elem_name', )


@admin.register(RegEstimationsSettings)
class RegEstimationsSettingsAdmin(admin.ModelAdmin):
    list_display    = ('name',)


@admin.register(RegPrices)
class RegPricesAdmin(admin.ModelAdmin):
    list_display    = ('task', 'manufacturer', 'date', 'article', 'article_search', 'name', 'category',)
    raw_id_fields   = ('task', 'manufacturer',)
    list_filter     = ('date', 'manufacturer', 'task', )


@admin.register(RegSwapKors)
class RegSwapKorsAdmin(admin.ModelAdmin):
    list_display    = ('estimation', 'rlk', 'date', 'uid', 'comment', 'status',)
    raw_id_fields   = ('estimation', 'rlk',)
    list_filter     = ('date',)
    


@admin.register(RegInteractivOcenkaHistoryOpens)
class RegInteractivOcenkaHistoryOpensAdmin(admin.ModelAdmin):
    list_display    = ('estimation', 'staff', 'date_open', 'page',)
    raw_id_fields   = ('estimation', 'staff', )
    list_filter     = ('staff',)
    search_fields   = ('page', 'staff',)


@admin.register(RegInteractivOcenkaEmailPush)
class RegInteractivOcenkaEmailPushAdmin(admin.ModelAdmin):
    list_display    = ('date', 'estimation', 'user', 'comment', 'send',)
    raw_id_fields   = ('estimation', 'user', )
    list_filter     = ('send',)
    search_fields   = ('user', 'estimation__vin',)
    

@admin.register(RegInteractivOcenkaProverki)
class RegInteractivOcenkaProverkiAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', )


@admin.register(RegInteractivOcenkaSoglasovanie)
class RegInteractivOcenkaSoglasovanieAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', )


@admin.register(RegInteractivOcenkaKolesa)
class RegInteractivOcenkaKolesaAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', )


@admin.register(RegInteractivOcenkaTestDrive)
class RegInteractivOcenkaTestDriveAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', )


@admin.register(RegInteractivOcenkaComplectnost)
class RegInteractivOcenkaComplectnostAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', )


@admin.register(RegInteractivOcenkaVnesh)
class RegInteractivOcenkaVneshAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', 'color', )


@admin.register(RegDashboardError)
class RegDashboardErrorAdmin(admin.ModelAdmin):
    list_display    = ('name', 'uin', 'critical', )
    

@admin.register(RegInteractivOcenkaSalon)
class RegInteractivOcenkaSalonAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', 'run', )


@admin.register(RegRegInteractivOcenkaFiles)
class RegRegInteractivOcenkaFilesAdmin(admin.ModelAdmin):
    list_display    = ('estimation', 'name', 'type_file', 'file_number', 'user', 'date', )
    raw_id_fields   = ('estimation', 'user') 
    search_fields   = ('estimation__vin',)

@admin.register(RegInteractivOcenkaDocument)
class RegInteractivOcenkaDocumentAdmin(admin.ModelAdmin):
    list_display    = ('start_estimation', 'end_estimation', )


@admin.register(RegInfoRefreshCatalog)
class RegInfoRefreshCatalogAdmin(admin.ModelAdmin):
    list_display    = ('date', 'site', )
    

@admin.register(TaskRegPrices)
class TaskRegPricesAdmin(admin.ModelAdmin):
    list_display    = ('date', 'manufacturer', 'status')
    raw_id_fields   = ('manufacturer', 'user', )


@admin.register(SettingsRegPrices)
class SettingsRegPricesAdmin(admin.ModelAdmin):
    list_display    = ('name', 'manufacturer', 'user')
    raw_id_fields   = ('manufacturer', 'user', )


@admin.register(RegInteractivOcenka)
class RegInteractivOcenkaAdmin(admin.ModelAdmin):
    list_display    = ('rlk', 'start_estimation', 'end_estimation', 'vin', 'year', 'staff', 'kors_start_store', 'hub_start', 'avtoteka_preview', 'avtoteka_task', 'avtoteka_web', 'avtoteka_car_autodex', 'dtp_red', 'taxi', 'carsharing',)
    raw_id_fields   = ('rlk', 'complectation', 'modification_avito', 'complectation_avito', 'modification', 'page_documents', 'page_salon','staff', 'staff_eco_1', 'staff_eco_2', 'page_documents', 'page_salon', 'page_vnesh', 'page_complectnost', 'page_kolesa', 'page_test_drive', 'page_proverki', 'page_soglasovanie', 'page_remote',)
    list_filter     = ('start_estimation', 'dtp_red', 'taxi', 'carsharing', ) 
    search_fields   = ('vin', 'rlk__pk' )


@admin.register(RegViewsCarsOrganization)
class RegViewsCarsOrganizationAdmin(admin.ModelAdmin):
    list_display    = ('cars', 'store', 'type', )
    list_filter     = ('store', 'type',)
    raw_id_fields   = ('cars',)


@admin.register(RegPodgotovkaWork)
class RegPodgotovkaWorkAdmin(admin.ModelAdmin):
    list_display    = ('name_group', 'name', 'price_podrad', 'price_podrad',  'price_kors', 'normo',)


@admin.register(RegUnitMonthlyPlan)
class RegUnitMonthlyPlanAdmin(admin.ModelAdmin):
    list_display = ('unit', 'year', 'month', 'intake_plan', 'sale_plan')
    list_filter = ('year', 'month', 'unit')
    search_fields = ('unit__name',)


@admin.register(RegInteractivOcenkaRLK)
class RegInteractivOcenkaRLKAdmin(admin.ModelAdmin):
    list_display = ('rlk', 'estimation', 'staff_rlk', 'staff_eco_1_rlk', 'staff_eco_2_rlk', 'unit', 'status', 'date_diagnostic')
    raw_id_fields = ('rlk', 'estimation', 'staff_rlk', 'staff_eco_1_rlk', 'staff_eco_2_rlk', 'unit', 'organization', 'filial', 'store', 'type_reception', 'status', 'page_soglasovanie')
    list_filter = ('status', 'date_diagnostic', 'unit', 'organization')
    search_fields   = ('rlk__nomer',)
    filter_horizontal = ('access_user',)


@admin.register(RegInteractivOcenkaKolesaReception)
class RegInteractivOcenkaKolesaReceptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'date',
        'rlk',
        'estimation',
        'unit_display',
        'kolesa_estimation',
        'send_wheels_ib',
        'send_wheels_ib_date',
        'send_wheels_ib_number',
        'send_wheels_ib_uin',
        'user',
    )
    list_filter = (
        'send_wheels_ib',
        'date',
        'rlk__unit',
        'kolesa_estimation',
    )
    search_fields = (
        'rlk__nomer',
        'rlk__uin',
        'estimation__vin',
        'estimation__number_body',
        'send_wheels_ib_number',
        'send_wheels_ib_uin',
    )
    raw_id_fields = (
        'rlk',
        'estimation',
        'user',
        'mark_tyre',
        'width_tyre',
        'profil_tyre',
        'radius',
        'sezon',
        'disk_type',
        'et_disk',
        'dia_disk',
        'psd_disk',
    )
    list_select_related = (
        'rlk',
        'rlk__unit',
        'estimation',
        'user',
    )
    date_hierarchy = 'date'
    ordering = ('-date', '-id')

    @admin.display(description='Подразделение', ordering='rlk__unit__name')
    def unit_display(self, obj):
        if obj.rlk_id and obj.rlk and obj.rlk.unit_id:
            return obj.rlk.unit.name
        return '—'


@admin.register(DiagnosticReferenceCategory)
class DiagnosticReferenceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active']


@admin.register(DiagnosticReferenceItem)
class DiagnosticReferenceItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'order', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'observation_zones', 'possible_causes', 'consequences']
    ordering = ['category', 'order', 'title']
    list_editable = ['order', 'is_active']
    raw_id_fields = ['category']
    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'title', 'description', 'order', 'is_active')
        }),
        ('Детальная информация', {
            'fields': ('observation_zones', 'possible_causes', 'consequences', 'additional_info'),
            'classes': ('wide',)
        }),
    )


@admin.register(DiagnosticReferenceSelection)
class DiagnosticReferenceSelectionAdmin(admin.ModelAdmin):
    list_display = ['test_drive', 'category_code', 'reference_item', 'created_at']
    list_filter = ['category_code', 'created_at']
    search_fields = ['test_drive__id', 'category_code', 'reference_item__title']
    raw_id_fields = ['test_drive', 'reference_item']
    readonly_fields = ['created_at']


@admin.register(BodyRefReplace)
class BodyRefReplaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'body_group', 'zg', 'element', 'amount')
    list_filter = ('body_group', 'zg', 'element')
    search_fields = ('zg', 'element')


@admin.register(BodyTypeGroup)
class BodyTypeGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('order', 'name')
    filter_horizontal = ('body_types',)


@admin.register(RegInteractivOcenkaPrice)
class RegInteractivOcenkaPriceAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'estimation', 'price_calculation', 'trigger', 'author', 'estimation_price',
        'price_auto_1', 'price_auto_2', 'price_auto_3', 'is_success',
    )
    list_filter = ('price_calculation', 'trigger', 'is_success', 'date')
    search_fields = ('estimation__vin', 'estimation__rlk__uin', 'author__username', 'user__name')
    raw_id_fields = ('estimation', 'page_soglasovanie', 'author', 'user')
    readonly_fields = ('date', 'text_json', 'raw_calculation_json')
    ordering = ('-date', '-id')