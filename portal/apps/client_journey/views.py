from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
import os
from django.utils import timezone

from client_journey.models import ClientJourneyLink
from client_journey.services.demo import build_demo_context
from client_journey.services.journey import build_journey_context
from documents.models import DocRLK


def _ceo_presentation_path():
    return os.path.join(settings.BASE_DIR, 'portal', 'presentation', 'client_journey_presentation.html')


def ceo_presentation(request):
    """Презентация для генерального директора — slide-deck (standalone HTML)."""
    path = _ceo_presentation_path()
    if not os.path.isfile(path):
        raise Http404('Презентация не найдена')
    with open(path, encoding='utf-8') as f:
        return HttpResponse(f.read(), content_type='text/html; charset=utf-8')


def presentation(request):
    """Презентация концепции для руководства и демонстрации клиентам."""
    return render(request, 'client_journey/presentation.html', {
        'demo_url_name': 'client_journey:demo',
        'concept_points': [
            {
                'title': 'Один рабочий лист — одна сделка',
                'text': 'Вся логика строится от РЛК отдела продаж: подбор, расчёт, trade-in, заказ, выдача.',
            },
            {
                'title': 'Прозрачность без внутренней кухни',
                'text': 'Клиент видит этапы, сроки и итог, но не маржу и служебные статусы.',
            },
            {
                'title': 'Удобство с телефона',
                'text': 'Ссылка по SMS или WhatsApp — без установки приложения и сложной регистрации.',
            },
            {
                'title': 'Доверие через факты',
                'text': 'Фото приёмки, статус trade-in, допоборудование и итоговый расчёт в одном месте.',
            },
        ],
    })


def demo(request):
    """Демо-версия клиентского кабинета для презентаций."""
    ctx = build_demo_context()
    return render(request, 'client_journey/journey.html', {
        'journey': ctx,
        'page_mode': 'demo',
    })


def journey_by_token(request, token):
    """Клиентский доступ по персональной ссылке."""
    link = get_object_or_404(ClientJourneyLink, token=token, is_active=True)
    link.opens_count += 1
    link.last_opened_at = timezone.now()
    link.save(update_fields=['opens_count', 'last_opened_at'])

    ctx = build_journey_context(link.rlk)
    return render(request, 'client_journey/journey.html', {
        'journey': ctx,
        'page_mode': 'client',
        'link': link,
    })


@login_required
def preview_rlk(request, rlk_id):
    """Предпросмотр пути по реальному РЛК (для сотрудников)."""
    rlk = get_object_or_404(DocRLK, pk=rlk_id)
    ctx = build_journey_context(rlk)
    link, _ = ClientJourneyLink.objects.get_or_create(rlk=rlk)
    return render(request, 'client_journey/journey.html', {
        'journey': ctx,
        'page_mode': 'preview',
        'link': link,
        'rlk': rlk,
    })


@login_required
def create_link(request, rlk_id):
    """Создать / обновить ссылку для клиента."""
    rlk = get_object_or_404(DocRLK, pk=rlk_id)
    link, _ = ClientJourneyLink.objects.get_or_create(rlk=rlk)
    return redirect('client_journey:preview_rlk', rlk_id=rlk.pk)
