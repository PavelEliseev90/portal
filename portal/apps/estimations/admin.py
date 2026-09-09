from django.contrib import admin

from .models import EstimationBriefFactor


@admin.register(EstimationBriefFactor)
class EstimationBriefFactorAdmin(admin.ModelAdmin):
    list_display = ('label', 'key', 'group', 'weight', 'active', 'sort')
    list_editable = ('weight', 'active', 'sort')
    list_filter = ('group', 'active')
    search_fields = ('key', 'label', 'objection')
    ordering = ('sort', 'id')
