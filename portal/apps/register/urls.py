from django.urls import path
from . import views
from . import views_repricing

app_name = 'register'

urlpatterns = [
    path('diagnostic_reference/', views.diagnostic_reference_api, name='diagnostic_reference_api'),
    path('diagnostic_reference/stats/', views.diagnostic_reference_stats, name='diagnostic_reference_stats'),
    
    # Переоценка автомобилей
    path('repricing/', views_repricing.repricing_list, name='repricing_list'),
    path('repricing/units/', views_repricing.repricing_units, name='repricing_units'),
    path('repricing/run/', views_repricing.repricing_run, name='repricing_run'),
    path('repricing/run/<int:unit_id>/', views_repricing.repricing_run, name='repricing_run_unit'),
    path('repricing/history/<int:history_id>/', views_repricing.repricing_history_detail, name='repricing_history_detail'),
    path('repricing/preview/', views_repricing.repricing_preview_cars, name='repricing_preview_cars'),
    path('repricing/preview/<int:unit_id>/', views_repricing.repricing_preview_cars, name='repricing_preview_cars_unit'),
]

