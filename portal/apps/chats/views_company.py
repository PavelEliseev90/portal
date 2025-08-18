from django.shortcuts import render
from .models import Chat, ChatMessage
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.db.models import Max, Subquery, OuterRef



def chats_list(request):
     
    user 	    = request.user
    chats       = Chat.objects.all()
    
    subqyery_message = Subquery(ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).annotate(max_date = Max('date')).values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    params = {
        'user'      : user,
        'chats'     : chats
    }
    return render(request, 'chats_company/chats_list.html', {'params': params})


def chats_company(request):
    user 	    = request.user
    chats       = Chat.objects.all()
    params = {
        'user'      : user,
        'chats'     : chats
    }
    return render(request, 'chats_company/chats.html', {'params': params})

def chats(request):
    user 	    = request.user
    chats       = Chat.objects.all()
    params = {
        'user'      : user,
        'chats'     : chats
    }
    return render(request, 'chats/chats.html', {'params': params})


def chat(request, slug):
   
    user 	    = request.user
    chat        = Chat.objects.get(pk = slug) 
    messages    = ChatMessage.objects.filter(chat = chat)[:25]
    params = {
        'user'      : user,
        'chat'      : chat,
        'messages'  : messages
    }
    return render(request, 'chats_company/chats.html', {'params': params})