from django.urls import path
from django.views.generic import TemplateView
from profiles import views

app_name = 'profiles'

urlpatterns = [ 
    path('',  views.profiles_edit),
    
]
