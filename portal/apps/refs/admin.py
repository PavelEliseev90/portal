from django.contrib import admin
from .models import AuctionStructureFiles, RefCarsOrganizationAuctionStatus, AutoruModificationOptions, RefModificationsOptionGroup, RefModificationsOption, AutoruModificationOptionsDetail,  Auction, AuctionStructure, RefStatusEstimation, RefTypeDrive, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefPsdDisk, RefTypeDisk, RefDiaDisk, RefEtDisk, RefFilial, AutoruModificationSpecifications, RefSpecification, RefSpecificationData, RefEventCarsOrganization, RefRatingCarsOrganization, RefStore, RefCarsOrganizationFiles, RefCarsOrganization, RefAvito, RefTypeBody, RefTypeEngine, RefUnitGroup, RefExchangeCars, RefTypeCanceledCheckList, RefIb, RefTypeItemRepair, AutoruMark, AutoruModification, AutoruComplectation, AutoruModel, RefArea, RefCity, RefOrganization, RefUnit, RefCustomer, RefCars, RefStaff, RefTypeDocRLK, RefWork, RefProduct, RefTypeRepair, RefStatusDocZN, RefContactType, RefStatusEvent, RefBoardsPage, RefTypeCanceledSMS, RefManufacturer, RefCatalogProduct, RefTypeResourcePlanning, RefBoards, RefPageOcenka, RefCustomerFiltr, RefAvitoComplectation, RefGroupPrice, UnitPriceGroupSettings
from django_mptt_admin.admin import DjangoMpttAdmin


@admin.register(AuctionStructureFiles)
class AuctionStructureFilesAdmin(admin.ModelAdmin):
    list_display    = ('pk',)


@admin.register(RefCarsOrganizationAuctionStatus)
class RefCarsOrganizationAuctionStatusAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', 'name_auction',)


@admin.register(AutoruModificationOptions)
class AutoruModificationOptionsAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'modification', 'complectation',  'name', 'link')
    readonly_fields = ('modification', 'complectation')
    search_fields   = ('name', 'link',)


@admin.register(RefModificationsOption)
class RefModificationsOptionGroupAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', 'group',)

@admin.register(AutoruModificationOptionsDetail)
class AutoruModificationOptionsDetailAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'modification', 'complectation',  'option',)
    readonly_fields = ('modification', 'complectation')


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'store', )
    readonly_fields = ('store', 'user')


@admin.register(AuctionStructure)
class AuctionStructureAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'auction', 'car')
    readonly_fields = ('car', 'auction')
    

@admin.register(RefTypeDrive)
class RefTypeDriveAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 

@admin.register(RefStatusEstimation)
class RefStatusEstimationAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefEtDisk)
class RefEtDiskAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefDiaDisk)
class RefDiaDiskAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefTypeDisk)
class RefTypeDiskAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefSezonTyres)
class RefSezonTyresAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefRadius)
class RefRadiusAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefProfileTyres)
class RefProfileTyresAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefWidthTyres)
class RefWidthTyresAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefMarkTyres)
class RefMarkTyresAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 

@admin.register(RefPsdDisk)
class RefPsdDiskAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(AutoruModificationSpecifications)
class AutoruModificationSpecificationsAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'modification', 'complectation', 'name', 'link', )
    search_fields   = ('name', ) 
    raw_id_fields   = ('modification', 'complectation', )


@admin.register(RefFilial)
class RefFilialAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )
    search_fields   = ('name', ) 


@admin.register(RefSpecification)
class RefSpecificationAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', 'group', )
    search_fields   = ('name', ) 


@admin.register(RefSpecificationData)
class RefSpecificationDataAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'modification_specifications', 'specification', 'value', )
    list_filter     = ('specification', )
    raw_id_fields   = ('modification_specifications', 'specification', ) 


@admin.register(RefAvitoComplectation)
class RefAvitoComplectationAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', 'avito_ref', 'avito_id', )
    search_fields   = ('name', 'avito_id', )
    raw_id_fields   = ('avito_ref', )


class RefAvitoChildInline(admin.TabularInline):
    model = RefAvito
    fk_name = 'parent'
    extra = 0
    show_change_link = True
    fields = (
        'name', 'avito_id', 'group', 'year_star', 'year_end',
        'doors', 'engine_volume', 'engine_power',
    )
    verbose_name = 'Дочерний элемент каталога'
    verbose_name_plural = 'Дочерние элементы каталога'


