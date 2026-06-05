from django.contrib import admin

from client_journey.models import ClientJourneyLink


@admin.register(ClientJourneyLink)
class ClientJourneyLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'rlk', 'token', 'is_active', 'opens_count', 'created_at', 'last_opened_at')
    list_filter = ('is_active',)
    search_fields = ('rlk__nomer', 'rlk__clientName', 'token')
    readonly_fields = ('token', 'created_at', 'last_opened_at', 'opens_count')
