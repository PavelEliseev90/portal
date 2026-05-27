"""
Сериализаторы для API подготовки автомобилей
"""
from datetime import datetime
from rest_framework import serializers
from .models import (
    RefCarPreparationStage, RefCarPreparationWork, RefCarPreparationStatus,
    CarPreparation, CarPreparationWorkItem, CarPreparationPhoto,
    CarPreparationChecklist, CarPreparationTemplate,
    CarPreparationWorkSchedule, CarPreparationCalendar, CarPreparationResource,
    CarPreparationNotification,
    RefPreparationMaterial, PreparationMaterialStock, PreparationMaterialMovement,
    PlannedMaterialConsumption,
)
from refs.models import RefCarsOrganization, RefUnit, RefStaff


class RefCarPreparationStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefCarPreparationStage
        fields = ['id', 'name', 'code', 'sort_order', 'description', 
                 'is_active', 'required', 'estimated_time']


class RefCarPreparationWorkSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    
    class Meta:
        model = RefCarPreparationWork
        fields = ['id', 'stage', 'stage_name', 'name', 'code', 'description',
                 'sort_order', 'is_active', 'default_required', 'estimated_time']


class RefCarPreparationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefCarPreparationStatus
        fields = ['id', 'name', 'code', 'color', 'is_final', 'can_edit']


class CarPreparationPhotoSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CarPreparationPhoto
        fields = ['id', 'work_item', 'preparation', 'photo_url', 'thumbnail_url',
                 'description', 'date_created', 'latitude', 'longitude', 
                 'device_info', 'created_by']
    
    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None
    
    def get_thumbnail_url(self, obj):
        if obj.photo_thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo_thumbnail.url)
            return obj.photo_thumbnail.url
        return None


class CarPreparationWorkScheduleSerializer(serializers.ModelSerializer):
    work_item_id = serializers.IntegerField(source='work_item.id', read_only=True)
    work_name = serializers.CharField(source='work_item.work.name', read_only=True)
    performer_name = serializers.CharField(source='planned_performer.name', read_only=True)
    duration_minutes = serializers.IntegerField(source='get_duration_minutes', read_only=True)
    
    class Meta:
        model = CarPreparationWorkSchedule
        fields = ['id', 'work_item', 'work_item_id', 'work_name',
                 'planned_start', 'planned_end', 'planned_performer', 'performer_name',
                 'priority', 'blocks_time', 'planning_comment', 'auto_scheduled',
                 'planning_status', 'duration_minutes', 'date_created', 'date_updated']


