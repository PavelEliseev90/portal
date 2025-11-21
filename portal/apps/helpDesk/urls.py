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
    path('task/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:pk>/comment/', views.task_add_comment, name='task_add_comment'),
    path('calendar/', views.calendar, name='calendar'),
    path('chart/', views.chart, name='chart'),
]
