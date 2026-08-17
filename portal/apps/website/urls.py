from django.urls import path, include
from django.views.generic import TemplateView
from website import views

app_name = 'website'

urlpatterns = [
   
   #path('',                TemplateView.as_view(template_name = 'login.html')),
   
   path('',                   views.start),
   path('login/',             views.loging),
   path('logout/',            views.logout),
   
   path('es/<slug:slug>/',       views.customer_est_es_redirect, name='customer_est_es_redirect'),
   path('est/<slug:slug>/',      views.customer_est, name='slug'),
   path('stok_im/',              views.stok_im_dashboard, name='stok_im'),
   path('stok_im/list/',         views.stok_im, name='stok_im_list'),
   path('stok_im/sync_log/',     views.stok_im_sync_log, name='stok_im_sync_log'),
   path('stok_im/activity/',     views.stok_im_user_activity, name='stok_im_user_activity'),
   path('stok_im/sync_run/',     views.stok_im_sync_run, name='stok_im_sync_run'),
   path('stok_im/sync_photos/', views.stok_im_sync_photos, name='stok_im_sync_photos'),
   path('stok_im/sync_photos/stream/', views.stok_im_sync_photos_stream, name='stok_im_sync_photos_stream'),
   path('stok_im/product/',      views.product, name='stok_im_product'),
   path('stok_im/product/photo/<int:photo_id>/delete/', views.product_photo_delete, name='stok_im_product_photo_delete'),

   path('auction/',                          views.auction_list),
   path('auction/new_lots/',                                   views.auction_doc_new),
   path('auction/<uuid:slug_auction>/auction_doc_refresh/',    views.auction_doc_refresh, name='slug'),
   path('auction/<uuid:slug_auction>/',                        views.auction_doc, name='slug'),
   path('auction/js/get_cars_lot_online/',                     views.auction_doc_get_cars),
   path('auction/js/get_cars_lot_online/<slug:slug>/',         views.auction_doc_get_cars_info, name='slug'),

   path('service/<id>/',         views.service_new, name='id'),
   path('s/<id>/',               views.service_new, name='id'),
   
   path('sale/<id>/',            views.sale, name='id'),
   path('dashboard_sms_opros/',  views.dashboard_sms_opros),
   
   path('sb_lo/',                views.sb_lo),
   # Мониторинг
   path('monitorings/',             views.board_monitoring),
   path('monitorings_eco/',         views.board_monitoring_eco),
   path('monitorings/exchange-testing/', views.board_exchange_testing, name='board_exchange_testing'),
   path('monitorings/queue/<str:kind>/', views.board_monitoring_queue, name='board_monitoring_queue'),
   path('monitorings/queue/<str:kind>/dismiss/', views.board_monitoring_queue_dismiss, name='board_monitoring_queue_dismiss'),
   path('monitorings/queue/send_1c/send/', views.board_monitoring_queue_send_1c, name='board_monitoring_queue_send_1c'),
   path(
       'monitorings/sync_tradeinfunnel/',
       views.board_monitoring_sync_tradeinfunnel,
       name='board_monitoring_sync_tradeinfunnel',
   ),

   # Справочники
   path('refs/',                 views.refs),
   
   path('settings/',                                        views.settings_),
   path('settings/settings_matrix_auction/',                views.settings_matrix_auction),
   path('settings/settings_diagnostic/',                    views.settings_diagnostic),
   path('settings/settings_diagnostic_reference/',          views.settings_diagnostic_reference),
   path('settings/settings_body_ref_replace/',              views.settings_body_ref_replace, name='settings_body_ref_replace'),
   path('settings/settings_body_type_groups/',              views.settings_body_type_groups, name='settings_body_type_groups'),
   path('settings/settings_vnesh/',                         views.settings_vnesh),
   path('settings/settings_works/',                         views.settings_works),
   path('settings/settings_works/export/',                views.settings_works_export, name='settings_works_export'),
   path('settings/settings_vnesh/export/',                views.settings_vnesh_works_export, name='settings_vnesh_works_export'),
   path('settings/settings_unit_groups/',                   views.settings_unit_groups),
   path('settings/settings_unit_groups/<int:group_id>/units/', views.settings_unit_group_units),
   path('settings/settings_autopricing_korsavto/',          views.settings_autopricing_korsavto_units, name='settings_autopricing_korsavto_units'),
   path('settings/settings_autopricing_korsavto/table/',   views.settings_autopricing_korsavto_table, name='settings_autopricing_korsavto_table'),
   path('settings/settings_autopricing_korsavto/<int:unit_id>/', views.settings_autopricing_korsavto_unit, name='settings_autopricing_korsavto_unit'),
   path(
       'settings/settings_price_group_stage_days/',
       views.settings_price_group_stage_days,
       name='settings_price_group_stage_days',
   ),
   path('settings/settings_new_cars_pricing/', views.settings_new_cars_pricing, name='settings_new_cars_pricing'),
   path('settings/settings_rules_cars/', views.settings_rules_cars, name='settings_rules_cars'),
   path('settings/settings_allowable_discount_km/', views.settings_allowable_discount_km, name='settings_allowable_discount_km'),
   path('settings/api/allowable_discount/marks/', views.api_allowable_discount_marks, name='api_allowable_discount_marks'),
   path('settings/api/allowable_discount/models/', views.api_allowable_discount_models, name='api_allowable_discount_models'),
   path('settings/api/allowable_discount/modifications/', views.api_allowable_discount_modifications, name='api_allowable_discount_modifications'),
   path('settings/api/allowable_discount/complectations/', views.api_allowable_discount_complectations, name='api_allowable_discount_complectations'),
   path('settings/settings_min_km_cars/', views.settings_min_km_cars, name='settings_min_km_cars'),

   path('traffic-desk/',   views.admin_traffic_desk, name='admin_traffic_desk'),

   path('refs/units_group/',     views.refs_unit_group_list),
   
   path('docs_zn/get_staffs/',   views.docs_zn_get_staffs, name='docs_zn_get_staffs'),
   
   path('balance_edit/<id>/',   views.balance_edit, name='id'),

   # Доски приветствия
   #path('boards/',            views.boards),
   #path('boards/<id>/',       views.board, name='id'),

   #path('monitors/',                views.monitors),
   #path('monitors/edit/<id>/',      views.monitor_edit, name='id'),
   #path('monitors/<id>/',           views.monitor, name='id'),

   # Записи диктофона
   path('voice_recorders/',            views.voice_recorders),
   path('voice_recorders/<id>/',       views.voice_recorder, name='id'),

   # Рабочие листы
   path('docs_rlk/',                   views.docs_rlk),
   path('docs_rlk/<id>/',              views.doc_rlk, name='id'),


   path('docs_zn/',                    views.docs_zn),
   path('docs_zn/<id>/',               views.doc_zn, name='id'),
   path('online_doc/',                 views.online_doc),
   path('records_online_doc/',         views.records_online_doc),
   path('docs_zn_report_tizer/',       views.docs_zn_report_tizer),
   path('docs_zn_report_tizer_mcu/',   views.docs_zn_report_tizer_mcu),
   

   path('sms_opros_op/',                  views.sms_opros_op),
   path('sms_opros_op_export/',           views.sms_opros_op_export),
   path('sms_opros_op/<slug:pk>/',        views.sms_opros_op_doc),


   path('sms_opros_service/',             views.sms_opros_service),
   path('sms_opros_service_export/',      views.sms_opros_service_export),
   path('sms_opros_service/<slug:pk>/',   views.sms_opros_service_doc),
   
   #path('stream/<int:pk>/',   views.get_streaming_video, name='stream'),
   #path('<int:pk>/',          views.get_video, name='video'),

   #path('docs_zn/',           views.docs_zn),
   path('docs_recomendation/<id>/',       views.doc_recomendation, name='id'),
   path('docs_recomendation_mcu/<id>/',   views.doc_recomendation_mcu, name='id'),

   #Обновление каталогов автору
   path('upload_auto_ru/post/',     views.upload_auto_ru_post),
   path('upload_auto_ru/',          views.upload_auto_ru),

   path('upload_avito_ru/',         views.upload_avito_ru),

   path('links_dc/',       views.links_dc),
   

   #cvc
   path('cvc_send/',       views.cvc_send),
   path('cvc/',            views.cvc),

   path('test/',           views.test),
   path('dev/styleguide/', views.portal_styleguide, name='portal_styleguide'),

   #test 
   path('rem_zone/',      views.rem_zone),
   
   path('refresh_base_manufacturen/' ,    views.refresh_base_manufacturen),
   path('prices_lists/',                  views.prices_lists),
   path('prices_lists/<id>/',             views.prices_list, name='id'),

   path('catalog_products/',              views.catalog_products),
   
   #КорсАвто
   path('rlks_trade_in/',              views.rlks_trade_in),
   path('rlks_trade_in/export/',       views.rlks_trade_in_export),
   path('rlks_trade_in/<id>/',         views.rlk_trade_in, name='id'),

   path('docs_car_agreement/',            views.docs_car_agreement),
   path('docs_car_agreement/<id>/',       views.doc_car_agreement, name='id'),
   
   path('docs_car_shipment/',           views.docs_car_shipment, name='id'),

   path('doc_car_shipment/<id>/',           views.doc_car_shipment, name='id'),
   path('docs_car_shipment/<id>/',           views.doc_car_shipment, name='id'),

   path('korsavto/dashboard/',               views.korsavto_dashboard, name='korsavto_dashboard'),
   path('korsavto/settings/',                views.korsavto_settings_dc, name='korsavto_settings'),
   path('korsavto/settings/<slug:slug>/',    views.korsavto_settings_dc_cars),
   path('korsavto/sales_funnel/',            views.sales_funnel),
   path('korsavto/kpi_eco/',                 views.kpi_eco),
   
   # Главное меню
   path('menu/',                              views.main_menu, name='main_menu'),
   path('menu/director/',                     views.director_menu, name='director_menu'),
]