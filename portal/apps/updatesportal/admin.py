from django.contrib import admin
from .models import UpdatesportalTag, Updatesportal


@admin.register(UpdatesportalTag)
class UpdatesportalTagAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Updatesportal)
class UpdatesportalAdmin(admin.ModelAdmin):
    list_display = ('activated','author', 'title', 'dateUpdate',)
    list_filter = ('dateUpdate', 'activated','tags',)