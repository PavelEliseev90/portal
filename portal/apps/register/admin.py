from django.contrib import admin
from .models import RegInfoRefreshEstimationCarsExpress, RegRefCarsOrganizationsCalculationPrice, RegEstimationBalanceStaffEco, RegRefCarsOrganizationsPrice, RegEstimationRefCarsOrganizations, RegEstimationBalanceUnit, RegPodgotovkaWork, RegInfoBody, RegEstimationsSettings, RegPrices, RegSwapKors, RegInteractivOcenkaHistoryOpens, RegInteractivOcenkaEmailPush, RegInteractivOcenkaProverki, RegInteractivOcenkaSoglasovanie, RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive ,RegInteractivOcenkaComplectnost, RegInteractivOcenkaVnesh, RegDashboardError, RegInteractivOcenkaSalon, RegRegInteractivOcenkaFiles, RegInteractivOcenka, RegViewsCarsOrganization, SettingsRegPrices, TaskRegPrices, RegInfoRefreshCatalog, RegInteractivOcenkaDocument, RegUnitMonthlyPlan


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
    list_display    = ('estimation', 'name', 'type_file', 'file_number', 'user', )
    raw_id_fields   = ('estimation',) 
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
    raw_id_fields   = ('rlk', 'complectation', 'modification_avito', 'complectation_avito', 'modification', 'page_documents', 'page_salon','staff', 'staff_eco_1', 'staff_eco_2', 'page_documents', 'page_salon', 'page_vnesh', 'page_complectnost', 'page_kolesa', 'page_test_drive', 'page_proverki', 'page_soglasovanie',)
    list_filter     = ('start_estimation', 'dtp_red', 'taxi', 'carsharing', ) 
    search_fields   = ('vin', )


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
    