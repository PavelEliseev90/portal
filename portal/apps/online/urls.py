# from django.urls import path
# from . import views
# from django.views.generic import TemplateView

# app_name = 'online'

# urlpatterns = [
#     path('estimate/<slug:slug>/', views.user_car_estimation, name='user_car_estimation'),
#     path('estimate/<slug:slug>/api/marks/', views.user_estimation_api_marks, name='user_estimation_api_marks'),
#     path('estimate/<slug:slug>/api/models/', views.user_estimation_api_models, name='user_estimation_api_models'),
#     path('estimate/<slug:slug>/api/modifications/', views.user_estimation_api_modifications, name='user_estimation_api_modifications'),
#     path('estimate/<slug:slug>/api/complectations/', views.user_estimation_api_complectations, name='user_estimation_api_complectations'),
    
#     path('s/<id>/',     views.record_service,   name='id'),
    
#     path('<id>/',       views.online,           name='id'),
    
#     path('consent/<str:token>/', views.personal_data_consent, name='personal_data_consent'),
# ]

from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'online'

urlpatterns = [
    path('s/<id>/',     views.record_service,   name='id'),
    path('estimate/<slug:slug>/', views.user_car_estimation, name='user_car_estimation'),
    path('estimate/<slug:slug>/year/', views.user_car_estimation_year, name='user_car_estimation_year'),
    path('estimate/<slug:slug>/mark/', views.user_car_estimation_mark, name='user_car_estimation_mark'),
    path('estimate/<slug:slug>/model/', views.user_car_estimation_model, name='user_car_estimation_model'),
    path('estimate/<slug:slug>/modification/', views.user_car_estimation_modification, name='user_car_estimation_modification'),
    path('estimate/<slug:slug>/complectation/', views.user_car_estimation_complectation, name='user_car_estimation_complectation'),
    path('estimate/<slug:slug>/details/', views.user_car_estimation_details, name='user_car_estimation_details'),
    path('estimate/<slug:slug>/api/marks/', views.user_estimation_api_marks, name='user_estimation_api_marks'),
    path('estimate/<slug:slug>/api/models/', views.user_estimation_api_models, name='user_estimation_api_models'),
    path('estimate/<slug:slug>/api/modifications/', views.user_estimation_api_modifications, name='user_estimation_api_modifications'),
    path('estimate/<slug:slug>/api/complectations/', views.user_estimation_api_complectations, name='user_estimation_api_complectations'),
    path('<id>/',       views.online,           name='id'),
    path('consent/<str:token>/', views.personal_data_consent, name='personal_data_consent'),
]
