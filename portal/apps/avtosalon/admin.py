from django.contrib import admin
from .models import AvtohubGroupOptions, AvtohubOptions, AvtohubComplectations, Avtohub, AvtohubSite, AvtohubSiteInfo, RefreshCarsLog, RefreshSpecificationsAutoRU, Autoteka_signal, Autoteka_signal_last_id, Autoteka_signal_region


@admin.register(AvtohubGroupOptions)
class AvtohubGroupOptionsAdmin(admin.ModelAdmin):
    list_display    = ('id', 'id_avtohub', 'name', 'sortOrder',)


@admin.register(AvtohubOptions)
class AvtohubOptionsAdmin(admin.ModelAdmin):
    list_display    = ('id', 'id_avtohub', 'name', 'sortOrder', 'groupId', 'keyEquipment',)
    

@admin.register(AvtohubComplectations)
class AvtohubComplectationsAdmin(admin.ModelAdmin):
    list_display    = ('id', 'id_avtohub', 'name', 'autoruId', 'isActive',)
    search_fields   = ('autoruId', 'id_avtohub', 'name',)


@admin.register(Autoteka_signal)
class Autoteka_signalAdmin(admin.ModelAdmin):
    list_display    = ('date', 'id_records', 'item_id', 'seller', 'vin', 'price', 'year', 'mileage', 'brand', 'model', 'description', 'condition', 'owners', 'city_name', 'region_name', 'phone_number',)
    list_filter     = ('date', 'region_name', 'is_pro_seller',)
    search_fields   = ('vin', 'brand', 'model', 'phone_number', 'seller',)


@admin.register(Autoteka_signal_last_id)
class Autoteka_signal_last_idAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'last_id',)


@admin.register(Autoteka_signal_region)
class Autoteka_signal_regionAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'name',)
   

@admin.register(RefreshSpecificationsAutoRU)
class RefreshSpecificationsAutoRUAdmin(admin.ModelAdmin):
    list_display    = ('date', 'modification', 'complectation',)
    raw_id_fields   = ('modification', 'complectation',)
    list_filter     = ('date', )


@admin.register(RefreshCarsLog)
class RefreshCarsLogAdmin(admin.ModelAdmin):
    list_display    = ('date', 'unit', 'count_add', 'count_del', 'count_stock',)
    list_filter     = ('date', 'unit', )


@admin.register(Avtohub)
class AvtohubAdmin(admin.ModelAdmin):
    list_display    = ('date', 
                       'id_vencle', 
                       'uin', 
                       'vin', 
                       'price', 
                       'dealer_name', 
                       'type', 
                       'year', 
                       'mileage', 
                       'isInSale', 
                       'daysInStock', 
                       'daysInSale',
                       'imv', 
                       'maxposterSaleCost', 
                       'avgMarketPrice',
                       'vRatingPosition', 
                       'numberOfCompetitors', 
                       'actualMarketSales',
                       'averageSalePeriod',
                       'averageMarketMileage', 
                       'averageDaysInSale',
                       'totalMarketSales', 
                       'totalMarketSales90',
                       'totalAdvertisingCost', 
                       'placementOnAutoru',
                       'promotionOnAutoru',
                       'placementOnAvito', 
                       'promotionOnAvito', 
                       'placementOnDrom', 
                       'promotionOnDrom', 
                       'callsCounts_uniqueTotal', 
                       'callsCounts_uniqueTotalAutoru', 
                       'callsCounts_uniqueTotalAvito', 
                       'callsCounts_uniqueTotalDrom', 
                       'chatsCounts_uniqueTotal', 
                       'chatsCounts_uniqueTotalAutoru', 
                       'chatsCounts_uniqueTotalAvito', 
                       'chatsCounts_uniqueTotalDrom', 
                       'avitoViews',
                       'autoruViews', 
                       'dromViews',)
    list_filter     = ('date', 'dealer_name', )
    search_fields   = ('vin', )


@admin.register(AvtohubSite)
class AvtohubSiteAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(AvtohubSiteInfo)
class AvtohubSiteInfoAdmin(admin.ModelAdmin):
    list_display = ('date', 'vin','site', 'externalState', 'externalURL',)
    list_filter     = ('date', 'site', )
    search_fields   = ('vin', )