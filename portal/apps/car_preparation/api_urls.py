from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    CarPreparationViewSet,
    CarPreparationWorkItemViewSet,
    CarPreparationPhotoViewSet,
    CarPreparationChecklistViewSet,
    CarPreparationScheduleViewSet,
    CarPreparationNotificationViewSet,
    RefPreparationMaterialViewSet, PreparationMaterialStockViewSet,
    PreparationMaterialMovementViewSet,
)

router = DefaultRouter()
router.register(r'preparations', CarPreparationViewSet, basename='car_preparations')
router.register(r'work_items', CarPreparationWorkItemViewSet, basename='car_preparation_work_items')
router.register(r'photos', CarPreparationPhotoViewSet, basename='car_preparation_photos')
router.register(r'checklists', CarPreparationChecklistViewSet, basename='car_preparation_checklists')
router.register(r'schedules', CarPreparationScheduleViewSet, basename='car_preparation_schedules')
router.register(r'notifications', CarPreparationNotificationViewSet, basename='car_preparation_notifications')
router.register(r'materials', RefPreparationMaterialViewSet, basename='car_prep_materials')
router.register(r'stock', PreparationMaterialStockViewSet, basename='car_prep_stock')
router.register(r'movements', PreparationMaterialMovementViewSet, basename='car_prep_movements')

urlpatterns = [
    *router.urls,
]


