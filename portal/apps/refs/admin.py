from django.contrib import admin
from .models import AuctionStructureFiles, RefCarsOrganizationAuctionStatus, AutoruModificationOptions, RefModificationsOptionGroup, RefModificationsOption, AutoruModificationOptionsDetail,  Auction, AuctionStructure, RefStatusEstimation, RefTypeDrive, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefPsdDisk, RefTypeDisk, RefDiaDisk, RefEtDisk, RefFilial, AutoruModificationSpecifications, RefSpecification, RefSpecificationData, RefEventCarsOrganization, RefRatingCarsOrganization, RefStore, RefCarsOrganizationFiles, RefCarsOrganization, RefAvito, RefTypeBody, RefTypeEngine, RefUnitGroup, RefExchangeCars, RefTypeCanceledCheckList, RefIb, RefTypeItemRepair, AutoruMark, AutoruModification, AutoruComplectation, AutoruModel, RefArea, RefCity, RefOrganization, RefUnit, RefCustomer, RefCars, RefStaff, RefTypeDocRLK, RefWork, RefProduct, RefTypeRepair, RefStatusDocZN, RefContactType, RefStatusEvent, RefBoardsPage, RefTypeCanceledSMS, RefManufacturer, RefCatalogProduct, RefTypeResourcePlanning, RefBoards, RefPageOcenka, RefCustomerFiltr, RefAvitoComplectation
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
    list_display    = ('pk', 'name', 'avito_ref', )
    search_fields   = ('name', ) 
    raw_id_fields   = ('avito_ref', )

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
    list_display    = ('unit', 'store', 'lo', 'vin', 'name', 'run', 'year', 'modification_autoru', 'complectation_autoru', 'modification_avito', 'plate_number', 'price', 'date_refresh', 'stage_price', 'group_price', 'get_files_count', )
    raw_id_fields   = ('organization', 'store', 'unit', 'modification_avito', 'complectation_avito', 'modification_autoru', 'complectation_autoru', 'lo', )
    search_fields   = ('vin', )  
    list_filter     = ("quantity", "reserve", 'store', 'unit', 'group_price',)

@admin.register(RefAvito)
class RefAvitoAdmin(DjangoMpttAdmin):
    prepopulated_fields = {"slug": ("name", "avito_id",)}
    raw_id_fields       = ('parent',)
    search_fields       = ('name', )


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


@admin.register(AutoruMark)
class AutoruMarkAdmin(admin.ModelAdmin):
	list_display    = ('name', 'idSite',)
	list_filter     = ("name",)
	search_fields   = ('name',)


@admin.register(AutoruModel)
class AutoruModelAdmin(admin.ModelAdmin):
    list_display    = ('mark', 'name', 'idSite',)
    list_filter     = ("mark",)
    raw_id_fields   = ('mark',)


@admin.register(AutoruModification)
class AutoruModificationAdmin(admin.ModelAdmin):
    list_display    = ('model', 'name', 'idSite', )
    search_fields   = ('idSite', 'model__name', 'name', )
    raw_id_fields   = ('model', )


@admin.register(AutoruComplectation)
class AutoruComplectationAdmin(admin.ModelAdmin):
    list_display    = ('modification', 'name', 'idSite',)
    search_fields   = ('name', 'idSite', )
    raw_id_fields   = ('modification',)
    list_filter     = ('modification__model__mark', 'idSite',)


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
    list_display    = ('name', 'buauto', 'city', 'ib', )
    search_fields   = ('name', )
    list_filter     = ('buauto', 'city', 'ib',)
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
    