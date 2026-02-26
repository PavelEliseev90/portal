from django.contrib import admin
from .models import Online_doc, Records_online_doc, PersonalDataConsent
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


@admin.register(PersonalDataConsent)
class PersonalDataConsentAdmin(ImportExportActionModelAdmin):
	list_display 	= ('date_created', 'get_full_name', 'phone', 'email', 'confirmed', 'revoked', 'date_confirmed', 'unit')
	list_filter 	= ('confirmed', 'revoked', 'date_created', 'date_confirmed', 'unit')
	search_fields 	= ('last_name', 'first_name', 'middle_name', 'phone', 'email', 'token')
	readonly_fields = ('token', 'date_created', 'rlk', 'date_opened', 'date_confirmed', 'date_revoked', 'ip_address', 'user_agent', 'consent_text')
	raw_id_fields 	= ('customer', 'rlk', 'unit')
	
	fieldsets = (
		('Основная информация', {
			'fields': ('rlk', 'token', 'last_name', 'first_name', 'middle_name', 'phone', 'email', 'customer', 'unit', 'comment')
		}),
		('Статус', {
			'fields': ('confirmed', 'revoked', 'date_created', 'date_opened', 'date_confirmed', 'date_revoked')
		}),
		('Техническая информация', {
			'fields': ('ip_address', 'user_agent', 'consent_text'),
			'classes': ('collapse',)
		}),
	)
	
	def get_full_name(self, obj):
		return obj.get_full_name()
	get_full_name.short_description = 'ФИО'