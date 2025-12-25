from django.urls import path, include
from django.views.generic import TemplateView
from avtosalon import views

app_name = 'avtosalon'

urlpatterns = [
   
   path('disposition/',                      views.disposition, name='disposition'),
   path('disposition/get_models/',           views.disposition_get_models, name='disposition_get_models'),
   path('catalog/',                          views.cars_catalog),
   path('catalog/<slug:mark_name_en>/',      views.catalog_mark, name='slug'),
   path('catalog/<slug:mark_name_en>/<slug:model_name>/',  views.catalog_model, name='slug'),
   
   path('',                                  views.cars),
   path('<slug>/specifications/',            views.specifications, name='slug'),
   path('<slug>/price_edit/',                views.price_edit, name='slug'),
   path('<slug>/info_js/',                   views.info_js, name='slug'),
   path('<slug>/',                           views.car, name='slug')
   
   #path('op/<slug:id>/<slug:pk>/', views.op_detail_recognition, name='slug'),
]