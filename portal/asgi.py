"""
ASGI config for portal project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')


django.setup()


from chats import consumers


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        #URLRouter(chat.routing.websocket_urlpatterns)
        URLRouter(
            [
                re_path(r'^ws/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
            ]
                
        )    
    ),
})