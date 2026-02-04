from django.urls import path
from . import views

app_name = 'register'

urlpatterns = [
    path('diagnostic_reference/', views.diagnostic_reference_api, name='diagnostic_reference_api'),
    path('diagnostic_reference/stats/', views.diagnostic_reference_stats, name='diagnostic_reference_stats'),
]

