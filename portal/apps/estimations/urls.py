from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('',                                                                    views.estimation),
    path('<slug:rlk_id>/start/',                                                views.estimation_start, name='slug'),
    path('<slug:rlk_id>/',                                                      views.estimation_rlk, name='slug'),
    path('<slug:rlk_id>/osmotr/<slug:type>/',                                   views.osmotr, name='slug'),
    path('<slug:rlk_id>/osmotr_salon/<slug:type>/',                             views.osmotr_salon, name='slug'),
    path('<slug:rlk_id>/s/',                                                    views.years, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/',                                       views.catalog, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/<slug:mark_id>/',                        views.models, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/<slug:mark_id>/<slug:model_id>/',        views.modifications, name='slug'),
    
    # API endpoints для новой страницы начала оценки
    path('<slug:rlk_id>/api/models/',                                          views.api_get_models_by_mark, name='api_models'),
    path('<slug:rlk_id>/api/years/',                                            views.api_get_years_by_model, name='api_years'),
    path('<slug:rlk_id>/api/modifications/',                                   views.api_get_modifications_by_model_year, name='api_modifications'),
    path('<slug:rlk_id>/api/complectations/',                                  views.api_get_complectations_by_modification, name='api_complectations'),
    path('<slug:rlk_id>/api/previous-estimation/',                             views.api_get_previous_estimation, name='api_previous_estimation'),
]