class CarPreparationWorkItemSerializer(serializers.ModelSerializer):
    work_name = serializers.CharField(source='work.name', read_only=True)
    work_stage = serializers.CharField(source='work.stage.name', read_only=True)
    performer_name = serializers.CharField(source='performer.name', read_only=True)
    photos = CarPreparationPhotoSerializer(many=True, read_only=True)
    schedule = CarPreparationWorkScheduleSerializer(read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.name', read_only=True)
    
    class Meta:
        model = CarPreparationWorkItem
        fields = ['id', 'preparation', 'work', 'work_name', 'work_stage',
                 'status', 'quality', 'is_confirmed', 'confirmed_by', 'confirmed_by_name',
                 'confirmed_at', 'confirmation_comment', 'planned_time', 'actual_time',
                 'date_start', 'date_end', 'cost', 'performer', 'performer_name',
                 'comment', 'rejection_reason', 'has_photos', 'photos', 'schedule',
                 'mobile_updated', 'mobile_updated_at']


class CarPreparationChecklistSerializer(serializers.ModelSerializer):
    checked_by_name = serializers.CharField(source='checked_by.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.name', read_only=True)
    
    class Meta:
        model = CarPreparationChecklist
        fields = ['id', 'preparation', 'overall_quality', 'cleanliness_score',
                 'completeness_score', 'defect_score', 'exterior_checked',
                 'interior_checked', 'technical_checked', 'documents_checked',
                 'defects_found', 'recommendations', 'checked_by', 'checked_by_name',
                 'date_checked', 'approved', 'approved_by', 'approved_by_name',
                 'date_approved']


class CarPreparationSerializer(serializers.ModelSerializer):
    car_vin = serializers.CharField(source='car.vin', read_only=True)
    car_name = serializers.CharField(source='car.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    status_name = serializers.CharField(source='status.name', read_only=True)
    current_stage_name = serializers.CharField(source='current_stage.name', read_only=True)
    responsible_name = serializers.CharField(source='responsible.name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.name', read_only=True)
    
    work_items = CarPreparationWorkItemSerializer(many=True, read_only=True)
    checklist = CarPreparationChecklistSerializer(read_only=True)
    total_time = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = CarPreparation
        fields = ['id', 'car', 'car_vin', 'car_name', 'unit', 'unit_name',
                 'status', 'status_name', 'current_stage', 'current_stage_name',
                 'date_start', 'date_planned_end', 'date_end', 'date_created',
                 'date_updated', 'responsible', 'responsible_name', 'inspector',
                 'inspector_name', 'comment_initial', 'comment_final',
                 'quality_notes', 'qr_code', 'mobile_created', 'mobile_last_sync',
                 'progress_percent', 'work_items', 'checklist', 'total_time',
                 'total_cost', 'is_overdue']
    
    def get_total_time(self, obj):
        return obj.get_total_time()
    
    def get_total_cost(self, obj):
        return float(obj.get_total_cost())
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()


class CarPreparationTemplateSerializer(serializers.ModelSerializer):
    stages = RefCarPreparationStageSerializer(many=True, read_only=True)
    
    class Meta:
        model = CarPreparationTemplate
        fields = ['id', 'name', 'description', 'unit', 'car_type', 'stages',
                 'is_active', 'is_default', 'date_created']


class CarPreparationNotificationSerializer(serializers.ModelSerializer):
    preparation_car_name = serializers.CharField(source='preparation.car.name', read_only=True)
    preparation_car_vin = serializers.CharField(source='preparation.car.vin', read_only=True)
    work_item_name = serializers.CharField(source='work_item.work.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)
    
    class Meta:
        model = CarPreparationNotification
        fields = ['id', 'preparation', 'preparation_car_name', 'preparation_car_vin',
                 'work_item', 'work_item_name', 'work_schedule', 'notification_type',
                 'priority', 'message', 'recipient', 'recipient_name', 'sent',
                 'date_sent', 'date_created', 'read', 'date_read', 'auto_created',
                 'channel_email', 'channel_push', 'channel_sms', 'metadata']


class RefPreparationMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefPreparationMaterial
        fields = ['id', 'name', 'code', 'uom', 'is_active']


class PreparationMaterialStockSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    
    class Meta:
        model = PreparationMaterialStock
        fields = ['id', 'unit', 'unit_name', 'material', 'material_name', 'qty_on_hand', 'min_qty', 'max_qty', 'date_updated']


class PreparationMaterialMovementSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    work_item_name = serializers.CharField(source='work_item.work.name', read_only=True)
    
    class Meta:
        model = PreparationMaterialMovement
        fields = ['id', 'date', 'unit', 'unit_name', 'material', 'material_name', 'qty', 'movement_type', 'work_item', 'work_item_name', 'comment', 'user']


class PlannedMaterialConsumptionSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    
    class Meta:
        model = PlannedMaterialConsumption
        fields = ['id', 'work_item', 'material', 'material_name', 'qty_planned', 'qty_reserved', 'reserved', 'date_created']


class CarPreparationCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подготовки"""
    template_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = CarPreparation
        fields = ['car', 'unit', 'template_id', 'responsible', 'date_planned_end',
                 'comment_initial']
    
    def create(self, validated_data):
        template_id = validated_data.pop('template_id', None)
        
        preparation = CarPreparation.objects.create(**validated_data)
        
        # Применение шаблона
        if template_id:
            try:
                template = CarPreparationTemplate.objects.get(id=template_id)
                template.apply_to_preparation(preparation)
            except CarPreparationTemplate.DoesNotExist:
                pass
        
        return preparation


class CarPreparationWorkItemUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления работы"""
    
    class Meta:
        model = CarPreparationWorkItem
        fields = ['status', 'quality', 'actual_time', 'cost', 'comment',
                 'rejection_reason', 'date_start', 'date_end', 'performer']
    
    def update(self, instance, validated_data):
        # Автоматическая установка дат
        if validated_data.get('status') == 'in_progress' and not instance.date_start:
            validated_data['date_start'] = datetime.now()
        
        if validated_data.get('status') == 'completed' and not instance.date_end:
            validated_data['date_end'] = datetime.now()
            validated_data['mobile_updated'] = True
            validated_data['mobile_updated_at'] = datetime.now()
        
        return super().update(instance, validated_data)


class CarPreparationPhotoUploadSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки фотографий"""
    
    class Meta:
        model = CarPreparationPhoto
        fields = ['work_item', 'preparation', 'photo', 'description',
                 'latitude', 'longitude', 'device_info', 'created_by']
    
    def create(self, validated_data):
        photo = validated_data.get('photo')
        work_item = validated_data.get('work_item')
        
        if work_item:
            work_item.has_photos = True
            work_item.save()
        
        return super().create(validated_data)

