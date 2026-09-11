from django.urls import path, include
from django.views.generic import TemplateView
from avtosalon import views

app_name = 'avtosalon'

urlpatterns = [
   
   path('director/',                         views.gk_director_dashboard, name='gk_director_dashboard'),
   path('js/get_chats_list_cars/',           views.get_chats_list_cars, name='get_chats_list_cars'),
   path('disposition/',                      views.disposition, name='disposition'),
   path('disposition/get_marks/',            views.disposition_get_marks, name='disposition_get_marks'),
   path('disposition/get_models/',           views.disposition_get_models, name='disposition_get_models'),
   path(
       'disposition/saved-filters/save/',
       views.disposition_saved_filter_save,
       name='disposition_saved_filter_save',
   ),
   path(
       'disposition/saved-filters/<int:filter_id>/delete/',
       views.disposition_saved_filter_delete,
       name='disposition_saved_filter_delete',
   ),
   path('warehouse/analysis/',               views.warehouse_analysis, name='warehouse_analysis'),
   path('catalog/',                          views.cars_catalog),
   path('catalog/<slug:mark_name_en>/',      views.catalog_mark, name='slug'),
   path('catalog/<slug:mark_name_en>/<slug:model_name>/',  views.catalog_model, name='slug'),
   
   path('',                                  views.cars),
   
   # Задачи по автомобилям (должны быть ПЕРЕД маршрутами со slug)
   path('tasks/',                            views.car_tasks_list, name='car_tasks_list'),
   path('tasks/<int:car_id>/',               views.car_tasks_list, name='car_tasks_list_by_car'),
   path('task/create/<int:car_id>/',         views.car_task_create, name='car_task_create'),
   path('task/<int:task_id>/',               views.car_task_detail, name='car_task_detail'),
   path('task/<int:task_id>/take/',          views.car_task_take, name='car_task_take'),
   path('task/<int:task_id>/complete/',      views.car_task_complete, name='car_task_complete'),
   path('task/<int:task_id>/comment/',       views.car_task_comment_add, name='car_task_comment_add'),
   path('task/<int:task_id>/file/upload/',   views.car_task_file_upload, name='car_task_file_upload'),
   path('task/file/<int:file_id>/delete/',   views.car_task_file_delete, name='car_task_file_delete'),
   path('task/<int:task_id>/file/upload/',   views.car_task_file_upload, name='car_task_file_upload'),
   path('task/file/<int:file_id>/delete/',   views.car_task_file_delete, name='car_task_file_delete'),
   
   path('deal/rlk-chat/poll/',                  views.rlk_op_chat_poll, name='rlk_op_chat_poll'),
   path('deal/rlk-chat/send/',                  views.rlk_op_chat_send, name='rlk_op_chat_send'),
   path('deal/rlk-chat/1c/<str:staff_uin>/<str:rlk_uin>/', views.rlk_op_chat, name='rlk_op_chat_1c'),
   path('deal/rlk-chat/',                     views.rlk_op_chat, name='rlk_op_chat_uin'),
   path('deal/rlk-chat/<int:rlk_id>/',        views.rlk_op_chat, name='rlk_op_chat'),
   path('deal/calculation/<int:id>/client-suggestions/count/', views.deal_calc_client_suggestions_count, name='deal_calc_client_suggestions_count'),
   path('deal/calculation/<int:id>/client-suggestions/', views.deal_calc_client_suggestions_list, name='deal_calc_client_suggestions_list'),
   path('deal/calculation/tg-action/<str:token>/', views.deal_calc_telegram_action, name='deal_calc_telegram_action'),
   path('deal/calculation/<int:id>/',        views.deal_calculation_doc, name='deal_calculation_doc'),
   path('deal/calculation/',                 views.deal_calculation, name='deal_calculation'),
   path('<slug:slug>/sms/send-code/',        views.car_sms_send_code, name='car_sms_send_code'),
   path('<slug:slug>/sms/verify-code/',      views.car_sms_verify_code, name='car_sms_verify_code'),
   
   path('<slug>/specifications/',            views.specifications, name='slug'),
   path('<slug>/price_edit/',                views.price_edit, name='slug'),
   path('<slug>/price/',                     views.price, name='slug'),
   path('<slug>/photos_edit/',               views.photos_edit, name='photos_edit'),
   path('<slug>/costs_edit/',                views.costs_edit, name='costs_edit'),
   path('<slug>/info_js/',                   views.info_js, name='slug'),
   path('<slug>/access_user/',               views.access_user, name='slug'),
   path('<slug>/',                           views.car, name='slug'),
   
   # Витрина склада
   path('warehouse/showcase/create/',        views.warehouse_showcase_create, name='warehouse_showcase_create'),
   
   #path('op/<slug:id>/<slug:pk>/', views.op_detail_recognition, name='slug'),
]