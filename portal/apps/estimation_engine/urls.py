from django.urls import path

from . import catalog_search
from . import views
from . import views_prep_catalogs

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

    # AJAX Select2
    path('api/catalog/works/', catalog_search.search_works, name='api_search_works'),
    path('api/catalog/materials/', catalog_search.search_materials, name='api_search_materials'),
    path('api/catalog/parts/', catalog_search.search_parts, name='api_search_parts'),
    path('api/catalog/services/', catalog_search.search_services, name='api_search_services'),
    path('api/catalog/service-offerings/', catalog_search.search_service_offerings, name='api_search_offerings'),
    path('api/catalog/providers/', catalog_search.search_providers, name='api_search_providers'),
    path('api/catalog/packages/', catalog_search.search_packages, name='api_search_packages'),

    path('catalogs/', views.catalogs_hub, name='catalogs_hub'),
    path('catalogs/elements/', views.elements_list, name='elements_list'),
    path('catalogs/elements/sync/', views.sync_elements_from_polygons, name='sync_elements_from_polygons'),
    path('catalogs/damage-types/', views.damage_types_list, name='damage_types_list'),
    path('catalogs/damage-types/create/', views.damage_type_create, name='damage_type_create'),
    path('catalogs/damage-types/<int:item_id>/edit/', views.damage_type_edit, name='damage_type_edit'),
    path('catalogs/damage-types/<int:item_id>/delete/', views.damage_type_delete, name='damage_type_delete'),
    path('catalogs/info-body/', views.info_body_list, name='info_body_list'),
    path('catalogs/info-body/create/', views.info_body_create, name='info_body_create'),
    path('catalogs/info-body/<int:item_id>/edit/', views.info_body_edit, name='info_body_edit'),
    path('catalogs/info-body/<int:item_id>/delete/', views.info_body_delete, name='info_body_delete'),

    # Справочники подготовки
    path('catalogs/works/', views_prep_catalogs.works_list, name='works_list'),
    path('catalogs/works/create/', views_prep_catalogs.work_create, name='work_create'),
    path('catalogs/works/<int:item_id>/edit/', views_prep_catalogs.work_edit, name='work_edit'),
    path('catalogs/materials/', views_prep_catalogs.materials_list, name='materials_list'),
    path('catalogs/parts/', views_prep_catalogs.parts_list, name='parts_list'),
    path('catalogs/parts/create/', views_prep_catalogs.part_create, name='part_create'),
    path('catalogs/parts/<int:item_id>/edit/', views_prep_catalogs.part_edit, name='part_edit'),
    path('catalogs/services/', views_prep_catalogs.services_list, name='services_list'),
    path('catalogs/services/create/', views_prep_catalogs.service_create, name='service_create'),
    path('catalogs/services/<int:item_id>/edit/', views_prep_catalogs.service_edit, name='service_edit'),
    path('catalogs/providers/', views_prep_catalogs.providers_list, name='providers_list'),
    path('catalogs/providers/create/', views_prep_catalogs.provider_create, name='provider_create'),
    path('catalogs/providers/<int:item_id>/edit/', views_prep_catalogs.provider_edit, name='provider_edit'),
]
