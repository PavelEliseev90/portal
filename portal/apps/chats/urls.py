from django.urls import path, include, re_path
from django.views.generic import TemplateView
from chats import views
from chats import views_company

app_name = 'chats'

urlpatterns = [
    
    #path('c/a/r/<slug:slug>',           views_company.chat,      name='chats_company'),
    #path('c/a/edit',                    views_company.chats_select_cookie, name='chats_select_cookie'),
    #path('c/a/edit/<slug:slug>',        views_company.chats_select_cookie_edit, name='chats_select_cookie_edit'),
    #path('c/a/r',                       views_company.chats_list, name='chats_list'),

    path('',                        views.chats, name='chats'),
    path('<slug:slug>/',            views.chat, name='chat'),

    

]