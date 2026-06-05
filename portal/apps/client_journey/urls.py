from django.urls import path

from client_journey import views

app_name = 'client_journey'

urlpatterns = [
    path('', views.presentation, name='presentation'),
    path('ceo/', views.ceo_presentation, name='ceo_presentation'),
    path('demo/', views.demo, name='demo'),
    path('c/<uuid:token>/', views.journey_by_token, name='journey'),
    path('preview/<int:rlk_id>/', views.preview_rlk, name='preview_rlk'),
    path('link/<int:rlk_id>/', views.create_link, name='create_link'),
]
