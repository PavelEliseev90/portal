from django.urls import path
from . import views

app_name = 'classifieds'

urlpatterns = [
    path('', views.classifieds_list, name='list'),
    path('config/create/', views.classifieds_config_create, name='config_create'),
    path('config/<int:config_id>/', views.classifieds_config_detail, name='config_detail'),
    path('config/<int:config_id>/edit/', views.classifieds_config_edit, name='config_edit'),
    path('config/<int:config_id>/export/', views.classifieds_export_run, name='export_run'),
    path('config/<int:config_id>/preview/', views.classifieds_preview_cars, name='preview_cars'),
    path('history/', views.classifieds_export_history, name='export_history'),
    path('history/<int:history_id>/', views.classifieds_export_history_detail, name='export_history_detail'),
    path('history/<int:history_id>/download/', views.classifieds_export_download, name='export_download'),
]

