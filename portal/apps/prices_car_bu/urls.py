from django.urls import path

from . import views

app_name = 'prices_car_bu'

urlpatterns = [
    path('cumulative/', views.cumulative_list, name='cumulative_list'),
    path('cumulative/send-1c/', views.cumulative_send_1c_batch, name='cumulative_send_1c_batch'),
    path('cumulative/set-send-1c/', views.cumulative_set_send_1c_flag, name='cumulative_set_send_1c_flag'),
    path('cumulative/<int:pk>/', views.cumulative_detail, name='cumulative_detail'),
    path('cumulative/<int:pk>/delete/', views.cumulative_delete, name='cumulative_delete'),
    path('cumulative/<int:pk>/send-1c/', views.cumulative_send_1c, name='cumulative_send_1c'),
]
