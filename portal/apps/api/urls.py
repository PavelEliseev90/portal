from django.urls import path, include
from django.views.generic import TemplateView
from api import views, views_avtosalon, views_catalog, views_mobile_android_api_v1
from rest_framework_swagger.views import get_swagger_view

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.routers import DefaultRouter





# swagger
schema_view = get_schema_view(
   openapi.Info(
      title="ILoveDjango",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

schema_view_v = get_swagger_view(title='KorsGroup API')
schema_view_v1 = get_swagger_view(title='KorsGroup API V1')

app_name = 'api'

urlpatterns = [


   path('post_info/',                         views.post_info),
   # API подготовки автомобилей (подключаем urls приложения)
   #path('car_preparation/', include('car_preparation.api_urls')),
   
   # мобильное приложение андроид версии 1
   path('a/v1/user_desctop/',                         views_mobile_android_api_v1.user_desctop),
   path('a/v1/list_cars_new_refresh/',                views_mobile_android_api_v1.list_cars_new_refresh),
   path('a/v1/login_in/',                             views_mobile_android_api_v1.login_in),
   path('a/v1/login_info/',                           views_mobile_android_api_v1.login_info),
   path('a/v1/rlk_eco/',                              views_mobile_android_api_v1.rlk_eco),
   path('a/v1/car/<slug:slug_car>/',                  views_mobile_android_api_v1.car, name='slug'),
   path('a/v1/staff_rlks_unit/',                      views_mobile_android_api_v1.staff_rlks_units),
   path('a/v1/staff_rlks_unit/<slug:slug_unit>/',     views_mobile_android_api_v1.staff_rlks_unit, name='slug'),
   path('a/v1/staff_rlk/<slug:slug_rlk>/',            views_mobile_android_api_v1.staff_rlk, name='slug'),
   path('a/v1/vin_estimation/<slug:vin>/',            views_mobile_android_api_v1.vin_estimation, name='slug'),
   path('a/v1/vin_repairs/<slug:vin>/',               views_mobile_android_api_v1.vin_repairs, name='slug'),
   path('a/v1/start_estimation/<slug:slug_rlk>/',                       views_mobile_android_api_v1.start_estimation, name='slug'),
   path('a/v1/start_estimation_modification/<slug:slug_rlk>/',          views_mobile_android_api_v1.start_estimation_modification, name='slug'),



   #Получаем данные для мобильной оценки
   path('a/v1/estimation_documents_start/<slug:slug_rlk>/',             views_mobile_android_api_v1.estimation_documents_start, name='slug'),
   path('a/v1/estimation_documents_post/<slug:slug_rlk>/',              views_mobile_android_api_v1.estimation_documents_post, name='slug'),
   path('a/v1/estimation_salon_post/<slug:slug_rlk>/',                  views_mobile_android_api_v1.estimation_salon_post, name='slug'),
   path('a/v1/estimation_vnesh_post/<slug:slug_rlk>/',                  views_mobile_android_api_v1.estimation_vnesh_post, name='slug'),
   path('a/v1/estimation_complectnost_post/<slug:slug_rlk>/',           views_mobile_android_api_v1.estimation_complectnost_post, name='slug'),
   path('a/v1/estimation_kolesa_post/<slug:slug_rlk>/',                 views_mobile_android_api_v1.estimation_kolesa_post, name='slug'),
   path('a/v1/estimation_test_drive_post/<slug:slug_rlk>/',             views_mobile_android_api_v1.estimation_test_drive_post, name='slug'),
   path('a/v1/estimation_proverki_post/<slug:slug_rlk>/',               views_mobile_android_api_v1.estimation_proverki_post, name='slug'),
   path('a/v1/estimation_soglasovanie_get/<slug:slug_rlk>/',            views_mobile_android_api_v1.estimation_soglasovanie_get, name='slug'), 
   path('a/v1/estimation_soglasovanie_post/<slug:slug_rlk>/',           views_mobile_android_api_v1.estimation_soglasovanie_post, name='slug'),


   path('a/v1/estimation_add_fotos/<slug:slug_rlk>/',              views_mobile_android_api_v1.estimation_add_fotos, name='slug'),

   #/<slug:id>/<slug:doc_id>/',    views.control_detail_doc, name='slug'

   path('catalogs/manufacturer/',   views_catalog.manufacturer),

   path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
   path('', schema_view_v), 

   #path('',                         views.versions),
   
   # Загрузка автомобилей организации
   path('v1/',                                  schema_view_v1),
   path('v1/refresh_cars/',                     views_avtosalon.refresh_cars),
   path('v1/post_image_autoru_mark/',           views_avtosalon.post_image_autoru_mark),
   path('v1/post_image_avito_mark/',            views_avtosalon.post_image_avito_mark),
   path('v1/info_cars_organization/',           views_avtosalon.info_cars_organization),
   path('v1/get_image_change/',                 views_avtosalon.get_image_change),
   path('v1/post_image_change/',                views_avtosalon.post_image_change),



   path('avtohub_info/',            views_avtosalon.avtohub_info),
   path('zna_info/',                views_avtosalon.zna_info),
   
   path('get_qrcode/',                                views.get_qrcode),
   path('specifications_refresh_info/',               views.specifications_refresh_info),
   path('options_refresh_info/',                      views.options_refresh_info),

   path('index/',                   views.index),
   # Временный обмен с корсавто
   path('refresh_rlk_bu/',          views.refresh_rlk_bu),
   path('get_info_estimation_vin/',  views.get_info_estimation_vin),
   #Обмен с 1С по формату общего модуля ОбменДаннымиAPI в 1С
   path('exchange/',                views.exchange),

   #Обмен с 1С по формату общего модуля ОбменДаннымиAPI в 1С КорсАвто
   path('exchange_bu/',                views.exchange_bu),
   
   #Работа с опросами
   path('create_opros/',            views.create_opros),
   path('create_opros_sale/',       views.create_opros_sale),
   path('create_opros_sale_bu/',    views.create_opros_sale_bu),
   path('refresh_opros/',           views.refresh_opros),
  
   #Работа с расширениями заказ - наряда (Тизер)
   path('recomendations_exchange/',      views.recomendations_exchange),
   
   # Конвертация аудио файлов с диктофона так как там уйня полная

   path('post_recordeds_voice_audio_portative_programm',       views.post_recordeds_voice_audio_portative_programm),
   path('get_recordeds_voice_audio_convert',                   views.get_recordeds_voice_audio_convert),
   path('post_recordeds_voice_audio_convert',                  views.post_recordeds_voice_audio_convert),
   path('post_recordeds_voice_audio_find',                     views.post_recordeds_voice_audio_find),

   # Функционал распознавания записи в текст
   path('get_recordeds_voice_audio/',               views.get_recordeds_voice_audio),
   path('post_recordeds_voice_audio/',              views.post_recordeds_voice_audio),
   
   # Функционал распознавания записи в текст из очереди
   path('get_records_queue/',                      views.get_records_queue),
   path('post_records_queue/',                     views.post_records_queue),

   # Функционал распознавания звонка в текст из очереди
   path('get_call_queue/',                      views.get_call_queue),
   path('post_call_queue/',                     views.post_call_queue),
   
   # Обновление каталогов для 1С
   path('catalog_mark',            views.catalog_mark),
   path('catalog_model',           views.catalog_model),
   path('catalog_modification',    views.catalog_modification),
   path('catalog_complectation',   views.catalog_complectation),
   path('catalog_modification_tech_info',   views.catalog_modification_tech_info),

   # Обновление ссылок на выгрузки автомобилей на сайты
   path('refresh_link_cars_exchange/',   views.refresh_link_cars_exchange),

   # Создание анкеты для онлайн записи
   path('create_online/',           views.create_online),
   
   # Создание документа подтверждения записи на сервис
   path('create_records_online_doc/',  views.create_records_online_doc),
   
   
   path('info_brand_article_shop_autoshina/',   views.info_brand_article_shop_autoshina),
   path('info_brand_article_emex/',             views.info_brand_article_emex),
   path('info_brand_article_emex_list/',        views.info_brand_article_emex_list),
   path('info_brand_article_image/',            views.info_brand_article_image),

   path('info_article/',                        views.get_info_article_product),
   path('info_articles/',                       views.get_info_article_products),

   
]