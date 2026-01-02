"""
Утилиты для работы с согласиями на обработку персональных данных
"""
from .models import PersonalDataConsent
from refs.models import RefCustomer, RefUnit
from django.conf import settings
from django.urls import reverse


def create_consent_link(phone, last_name='', first_name='', middle_name='', 
                        email='', customer=None, unit=None, comment=''):
    """
    Создает новую запись согласия и возвращает ссылку для подтверждения
    
    Args:
        phone: Номер телефона клиента
        last_name: Фамилия (опционально, может быть заполнена позже)
        first_name: Имя (опционально, может быть заполнено позже)
        middle_name: Отчество (опционально)
        email: Email адрес (опционально)
        customer: Объект RefCustomer (опционально)
        unit: Объект RefUnit (опционально)
        comment: Комментарий (опционально)
    
    Returns:
        dict: {
            'consent': объект PersonalDataConsent,
            'url': полная ссылка для подтверждения,
            'token': токен для ссылки
        }
    """
    consent = PersonalDataConsent(
        phone=phone,
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        email=email,
        customer=customer,
        unit=unit,
        comment=comment
    )
    consent.save()
    
    # Генерируем полную ссылку
    token = consent.token
    url = reverse('online:personal_data_consent', args=[token])
    full_url = f"{settings.SITE_URL.rstrip('/')}{url}" if hasattr(settings, 'SITE_URL') else url
    
    return {
        'consent': consent,
        'url': full_url,
        'token': token
    }


def get_consent_by_token(token):
    """
    Получить согласие по токену
    
    Args:
        token: Токен согласия
    
    Returns:
        PersonalDataConsent или None
    """
    try:
        return PersonalDataConsent.objects.get(token=token)
    except PersonalDataConsent.DoesNotExist:
        return None

