from django.urls import path
from . import views

app_name = 'prices_car'

urlpatterns = [
    path('', views.index, name='index'),
    path('director/', views.director_dashboard, name='director'),
    path('director/kp/', views.new_cars_director_desktop, name='new_cars_director_desktop'),
    path('director/kp/<slug:section>/', views.new_cars_director_desktop_list, name='new_cars_director_desktop_list'),
    path('calculations_list/', views.calculations_list, name='calculations_list'),
    path('calculations_list/export/', views.calculations_list_export, name='calculations_list_export'),
    path('calculations_list/columns/', views.calculations_list_columns_save, name='calculations_list_columns_save'),
    path('brands/', views.brands_list, name='brands'),
    path('brands/get_models/', views.brands_get_models, name='brands_get_models'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/preview/', views.settings_km_preview, name='settings_km_preview'),
    path('stage_km/', views.stage_km_page, name='stage_km'),
    path('discount_km/', views.discount_km_page, name='discount_km'),
    path('discount_km/get_models/', views.discount_get_models, name='discount_get_models'),
    path('discount_km/get_modifications/', views.discount_get_modifications, name='discount_get_modifications'),
    path('discount_km/get_complectations/', views.discount_get_complectations, name='discount_get_complectations'),
    path('presentation/', views.presentation_page, name='presentation'),
    path('presentation/<path:asset>', views.presentation_asset, name='presentation_asset'),
    path('km-lab/', views.km_calculator_lab, name='km_calculator_lab'),
]
