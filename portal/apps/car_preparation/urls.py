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

