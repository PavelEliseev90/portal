from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('',                                                                    views.estimation),
    path('<slug:rlk_id>/',                                                      views.estimation_rlk, name='slug'),
    path('<slug:rlk_id>/osmotr/<slug:type>/',                                   views.osmotr, name='slug'),
    path('<slug:rlk_id>/s/',                                                    views.years, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/',                                       views.catalog, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/<slug:mark_id>/',                        views.models, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/<slug:mark_id>/<slug:model_id>/',        views.modifications, name='slug'),
]
