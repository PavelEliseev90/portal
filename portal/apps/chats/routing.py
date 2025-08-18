from django.urls import path
from . import consumers
from django.urls import re_path

'''
websocket_urlpatterns = [
    re_path('ws/<chat_name>/', consumers.ChatConsumer.as_asgi()),
]
'''

websocket_urlpatterns = [
    re_path(r'^ws/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
]