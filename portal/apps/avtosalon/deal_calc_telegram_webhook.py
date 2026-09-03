from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def deal_calc_telegram_webhook(request):
    """Webhook Telegram-бота согласования КП."""
    try:
        import json
        from avtosalon.deal_calc_telegram import get_runtime_config, process_telegram_update

        runtime = get_runtime_config()
        if not runtime.get('enabled'):
            return HttpResponse(status=200)

        expected = (runtime.get('webhook_secret') or '').strip()
        got = (request.headers.get('X-Telegram-Bot-Api-Secret-Token') or '').strip()
        if expected and got != expected:
            return HttpResponse(status=403)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            return HttpResponse(status=400)

        if isinstance(payload, dict):
            process_telegram_update(payload)
    except Exception:
        pass
    return HttpResponse(status=200)
