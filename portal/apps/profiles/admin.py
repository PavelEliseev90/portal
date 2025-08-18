from django.contrib import admin
from .models import Profiles
from django.utils.safestring import mark_safe


@admin.register(Profiles)
class ProfilesAdmin(admin.ModelAdmin):
	list_display 	= ( 'image_img', 'user', 'nameUser', 'birth_date', 'phone', 'email', 'eco_name', 'eco', 'eco_name', 'eco_visible', 'eco_page_price_info', 'korsavto_settings', )
	search_fields 	= ('user__last_name', 'user__first_name', )
	raw_id_fields 	= ('user',)
	list_filter 	= ('eco', 'eco_visible', 'eco_page_price_info', 'korsavto_settings',)
	
	def nameUser(self, obj):
		return mark_safe(u'%s %s' % (obj.user.first_name, obj.user.last_name))
	nameUser.short_description = 'Фамилия Имя'