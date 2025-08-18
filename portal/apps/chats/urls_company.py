from django.urls import path, include
from django.views.generic import TemplateView
from chats import views
from chats import views_company

app_name = 'chats'

urlpatterns = [
    
    path('chats_company/',          views_company.chats_company, name='chats_company'),
    path('',                        views.chats, name='chats'),
    path('<slug:slug>/',            views.chat, name='chat'),

    

]