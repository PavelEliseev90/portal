from django.contrib import admin
from .models import DocLO, DocZN, DocZNPerformers, DocZNWork, DocZNProduct, DocRLK, DocRLKEvents, DocCarAgreement, DocCarShipment, DocOprosZN, DocOprosCarShipment, DoсRecomendation,  DocRecomendationFiles, DoсRecomendationMCU, DocZNRecomendation, DocServiceRequest, ResourcePlanning, DocSMS


@admin.register(DocLO)
class DocLOAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'active', 'nomer', 'unit', 'store', 'filial', 'staff', 'customer', 'vin', 'carsGRZ', 'year', 'run',)
    raw_id_fields   = ('unit', 'staff', 'rlk', 'customer', 'cars', 'modification_autoru', 'complectation_autoru', )
    search_fields   = ('nomer', 'uin', 'vin',)
    list_filter     = ('active', )


@admin.register(DocSMS)
class DocSMSAdmin(admin.ModelAdmin):
    list_display    = ('dateTime', 'dateSend', 'unit', 'modelName', 'staff', 'customer', 'phone',)
    raw_id_fields   = ('customer', 'staff', 'unit', )
    search_fields   = ('modelId', 'phone',)


@admin.register(ResourcePlanning)
class ResourcePlanningtAdmin(admin.ModelAdmin):
    list_display    = ('dateStart', 'dateEnd', 'active', 'staff', 'type',)
    raw_id_fields   = ('serviceRequest', 'staff', )
    

@admin.register(DocServiceRequest)
class DocServiceRequestAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'nomer', 'active', 'organization', 'unit', 'customer', 'cars', 'typeRemont', )
    search_fields   = ('nomer', 'uin',)
    raw_id_fields   = ('customer', 'cars', 'master', 'masterOut', 'readyStatus', 'unit', 'organization',)
    list_filter     = ('unit', 'active', )
    #inlines         = [DocZNWorkInline, ]


class DocZNWorkInline(admin.TabularInline):
    fk_name             = 'zn'
    model               = DocZNWork
    extra               = 0
    classes             = ['collapse']


@admin.register(DocZNRecomendation)
class DocZNRecomendationAdmin(admin.ModelAdmin):
    list_display    = ('zn', 'name',  )
    raw_id_fields   = ('zn', )


@admin.register(DocRecomendationFiles)
class DocRecomendationFilesAdmin(admin.ModelAdmin):
    list_display    = ('recomendation', )
    raw_id_fields   = ('recomendation', )


@admin.register(DocZNPerformers)
class DocZNPerformersAdmin(admin.ModelAdmin):
    list_display    = ('zn', 'staff', 'uin', 'percent', )
    raw_id_fields   = ('zn', 'staff',)


@admin.register(DoсRecomendationMCU)
class DoсRecomendationMCUAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'unit', 'zn', 'name', 'dataTimeCutomerEvent', 'customerStatus', 'status', )
    search_fields   = ('zn__uin',)
    list_filter     = ('dataTime', 'customerStatus', 'status', )
    raw_id_fields   = ('zn', )


@admin.register(DoсRecomendation)
class DoсRecomendationAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'zn', 'name', 'customerStatus', 'status', )
    search_fields   = ('kod_recomendation', 'zn__uin',)
    list_filter     = ('customerStatus', 'status',)
    raw_id_fields   = ('zn', )

@admin.register(DocZN)
class DocZNAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'nomer', 'active', 'organization', 'unit', 'customer', 'cars', 'typeRemont', 'amount', )
    search_fields   = ('nomer', 'uin',)
    raw_id_fields   = ('customer', 'cars', 'master', 'masterOut', 'readyStatus', 'unit', 'organization', 'serviceRequest',)
    list_filter     = ('unit', 'active', )
    #inlines         = [DocZNWorkInline, ]

@admin.register(DocZNWork)
class DocZNWorkAdmin(admin.ModelAdmin):
    list_display    = ('id', 'zn', 'work', 'type', )
    search_fields   = ('zn', )
    raw_id_fields   = ('zn', 'work', )


@admin.register(DocZNProduct)
class DocZNProductAdmin(admin.ModelAdmin):
    list_display    = ('id', 'zn', 'product', 'type', )
    search_fields   = ('zn', )
    raw_id_fields   = ('zn', 'product', )


@admin.register(DocRLK)
class DocRLKAdmin(admin.ModelAdmin):
    list_display    = ('nomer', 'dataTime', 'dataTimeCreate', 'unit', 'unit_dc', 'staff', 'type', 'contacType',  )
    search_fields   = ('nomer', 'uin', )
    list_filter     = ('unit', 'is_missed', )
    raw_id_fields   = ('cars', 'customer', 'unit', 'staff', 'unit_dc', 'staffECO1', 'staffECO2', 'footing',)


@admin.register(DocRLKEvents)
class DocRLKEventsAdmin(admin.ModelAdmin):
    list_display    = ('rlk', 'dataTime', 'dataTimeEvent', 'contacType', )
    list_filter     = ('contacType',)
    search_fields   = ('rlk__nomer', )


@admin.register(DocCarAgreement)
class DocCarAgreementAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'active', 'nomer', 'organization', 'unit', 'client', 'cars', 'rlk', )
    search_fields   = ('nomer', 'cars__vin', )
    raw_id_fields   = ('client', 'cars', 'rlk', 'lo', 'staff', 'unit', 'organization',)


@admin.register(DocCarShipment)
class DocCarShipmentAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'active', 'nomer', 'organization', 'unit', 'client', 'cars', 'rlk', )
    search_fields   = ('nomer', 'cars__vin', )
    raw_id_fields   = ('client', 'cars', 'rlk', 'lo', 'agreement', 'staff', 'unit', 'organization',)


@admin.register(DocOprosZN)
class DocOprosZNAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'dataClose', 'zn', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8',)
    list_filter     = ('close',)
    search_fields   = ('zn__nomer', 'uin', )
    raw_id_fields   = ('zn', )


@admin.register(DocOprosCarShipment)
class DocOprosCarShipmentAdmin(admin.ModelAdmin):
    list_display    = ('dataTime', 'dataClose', 'shipment', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8',)
    list_filter     = ('close', 'shipment__unit',)
    search_fields   = ('shipment__nomer', 'uin',  )
    raw_id_fields   = ('shipment', )