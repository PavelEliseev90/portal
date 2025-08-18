from django.contrib import admin
from .models import Online_doc, Records_online_doc
from import_export.admin import ImportExportActionModelAdmin


@admin.register(Online_doc)
class Online_docAdmin(ImportExportActionModelAdmin):
	list_display 	= ('dataTimeCreate', 'dataTimeOpen', 'uin',)
	list_filter 	= ('dataTimeCreate', 'dataTimeOpen', 'dataTimeRecord', 'call',)
	raw_id_fields 	= ('cars', 'customer', 'unit', 'unitRecord', )
	search_fields 	= ('uin',)


@admin.register(Records_online_doc)
class Records_online_docAdmin(ImportExportActionModelAdmin):
	list_display 	= ('dataTimeCreate', 'dataTimeOpen', 'uin','clientName', 'clientPhone', 'cars', 'dataTimeRecord', )
	list_filter 	= ('dataTimeCreate', 'dataTimeOpen', 'dataTimeRecord', 'unit', )
	raw_id_fields 	= ('cars', 'customer', 'unit',)
	search_fields 	= ('uin',)