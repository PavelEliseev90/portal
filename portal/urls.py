"""portal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import  include, path, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static


handler404 = 'website.views.custom_page_not_found_view'
handler400 = 'website.views.custom_bad_request_view'
handler500 = 'website.views.custom_error_view'
handler403 = 'website.views.custom_permission_denied_view'

urlpatterns = [
    
    #path('', TemplateView.as_view(template_name = 'login.html')),
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}), 
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}), 
    re_path(r'^media_dop/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT_DOP}),

    #АПИ
    path('api/',        include('api.urls')),
    path('chats/',      include('chats.urls')),
    #PowerBI
    path('powerbi/',    include('powerbi.urls')),
    
    #Подготовка и работы по авто
    
    path('car_preparation/',    include('car_preparation.urls')),

    #PowerBI
    path('checklists/',    include('checklists.urls')),

    #Веб - сайт
    path('',            include('website.urls')),
    
    #Инструкции и документация
    path('manuals/',    include('manuals.urls')),

    path('ckeditor/',   include('ckeditor_uploader.urls')),

    #онлайн запись на сервис
    path('online/',     include('online.urls')),
    
    #подтверждение записи на сервис
    path('r_s/',        include('online.urls')),

    #recognitions
    path('recognitions/', include('recognition.urls')),
    
    #help desk
    path('help_desk/',   include('helpDesk.urls')),

    #автосалон 
    path('cars/',            include('avtosalon.urls')),
    path('catalog/',         include('avtosalon.urls')),

    #cvc
    path('profiles_edit/',  include('profiles.urls')),

       #телефония
    path('telephony/',      include('telephony.urls')),

    path('eco/',                include('eco.urls')),
    path('eco_monitors/',       include('eco.urls')),

    path('ecot/',               include('eco.urls')),

    path('estimations/',        include('estimations.urls')),


]