class RefAvitoComplectationInline(admin.TabularInline):
    model = RefAvitoComplectation
    fk_name = 'avito_ref'
    extra = 0
    show_change_link = True
    fields = ('name', 'avito_id',)
    verbose_name = 'Комплектация'
    verbose_name_plural = 'Комплектации'


@admin.register(RefAvito)
class RefAvitoAdmin(DjangoMpttAdmin):
    prepopulated_fields = {"slug": ("name", "avito_id",)}
    raw_id_fields = ('parent', 'kpp', 'engine', 'drive', 'body')
    search_fields = ('name', 'slug', 'avito_id',)
    list_display = (
        'name', 'parent', 'group', 'avito_id',
        'year_star', 'year_end', 'children_count', 'complectations_count',
    )
    list_filter = ('group',)
    readonly_fields = ('hierarchy_path', 'children_count', 'complectations_count')
    inlines = (RefAvitoChildInline, RefAvitoComplectationInline)
    fieldsets = (
        (None, {
            'fields': (
                'name', 'slug', 'parent', 'group', 'avito_id', 'hierarchy_path',
                'children_count', 'complectations_count',
            ),
        }),
        ('Характеристики', {
            'fields': (
                'year_star', 'year_end', 'doors',
                'engine_volume', 'engine_power',
                'kpp', 'engine', 'drive', 'body',
            ),
        }),
        ('Изображение', {
            'fields': ('image_url', 'file',),
        }),
    )

    @admin.display(description='Путь в каталоге')
    def hierarchy_path(self, obj):
        if obj is None or not obj.pk:
            return '—'
        return ' → '.join(node.name or '—' for node in obj.get_ancestors(include_self=True))

    @admin.display(description='Дочерних элементов')
    def children_count(self, obj):
        if obj is None or not obj.pk:
            return 0
        return obj.get_children().count()

    @admin.display(description='Комплектаций')
    def complectations_count(self, obj):
        if obj is None or not obj.pk:
            return 0
        return RefAvitoComplectation.objects.filter(avito_ref=obj).count()


@admin.register(RefEventCarsOrganization)
class RefEventCarsOrganizationAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', )


@admin.register(RefCarsOrganizationFiles)
class RefCarsOrganizationFilesAdmin(admin.ModelAdmin):
    list_display    = ('сars_organization', 'name', )
    list_filter     = ('processed',)
    raw_id_fields   = ('сars_organization', )
    search_fields   = ('сars_organization__vin', ) 


@admin.register(RefStore)
class RefStoreAdmin(admin.ModelAdmin):
    list_display    = ('name', )

@admin.register(RefRatingCarsOrganization)
class RefRatingCarsOrganizationAdmin(admin.ModelAdmin):
    list_display    = ('name', )
     

@admin.register(RefCarsOrganization)
class RefCarsOrganizationAdmin(admin.ModelAdmin):
    list_display    = ('unit', 'slug', 'store', 'lo', 'vin', 'name', 'run', 'year', 'modification_autoru', 'complectation_autoru', 'modification_avito', 'plate_number', 'price', 'date_refresh', 'stage_price', 'group_price', 'get_files_count', )
    raw_id_fields   = ('organization', 'store', 'unit', 'modification_avito', 'complectation_avito', 'modification_autoru', 'complectation_autoru', 'lo', )
    search_fields   = ('vin', 'slug', )  
    list_filter     = ("quantity", "reserve", 'store', 'unit', 'group_price',)


@admin.register(RefTypeBody)
class RefTypeBodyAdmin(admin.ModelAdmin):
	list_display    = ('name', )


@admin.register(RefTypeEngine)
class RefTypeEngineAdmin(admin.ModelAdmin):
	list_display    = ('name', )
      

@admin.register(RefCustomerFiltr)
class RefCustomerFiltrAdmin(admin.ModelAdmin):
	list_display    = ('name', 'path', 'user', )
    

@admin.register(RefUnitGroup)
class RefUnitGroupAdmin(admin.ModelAdmin):
	list_display    = ('name', 'name_bi', 'comment', )


@admin.register(RefBoards)
class RefBoardsAdmin(admin.ModelAdmin):
	list_display    = ('name', 'name_title', 'table_view_customer', 'table_view_staff', 'table_view_plate_number', 'table_view_status', )


@admin.register(RefTypeResourcePlanning)
class RefTypeResourcePlanningAdmin(admin.ModelAdmin):
	list_display    = ('name', )


@admin.register(RefTypeCanceledSMS)
class RefTypeCanceledSMSAdmin(admin.ModelAdmin):
	list_display    = ('name', )
     

