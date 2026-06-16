# chat/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

from .models import Chat, ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        
        self.room_name          = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name    = 'chat_%s' % self.room_name
 
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
 
        await self.accept()
 
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
 
    async def channel_message(self, event):
        message = event['message']
        await self.receive(message)
        # Send message to WebSocket

    # Receive message from WebSocket
    async def receive(self, text_data):
        
        text_data_json  = json.loads(text_data)
        chat_id         = text_data_json['chat_id']
        name            = text_data_json['name']
        message         = text_data_json['message']
        username        = text_data_json['username']
        chat            = text_data_json['chat']
        last_name       = text_data_json['last_name']
        first_name      = text_data_json['first_name']
        psevdo_name     = text_data_json['psevdo_name']
        eco             = text_data_json['eco']
        skip_save       = text_data_json.get('skip_save', False)

        if chat_id != '' and not skip_save:
            await self.save_message(username, chat, message, chat_id)
        
        admin = False
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'chat_id'       : chat_id,
                'chat'          : chat,
                'admin'         : admin,
                'name'          : name,
                'type'          : 'chat_message',
                'message'       : message,
                'username'      : username,
                'last_name'     : last_name,
                'first_name'    : first_name,
                'psevdo_name'   : psevdo_name,
                'eco'           : eco
            }
        )
 
    # Receive message from room group
    async def chat_message(self, event):
        message     = event['message']
        username    = event['username']
        psevdo_name =  event['psevdo_name']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'chat_id'       : event['chat_id'],
            'chat'          : event['chat'],
            'admin'         : event['admin'],
            'name'          : event['name'],
            'message'       : message,
            'username'      : username,
            'last_name'     : event['last_name'],
            'first_name'    : event['first_name'],
            'psevdo_name'   : psevdo_name,
            'eco'           : event['eco']
        }))
   
    @sync_to_async
    def save_message(self, username, chat, message, chat_id):
        chat        = Chat.objects.get(pk = chat_id)
        user        = User.objects.get(username = username)
        ChatMessage.objects.create(user = user, chat = chat, content = message)
    