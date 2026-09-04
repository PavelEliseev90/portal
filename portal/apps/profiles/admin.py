from django.contrib import admin
from .models import Profiles
from django.utils.safestring import mark_safe


@admin.register(Profiles)
class ProfilesAdmin(admin.ModelAdmin):
	list_display = (
		'image_img', 'user', 'nameUser', 'birth_date', 'phone', 'email',
		'eco_name', 'telegram_chat_id', 'eco', 'eco_visible',
		'eco_chat_important', 'eco_price_increase', 'eco_page_price_info',
		'korsavto_settings',
	)
	search_fields = ('user__last_name', 'user__first_name', 'telegram_chat_id')
	raw_id_fields = ('user',)
	list_filter = (
		'eco', 'eco_visible', 'eco_chat_important', 'eco_price_increase',
		'eco_page_price_info', 'korsavto_settings', 'price_car_new_all',
		'price_car_new_director',
	)
	filter_horizontal = ('korsavto_stores', 'available_units')
	fieldsets = (
		(None, {
			'fields': (
				'user', 'birth_date', 'email', 'phone', 'image', 'eco_name',
			),
		}),
		('Telegram — согласование КП', {
			'fields': (
				'telegram_chat_id',
				'telegram_notify_pending',
				'telegram_notify_auto_approved',
				'telegram_notify_results',
			),
			'description': (
				'Привязка личного Telegram только здесь (админка) '
				'или на странице редактирования профиля пользователя. '
				'Chat ID — числовой Id из @userinfobot. '
				'Ниже — какие типы оповещений слать в бот.'
			),
		}),
		('Права и доступы', {
			'fields': (
				'view_checklist', 'edit_sms_opros',
				'eco', 'eco_visible', 'eco_page_price_info', 'eco_page_price_auto',
				'eco_toast', 'eco_chat_important', 'eco_price_increase',
				'eco_report',
				'korsavto_settings', 'korsavto_settings_dc', 'korsavto_auction',
				'korsavto_city', 'korsavto_stores', 'available_units',
				'user_sb',
				'price_car_new', 'price_car_new_director', 'price_car_new_all',
				'price_car_bu', 'price_car_new_settings', 'price_car_bu_settings',
				'estimation_settings', 'estimation_report',
			),
		}),
		('Служебное', {
			'classes': ('collapse',),
			'fields': ('current_session_key',),
		}),
	)

	def nameUser(self, obj):
		return mark_safe(u'%s %s' % (obj.user.first_name, obj.user.last_name))
	nameUser.short_description = 'Фамилия Имя'
