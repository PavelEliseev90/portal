from django.urls import path
from . import views, views_notifications

app_name = 'car_preparation'

urlpatterns = [
    path('', views.preparation_list, name='list'),
    path('performer/', views.performer_dashboard, name='performer_dashboard'),
    path('performers/', views.performers_works, name='performers_works'),
    # ресурсы планирования
    path('resources/', views.resources_list, name='resources_list'),
    path('resources/add/', views.resource_create, name='resource_create'),
    path('resources/<int:resource_id>/edit/', views.resource_edit, name='resource_edit'),
    path('mobile/<int:preparation_id>/', views.mobile_checklist, name='mobile_checklist'),
    path('report/<int:preparation_id>/', views.preparation_report, name='preparation_report'),
    path('calendar/', views.preparation_calendar, name='calendar'),
    path('schedule/<int:preparation_id>/', views.preparation_schedule, name='schedule'),
    # Заказ-наряды
    path('work_order/create/<int:preparation_id>/', views.work_order_create, name='work_order_create'),
    path('work_order/<int:work_order_id>/', views.work_order_detail, name='work_order_detail'),
    path('work_order/timeline/<int:car_id>/', views.work_order_timeline, name='work_order_timeline'),
    path('work_order/item/<int:item_id>/start/', views.work_order_item_start, name='work_order_item_start'),
    path('work_order/item/<int:item_id>/complete/', views.work_order_item_complete, name='work_order_item_complete'),
    path('work_order/item/<int:item_id>/photo/', views.work_order_item_photo_upload, name='work_order_item_photo_upload'),
    path('api/templates/<int:template_id>/works/', views.work_order_template_works, name='work_order_template_works'),
    path('notifications/', views_notifications.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views_notifications.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views_notifications.notification_mark_all_read, name='notification_mark_all_read'),
    # материалы
    path('materials/', views.materials_list, name='materials_list'),
    path('materials/add/', views.material_create, name='material_create'),
    path('materials/<int:material_id>/edit/', views.material_edit, name='material_edit'),
    # остатки
    path('stock/', views.stock_list, name='stock_list'),
    # движения
    path('movements/', views.movements_list, name='movements_list'),
    path('movements/receipt/', views.movement_receipt, name='movement_receipt'),
    path('movements/consume/', views.movement_consume, name='movement_consume'),
]

