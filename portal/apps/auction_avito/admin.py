from django.contrib import admin

from .models import (
    AvitoAutotekaEvent,
    AvitoAutotekaReport,
    AvitoBidderAccount,
    AvitoBidHistory,
    AvitoLotCalculation,
    AvitoLot,
    AvitoLotAutohubVehicle,
    AvitoLotEquipment,
    AvitoLotImage,
    AvitoLotOffer,
    AvitoLotVehicle,
    AvitoLotBadge,
    AvitoOfferBadge,
    AvitoSyncLog,
)


class AvitoLotImageInline(admin.TabularInline):
    model = AvitoLotImage
    extra = 0


class AvitoLotEquipmentInline(admin.TabularInline):
    model = AvitoLotEquipment
    extra = 0


class AvitoAutotekaEventInline(admin.TabularInline):
    model = AvitoAutotekaEvent
    extra = 0


@admin.register(AvitoBidderAccount)
class AvitoBidderAccountAdmin(admin.ModelAdmin):
    list_display = ('bidder_id', 'dealer_id', 'unit', 'is_active')
    list_filter = ('is_active',)


@admin.register(AvitoLot)
class AvitoLotAdmin(admin.ModelAdmin):
    list_display = ('lot_id', 'seller_place_name', 'min_price', 'finish_at', 'synced_at')
    list_filter = ('finish_at',)
    search_fields = ('lot_id', 'description', 'seller_place_name')
    inlines = [AvitoLotImageInline, AvitoLotEquipmentInline]
    readonly_fields = ('synced_at',)


@admin.register(AvitoLotOffer)
class AvitoLotOfferAdmin(admin.ModelAdmin):
    list_display = (
        'lot_offer_id',
        'lot',
        'account',
        'status_name',
        'bid',
        'gm1_money',
        'updated_at',
    )
    list_filter = ('status_code', 'account')
    search_fields = ('lot_offer_id',)
    raw_id_fields = ('lot', 'account', 'car', 'bid_made_by_user')


@admin.register(AvitoAutotekaReport)
class AvitoAutotekaReportAdmin(admin.ModelAdmin):
    inlines = [AvitoAutotekaEventInline]


@admin.register(AvitoLotCalculation)
class AvitoLotCalculationAdmin(admin.ModelAdmin):
    list_display = (
        'calculated_at',
        'lot',
        'estimation_price',
        'zna',
        'profit',
        'is_success',
        'unit',
    )
    list_filter = ('is_success', 'auction_risk', 'calculated_at')
    search_fields = ('lot__lot_id',)
    raw_id_fields = ('lot', 'offer', 'unit', 'user')
    readonly_fields = ('calculated_at',)


@admin.register(AvitoSyncLog)
class AvitoSyncLogAdmin(admin.ModelAdmin):
    list_display = ('started_at', 'account', 'success', 'offers_count')
    list_filter = ('success',)
