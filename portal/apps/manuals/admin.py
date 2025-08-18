from django.contrib import admin
from .models import ManualsTag, Manuals


@admin.register(ManualsTag)
class ManualsTagAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Manuals)
class ManualsAdmin(admin.ModelAdmin):
    list_display = ('activated', 'author', 'title', 'dateUpdate',)
    list_filter = ('dateUpdate', 'activated','tags',)
    