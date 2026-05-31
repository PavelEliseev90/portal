from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.hub, name='hub'),
    path('exchange-errors/', views.exchange_errors_list, name='exchange_errors_list'),
    path('exchange-errors/<int:pk>/', views.exchange_errors_detail, name='exchange_errors_detail'),
]