@admin.register(RefExchangeCars)
class RefExchangeCarsAdmin(admin.ModelAdmin):
	list_display    = ('unit','mark_filter','adress','file_name','city_name', 'link', )


@admin.register(RefTypeCanceledCheckList)
class RefTypeCanceledCheckListAdmin(admin.ModelAdmin):
	list_display    = ('name', )
        
        
@admin.register(RefIb)
class RefIbAdmin(admin.ModelAdmin):
	list_display    = ('name', 'server', 'base', )
	list_filter     = ('server',)


@admin.register(RefTypeItemRepair)
class RefTypeItemRepairAdmin(admin.ModelAdmin):
	list_display    = ('name',)
	list_filter     = ("name",)


# --- Автору: марки, модели, модификации, комплектации ---

@admin.register(AutoruMark)
class AutoruMarkAdmin(admin.ModelAdmin):
    list_display    = ('name', 'nameEn', 'idSite', 'avtosalon')
    list_filter     = ('avtosalon', 'name')
    search_fields   = ('name', 'nameEn')


@admin.register(AutoruModel)
class AutoruModelAdmin(admin.ModelAdmin):
    list_display    = ('mark', 'name', 'nameEn', 'idSite')
    list_filter     = ('mark',)
    search_fields   = ('name', 'nameEn', 'mark__name')
    raw_id_fields   = ('mark',)
    list_select_related = ('mark',)


@admin.register(AutoruModification)
class AutoruModificationAdmin(admin.ModelAdmin):
    list_display    = ('model', 'name', 'idSite', 'typeBody', 'typeEngine', 'typeGear')
    list_filter     = ('model__mark',)
    search_fields   = ('name', 'nameEn', 'model__name', 'model__mark__name')
    raw_id_fields   = ('model', 'typeBody', 'typeEngine', 'typeGear')
    list_select_related = ('model', 'model__mark')


@admin.register(AutoruComplectation)
class AutoruComplectationAdmin(admin.ModelAdmin):
    list_display    = ('modification', 'name', 'idSite')
    list_filter     = ('modification__model__mark', 'modification__model', 'idSite')
    search_fields   = ('name', 'modification__name', 'modification__model__name', 'idSite',)
    raw_id_fields   = ('modification',)
    list_select_related = ('modification', 'modification__model', 'modification__model__mark')


@admin.register(RefArea)
class RefAreaAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', )


@admin.register(RefCity)
class RefCityAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', )


@admin.register(RefOrganization)
class RefOrganizationAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', ) 


@admin.register(RefUnit)
class RefUnitAdmin(admin.ModelAdmin):
    list_display    = ('name', 'buauto', 'auto_reprice_new', 'alfa_auto_transition_date', 'active_eco', 'city', 'ib', )
    search_fields   = ('name', )
    list_filter     = ('buauto', 'auto_reprice_new', 'active_eco', 'city', 'ib', 'alfa_auto_transition_date')
    raw_id_fields   = ('eco_staff', 'eco_units', )


@admin.register(RefCustomer)
class RefCustomerAdmin(admin.ModelAdmin):
    list_display    = ('name', 'phoneNorm', 'email', 'actual_addres', 'description', 'comment',    )
    search_fields   = ('name', 'phoneNorm', 'email', ) 


@admin.register(RefCars)
class RefCarsAdmin(admin.ModelAdmin):
    list_display    = ('name', 'mark', 'model', 'year' )
    search_fields   = ('name', ) 
    raw_id_fields   = ('modification_autoru', 'complectation_autoru',) 


@admin.register(RefStaff)
class RefStaffAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name', 'domain_login', )
    search_fields   = ('name', 'domain_login', ) 


@admin.register(RefTypeDocRLK)
class RefTypeDocRLKAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', ) 


@admin.register(RefWork)
class RefWorkAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', ) 


@admin.register(RefProduct)
class RefProductAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', ) 


@admin.register(RefTypeRepair)
class RefTypeRepairAdmin(admin.ModelAdmin):
    list_display    = ('name', 'opros',)
    list_filter     = ('opros',)
    search_fields   = ('name', ) 


@admin.register(RefStatusDocZN)
class RefStatusDocZNAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', ) 


@admin.register(RefContactType)
class RefContactTypeAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', )


@admin.register(RefStatusEvent)
class RefStatusEventAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', )


@admin.register(RefBoardsPage)
class RefBoardsPageAdmin(admin.ModelAdmin):
    list_display    = ( 'title', 'activated', 'time',)
    search_fields   = ( 'title',)
    list_filter     = ('activated',)


