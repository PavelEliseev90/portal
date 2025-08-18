from django.contrib import admin

# Register your models here.
from django.contrib import admin
from recognition.models import Records_voice_recorder_cvc_checklist_kg, Check_settings, Records_voice_recorder_cvc_checklist, Recognition_call, Records_voice_recorder, Recognition_Anketa, Recognition_Anketa_Type, Recognition_Dictonary, Recognition_Tematika, Records_voice_recorder_cvc, Records_voice_recorder_queue, Records_voice_recorder_cvc_checklist_tematics, Records_questions, Check_settings_cvc, Records_voice_recorder_cvc_tematics



@admin.register(Records_voice_recorder_cvc_tematics)
class Records_voice_recorder_cvc_tematicsAdmin(admin.ModelAdmin):
    list_display    = ('name', 'id_cvc', 'activated', 'company', 'canceled', 'field', )
    list_filter     = ('activated', 'company', 'canceled', 'field',)


@admin.register(Check_settings_cvc)
class Check_settings_cvcAdmin(admin.ModelAdmin):
    list_display    = ('name', 'id_cvc',)

@admin.register(Records_voice_recorder_cvc_checklist_kg)
class Records_voice_recorder_cvc_checklist_kgAdmin(admin.ModelAdmin):
    list_display    = ('checklist_cvc', 'questions_kg',)



@admin.register(Check_settings)
class Check_settingsAdmin(admin.ModelAdmin):
    list_display    = ('name', 'direction',)
    list_filter     = ('direction',)


@admin.register(Records_questions)
class Records_questionsAdmin(admin.ModelAdmin):
    list_display    = ('name', 'direction', 'canceled', 'estimation', 'field', 'chapter_name',)
    list_filter     = ('direction', 'сheck_settings',)
    

@admin.register(Records_voice_recorder_cvc_checklist_tematics)
class Records_voice_recorder_cvc_checklist_tematicsAdmin(admin.ModelAdmin):
    list_display    = ('checklist', 'tematic', 'value', 'confirmed',)
    list_filter     = ('confirmed',)
    raw_id_fields   = ('checklist', 'tematic', )


@admin.register(Records_voice_recorder_cvc_checklist)
class Records_voice_recorder_cvc_checklistAdmin(admin.ModelAdmin):
    list_display    = ('date', 'rlk', 'records', 'time_start', 'time_end', 'duration',)
    list_filter     = ('date', 'success', 'result',)
    raw_id_fields   = ('records', 'rlk', )
    search_fields   = ('rlk__nomer', 'rlk__pk')


@admin.register(Records_voice_recorder_queue)
class Records_voice_recorder_queueAdmin(admin.ModelAdmin):
    list_display    = ('date', 'doc_id', 'direction', 'time_start', 'time_end', 'records', 'duration', 'error', )
    list_filter     = ('date', 'error', )
    search_fields   = ('doc_id',)
    raw_id_fields   = ('records', 'rlk', )
    

@admin.register(Records_voice_recorder_cvc)
class Records_voice_recorder_cvcAdmin(admin.ModelAdmin):
    list_display    = ('records','date', 'comment',)
    list_filter     = ('date',)
    search_fields   = ('comment', 'records__name' )
    raw_id_fields   = ('records', )


@admin.register(Recognition_Anketa)
class Recognition_AnketaAdmin(admin.ModelAdmin):
    list_display    = ('name','direction', 'type',)
    list_filter     = ('type',)
    search_fields   = ('name',)


@admin.register(Recognition_Anketa_Type)
class Recognition_Anketa_TypeAdmin(admin.ModelAdmin):
    list_display    = ('name',)
    search_fields   = ('name',)


@admin.register(Recognition_Dictonary)
class Recognition_DictonaryAdmin(admin.ModelAdmin):
    list_display    = ('date', 'name', 'added',)
    search_fields   = ('name',)
    search_fields   = ('added',)


@admin.register(Recognition_call)
class Recognition_callAdmin(admin.ModelAdmin):
    list_display    = ('date','time', 'name',)
    list_filter     = ('date',)
    search_fields   = ('name',)


@admin.register(Recognition_Tematika)
class Recognition_TematikaAdmin(admin.ModelAdmin):
    list_display    = ('name','anketa', 'rating', 'field', )
    list_filter     = ('name',)
    search_fields   = ('anketa',)


@admin.register(Records_voice_recorder)
class Records_voice_recorderAdmin(admin.ModelAdmin):
    list_display    = ('date','time', 'name', 'user', 'recognition', 'dateRecognitions', 'date_create','version_programm', 'error',)
    list_filter     = ('date', 'recognition', 'version_programm', 'error', 'user',)
    search_fields   = ('name', )