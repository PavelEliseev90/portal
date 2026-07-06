from django.urls import path

from auction_avito import views

app_name = 'auction_avito'

urlpatterns = [
    path('', views.lot_list, name='lot_list'),
    path('chat/send/', views.feed_chat_send, name='feed_chat_send'),
    path('buyout-recommendations/', views.buyout_recommendations, name='buyout_recommendations'),
    path('lots/<int:pk>/', views.lot_detail, name='lot_detail'),
    path('lots/<int:pk>/load-images/', views.lot_load_images, name='lot_load_images'),
    path('lots/<int:pk>/upload-images/', views.lot_upload_images, name='lot_upload_images'),
]
