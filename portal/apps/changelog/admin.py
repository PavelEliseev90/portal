from django.contrib import admin
from .models import ChangeLog, PageViewLog


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
  list_display      = ('changed', 'model', 'user', 'record_id', 'data', 'ipaddress', 'action_on_model',)
  readonly_fields   = ('user', )
  list_filter       = ('model', 'action_on_model',)
  search_fields     = ('record_id',)


@admin.register(PageViewLog)
class PageViewLogAdmin(admin.ModelAdmin):
  list_display      = ('created', 'user', 'device_type', 'session_key', 'path', 'method', 'status_code', 'ip')
  list_filter       = ('method', 'device_type', 'created')
  search_fields     = ('path', 'path_full', 'user_agent')
  readonly_fields   = ('user', 'session_key', 'path', 'path_full', 'method', 'status_code', 'ip', 'device_type', 'user_agent', 'created')
  date_hierarchy    = 'created'
