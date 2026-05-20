from django.urls import path, include
from django.views.generic import TemplateView
from asp import views

app_name = 'asp'

urlpatterns = [
   
   path('',    views.asp, name='asp'),
   
]