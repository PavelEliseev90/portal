from django.urls import path
from asp import views

app_name = 'asp'

urlpatterns = [
    path('', views.asp, name='asp'),
    path(
        'reports/cumulative-margin/',
        views.cumulative_margin_report,
        name='cumulative_margin_report',
    ),
    path(
        'reports/stock/',
        views.stock_report,
        name='stock_report',
    ),
    path(
        'reports/accepted/',
        views.accepted_report,
        name='accepted_report',
    ),
]
