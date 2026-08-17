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
    path('cars-photos/', views.cars_photos_list, name='cars_photos_list'),
    path('cars-photos/cleanup/', views.cars_photos_cleanup, name='cars_photos_cleanup'),
    path('cars-photos/enqueue-retries/', views.cars_photos_enqueue_retries, name='cars_photos_enqueue_retries'),
    path('cars-photos/<int:pk>/retry/', views.cars_photos_retry, name='cars_photos_retry'),
    path('cumulative-send/', views.cumulative_send_list, name='cumulative_send_list'),
    path('cumulative-send/send/', views.cumulative_send, name='cumulative_send'),
]
