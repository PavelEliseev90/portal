from django.contrib import admin

from .models import (
    AvitoAuctionSettings,
    AvitoAutoBidDecision,
    AvitoAutotekaEvent,
    AvitoAutotekaReport,
    AvitoBidderAccount,
    AvitoVenue,
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
    fields = ('bidder_id', 'dealer_id', 'unit', 'is_active', 'comment', 'win_notify_emails')


@admin.register(AvitoVenue)
class AvitoVenueAdmin(admin.ModelAdmin):
    list_display = ('dealer_id', 'name', 'city', 'updated_at')
    search_fields = ('dealer_id', 'name', 'city__name')
    list_filter = ('city',)
    autocomplete_fields = ('city',)


@admin.register(AvitoLot)
class AvitoLotAdmin(admin.ModelAdmin):
    list_display = ('lot_id', 'venue', 'seller_place_name', 'min_price', 'finish_at', 'synced_at')
    list_filter = ('finish_at', 'venue')
    search_fields = ('lot_id', 'description', 'seller_place_name', 'venue__name', 'venue__city__name')
    raw_id_fields = ('venue',)
    inlines = [AvitoLotImageInline, AvitoLotEquipmentInline]
    readonly_fields = ('synced_at',)


@admin.register(AvitoLotOffer)
class AvitoLotOfferAdmin(admin.ModelAdmin):
    list_display = (
        'lot_offer_id',
        'lot',
        'account',
        'status_name',
        'outcome_code',
        'bid',
        'manual_max_bid',
        'gm1_money',
        'updated_at',
    )
    list_filter = ('status_code', 'outcome_code', 'account')
    search_fields = ('lot_offer_id',)
    raw_id_fields = ('lot', 'account', 'car', 'bid_made_by_user')
    readonly_fields = ('outcome_synced_at', 'win_email_sent_at')


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


@admin.register(AvitoAutoBidDecision)
class AvitoAutoBidDecisionAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'should_bid',
        'reason_category',
        'lot_id_ext',
        'lot_offer_id_ext',
        'reason',
    )
    list_filter = ('should_bid', 'reason_category', 'filters_ok')
    search_fields = ('reason', 'lot_id_ext', 'lot_offer_id_ext')
    readonly_fields = ('created_at',)
    raw_id_fields = ('lot', 'offer')


@admin.register(AvitoAuctionSettings)
class AvitoAuctionSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'auto_bid_enabled',
        'outcome_poll_enabled',
        'mileage_min',
        'mileage_max',
        'year_min',
        'year_max',
        'block_taxi',
        'block_carsharing',
        'block_mileage_twisted',
        'cap_bid_by_seller_wish',
        'updated_at',
    )
    readonly_fields = ('updated_at',)
