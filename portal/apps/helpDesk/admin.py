from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import TaskStatus, Priority, ProjectTag, HelpDeskTask, TaskComment, TaskAttachment, TaskHistory


@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color_display', 'order', 'is_closed', 'is_active']
    list_editable = ['order', 'is_closed', 'is_active']
    list_filter = ['is_closed', 'is_active']
    search_fields = ['name', 'code']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Цвет'


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'level', 'color_display']
    list_editable = ['level']
    search_fields = ['name', 'code']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Цвет'


@admin.register(ProjectTag)
class ProjectTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color_display', 'order', 'is_active', 'tasks_count']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'date_created']
    search_fields = ['name', 'code', 'description']
    fields = ('name', 'code', 'description', 'color', 'order', 'is_active', 'date_created')
    readonly_fields = ['date_created']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Цвет'
    
    def tasks_count(self, obj):
        return obj.tasks.filter(is_deleted=False).count()
    tasks_count.short_description = 'Количество задач'


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ['author', 'date_created', 'date_updated']
    fields = ['author', 'text', 'is_internal', 'date_created']


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ['uploaded_by', 'date_uploaded', 'file_size']
    fields = ['file', 'original_filename', 'uploaded_by', 'date_uploaded']


class TaskHistoryInline(admin.TabularInline):
    model = TaskHistory
    extra = 0
    readonly_fields = ['user', 'action', 'field_name', 'old_value', 'new_value', 'date_created']
    can_delete = False


@admin.register(HelpDeskTask)
class HelpDeskTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'title_short', 'author', 'assignee', 'status_display', 
                   'priority_display', 'date_created', 'date_deadline', 'is_overdue_display']
    list_filter = ['status', 'priority', 'date_created', 'is_deleted']
    search_fields = ['title', 'description', 'author__username', 'assignee__username']
    readonly_fields = ['date_created', 'date_updated', 'id']
    filter_horizontal = ['observers', 'projects']
    inlines = [TaskCommentInline, TaskAttachmentInline, TaskHistoryInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'title', 'description', 'tags')
        }),
        ('Участники', {
            'fields': ('author', 'assignee', 'observers')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority')
        }),
        ('Временные рамки', {
            'fields': ('date_created', 'date_updated', 'date_start', 'date_deadline', 
                      'date_closed', 'estimated_time', 'actual_time')
        }),
        ('Проекты и теги', {
            'fields': ('projects', 'tags')
        }),
        ('Дополнительно', {
            'fields': ('is_deleted',)
        }),
    )

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Заголовок'

    def status_display(self, obj):
        if obj.status:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
                obj.status.color, obj.status.name
            )
        return '-'
    status_display.short_description = 'Статус'

    def priority_display(self, obj):
        if obj.priority:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
                obj.priority.color, obj.priority.name
            )
        return '-'
    priority_display.short_description = 'Приоритет'

    def is_overdue_display(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: red;">⚠ Просрочена</span>')
        return '-'
    is_overdue_display.short_description = 'Просрочка'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'task_link', 'author', 'text_short', 'date_created', 'is_internal']
    list_filter = ['date_created', 'is_internal', 'is_deleted']
    search_fields = ['text', 'task__title', 'author__username']
    readonly_fields = ['date_created', 'date_updated']

    def task_link(self, obj):
        url = reverse('admin:helpDesk_helpdesktask_change', args=[obj.task.pk])
        return format_html('<a href="{}">Задача #{}</a>', url, obj.task.pk)
    task_link.short_description = 'Задача'

    def text_short(self, obj):
        text = str(obj.text).replace('<p>', '').replace('</p>', '')
        return text[:50] + '...' if len(text) > 50 else text
    text_short.short_description = 'Текст'


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'task_link', 'original_filename', 'file_size_display', 
                   'uploaded_by', 'date_uploaded']
    list_filter = ['date_uploaded']
    search_fields = ['original_filename', 'task__title']
    readonly_fields = ['date_uploaded', 'file_size']

    def task_link(self, obj):
        url = reverse('admin:helpDesk_helpdesktask_change', args=[obj.task.pk])
        return format_html('<a href="{}">Задача #{}</a>', url, obj.task.pk)
    task_link.short_description = 'Задача'

    def file_size_display(self, obj):
        size = obj.file_size
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"
    file_size_display.short_description = 'Размер'


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'task_link', 'user', 'action', 'field_name', 'date_created']
    list_filter = ['action', 'date_created']
    search_fields = ['task__title', 'action', 'user__username']
    readonly_fields = ['task', 'user', 'action', 'field_name', 'old_value', 
                      'new_value', 'date_created', 'comment']

    def task_link(self, obj):
        url = reverse('admin:helpDesk_helpdesktask_change', args=[obj.task.pk])
        return format_html('<a href="{}">Задача #{}</a>', url, obj.task.pk)
    task_link.short_description = 'Задача'
