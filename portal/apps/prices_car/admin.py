from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    BrandKM,
    CarCalculations,
    CarCalculationsTypeDetail,
    CarCalculationUkApproval,
    DcKeyModel,
    DcMonthlyPlan,
    DealCalcTelegramSettings,
    KMCar,
    PriceCarBrand,
    PriceCarKmDiscount,
    PriceCarStageKM,
)


@admin.register(CarCalculations)
class CarCalculationsAdmin(admin.ModelAdmin):
    list_display = ('date', 'number', 'active', 'car', 'kvp', 'km_raschet', 'amount', 'unit', 'price', 'comment',)
    list_filter = ('unit', )
    raw_id_fields = ('rlk', 'unit', 'staff', 'author', 'user', 'car', )
    search_fields = ('rlk__nomer',)
    ordering = ('-date',)


class DcKeyModelInline(admin.TabularInline):
    model = DcKeyModel
    extra = 1
    raw_id_fields = ('model',)


@admin.register(DcMonthlyPlan)
class DcMonthlyPlanAdmin(admin.ModelAdmin):
    list_display = ('unit', 'month', 'plan_dc_qty', 'plan_importer_qty', 'tactic', 'is_autopilot', 'author', 'updated_at')
    list_filter = ('month', 'tactic', 'is_autopilot', 'unit')
    search_fields = ('unit__name',)
    inlines = [DcKeyModelInline]
    date_hierarchy = 'month'
    ordering = ('-month', 'unit')


@admin.register(PriceCarKmDiscount)
class PriceCarKmDiscountAdmin(admin.ModelAdmin):
    list_display = (
        'brand', 'model', 'unit', 'type_sale', 'is_yellow_car', 'is_key_model',
        'discount_percent', 'discount_rub', 'days_consignment_left_lte', 'is_autopilot',
        'date_from', 'date_to',
    )
    list_filter = ('brand', 'unit', 'is_yellow_car', 'is_key_model', 'is_autopilot', 'type_sale', 'date_from')
    search_fields = ('brand__name', 'model__name', 'comment')
    raw_id_fields = ('model', 'modification', 'complectation', 'unit')
    ordering = ('-date_from', 'brand')


@admin.register(PriceCarBrand)
class PriceCarBrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'free_consignment_days')
    search_fields = ('name',)
    filter_horizontal = ('marks', 'models_included')


@admin.register(BrandKM)
class BrandKMAdmin(admin.ModelAdmin):
    list_display = ('brand', 'month', 'km', 'km_min_dc', 'allow_dc_transfers')
    list_filter = ('brand', 'month')
    search_fields = ('brand__name',)
    date_hierarchy = 'month'
    ordering = ('-month', 'brand')


@admin.register(PriceCarStageKM)
class PriceCarStageKMAdmin(admin.ModelAdmin):
    list_display = ('stage', 'month', 'km_index')
    list_filter = ('stage', 'month')
    search_fields = ('stage__name',)
    date_hierarchy = 'month'
    ordering = ('-month', 'stage')


@admin.register(CarCalculationsTypeDetail)
class CarCalculationsTypeDetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_trade_in')
    list_filter = ('is_trade_in',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(KMCar)
class KMCarAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'car', 'km', 'type_km', 'km_manual',
        'km_auto_k', 'km_auto_k_tradein', 'km_auto_1', 'km_auto_2', 'km_auto_3',
    )
    list_filter = ('date',)
    raw_id_fields = ('car',)
    search_fields = ('car__vin', 'car__name', 'car__slug')
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('km',)


@admin.register(DealCalcTelegramSettings)
class DealCalcTelegramSettingsAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'bot_username', 'chat_ids', 'updated_at')
    fields = (
        'enabled',
        'bot_token',
        'bot_username',
        'chat_ids',
        'api_proxy',
        'webhook_secret',
        'webhook_help',
        'updated_at',
    )
    readonly_fields = ('updated_at', 'webhook_secret', 'webhook_help')

    def has_add_permission(self, request):
        try:
            return not DealCalcTelegramSettings.objects.exists()
        except Exception:
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'register-webhook/',
                self.admin_site.admin_view(self.register_webhook_view),
                name='prices_car_dealcalctelegramsettings_register_webhook',
            ),
            path(
                'webhook-info/',
                self.admin_site.admin_view(self.webhook_info_view),
                name='prices_car_dealcalctelegramsettings_webhook_info',
            ),
            path(
                'delete-webhook/',
                self.admin_site.admin_view(self.delete_webhook_view),
                name='prices_car_dealcalctelegramsettings_delete_webhook',
            ),
        ]
        return custom + urls

    def webhook_help(self, obj=None):
        from avtosalon.deal_calc_telegram import webhook_url

        url = webhook_url()
        register_url = reverse('admin:prices_car_dealcalctelegramsettings_register_webhook')
        info_url = reverse('admin:prices_car_dealcalctelegramsettings_webhook_info')
        delete_url = reverse('admin:prices_car_dealcalctelegramsettings_delete_webhook')
        return mark_safe(
            '<p>Сначала сохраните токен бота и включите функцию.</p>'
            '<p>URL webhook: <code>{}</code></p>'
            '<p>'
            '<a class="button" href="{}">Зарегистрировать webhook</a> '
            '<a class="button" href="{}">Проверить webhook</a> '
            '<a class="button" href="{}">Снять webhook (для polling)</a>'
            '</p>'
            '<p class="help">'
            'Если getWebhookInfo показывает <b>Connection timed out</b> — '
            'Telegram не достучится до портала (firewall/сеть). '
            'Тогда: снимите webhook и держите процесс '
            '<code>python manage.py deal_calc_telegram_poll --delete-webhook</code>.'
            '</p>'
            .format(url, register_url, info_url, delete_url)
        )
    webhook_help.short_description = 'Webhook'

    def register_webhook_view(self, request):
        from avtosalon.deal_calc_telegram import register_telegram_webhook, webhook_url

        ok, message = register_telegram_webhook()
        if ok:
            self.message_user(request, message, level=messages.SUCCESS)
        else:
            self.message_user(
                request,
                '{} (ожидаемый URL: {})'.format(message, webhook_url()),
                level=messages.ERROR,
            )
        obj = DealCalcTelegramSettings.load()
        return HttpResponseRedirect(
            reverse('admin:prices_car_dealcalctelegramsettings_change', args=[obj.pk])
        )

    def webhook_info_view(self, request):
        from avtosalon.deal_calc_telegram import get_telegram_webhook_info

        ok, message, _info = get_telegram_webhook_info()
        self.message_user(
            request,
            message,
            level=messages.SUCCESS if ok else messages.ERROR,
        )
        obj = DealCalcTelegramSettings.load()
        return HttpResponseRedirect(
            reverse('admin:prices_car_dealcalctelegramsettings_change', args=[obj.pk])
        )

    def delete_webhook_view(self, request):
        from avtosalon.deal_calc_telegram import delete_telegram_webhook

        ok, message = delete_telegram_webhook(drop_pending=False)
        self.message_user(
            request,
            message,
            level=messages.SUCCESS if ok else messages.ERROR,
        )
        obj = DealCalcTelegramSettings.load()
        return HttpResponseRedirect(
            reverse('admin:prices_car_dealcalctelegramsettings_change', args=[obj.pk])
        )
