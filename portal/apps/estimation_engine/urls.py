from django.urls import path

from . import views

app_name = 'estimation_engine'

urlpatterns = [
    path('', views.settings_hub, name='settings_hub'),
    path('packages/', views.work_packages_list, name='work_packages_list'),
    path('packages/create/', views.work_package_create, name='work_package_create'),
    path('packages/<int:package_id>/edit/', views.work_package_edit, name='work_package_edit'),
    path('packages/<int:package_id>/delete/', views.work_package_delete, name='work_package_delete'),
    path('rules/', views.rules_list, name='rules_list'),
    path('rules/create/', views.rule_create, name='rule_create'),
    path('rules/<int:rule_id>/edit/', views.rule_edit, name='rule_edit'),
    path('rules/<int:rule_id>/delete/', views.rule_delete, name='rule_delete'),
    path('rules/preview/', views.rules_preview, name='rules_preview'),
    path('api/rules/preview/', views.rules_preview_api, name='rules_preview_api'),
    path('catalogs/', views.catalogs_hub, name='catalogs_hub'),
    path('catalogs/elements/', views.elements_list, name='elements_list'),
    path('catalogs/elements/sync/', views.sync_elements_from_polygons, name='sync_elements_from_polygons'),
    path('catalogs/damage-types/', views.damage_types_list, name='damage_types_list'),
]
