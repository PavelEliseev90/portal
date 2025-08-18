from django.contrib import admin
from checklists.models import CheckList, CheckListServiceIn, CheckListServiceOut, CheckListTradeIn, CheckList_op_kors
from django.utils.safestring import mark_safe


@admin.register(CheckList)
class CheckListAdmin(admin.ModelAdmin):
	list_display    = ('id', 'dataTimeCreate', 'user', 'rlk', 'comment', )
	raw_id_fields   = ('rlk', 'audio_voice_recorder')
	search_fields   = ('id', 'v8_3', )
	list_filter     = ('version_checklist',  )


@admin.register(CheckListServiceIn)
class CheckListServiceInAdmin(admin.ModelAdmin):
	list_display    = ('id', 'dataTimeCreate', 'user', 'zn', 'comment', )
	raw_id_fields   = ('zn',)
	search_fields   = ('id', )


@admin.register(CheckListServiceOut)
class CheckListServiceOutAdmin(admin.ModelAdmin):
	list_display    = ('id', 'dataTimeCreate', 'user', 'zn', 'comment', )
	raw_id_fields   = ('zn',)
	search_fields   = ('id', )


@admin.register(CheckListTradeIn)
class CheckListTradeInAdmin(admin.ModelAdmin):
	list_display    = ('id', 'dataTimeCreate', 'user', 'rlk', 'comment', )
	raw_id_fields   = ('rlk',)
	search_fields   = ('id', )


@admin.register(CheckList_op_kors)
class CheckList_op_korsAdmin(admin.ModelAdmin):
	list_display    = ('id', 'dataTimeCreate', 'user', 'rlk', 'comment', )
	raw_id_fields   = ('rlk', 'audio_voice_recorder', )
	search_fields   = ('id',  )