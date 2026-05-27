from django.urls import path

from . import views

app_name = 'prices_car_bu'

urlpatterns = [
    path('cumulative/', views.cumulative_list, name='cumulative_list'),
    path('cumulative/<int:pk>/', views.cumulative_detail, name='cumulative_detail'),
    path('cumulative/<int:pk>/delete/', views.cumulative_delete, name='cumulative_delete'),
]
