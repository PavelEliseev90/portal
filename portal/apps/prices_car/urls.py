from django.urls import path
from . import views

app_name = 'prices_car'

urlpatterns = [
    path('', views.index, name='index'),
    path('director/', views.director_dashboard, name='director'),
    path('brands/', views.brands_list, name='brands'),
    path('settings/', views.settings_page, name='settings'),
    path('stage_km/', views.stage_km_page, name='stage_km'),
    path('discount_km/', views.discount_km_page, name='discount_km'),
]
