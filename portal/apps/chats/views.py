from django.shortcuts import render
from .models import Chat, ChatMessage
import uuid
from django.conf import settings
from datetime import datetime, timedelta
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse


def chats_company(request):
    user 	    = request.user
    chats       = Chat.objects.all()
    params = {
        'user'      : user,
        'chats'     : chats
    }
    return render(request, 'chats_company/chats.html', {'params': params})

def chats(request):
    response = render(request, 'chats/chat.html')
    user 	    = request.user
    chats       = Chat.objects.filter(user = user)
    params = {
        'user'      : user,
        'chats'     : chats
    }
    return render(request, 'chats/chats.html', {'params': params})


def chat(request, slug):

    
    response = render(request, 'chats/chat.html')
    
    if request.method == 'POST':
        if 'name_ok' in request.POST:
            name = request.POST.get('name', '')
            return HttpResponseRedirect(request.build_absolute_uri())

    chat_count  = Chat.objects.filter(slug=slug).count()
    if chat_count == 0:
        chat            = Chat()
        chat.name       = 'name'
        chat.slug       = slug
        chat.user       = request.user
        chat.save()
    else:
        chat = Chat.objects.filter(slug=slug)[0] 
    messages    = ChatMessage.objects.filter(chat = chat)[:25]
    params = {
        'user'      : request.user,
        'chat'      : chat,
        'messages'  : messages
    }
    return render(request, 'chats/chat.html', {'params': params})