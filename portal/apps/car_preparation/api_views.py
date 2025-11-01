"""
API Views для мобильного приложения подготовки автомобилей
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    CarPreparation, CarPreparationWorkItem, CarPreparationPhoto,
    CarPreparationChecklist, RefCarPreparationStatus,
    CarPreparationWorkSchedule, CarPreparationResource,
    CarPreparationNotification,
    RefPreparationMaterial, PreparationMaterialStock, PreparationMaterialMovement,
    PlannedMaterialConsumption,
)
from .serializers import (
    CarPreparationSerializer, CarPreparationCreateSerializer,
    CarPreparationWorkItemSerializer, CarPreparationWorkItemUpdateSerializer,
    CarPreparationPhotoUploadSerializer, CarPreparationWorkScheduleSerializer,
    CarPreparationNotificationSerializer,
    RefPreparationMaterialSerializer, PreparationMaterialStockSerializer,
    PreparationMaterialMovementSerializer, PlannedMaterialConsumptionSerializer,
)


class CarPreparationViewSet(viewsets.ModelViewSet):
    """ViewSet для управления подготовками автомобилей"""
    permission_classes = [IsAuthenticated]
    queryset = CarPreparation.objects.all()
    serializer_class = CarPreparationSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CarPreparationCreateSerializer
        return CarPreparationSerializer
    
    def get_queryset(self):
        queryset = CarPreparation.objects.all()
        
        # Фильтры
        car_id = self.request.query_params.get('car_id', None)
        unit_id = self.request.query_params.get('unit_id', None)
        status_code = self.request.query_params.get('status', None)
        responsible_id = self.request.query_params.get('responsible_id', None)
        qr_code = self.request.query_params.get('qr_code', None)
        
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)
        if status_code:
            queryset = queryset.filter(status__code=status_code)
        if responsible_id:
            queryset = queryset.filter(responsible_id=responsible_id)
        if qr_code:
            queryset = queryset.filter(qr_code=qr_code)
        
        # Для мобильного приложения - только активные
        mobile = self.request.query_params.get('mobile', None)
        if mobile == 'true':
            queryset = queryset.exclude(
                status__code__in=['completed', 'cancelled', 'archived']
            )
        
        return queryset.order_by('-date_created')
    
    @action(detail=True, methods=['post'], url_path='add_works')
    def add_works(self, request, pk=None):
        """Добавление работ в подготовку вручную"""
        preparation = self.get_object()
        work_ids = request.data.get('work_ids', [])
        
        if not work_ids:
            return Response({
                'success': False,
                'message': 'Не указаны работы для добавления'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from .models import RefCarPreparationWork, CarPreparationWorkItem
        
        added_count = 0
        for work_id in work_ids:
            try:
                work = RefCarPreparationWork.objects.get(id=work_id, is_active=True)
                # Проверяем, не добавлена ли уже эта работа
                if not CarPreparationWorkItem.objects.filter(preparation=preparation, work=work).exists():
                    CarPreparationWorkItem.objects.create(
                        preparation=preparation,
                        work=work,
                        is_confirmed=True,  # Автоматически подтверждаем при добавлении
                        status='pending'
                    )
                    added_count += 1
            except RefCarPreparationWork.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': f'Добавлено {added_count} работ(ы)',
            'added_count': added_count
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Завершение подготовки"""
        preparation = self.get_object()
        
        # Проверка, что все обязательные работы выполнены
        incomplete_works = preparation.work_items.filter(
            status__in=['pending', 'in_progress'],
            work__default_required=True
        )
        
        if incomplete_works.exists():
            return Response({
                'success': False,
                'message': 'Не все обязательные работы выполнены'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Обновление статуса
        completed_status = RefCarPreparationStatus.objects.filter(
            code='completed'
        ).first()
        
        if completed_status:
            preparation.status = completed_status
            preparation.date_end = timezone.now()
            preparation.progress_percent = 100
            preparation.comment_final = request.data.get('comment_final', '')
            preparation.save()
        
        return Response({
            'success': True,
            'message': 'Подготовка завершена'
        })
    
    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        """Получение QR-кода для подготовки"""
        preparation = self.get_object()
        
        if not preparation.qr_code:
            # Генерация QR-кода
            import uuid
            preparation.qr_code = str(uuid.uuid4())[:8].upper()
            preparation.save()
        
        return Response({
            'qr_code': preparation.qr_code,
            'url': f'/car_preparation/mobile/{preparation.id}/'
        })


class CarPreparationWorkItemViewSet(viewsets.ModelViewSet):
    """ViewSet для управления работами по подготовке"""
    permission_classes = [IsAuthenticated]
    queryset = CarPreparationWorkItem.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return CarPreparationWorkItemUpdateSerializer
        return CarPreparationWorkItemSerializer
    
    def get_queryset(self):
        queryset = CarPreparationWorkItem.objects.all()
        
        # Фильтр по подготовке
        preparation_id = self.request.query_params.get('preparation_id', None)
        if preparation_id:
            queryset = queryset.filter(preparation_id=preparation_id)
        
        # Фильтр по статусу
        work_status = self.request.query_params.get('status', None)
        if work_status:
            queryset = queryset.filter(status=work_status)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Подтверждение работы для планирования"""
        work_item = self.get_object()
        
        is_confirmed = request.data.get('is_confirmed', True)
        comment = request.data.get('comment', '')
        
        work_item.is_confirmed = is_confirmed
        work_item.confirmed_by = request.user.staff if hasattr(request.user, 'staff') else None
        work_item.confirmed_at = timezone.now() if is_confirmed else None
        work_item.confirmation_comment = comment
        
        work_item.save()
        
        # Если работа не подтверждена, удаляем расписание
        if not is_confirmed and hasattr(work_item, 'schedule'):
            work_item.schedule.delete()
        
        return Response({
            'success': True,
            'message': 'Статус подтверждения обновлен'
        })
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Начало выполнения работы"""
        work_item = self.get_object()
        
        # Проверка прав (исполнитель должен быть назначен на эту работу)
        staff = getattr(request.user, 'staff', None)
        if not staff:
            return Response({
                'success': False,
                'message': 'Пользователь не связан с сотрудником'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, назначен ли текущий пользователь исполнителем
        is_performer = False
        if hasattr(work_item, 'schedule') and work_item.schedule:
            if work_item.schedule.planned_performer == staff:
                is_performer = True
        
        if not is_performer and work_item.performer != staff:
            return Response({
                'success': False,
                'message': 'Вы не назначены исполнителем этой работы'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if work_item.status == 'completed':
            return Response({
                'success': False,
                'message': 'Работа уже завершена'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        work_item.status = 'in_progress'
        work_item.date_start = timezone.now()
        work_item.performer = staff
        work_item.save()
        
        # Обновляем статус в расписании
        if hasattr(work_item, 'schedule') and work_item.schedule:
            work_item.schedule.planning_status = 'in_progress'
            work_item.schedule.save()
        
        # Пересчет прогресса подготовки
        work_item.preparation.progress_percent = work_item.preparation.calculate_progress()
        work_item.preparation.save()
        
        # Создание уведомления о начале работы
        from .notifications import create_work_started_notification
        create_work_started_notification(work_item, staff)
        
        return Response({
            'success': True,
            'message': 'Работа начата'
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Завершение работы"""
        work_item = self.get_object()
        
        # Проверка прав (исполнитель должен быть назначен на эту работу)
        staff = getattr(request.user, 'staff', None)
        if not staff:
            return Response({
                'success': False,
                'message': 'Пользователь не связан с сотрудником'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, назначен ли текущий пользователь исполнителем
        is_performer = False
        if hasattr(work_item, 'schedule') and work_item.schedule:
            if work_item.schedule.planned_performer == staff:
                is_performer = True
        
        if not is_performer and work_item.performer != staff:
            return Response({
                'success': False,
                'message': 'Вы не назначены исполнителем этой работы'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if work_item.status not in ['pending', 'in_progress']:
            return Response({
                'success': False,
                'message': 'Работа не может быть завершена'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CarPreparationWorkItemUpdateSerializer(
            work_item,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save(status='completed', date_end=timezone.now(), performer=staff)
            
            # Обновляем статус в расписании
            if hasattr(work_item, 'schedule') and work_item.schedule:
                work_item.schedule.planning_status = 'completed'
                work_item.schedule.save()
            
            # Пересчет прогресса подготовки
            work_item.preparation.progress_percent = work_item.preparation.calculate_progress()
            work_item.preparation.save()
            
            # Создание уведомления о завершении работы
            from .notifications import create_work_completed_notification
            create_work_completed_notification(work_item)
            
            return Response({
                'success': True,
                'message': 'Работа завершена'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CarPreparationPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet для управления фотографиями"""
    permission_classes = [IsAuthenticated]
    queryset = CarPreparationPhoto.objects.all()
    serializer_class = CarPreparationPhotoUploadSerializer
    
    def get_queryset(self):
        queryset = CarPreparationPhoto.objects.all()
        
        # Фильтр по работе
        work_item_id = self.request.query_params.get('work_item_id', None)
        if work_item_id:
            queryset = queryset.filter(work_item_id=work_item_id)
        
        # Фильтр по подготовке
        preparation_id = self.request.query_params.get('preparation_id', None)
        if preparation_id:
            queryset = queryset.filter(preparation_id=preparation_id)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.staff if hasattr(self.request.user, 'staff') else None)


class CarPreparationChecklistViewSet(viewsets.ModelViewSet):
    """ViewSet для управления чек-листами"""
    permission_classes = [IsAuthenticated]
    queryset = CarPreparationChecklist.objects.all()
    
    def get_queryset(self):
        queryset = CarPreparationChecklist.objects.all()
        
        # Фильтр по подготовке
        preparation_id = self.request.query_params.get('preparation_id', None)
        if preparation_id:
            queryset = queryset.filter(preparation_id=preparation_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Утверждение чек-листа"""
        checklist = self.get_object()
        
        checklist.approved = True
        checklist.approved_by = request.user.staff if hasattr(request.user, 'staff') else None
        checklist.date_approved = timezone.now()
        checklist.save()
        
        return Response({
            'success': True,
            'message': 'Чек-лист утвержден'
        })


class CarPreparationScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet для управления расписаниями работ"""
    permission_classes = [IsAuthenticated]
    queryset = CarPreparationWorkSchedule.objects.all()
    serializer_class = CarPreparationWorkScheduleSerializer
    
    def get_queryset(self):
        queryset = CarPreparationWorkSchedule.objects.all()
        
        # Фильтры
        work_item_id = self.request.query_params.get('work_item_id', None)
        preparation_id = self.request.query_params.get('preparation_id', None)
        performer_id = self.request.query_params.get('performer_id', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if work_item_id:
            queryset = queryset.filter(work_item_id=work_item_id)
        if preparation_id:
            queryset = queryset.filter(work_item__preparation_id=preparation_id)
        if performer_id:
            queryset = queryset.filter(planned_performer_id=performer_id)
        if date_from:
            queryset = queryset.filter(planned_start__gte=date_from)
        if date_to:
            queryset = queryset.filter(planned_end__lte=date_to)
        
        return queryset.select_related('work_item', 'work_item__work', 'planned_performer')
    
    @action(detail=False, methods=['post'])
    def create_schedule(self, request):
        """Создание расписания для работы"""
        work_item_id = request.data.get('work_item_id')
        planned_start = request.data.get('planned_start')
        planned_end = request.data.get('planned_end')
        planned_performer_id = request.data.get('planned_performer_id')
        priority = request.data.get('priority', 'normal')
        
        try:
            work_item = CarPreparationWorkItem.objects.get(id=work_item_id)
        except CarPreparationWorkItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Работа не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Проверка, что работа подтверждена
        if not work_item.is_confirmed:
            return Response({
                'success': False,
                'message': 'Работа должна быть подтверждена перед планированием'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверка пересечений
        if planned_performer_id and planned_start and planned_end:
            overlapping = CarPreparationWorkSchedule.objects.filter(
                planned_performer_id=planned_performer_id,
                planned_start__lt=planned_end,
                planned_end__gt=planned_start,
                planning_status__in=['scheduled', 'in_progress'],
                blocks_time=True
            ).exclude(work_item=work_item).exists()
            
            if overlapping:
                return Response({
                    'success': False,
                    'message': 'Время пересекается с другой работой'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Создание или обновление расписания
        schedule, created = CarPreparationWorkSchedule.objects.get_or_create(
            work_item=work_item,
            defaults={
                'planned_start': planned_start,
                'planned_end': planned_end,
                'planned_performer_id': planned_performer_id,
                'priority': priority,
                'planning_status': 'scheduled'
            }
        )
        
        if not created:
            schedule.planned_start = planned_start
            schedule.planned_end = planned_end
            schedule.planned_performer_id = planned_performer_id
            schedule.priority = priority
            schedule.save()
        
        serializer = CarPreparationWorkScheduleSerializer(schedule)
        return Response({
            'success': True,
            'schedule': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='auto/(?P<preparation_id>[^/.]+)')
    def auto_schedule(self, request, preparation_id=None):
        """Автоматическое планирование подготовки"""
        preparation = CarPreparation.objects.get(id=preparation_id)
        
        # Получаем только подтвержденные незапланированные работы
        unscheduled_works = preparation.work_items.filter(
            is_confirmed=True
        ).filter(
            models.Q(schedule__isnull=True) | models.Q(schedule__planning_status='not_scheduled')
        )
        
        # Получаем доступные ресурсы
        resources = CarPreparationResource.objects.filter(
            unit=preparation.unit,
            is_active=True,
            resource_type='performer'
        )
        
        current_time = preparation.scheduled_start or timezone.now()
        
        for work_item in unscheduled_works:
            # Находим свободного исполнителя
            for resource in resources:
                if resource.is_available_at(current_time):
                    # Расчет времени выполнения
                    duration_minutes = work_item.planned_time or work_item.work.estimated_time or 60
                    end_time = current_time + timedelta(minutes=duration_minutes)
                    
                    # Создаем расписание
                    schedule, created = CarPreparationWorkSchedule.objects.get_or_create(
                        work_item=work_item,
                        defaults={
                            'planned_start': current_time,
                            'planned_end': end_time,
                            'planned_performer': resource.performer,
                            'planning_status': 'scheduled',
                            'auto_scheduled': True,
                            'blocks_time': True
                        }
                    )
                    
                    current_time = end_time + timedelta(minutes=15)  # Перерыв между работами
                    break
        
        return Response({
            'success': True,
            'message': 'Планирование выполнено'
        })


class CarPreparationNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления уведомлениями"""
    permission_classes = [IsAuthenticated]
    serializer_class = CarPreparationNotificationSerializer
    
    def get_queryset(self):
        # Получаем сотрудника для текущего пользователя
        user = self.request.user
        staff = None
        if hasattr(user, 'staff'):
            staff = user.staff
        elif hasattr(user, 'refstaff'):
            staff = user.refstaff
        
        if not staff:
            return CarPreparationNotification.objects.none()
        
        queryset = CarPreparationNotification.objects.filter(
            recipient=staff
        ).select_related(
            'preparation', 'preparation__car', 'work_item', 
            'work_item__work', 'work_schedule', 'recipient'
        )
        
        # Фильтры
        notification_type = self.request.query_params.get('type', None)
        priority = self.request.query_params.get('priority', None)
        read = self.request.query_params.get('read', None)
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        if priority:
            queryset = queryset.filter(priority=priority)
        
        if read == 'false' or read == '0':
            queryset = queryset.filter(read=False)
        elif read == 'true' or read == '1':
            queryset = queryset.filter(read=True)
        
        return queryset.order_by('-date_created')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Отметить уведомление как прочитанное"""
        notification = self.get_object()
        
        # Проверка, что уведомление принадлежит текущему пользователю
        user = request.user
        staff = None
        if hasattr(user, 'staff'):
            staff = user.staff
        elif hasattr(user, 'refstaff'):
            staff = user.refstaff
        
        if not staff or notification.recipient != staff:
            return Response({
                'success': False,
                'message': 'Уведомление не найдено'
            }, status=status.HTTP_404_NOT_FOUND)
        
        notification.read = True
        notification.date_read = timezone.now()
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Уведомление отмечено как прочитанное'
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Отметить все уведомления как прочитанные"""
        user = request.user
        staff = None
        if hasattr(user, 'staff'):
            staff = user.staff
        elif hasattr(user, 'refstaff'):
            staff = user.refstaff
        
        if not staff:
            return Response({
                'success': False,
                'message': 'Пользователь не связан с сотрудником'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated = CarPreparationNotification.objects.filter(
            recipient=staff,
            read=False
        ).update(read=True, date_read=timezone.now())
        
        return Response({
            'success': True,
            'message': f'Отмечено {updated} уведомлений как прочитанных',
            'updated': updated
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика уведомлений"""
        user = request.user
        staff = None
        if hasattr(user, 'staff'):
            staff = user.staff
        elif hasattr(user, 'refstaff'):
            staff = user.refstaff
        
        if not staff:
            return Response({
                'unread_count': 0,
                'urgent_count': 0,
                'overdue_count': 0
            })
        
        unread_count = CarPreparationNotification.objects.filter(
            recipient=staff, read=False
        ).count()
        
        urgent_count = CarPreparationNotification.objects.filter(
            recipient=staff, read=False, priority='urgent'
        ).count()
        
        overdue_count = CarPreparationNotification.objects.filter(
            recipient=staff, read=False,
            notification_type__in=['work_overdue', 'preparation_overdue']
        ).count()
        
        return Response({
            'unread_count': unread_count,
            'urgent_count': urgent_count,
            'overdue_count': overdue_count
        })


class RefPreparationMaterialViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RefPreparationMaterial.objects.all()
    serializer_class = RefPreparationMaterialSerializer
    filterset_fields = ['is_active']


class PreparationMaterialStockViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PreparationMaterialStockSerializer
    
    def get_queryset(self):
        queryset = PreparationMaterialStock.objects.select_related('material', 'unit')
        unit_id = self.request.query_params.get('unit_id')
        material_id = self.request.query_params.get('material_id')
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)
        if material_id:
            queryset = queryset.filter(material_id=material_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        qs = PreparationMaterialStock.objects.filter(qty_on_hand__lt=models.F('min_qty'))
        return Response(PreparationMaterialStockSerializer(qs, many=True).data)


class PreparationMaterialMovementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PreparationMaterialMovement.objects.select_related('material', 'unit', 'work_item')
    serializer_class = PreparationMaterialMovementSerializer
    
    @action(detail=False, methods=['post'])
    def receipt(self, request):
        unit_id = request.data.get('unit_id')
        material_id = request.data.get('material_id')
        qty = request.data.get('qty')
        comment = request.data.get('comment', '')
        
        if not unit_id or not material_id or not qty:
            return Response({'success': False, 'message': 'unit_id, material_id, qty обязательны'}, status=400)
        
        movement = PreparationMaterialMovement.objects.create(
            unit_id=unit_id,
            material_id=material_id,
            qty=qty,
            movement_type='receipt',
            comment=comment,
            user=getattr(request.user, 'staff', None)
        )
        stock, _ = PreparationMaterialStock.objects.get_or_create(unit_id=unit_id, material_id=material_id)
        stock.qty_on_hand = (stock.qty_on_hand or 0) + float(qty)
        stock.save()
        return Response({'success': True, 'id': movement.id})
    
    @action(detail=False, methods=['post'])
    def consume(self, request):
        unit_id = request.data.get('unit_id')
        material_id = request.data.get('material_id')
        qty = request.data.get('qty')
        work_item_id = request.data.get('work_item_id')
        comment = request.data.get('comment', '')
        
        if not unit_id or not material_id or not qty:
            return Response({'success': False, 'message': 'unit_id, material_id, qty обязательны'}, status=400)
        
        stock = PreparationMaterialStock.objects.filter(unit_id=unit_id, material_id=material_id).first()
        if not stock or stock.qty_on_hand < float(qty):
            return Response({'success': False, 'message': 'Недостаточно остатка'}, status=400)
        
        movement = PreparationMaterialMovement.objects.create(
            unit_id=unit_id,
            material_id=material_id,
            qty=-abs(float(qty)),
            movement_type='consume',
            work_item_id=work_item_id,
            comment=comment,
            user=getattr(request.user, 'staff', None)
        )
        stock.qty_on_hand = (stock.qty_on_hand or 0) - float(qty)
        stock.save()
        return Response({'success': True, 'id': movement.id})

