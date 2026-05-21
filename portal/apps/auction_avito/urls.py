from django.urls import path

from auction_avito import views

app_name = 'auction_avito'

urlpatterns = [
    path('', views.lot_list, name='lot_list'),
    path('lots/<int:pk>/', views.lot_detail, name='lot_detail'),
]
