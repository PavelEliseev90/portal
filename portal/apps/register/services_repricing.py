"""
Сервис для переоценки автомобилей
"""
from django.db.models import Q
from django.conf import settings
from refs.models import RefCarsOrganization, RefUnit, RefTypeEvaluationCarsOrganization
from .models import RegCarsRepricingHistory, RegCarsRepricingLog
from datetime import datetime


class CarsRepricingService:
    """Сервис для переоценки автомобилей"""
    
    def __init__(self, unit=None, evaluation=None):
        self.unit = unit
        self.evaluation = evaluation
    
    def get_cars_for_repricing(self):
        """Получить queryset автомобилей для переоценки"""
        qs = RefCarsOrganization.objects.filter(quantity__gt=0)  # Только автомобили в наличии
        
        # Фильтр по подразделению
        if self.unit:
            qs = qs.filter(unit=self.unit)
        
        # Фильтр по варианту управления ценой
        if self.evaluation:
            qs = qs.filter(evaluation=self.evaluation)
        else:
            # Только автомобили с установленным вариантом управления ценой
            qs = qs.exclude(evaluation__isnull=True)
        
        return qs
    
    def calculate_car_price(self, car):
        """
        Расчет новой цены для автомобиля
        
        TODO: Реализовать логику расчета цены
        Пользователь сам напишет эту функцию
        
        Args:
            car: RefCarsOrganization объект
        
        Returns:
            dict: {
                'new_price': int,  # Новая цена
                'old_price': int,  # Старая цена
                'price_difference': int,  # Разница
                'calculation_details': dict,  # Детали расчета
                'error': str or None  # Ошибка если есть
            }
        """
        # Заглушка - пользователь сам реализует
        old_price = car.price or 0
        new_price = old_price  # Пока без изменений
        price_difference = new_price - old_price
        
        return {
            'new_price': new_price,
            'old_price': old_price,
            'price_difference': price_difference,
            'calculation_details': {
                'method': 'manual',  # Пользователь заменит на свою логику
                'note': 'Функция расчета цены не реализована',
            },
            'error': None
        }
    
    def run_repricing(self, user=None):
        """Выполнить переоценку автомобилей"""
        # Создаем запись истории
        history = RegCarsRepricingHistory.objects.create(
            unit=self.unit,
            evaluation=self.evaluation,
            status='processing',
            user=user,
            is_manual=(user is not None),
            date_start=datetime.now()
        )
        
        try:
            # Получаем автомобили
            cars_qs = self.get_cars_for_repricing()
            cars = list(cars_qs)
            cars_total = len(cars)
            
            history.cars_total = cars_total
            history.save()
            
            if cars_total == 0:
                history.status = 'error'
                history.error_message = 'Не найдено автомобилей для переоценки'
                history.date_end = datetime.now()
                history.save()
                return history
            
            # Обрабатываем каждый автомобиль
            processed_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0
            
            for car in cars:
                try:
                    processed_count += 1
                    
                    # Рассчитываем новую цену
                    calculation_result = self.calculate_car_price(car)
                    
                    if calculation_result['error']:
                        # Ошибка при расчете
                        RegCarsRepricingLog.objects.create(
                            repricing_history=history,
                            car=car,
                            status='error',
                            old_price=calculation_result['old_price'],
                            error_message=calculation_result['error'],
                            calculation_details=str(calculation_result['calculation_details'])
                        )
                        error_count += 1
                    elif calculation_result['new_price'] != calculation_result['old_price']:
                        # Цена изменилась - обновляем
                        car.price = calculation_result['new_price']
                        car.save()
                        
                        RegCarsRepricingLog.objects.create(
                            repricing_history=history,
                            car=car,
                            status='success',
                            old_price=calculation_result['old_price'],
                            new_price=calculation_result['new_price'],
                            price_difference=calculation_result['price_difference'],
                            calculation_details=str(calculation_result['calculation_details'])
                        )
                        updated_count += 1
                    else:
                        # Цена не изменилась - пропускаем
                        RegCarsRepricingLog.objects.create(
                            repricing_history=history,
                            car=car,
                            status='skipped',
                            old_price=calculation_result['old_price'],
                            new_price=calculation_result['new_price'],
                            calculation_details=str(calculation_result['calculation_details'])
                        )
                        skipped_count += 1
                    
                except Exception as e:
                    RegCarsRepricingLog.objects.create(
                        repricing_history=history,
                        car=car,
                        status='error',
                        error_message=str(e)
                    )
                    error_count += 1
            
            # Обновляем историю
            history.status = 'success' if error_count == 0 else ('partial' if updated_count > 0 else 'error')
            history.cars_processed = processed_count
            history.cars_updated = updated_count
            history.cars_skipped = skipped_count
            history.cars_errors = error_count
            history.date_end = datetime.now()
            history.save()
            
            return history
            
        except Exception as e:
            history.status = 'error'
            history.error_message = str(e)
            history.date_end = datetime.now()
            history.save()
            return history

