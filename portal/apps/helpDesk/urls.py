
from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import  include, path
from helpDesk import views

urlpatterns = [

    path('',                views.task_list),
    path('task/<id>/',      views.task, name='id'),
]
