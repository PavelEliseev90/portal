from django.urls import path
from . import views

app_name = 'changelog'

urlpatterns = [
    path('pageview-dashboard/', views.pageview_dashboard, name='pageview_dashboard'),
]
