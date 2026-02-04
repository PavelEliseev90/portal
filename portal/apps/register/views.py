from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import DiagnosticReferenceCategory, DiagnosticReferenceItem, DiagnosticReferenceSelection

# Create your views here.

@login_required
@require_http_methods(["GET"])
def diagnostic_reference_api(request):
    """
    API для получения справочника диагностики по категории
    GET /register/diagnostic_reference/?category=engine
    """
    category_code = request.GET.get('category', '')
    
    if not category_code:
        return JsonResponse({'error': 'Category parameter required'}, status=400)
    
    try:
        category = DiagnosticReferenceCategory.objects.get(code=category_code, is_active=True)
        items = DiagnosticReferenceItem.objects.filter(
            category=category,
            is_active=True
        ).select_related('category').order_by('order', 'title')
        
        data = {
            'category': {
                'code': category.code,
                'name': category.name,
                'description': category.description,
            },
            'items': [
                {
                    'id': item.id,
                    'title': item.title,
                    'description': item.description,
                    'observation_zones': item.observation_zones,
                    'possible_causes': item.possible_causes,
                    'consequences': item.consequences,
                    'additional_info': item.additional_info,
                }
                for item in items
            ]
        }
        return JsonResponse(data, safe=False)
    except DiagnosticReferenceCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def diagnostic_reference_stats(request):
    """
    API для получения статистики использования справочника
    GET /register/diagnostic_reference/stats/
    """
    try:
        # Статистика по категориям
        category_stats = DiagnosticReferenceCategory.objects.filter(
            is_active=True
        ).annotate(
            items_count=Count('items', filter=Q(items__is_active=True)),
            selections_count=Count('items__selections')
        ).values('code', 'name', 'items_count', 'selections_count')
        
        # Топ используемых элементов
        top_items = DiagnosticReferenceItem.objects.filter(
            is_active=True
        ).annotate(
            usage_count=Count('selections')
        ).order_by('-usage_count')[:10].values(
            'id', 'title', 'category__name', 'usage_count'
        )
        
        # Статистика по категориям использования
        category_usage = DiagnosticReferenceSelection.objects.values(
            'category_code'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        data = {
            'category_stats': list(category_stats),
            'top_items': list(top_items),
            'category_usage': list(category_usage),
        }
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
