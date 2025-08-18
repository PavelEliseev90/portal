from django.contrib import admin
from .models import MangoGroup, MangoHystoryCalls, MangoNumberSip, MangoNumberSipGroup, MangoHystoryCallsRecords, Telephony_records_queue


@admin.register(MangoGroup)
class MangoGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'mango_id',)
    search_fields   = ('name', 'mango_id', )


@admin.register(MangoHystoryCalls)
class MangoHystoryCallsAdmin(admin.ModelAdmin):
    list_display    = ('entry_id', 'from_number', 'to_number', 'start', 'finish', 'time', 'records', 'answer',)
    search_fields   = ('from_number', 'to_number', 'entry_id',)


@admin.register(MangoNumberSip)
class MangoNumberSipAdmin(admin.ModelAdmin):
    list_display    = ('name', 'sip', 'description', )
    search_fields   = ('name', 'description', )


@admin.register(MangoNumberSipGroup)
class MangoNumberSipGroupAdmin(admin.ModelAdmin):
    list_display    = ('group', 'number', )
    search_fields   = ('group__name', 'number__name', )


@admin.register(MangoHystoryCallsRecords)
class MangoHystoryCallsRecordsAdmin(admin.ModelAdmin):
    list_display    = ('entry_id', 'record', )
    search_fields   = ('entry_id', 'record', )


@admin.register(Telephony_records_queue)
class Telephony_records_queueAdmin(admin.ModelAdmin):
    list_display    = ('rlk', 'record', )
    search_fields   = ('rlk', 'record', )
    raw_id_fields   = ('rlk',)