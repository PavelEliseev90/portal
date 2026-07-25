from django.urls import path

from auction_avito import views

app_name = 'auction_avito'

urlpatterns = [
    path('', views.lot_list, name='lot_list'),
    path('monitor/', views.monitor, name='monitor'),
    path('monitor/data/', views.monitor_data, name='monitor_data'),
    path('monitor/set-manual-max/', views.monitor_set_manual_max, name='monitor_set_manual_max'),
    path('monitor/hand-to-work/', views.monitor_hand_to_work, name='monitor_hand_to_work'),
    path('chat/send/', views.feed_chat_send, name='feed_chat_send'),
    path('chat/messages/', views.feed_chat_messages, name='feed_chat_messages'),
    path('buyout-recommendations/', views.buyout_recommendations, name='buyout_recommendations'),
    path('analytics/', views.analytics, name='analytics'),
    path('loss-report/', views.loss_report, name='loss_report'),
    path('settings/', views.auction_settings, name='auction_settings'),
    path('lots/<int:pk>/', views.lot_detail, name='lot_detail'),
    path('lots/<int:pk>/chat/send/', views.lot_chat_send, name='lot_chat_send'),
    path('lots/<int:pk>/load-images/', views.lot_load_images, name='lot_load_images'),
    path('lots/<int:pk>/upload-images/', views.lot_upload_images, name='lot_upload_images'),
]
