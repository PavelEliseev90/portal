from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'online'

urlpatterns = [
    path('s/<id>/',     views.record_service,   name='id'),
    path('<id>/',       views.online,           name='id'),
    path('consent/<str:token>/', views.personal_data_consent, name='personal_data_consent'),
]
