import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def deal_calc_telegram_webhook(request):
    """Webhook Telegram-бота согласования КП."""
    try:
        import json
        from avtosalon.deal_calc_telegram import get_runtime_config, process_telegram_update

        runtime = get_runtime_config()
        if not runtime.get('enabled'):
            logger.warning('deal_calc_telegram webhook: disabled, ignore update')
            return HttpResponse(status=200)

        expected = (runtime.get('webhook_secret') or '').strip()
        got = (request.headers.get('X-Telegram-Bot-Api-Secret-Token') or '').strip()
        if expected and got != expected:
            logger.warning(
                'deal_calc_telegram webhook: secret mismatch '
                '(got_len=%s expected_len=%s) — перерегистрируйте webhook',
                len(got),
                len(expected),
            )
            return HttpResponse(status=403)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            logger.warning('deal_calc_telegram webhook: bad json body')
            return HttpResponse(status=400)

        if isinstance(payload, dict):
            update_id = payload.get('update_id')
            kind = (
                'callback_query' if 'callback_query' in payload
                else 'message' if 'message' in payload
                else 'other'
            )
            logger.info(
                'deal_calc_telegram webhook: update_id=%s kind=%s proxy=%s',
                update_id,
                kind,
                bool(runtime.get('proxy')),
            )
            process_telegram_update(payload)
    except Exception:
        logger.exception('deal_calc_telegram webhook: unhandled error')
    return HttpResponse(status=200)
