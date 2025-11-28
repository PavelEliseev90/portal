from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import include, path
from helpDesk import views

app_name = 'helpdesk'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tasks/', views.task_list, name='task_list'),
    path('task/<int:pk>/', views.task_detail, name='task_detail'),
    path('task/create/', views.task_create, name='task_create'),
    path('task/quick-create/', views.task_quick_create, name='task_quick_create'),
    path('task/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:pk>/comment/', views.task_add_comment, name='task_add_comment'),
    path('task/<int:pk>/attachment/', views.task_add_attachment, name='task_add_attachment'),
    path('task/<int:pk>/quick-status/', views.task_quick_status_change, name='task_quick_status_change'),
    path('task/<int:pk>/duplicate/', views.task_duplicate, name='task_duplicate'),
    path('calendar/', views.calendar, name='calendar'),
    path('chart/', views.chart, name='chart'),
    path('export/', views.export_tasks, name='export_tasks'),
    path('autocomplete/', views.task_autocomplete, name='task_autocomplete'),
    path('filter/save/', views.save_filter, name='save_filter'),
    path('filter/<int:filter_id>/delete/', views.delete_saved_filter, name='delete_saved_filter'),
    path('task/<int:pk>/reminder/add/', views.add_deadline_reminder, name='add_deadline_reminder'),
    path('task/<int:pk>/reminder/<int:reminder_id>/delete/', views.delete_deadline_reminder, name='delete_deadline_reminder'),
]
