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
    path(
        'reports/columns/',
        views.report_columns_save,
        name='report_columns_save',
    ),
    path(
        'reports/saved-filters/save/',
        views.report_saved_filter_save,
        name='report_saved_filter_save',
    ),
    path(
        'reports/saved-filters/<int:filter_id>/delete/',
        views.report_saved_filter_delete,
        name='report_saved_filter_delete',
    ),
]
