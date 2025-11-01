"""
Сигналы для автоматического создания плана работ по подготовке
при проведении интерактивной оценки со статусом 8
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.signals import request_finished
import logging

# Получаем логгер
logger = logging.getLogger(__name__)

try:
    from .models import RegInteractivOcenka, RegEstimationMCU, RegEstimationSS, RegEstimationPodgotovka
except ImportError:
    # Если модели не импортируются, сигнал не будет зарегистрирован
    RegInteractivOcenka = None
    print("⚠️ Warning: Cannot import RegInteractivOcenka model")


# Защита от регистрации сигнала, если модель не импортирована
if RegInteractivOcenka is not None:
    @receiver(post_save, sender=RegInteractivOcenka)
    def create_car_preparation_from_estimation(sender, instance, created, **kwargs):
        """
        Создание плана подготовки автомобиля при достижении статуса 8
        """
        # Добавляем логирование для проверки
        print(f"🔔 Signal triggered for RegInteractivOcenka ID={instance.id}, created={created}")
        logger.info(f"RegInteractivOcenka signal triggered: ID={instance.id}, created={created}")
        
        if instance.status:
            print(f"📊 Status: {instance.status.name}, Status ID: {instance.status.id}")
            logger.info(f"Status: {instance.status.name} (ID: {instance.status.id})")
        else:
            print(f"📊 Status: None")
            logger.info("Status: None")
        
        # Проверяем, что статус = 8 (проведена)
        if instance.status and instance.status.id == 8:
            print(f"✅ Status = 8 confirmed, proceeding with preparation creation")
            # Импортируем модели car_preparation
            try:
                from car_preparation.models import (
                    CarPreparation, CarPreparationWorkItem, RefCarPreparationWork,
                    RefCarsOrganization, RefCarPreparationStage, RefCarPreparationStatus
                )
                from refs.models import RefUnit, RefStaff
                from datetime import datetime, timedelta
                from django.utils import timezone
            except ImportError as e:
                # Если модуль car_preparation не установлен, выходим
                print(f"⚠️ Warning: car_preparation module not found, skipping auto-creation: {e}")
                logger.warning(f"car_preparation module not found: {e}")
                return
            
            # Проверяем, не создана ли уже подготовка для этой оценки
            try:
                existing_prep = CarPreparation.objects.filter(
                    rlk=instance.rlk
                ).first()
                
                if existing_prep:
                    print(f"Preparation already exists for estimation {instance.id}")
                    return
            except Exception as e:
                print(f"Error checking existing preparation: {e}")
            
            try:
                # Получаем или создаем автомобиль из RefCarsOrganization
                car_org = None
                if instance.rlk and hasattr(instance.rlk, 'car'):
                    car = instance.rlk.car
                    # Ищем автомобиль в RefCarsOrganization
                    car_org = RefCarsOrganization.objects.filter(vin=instance.vin).first()
                    
                    # Если не нашли, выходим
                    if not car_org:
                        print(f"Car with VIN {instance.vin} not found in RefCarsOrganization")
                        return
                elif instance.vin:
                    # Если есть VIN, пытаемся найти автомобиль
                    car_org = RefCarsOrganization.objects.filter(vin=instance.vin).first()
                    if not car_org:
                        print(f"Car with VIN {instance.vin} not found in RefCarsOrganization")
                        return
                else:
                    print("No car information available")
                    return
                
                # Получаем подразделение из rlk
                unit = instance.rlk.unit if instance.rlk else None
                if not unit:
                    print("Unit not found in rlk")
                    return
                
                # Получаем ответственного (оценщика)
                responsible = instance.staff if instance.staff else None
                
                # Находим или создаем статус
                status = RefCarPreparationStatus.objects.first()
                if not status:
                    status = RefCarPreparationStatus.objects.first()
                
                # Получаем все работы из оценок
                mcu_works = RegEstimationMCU.objects.filter(
                    estimation=instance
                )
                ss_works = RegEstimationSS.objects.filter(
                    estimation=instance
                )
                prep_works = RegEstimationPodgotovka.objects.filter(
                    estimation=instance
                )
                
                # Если нет работ, не создаем подготовку
                if not (mcu_works.exists() or ss_works.exists() or prep_works.exists()):
                    print("No estimation works found")
                    return
                
                # Создаем подготовку
                preparation = CarPreparation.objects.create(
                    rlk=instance.rlk,
                    car=car_org,
                    unit=unit,
                    status=status,
                    responsible=responsible,
                    date_created=timezone.now(),
                    comment_initial=f"Создано автоматически из оценки {instance.id}"
                )
                
                print(f"Created CarPreparation {preparation.id} for estimation {instance.id}")
                
                # Добавляем этапы и работы
                stages_created = {}
                
                # Создаем этап для кузовного цеха
                if mcu_works.exists():
                    mcu_stage_name = "Кузовной цех"
                    mcu_stage = None
                    
                    # Ищем или создаем этап
                    if mcu_stage_name in stages_created:
                        mcu_stage = stages_created[mcu_stage_name]
                    else:
                        mcu_stage = RefCarPreparationStage.objects.filter(name=mcu_stage_name).first()
                        if not mcu_stage:
                            mcu_stage = RefCarPreparationStage.objects.create(
                                name=mcu_stage_name,
                                sort_order=1,
                                is_active=True
                            )
                        stages_created[mcu_stage_name] = mcu_stage
                    
                    # Добавляем работы
                    for work in mcu_works:
                        # Ищем или создаем работу
                        work_name = work.name
                        prep_work = RefCarPreparationWork.objects.filter(name=work_name).first()
                        
                        if not prep_work:
                            prep_work = RefCarPreparationWork.objects.create(
                                name=work_name,
                                stage=mcu_stage,
                                estimated_time=int(work.normo * 60) if work.normo else 0,  # конвертируем нормочасы в минуты
                                #cost=work.price_kors or 0,
                                sort_order=1,
                                is_active=True
                            )
                        
                        # Создаем запись работы в подготовке
                        CarPreparationWorkItem.objects.create(
                            preparation=preparation,
                            work=prep_work,
                            status='pending',
                            is_confirmed=False,
                            confirmed_at=timezone.now(),
                            planned_time=int(work.normo * 60) if work.normo else 0,
                            cost=work.price_kors or 0,
                            comment=f"Передано из оценки (MCU)"
                        )
                
                # Создаем этап для слесарного цеха
                if ss_works.exists():
                    ss_stage_name = "Слесарный цех"
                    ss_stage = None
                    
                    if ss_stage_name in stages_created:
                        ss_stage = stages_created[ss_stage_name]
                    else:
                        ss_stage = RefCarPreparationStage.objects.filter(name=ss_stage_name).first()
                        if not ss_stage:
                            ss_stage = RefCarPreparationStage.objects.create(
                                name=ss_stage_name,
                                sort_order=2,
                                is_active=True
                            )
                        stages_created[ss_stage_name] = ss_stage
                    
                    for work in ss_works:
                        work_name = work.name
                        prep_work = RefCarPreparationWork.objects.filter(name=work_name).first()
                        
                        if not prep_work:
                            prep_work = RefCarPreparationWork.objects.create(
                                name=work_name,
                                stage=ss_stage,
                                estimated_time=int(work.normo * 60) if work.normo else 0,
                                #cost=work.price_kors or 0,
                                sort_order=1,
                                is_active=True
                            )
                        
                        CarPreparationWorkItem.objects.create(
                            preparation=preparation,
                            work=prep_work,
                            status='pending',
                            is_confirmed=False,
                            confirmed_at=timezone.now(),
                            planned_time=int(work.normo * 60) if work.normo else 0,
                            cost=work.price_kors or 0,
                            comment=f"Передано из оценки (SS)"
                        )
                
                # Создаем этап для подготовки
                if prep_works.exists():
                    prep_stage_name = "Подготовка"
                    prep_stage = None
                    
                    if prep_stage_name in stages_created:
                        prep_stage = stages_created[prep_stage_name]
                    else:
                        prep_stage = RefCarPreparationStage.objects.filter(name=prep_stage_name).first()
                        if not prep_stage:
                            prep_stage = RefCarPreparationStage.objects.create(
                                name=prep_stage_name,
                                sort_order=3,
                                is_active=True
                            )
                        stages_created[prep_stage_name] = prep_stage
                    
                    for work in prep_works:
                        work_name = work.name
                        prep_work = RefCarPreparationWork.objects.filter(name=work_name).first()
                        
                        if not prep_work:
                            prep_work = RefCarPreparationWork.objects.create(
                                name=work_name,
                                stage=prep_stage,
                                estimated_time=int(work.normo * 60) if work.normo else 0,
                                #cost=work.price_kors or 0,
                                sort_order=1,
                                is_active=True
                            )
                        
                        CarPreparationWorkItem.objects.create(
                            preparation=preparation,
                            work=prep_work,
                            status='pending',
                            is_confirmed=False,
                            confirmed_at=timezone.now(),
                            planned_time=int(work.normo * 60) if work.normo else 0,
                            cost=work.price_kors or 0,
                            comment=f"Передано из оценки (Подготовка)"
                        )
                
                # Пересчитываем прогресс
                preparation.progress_percent = preparation.calculate_progress()
                preparation.save()
                
                print(f"Successfully created preparation {preparation.id} with works from estimation {instance.id}")
                
            except Exception as e:
                print(f"❌ Error creating preparation from estimation: {e}")
                logger.error(f"Error creating preparation from estimation: {e}", exc_info=True)
                import traceback
                traceback.print_exc()
else:
    # Если модель не импортирована, создаем заглушку
    def create_car_preparation_from_estimation(*args, **kwargs):
        print("⚠️ Signal handler not registered - RegInteractivOcenka model not available")
        pass

