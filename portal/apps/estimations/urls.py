from django.urls import path
from . import views
from . import views_kolesa_reception
from . import views_osmotr_test

app_name = 'eco'

urlpatterns = [

    path('1c/<str:staff_uin>/<str:rlk_uin>/',                                  views.estimation_1c_entry, name='estimation_1c'),
    path('1c/<str:staff_uin>/<str:rlk_uin>/start/',                             views.estimation_1c_entry, {'force_start': True}, name='estimation_1c_start'),

    path('kolesa-reception/',                                                   views_kolesa_reception.kolesa_reception_list, name='kolesa_reception_list'),
    path('kolesa-reception/create/<int:estimation_id>/',                        views_kolesa_reception.kolesa_reception_create, name='kolesa_reception_create'),
    path('kolesa-reception/<int:reception_id>/',                                views_kolesa_reception.kolesa_reception_detail, name='kolesa_reception_detail'),

    # Тестовый UI осмотра кузова (не трогает legacy osmotr)
    path('osmotr-test/',                                                       views_osmotr_test.osmotr_body_test, {'side': 'pered'}, name='osmotr_body_test'),
    path('osmotr-test/<slug:side>/',                                           views_osmotr_test.osmotr_body_test, name='osmotr_body_test_side'),
    path('<slug:rlk_id>/<slug:rl_id>/osmotr-test/<slug:side>/',                views_osmotr_test.osmotr_body_test, name='osmotr_body_test_est'),

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
