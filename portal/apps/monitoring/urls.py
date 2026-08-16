from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.hub, name='hub'),
    path('exchange-errors/', views.exchange_errors_list, name='exchange_errors_list'),
    path('exchange-errors/purge/', views.exchange_errors_purge, name='exchange_errors_purge'),
    path('exchange-errors/<int:pk>/', views.exchange_errors_detail, name='exchange_errors_detail'),
    path('stores/', views.stores_list, name='stores_list'),
    path('stores/<int:pk>/clear-stock/', views.stores_clear_stock, name='stores_clear_stock'),
]