@admin.register(RefManufacturer)
class RefManufacturerAdmin(admin.ModelAdmin):
    list_display    = ('name', 'group_name', 'search_fields', )
    search_fields   = ('name', 'group_name', 'search_fields', )

@admin.register(RefCatalogProduct)
class RefCatalogProductAdmin(admin.ModelAdmin):
    list_display    = ('name', 'manufacturer', 'article', )
    search_fields   = ('name', )
    
@admin.register(RefPageOcenka)
class RefPageOcenkaAdmin(admin.ModelAdmin):
    list_display    = ('name', )
    search_fields   = ('name', )


@admin.register(RefGroupPrice)
class RefGroupPriceAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'min_price_rub', 'max_price_rub',
        'sort_order', 'label_1c', 'is_active',
    )
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'label_1c')
    ordering = ('sort_order', 'code', 'name')
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'is_active', 'sort_order'),
            'description': (
                'Код (code) — суффикс полей формы и ключ в настройках, напр. 400, 5001. '
                'Новая активная ЦГ автоматически появится в автопереоценке КорсАвто.'
            ),
        }),
        ('Диапазон цены, руб', {
            'fields': ('min_price_rub', 'max_price_rub'),
            'description': 'Верхняя граница не включается (как в расчёте оценки). Для последней ЦГ max можно оставить пустым.',
        }),
        ('1С', {
            'fields': ('label_1c',),
        }),
    )


class UnitPriceGroupSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'created_at', 'unit', 'price_group',
        'auto_active', 'auto_strategy', 'correction_kor', 'eval_type',
    )
    list_filter = ('price_group', 'auto_active', 'auto_strategy', 'created_at')
    search_fields = ('unit__name', 'price_group__code', 'price_group__name')
    readonly_fields = ('created_at',)
    raw_id_fields = ('unit', 'eval_type')
    autocomplete_fields = ('price_group',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at', '-id')
    list_select_related = ('unit', 'price_group', 'eval_type')

    fieldsets = (
        (None, {
            'fields': ('unit', 'price_group', 'created_at'),
        }),
        ('Автопереоценка — флаги', {
            'fields': (
                'auto_strategy', 'auto_active',
                'lock_eval_change_after_stage', 'deny_manual_price', 'deny_discount',
                'no_limit_max_manual', 'reset_manual_prices', 'delay_repricing_new_stage',
                'check_price_rule_before_sale', 'check_open_tasks', 'calc_by_days_in_sale',
            ),
        }),
        ('Автохаб', {
            'fields': (
                'autohub_mode_kor', 'autohub_mode_rdo', 'autohub_mode_test', 'autohub_mode_txt',
            ),
        }),
        ('Корректировки и наценки', {
            'fields': (
                'correction_kor', 'correction_kor_1c', 'correction_kor_express',
                'correction_rdo', 'correction_rdo_1c', 'correction_rdo_express',
                'correction_test', 'correction_test_1c', 'correction_test_express',
                'correction_txt', 'correction_txt_1c', 'correction_txt_express',
                'markup_base', 'markup_kor', 'markup_rdo', 'markup_test', 'markup_txt',
                'max_discount_tradein', 'max_discount_bargain_percent', 'marketing',
            ),
        }),
        ('Legacy / ИРЦ', {
            'classes': ('collapse',),
            'fields': (
                'ratio_1c_test_price', 'ratio_1c_rdo', 'ratio_1c_kor', 'ratio_1c_txt',
                'ratio_avtohub_test_price', 'ratio_avtohub_rdo', 'ratio_avtohub_kor', 'ratio_avtohub_txt',
                'percent_txt', 'percent_torg_txt', 'discount_tt', 'discount_torg',
            ),
        }),
        ('Правило вывода в продажу', {
            'fields': ('eval_type',),
        }),
    )


admin.site.register(UnitPriceGroupSettings, UnitPriceGroupSettingsAdmin)

from refs.price_group_stage_days import (  # noqa: E402
    PriceGroupStageDaysLine,
    PriceGroupStageDaysSnapshot,
)


class PriceGroupStageDaysLineInline(admin.TabularInline):
    model = PriceGroupStageDaysLine
    extra = 0
    autocomplete_fields = ('price_group',)


class PriceGroupStageDaysSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'created_by', 'comment')
    list_filter = ('created_at',)
    search_fields = ('comment', 'created_by__username')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at', '-id')
    inlines = [PriceGroupStageDaysLineInline]


admin.site.register(PriceGroupStageDaysSnapshot, PriceGroupStageDaysSnapshotAdmin)
