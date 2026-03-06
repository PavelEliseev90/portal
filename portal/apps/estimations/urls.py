from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('',                                                                    views.estimation),
    path('<slug:rlk_id>/',                                                      views.estimation_rlk, name='slug'),
    path('<slug:rlk_id>/start/',                                                views.estimation_start, name='slug'),
    path('<slug:rlk_id>/<slug:rl_id>/osmotr/<slug:type>/',                      views.osmotr, name='slug'),
    path('<slug:rlk_id>/<slug:rl_id>/osmotr_salon/<slug:type>/',                views.osmotr_salon, name='slug'),
    path('<slug:rlk_id>/s/',                                                    views.years, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/',                                       views.catalog, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/<slug:mark_id>/',                        views.models, name='slug'),
    path('<slug:rlk_id>/s/<slug:years>/<slug:mark_id>/<slug:model_id>/',        views.modifications, name='slug'),
    
    # API endpoints для новой страницы начала оценки
    path('<slug:rlk_id>/api/marks/',                                           views.api_get_marks_by_year, name='api_marks'),
    path('<slug:rlk_id>/api/models/',                                          views.api_get_models_by_mark, name='api_models'),
    path('<slug:rlk_id>/api/body-types/',                                      views.api_get_body_types_by_model, name='api_body_types'),
    path('<slug:rlk_id>/api/engine-types/',                                    views.api_get_engine_types_by_model, name='api_engine_types'),
    path('<slug:rlk_id>/api/kpp-types/',                                       views.api_get_kpp_types_by_model, name='api_kpp_types'),
    path('<slug:rlk_id>/api/modifications/',                                   views.api_get_modifications_by_model_year, name='api_modifications'),
    path('<slug:rlk_id>/api/complectations/',                                  views.api_get_complectations_by_modification, name='api_complectations'),
    path('<slug:rlk_id>/api/complectation-options/',                           views.api_get_complectation_options, name='api_complectation_options'),
    path('<slug:rlk_id>/api/previous-estimation/',                             views.api_get_previous_estimation, name='api_previous_estimation'),
    path('<slug:rlk_id>/api/repair-history/',                                 views.api_get_repair_history, name='api_repair_history'),
    path('<slug:rlk_id>/api/estimation-history/',                             views.api_get_estimation_history, name='api_estimation_history'),
]
