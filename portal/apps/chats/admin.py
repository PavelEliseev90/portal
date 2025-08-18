from django.contrib import admin
from django.contrib import admin
from .models import Chat, ChatMessage


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display    = ('name', 'user',)
    raw_id_fields   = ('user', )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display    = ('chat', 'date', 'user', 'content',)
    raw_id_fields   = ('chat', )
    