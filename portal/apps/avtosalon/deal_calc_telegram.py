"""
Telegram-уведомления и согласование КП прямо в боте.

Поток:
1) бот шлёт карточку КП с callback-кнопками;
2) пользователь жмёт кнопку → бот просит комментарий;
3) пользователь пишет комментарий → выполняется та же логика, что на портале.

Безопасность:
- по умолчанию выключено;
- FORCE_OFF / короткий timeout / ошибки не ломают email;
- действие только от пользователя с привязанным telegram_chat_id и правами;
- webhook проверяет secret_token.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

logger = logging.getLogger(__name__)

TG_ACTION_SALT = 'deal-calc-tg-action-v1'
TG_ACTION_MAX_AGE = 3 * 24 * 60 * 60
PENDING_MAX_AGE = timedelta(minutes=30)
DESKTOP_LIST_LIMIT = 12

ACTION_BUTTON_LABELS = {
    'director_approve': 'Согласовать',
    'director_send_uk': 'В УК',
    'director_reject': 'Отклонить',
    'uk_approve': 'Согласовать УК',
    'uk_reject': 'Отклонить УК',
}

ACTION_TO_CODE = {
    'director_approve': 'da',
    'director_send_uk': 'du',
    'director_reject': 'dr',
    'uk_approve': 'ua',
    'uk_reject': 'ur',
}
CODE_TO_ACTION = {v: k for k, v in ACTION_TO_CODE.items()}

# Тексты reply-кнопок меню (как подписи на рабочем столе)
MENU_PENDING_UK = 'Ожидают согласования УК'
MENU_PENDING_DIRECTOR = 'Ожидают согласования'
MENU_UK_REACHED = 'Дошли до согласования УК'
MENU_HOME = 'Меню'


def _settings_dict():
    return getattr(settings, 'DEAL_CALC_TELEGRAM', None) or {}


def _parse_chat_ids(raw):
    if not raw:
        return []
    result = []
    for part in str(raw).replace(';', ',').split(','):
        chat_id = part.strip()
        if chat_id:
            result.append(chat_id)
    return result


def normalize_telegram_chat_id(raw):
    value = (raw or '').strip()
    if not value:
        return ''
    if re.fullmatch(r'-?\d{5,20}', value):
        return value
    return ''


def get_runtime_config():
    cfg = _settings_dict()
    force_off = bool(cfg.get('force_off'))
    timeout = int(cfg.get('timeout') or 20)
    if timeout < 1:
        timeout = 1
    if timeout > 60:
        timeout = 60

    public_base_url = (
        (cfg.get('public_base_url') or '').rstrip('/')
        or getattr(settings, 'MYKORS_PORTAL_PUBLIC_BASE_URL', '')
        or 'https://ah.kors-group.com'
    )
    env_token = (cfg.get('bot_token') or '').strip()
    env_chat_ids = _parse_chat_ids(cfg.get('chat_ids') or '')
    env_proxy = (cfg.get('proxy') or '').strip()

    enabled = False
    bot_token = env_token
    broadcast_chat_ids = list(env_chat_ids)
    bot_username = ''
    webhook_secret = ''
    proxy = env_proxy

    empty = {
        'enabled': False,
        'bot_token': '',
        'broadcast_chat_ids': [],
        'timeout': timeout,
        'public_base_url': public_base_url,
        'bot_username': '',
        'webhook_secret': '',
        'proxy': '',
    }

    if force_off:
        return empty

    try:
        from prices_car.models import DealCalcTelegramSettings

        row = DealCalcTelegramSettings.load()
        enabled = bool(row.enabled)
        if (row.bot_token or '').strip():
            bot_token = row.bot_token.strip()
        db_chats = _parse_chat_ids(row.chat_ids)
        if db_chats:
            broadcast_chat_ids = db_chats
        bot_username = (row.bot_username or '').strip().lstrip('@')
        webhook_secret = (row.webhook_secret or '').strip()
        if (getattr(row, 'api_proxy', None) or '').strip():
            proxy = row.api_proxy.strip()
    except Exception:
        logger.exception('deal_calc_telegram: failed to load settings')
        enabled = False

    if not bot_token:
        enabled = False

    return {
        'enabled': enabled,
        'bot_token': bot_token,
        'broadcast_chat_ids': broadcast_chat_ids,
        'timeout': timeout,
        'public_base_url': public_base_url,
        'bot_username': bot_username,
        'webhook_secret': webhook_secret,
        'proxy': proxy,
    }


def _requests_proxies(runtime=None):
    runtime = runtime or get_runtime_config()
    proxy = (runtime.get('proxy') or '').strip()
    if not proxy:
        return None
    return {'http': proxy, 'https': proxy}


def is_telegram_notify_enabled():
    try:
        return bool(get_runtime_config().get('enabled'))
    except Exception:
        return False


def get_bot_username():
    try:
        return get_runtime_config().get('bot_username') or ''
    except Exception:
        return ''


def webhook_url(public_base_url=None):
    base = (public_base_url or get_runtime_config().get('public_base_url') or '').rstrip('/')
    return '{}/api/telegram/deal-calc-webhook/'.format(base)


def register_telegram_webhook():
    """Зарегистрировать webhook в Telegram. Возвращает (ok, message)."""
    runtime = get_runtime_config()
    if not runtime['bot_token']:
        return False, 'Не задан токен бота.'
    if not runtime['webhook_secret']:
        return False, 'Не задан секрет webhook — сохраните настройки ещё раз.'
    url = webhook_url(runtime['public_base_url'])
    try:
        response = requests.post(
            'https://api.telegram.org/bot{}/setWebhook'.format(runtime['bot_token']),
            json={
                'url': url,
                'secret_token': runtime['webhook_secret'],
                'allowed_updates': ['message', 'callback_query'],
                'drop_pending_updates': False,
            },
            timeout=runtime['timeout'],
            proxies=_requests_proxies(runtime),
        )
        data = response.json() if response.content else {}
        if response.status_code == 200 and data.get('ok'):
            return True, 'Webhook установлен: {}'.format(url)
        return False, 'Ошибка setWebhook: {}'.format(data or response.text)
    except Exception as exc:
        logger.exception('deal_calc_telegram: setWebhook failed')
        hint = ''
        if not runtime.get('proxy'):
            hint = (
                ' Сервер не достучался до api.telegram.org. '
                'Укажите прокси в настройках или зарегистрируйте webhook '
                'с ПК, где Telegram доступен (curl setWebhook).'
            )
        return False, 'Ошибка setWebhook: {}{}'.format(exc, hint)


def delete_telegram_webhook(drop_pending=False):
    """Снять webhook (нужно для long polling getUpdates)."""
    runtime = get_runtime_config()
    if not runtime['bot_token']:
        return False, 'Не задан токен бота.'
    try:
        response = requests.post(
            'https://api.telegram.org/bot{}/deleteWebhook'.format(runtime['bot_token']),
            json={'drop_pending_updates': bool(drop_pending)},
            timeout=runtime['timeout'],
            proxies=_requests_proxies(runtime),
        )
        data = response.json() if response.content else {}
        if response.status_code == 200 and data.get('ok'):
            return True, 'Webhook снят. Дальше используйте: python manage.py deal_calc_telegram_poll'
        return False, 'Ошибка deleteWebhook: {}'.format(data or response.text)
    except Exception as exc:
        logger.exception('deal_calc_telegram: deleteWebhook failed')
        return False, 'Ошибка deleteWebhook: {}'.format(exc)


def fetch_telegram_updates(offset=None, timeout_sec=25, runtime=None):
    """Один long-poll getUpdates. Возвращает (ok, updates_list, error_message)."""
    runtime = runtime or get_runtime_config()
    if not runtime.get('bot_token'):
        return False, [], 'Не задан токен бота.'
    payload = {
        'timeout': max(1, min(int(timeout_sec or 25), 50)),
        'allowed_updates': json.dumps(['message', 'callback_query']),
    }
    if offset is not None:
        payload['offset'] = int(offset)
    # HTTP timeout чуть больше long-poll timeout
    http_timeout = payload['timeout'] + max(10, int(runtime.get('timeout') or 20))
    try:
        response = requests.get(
            'https://api.telegram.org/bot{}/getUpdates'.format(runtime['bot_token']),
            params=payload,
            timeout=http_timeout,
            proxies=_requests_proxies(runtime),
        )
        data = response.json() if response.content else {}
        if response.status_code != 200 or not data.get('ok'):
            return False, [], 'Ошибка getUpdates: {}'.format(data or response.text)
        updates = data.get('result') or []
        if not isinstance(updates, list):
            updates = []
        return True, updates, ''
    except Exception as exc:
        logger.exception('deal_calc_telegram: getUpdates failed')
        return False, [], 'Ошибка getUpdates: {}'.format(exc)


def run_telegram_polling_loop(
    *,
    poll_timeout=25,
    idle_sleep=1,
    max_iterations=None,
    stop_event=None,
):
    """
    Long polling цикл. Сервер сам тянет updates у Telegram —
    работает, когда Telegram не может достучаться до webhook (Connection timed out).

    При сетевых ошибках делает паузу с backoff и продолжает работу
    (не завершает процесс).
    """
    import time

    runtime = get_runtime_config()
    if not runtime.get('enabled'):
        logger.warning('deal_calc_telegram poll: disabled in settings')
        return
    if not runtime.get('bot_token'):
        logger.warning('deal_calc_telegram poll: no bot token')
        return

    offset = None
    iterations = 0
    fail_streak = 0
    logger.info(
        'deal_calc_telegram poll: started poll_timeout=%s proxy=%s',
        poll_timeout,
        bool(runtime.get('proxy')),
    )
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        try:
            runtime = get_runtime_config()
            if not runtime.get('enabled') or not runtime.get('bot_token'):
                logger.warning('deal_calc_telegram poll: stopped (disabled or no token)')
                break

            ok, updates, err = fetch_telegram_updates(
                offset=offset,
                timeout_sec=poll_timeout,
                runtime=runtime,
            )
            if not ok:
                fail_streak += 1
                # 1, 2, 4, 8, 16, 32, max 60 сек — сеть/Telegram отвалились
                sleep_sec = min(60, max(int(idle_sleep or 1), 2 ** min(fail_streak, 5)))
                logger.warning(
                    'deal_calc_telegram poll: %s (streak=%s, sleep=%ss)',
                    err,
                    fail_streak,
                    sleep_sec,
                )
                time.sleep(sleep_sec)
                continue

            fail_streak = 0
            for update in updates:
                try:
                    update_id = int(update.get('update_id'))
                    offset = update_id + 1
                except (TypeError, ValueError):
                    continue
                try:
                    process_telegram_update(update)
                except Exception:
                    logger.exception(
                        'deal_calc_telegram poll: update failed update_id=%s',
                        update.get('update_id'),
                    )
        except Exception:
            fail_streak += 1
            sleep_sec = min(60, max(5, 2 ** min(fail_streak, 5)))
            logger.exception(
                'deal_calc_telegram poll: unexpected error (streak=%s, sleep=%ss)',
                fail_streak,
                sleep_sec,
            )
            time.sleep(sleep_sec)



NOTIFY_KIND_PENDING = 'pending'
NOTIFY_KIND_AUTO_APPROVED = 'auto_approved'
NOTIFY_KIND_RESULTS = 'results'

NOTIFY_PREF_FIELDS = {
    NOTIFY_KIND_PENDING: 'telegram_notify_pending',
    NOTIFY_KIND_AUTO_APPROVED: 'telegram_notify_auto_approved',
    NOTIFY_KIND_RESULTS: 'telegram_notify_results',
}


def chat_ids_from_users(users, notify_kind=None):
    """chat_id пользователей с учётом персональных настроек уведомлений."""
    ids = []
    seen = set()
    pref_field = NOTIFY_PREF_FIELDS.get(notify_kind) if notify_kind else None
    for user in users or []:
        try:
            profile = getattr(user, 'profiles', None)
            if pref_field and profile is not None:
                if not bool(getattr(profile, pref_field, True)):
                    continue
            chat_id = normalize_telegram_chat_id(
                getattr(profile, 'telegram_chat_id', '') if profile else ''
            )
            if chat_id and chat_id not in seen:
                seen.add(chat_id)
                ids.append(chat_id)
        except Exception:
            continue
    return ids


def resolve_portal_user_by_telegram_ids(*candidate_ids):
    from profiles.models import Profiles

    for raw in candidate_ids:
        chat_id = normalize_telegram_chat_id(str(raw) if raw is not None else '')
        if not chat_id:
            continue
        profile = (
            Profiles.objects
            .select_related('user')
            .filter(telegram_chat_id=chat_id, user__is_active=True)
            .first()
        )
        if profile and profile.user_id:
            return profile.user, chat_id
    return None, ''


def _fmt_money(value):
    try:
        return '{:,}'.format(int(value or 0)).replace(',', ' ')
    except (TypeError, ValueError):
        return str(value or 0)


def _car_lines(calc):
    car = getattr(calc, 'car', None)
    lines = []
    if not car:
        return lines
    try:
        mark = ''
        model = ''
        modification = ''
        complectation = '-'
        mod = getattr(car, 'modification_autoru', None)
        if mod and getattr(mod, 'model', None):
            if getattr(mod.model, 'mark', None):
                mark = mod.model.mark.name or ''
            model = mod.model.name or ''
            modification = mod.name or ''
        comp = getattr(car, 'complectation_autoru', None)
        if comp:
            complectation = comp.name or '-'
        car_title = '{} {}'.format(mark, model).strip() or (car.name or '')
        lines.append('Авто: {}'.format(car_title))
        if car.vin:
            lines.append('VIN: {}'.format(str(car.vin).upper()))
        if getattr(car, 'unit', None) and car.unit:
            lines.append('ДЦ: {}'.format(car.unit.name))
        if getattr(car, 'year', None):
            lines.append('Год: {}'.format(car.year))
        if modification:
            lines.append('Модификация: {}'.format(modification))
        lines.append('Комплектация: {}'.format(complectation))
    except Exception:
        logger.exception('deal_calc_telegram: car lines failed calc_id=%s', getattr(calc, 'pk', None))
        if getattr(car, 'vin', None):
            lines.append('VIN: {}'.format(car.vin))
    return lines


def build_calc_portal_url(calc, public_base_url):
    return '{}/cars/deal/calculation/{}/'.format(public_base_url.rstrip('/'), calc.pk)


def build_action_token(calc_id, action):
    signer = TimestampSigner(salt=TG_ACTION_SALT)
    return signer.sign('{}:{}'.format(calc_id, action))


def unsign_action_token(token, max_age=TG_ACTION_MAX_AGE):
    signer = TimestampSigner(salt=TG_ACTION_SALT)
    value = signer.unsign(token, max_age=max_age)
    calc_id_str, action = value.split(':', 1)
    return int(calc_id_str), action


def build_action_url(public_base_url, calc_id, action):
    token = build_action_token(calc_id, action)
    return '{}/cars/deal/calculation/tg-action/{}/'.format(
        public_base_url.rstrip('/'),
        token,
    )


def build_callback_data(calc_id, action):
    code = ACTION_TO_CODE.get(action)
    if not code:
        return ''
    data = 'kp:{}:{}'.format(calc_id, code)
    if len(data.encode('utf-8')) > 64:
        return ''
    return data


def parse_callback_data(data):
    parts = (data or '').split(':')
    if len(parts) != 3 or parts[0] != 'kp':
        return None, None
    try:
        calc_id = int(parts[1])
    except (TypeError, ValueError):
        return None, None
    action = CODE_TO_ACTION.get(parts[2])
    if not action:
        return None, None
    return calc_id, action


def build_telegram_message(calc, title, comment=''):
    number = getattr(calc, 'number', None) or calc.pk
    lines = [
        'КП #{}'.format(number),
        title,
    ]
    lines.extend(_car_lines(calc))
    lines.append('КВП: {}'.format(_fmt_money(getattr(calc, 'kvp', 0))))
    km_raschet = getattr(calc, 'km_raschet', None)
    if km_raschet is not None:
        lines.append('КМ по правилу: {}'.format(_fmt_money(km_raschet)))
    text = (comment or '').strip()
    if text:
        if len(text) > 800:
            text = text[:797] + '...'
        lines.append('Комментарий: {}'.format(text))
    lines.append('')
    lines.append('Нажмите кнопку, затем напишите комментарий в этот чат.')
    lines.append('Отмена: /cancel')
    return '\n'.join(lines)


def build_reply_markup(calc, public_base_url, actions=None, include_open_button=True):
    rows = []
    action_row = []
    for action in actions or []:
        label = ACTION_BUTTON_LABELS.get(action)
        callback_data = build_callback_data(calc.pk, action)
        if not label or not callback_data:
            continue
        action_row.append({'text': label, 'callback_data': callback_data})
        if len(action_row) >= 3:
            rows.append(action_row)
            action_row = []
    if action_row:
        rows.append(action_row)
    if include_open_button:
        rows.append([{
            'text': 'Открыть КП на портале',
            'url': build_calc_portal_url(calc, public_base_url),
        }])
    if not rows:
        return None
    return {'inline_keyboard': rows}


def _api_call(method, payload, runtime=None):
    runtime = runtime or get_runtime_config()
    token = runtime.get('bot_token') or ''
    if not token:
        return False
    try:
        response = requests.post(
            'https://api.telegram.org/bot{}/{}'.format(token, method),
            data=payload,
            timeout=runtime.get('timeout') or 20,
            proxies=_requests_proxies(runtime),
        )
        if response.status_code != 200:
            logger.warning(
                'deal_calc_telegram api %s failed status=%s body=%s proxy=%s',
                method,
                response.status_code,
                (response.text or '')[:300],
                bool(runtime.get('proxy')),
            )
            return False
        data = {}
        try:
            data = response.json() if response.content else {}
        except Exception:
            data = {}
        if data and data.get('ok') is False:
            logger.warning(
                'deal_calc_telegram api %s ok=false body=%s',
                method,
                (response.text or '')[:300],
            )
            return False
        return True
    except Exception:
        logger.exception(
            'deal_calc_telegram api %s error proxy=%s',
            method,
            bool((runtime or {}).get('proxy')),
        )
        return False


def _send_telegram_message(
    bot_token,
    chat_id,
    text,
    reply_markup=None,
    timeout=None,
    force_reply=False,
    runtime=None,
):
    """Отправить сообщение. Важно: всегда берём proxy из runtime (иначе сервер
    без прямого доступа к api.telegram.org молча не отвечает на /start)."""
    runtime = dict(runtime or get_runtime_config())
    if bot_token:
        runtime['bot_token'] = bot_token
    if timeout is not None:
        runtime['timeout'] = timeout
    payload = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True,
    }
    if force_reply:
        payload['reply_markup'] = json.dumps(
            {'force_reply': True, 'selective': True},
            ensure_ascii=False,
        )
    elif reply_markup is not None:
        payload['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    return _api_call('sendMessage', payload, runtime=runtime)


def get_telegram_webhook_info():
    """getWebhookInfo — диагностика. Возвращает (ok, message, data)."""
    runtime = get_runtime_config()
    if not runtime['bot_token']:
        return False, 'Не задан токен бота.', {}
    try:
        response = requests.get(
            'https://api.telegram.org/bot{}/getWebhookInfo'.format(runtime['bot_token']),
            timeout=runtime['timeout'],
            proxies=_requests_proxies(runtime),
        )
        data = response.json() if response.content else {}
        if response.status_code != 200 or not data.get('ok'):
            return False, 'Ошибка getWebhookInfo: {}'.format(data or response.text), data
        info = data.get('result') or {}
        lines = [
            'url: {}'.format(info.get('url') or '—'),
            'pending_update_count: {}'.format(info.get('pending_update_count')),
            'last_error_date: {}'.format(info.get('last_error_date') or '—'),
            'last_error_message: {}'.format(info.get('last_error_message') or '—'),
            'has_custom_certificate: {}'.format(info.get('has_custom_certificate')),
            'max_connections: {}'.format(info.get('max_connections')),
            'ожидаемый URL портала: {}'.format(webhook_url(runtime['public_base_url'])),
            'прокси для исходящих: {}'.format(runtime.get('proxy') or 'не задан'),
        ]
        return True, '\n'.join(lines), info
    except Exception as exc:
        logger.exception('deal_calc_telegram: getWebhookInfo failed')
        return False, 'Ошибка getWebhookInfo: {}'.format(exc), {}



def build_desktop_reply_keyboard(role):
    from avtosalon.deal_calc_desktop import ROLE_DIRECTOR, ROLE_UK

    if role == ROLE_UK:
        rows = [
            [{'text': MENU_PENDING_UK}],
            [{'text': MENU_UK_REACHED}],
            [{'text': MENU_HOME}],
        ]
    elif role == ROLE_DIRECTOR:
        rows = [
            [{'text': MENU_PENDING_DIRECTOR}],
            [{'text': MENU_HOME}],
        ]
    else:
        return None
    return {
        'keyboard': rows,
        'resize_keyboard': True,
        'is_persistent': True,
    }


def build_desktop_inline_menu(role):
    from avtosalon.deal_calc_desktop import ROLE_DIRECTOR, ROLE_UK

    rows = []
    if role == ROLE_UK:
        rows.append([
            {'text': MENU_PENDING_UK, 'callback_data': 'ds:pending'},
            {'text': MENU_UK_REACHED, 'callback_data': 'ds:uk_reached'},
        ])
    elif role == ROLE_DIRECTOR:
        rows.append([
            {'text': MENU_PENDING_DIRECTOR, 'callback_data': 'ds:pending'},
        ])
    else:
        return None
    return {'inline_keyboard': rows}


def resolve_menu_section(text, role):
    from avtosalon.deal_calc_desktop import (
        ROLE_DIRECTOR,
        ROLE_UK,
        SECTION_PENDING,
        SECTION_UK_REACHED,
        section_allowed_for_role,
    )

    mapping = {
        MENU_PENDING_UK: SECTION_PENDING,
        MENU_PENDING_DIRECTOR: SECTION_PENDING,
        MENU_UK_REACHED: SECTION_UK_REACHED,
        '/pending': SECTION_PENDING,
        '/uk_reached': SECTION_UK_REACHED,
        '/pending_uk': SECTION_PENDING,
    }
    section = mapping.get((text or '').strip())
    if not section:
        return None
    if not section_allowed_for_role(section, role):
        return None
    # Кнопка «Ожидают согласования УК» только для УК
    if text == MENU_PENDING_UK and role != ROLE_UK:
        return None
    if text == MENU_PENDING_DIRECTOR and role != ROLE_DIRECTOR:
        return None
    return section


def actions_for_listed_calc(calc, role):
    from avtosalon.deal_calc_desktop import ROLE_DIRECTOR, ROLE_UK
    from prices_car.models import CarCalculations

    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    if role == ROLE_UK and status == CarCalculations.SOGLASOVANIE_PENDING_UK:
        return ['uk_approve', 'uk_reject']
    if role == ROLE_DIRECTOR and status in (
        CarCalculations.SOGLASOVANIE_PENDING, '', None,
    ):
        return ['director_approve', 'director_send_uk', 'director_reject']
    return None


def build_desktop_card_text(calc, section_label=''):
    number = getattr(calc, 'number', None) or calc.pk
    status = ''
    try:
        status = calc.get_soglasovanie_status_display() or ''
    except Exception:
        status = calc.soglasovanie_status or ''
    lines = []
    if section_label:
        lines.append(section_label)
    lines.append('КП #{}'.format(number))
    if status:
        lines.append('Статус: {}'.format(status))
    lines.extend(_car_lines(calc))
    lines.append('КВП: {}'.format(_fmt_money(getattr(calc, 'kvp', 0))))
    if getattr(calc, 'director_approve_comment', None):
        comment = str(calc.director_approve_comment).strip()
        if comment:
            if len(comment) > 300:
                comment = comment[:297] + '...'
            lines.append('Комментарий ДЦ: {}'.format(comment))
    return '\n'.join(lines)


def send_desktop_section_cards(user, chat_id, section, runtime=None):
    """Прислать карточки КП из очереди рабочего стола (только просмотр + кнопки если актуально)."""
    runtime = runtime or get_runtime_config()
    from avtosalon.deal_calc_desktop import (
        get_desktop_role,
        get_section_label,
        get_section_queryset,
        get_section_today_count,
        section_allowed_for_role,
    )

    role = get_desktop_role(user)
    if not role or not section_allowed_for_role(section, role):
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            'Нет доступа к этому списку.',
            timeout=runtime['timeout'],
            reply_markup=build_desktop_reply_keyboard(role) if role else None,
            runtime=runtime,
        )
        return False

    label = get_section_label(section, role)
    qs = get_section_queryset(user, role, section)
    total = qs.count()
    today = get_section_today_count(user, role, section)
    items = list(qs[:DESKTOP_LIST_LIMIT])

    header = '{}\nВсего: {} · сегодня: {}\nПоказываю до {} карточек.'.format(
        label, total, today, DESKTOP_LIST_LIMIT,
    )
    if total == 0:
        header = '{}\nСписок пуст.'.format(label)

    _send_telegram_message(
        runtime['bot_token'],
        chat_id,
        header,
        timeout=runtime['timeout'],
        reply_markup=build_desktop_reply_keyboard(role),
        runtime=runtime,
    )

    for calc in items:
        actions = actions_for_listed_calc(calc, role)
        markup = build_reply_markup(
            calc,
            runtime['public_base_url'],
            actions=actions,
            include_open_button=True,
        )
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            build_desktop_card_text(calc),
            reply_markup=markup,
            timeout=runtime['timeout'],
            runtime=runtime,
        )

    if total > DESKTOP_LIST_LIMIT:
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            'Показано {} из {}. Полный список — на рабочем столе портала.'.format(
                DESKTOP_LIST_LIMIT, total,
            ),
            timeout=runtime['timeout'],
            runtime=runtime,
        )
    return True


def send_bot_home(user, chat_id, runtime=None):
    runtime = runtime or get_runtime_config()
    from avtosalon.deal_calc_desktop import get_desktop_role, user_has_deal_calc_director_desktop_access

    name = user.get_full_name() or user.username
    if not user_has_deal_calc_director_desktop_access(user):
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            'Привязка есть ({}). Ожидайте уведомления по КП.'.format(name),
            timeout=runtime['timeout'],
            runtime=runtime,
        )
        return

    role = get_desktop_role(user)
    keyboard = build_desktop_reply_keyboard(role)
    inline = build_desktop_inline_menu(role)
    text = (
        'Привязка есть ({}).\n'
        'Выберите очередь — пришлю карточки КП для просмотра.\n'
        'Можно согласовывать прямо из карточки (кнопка → комментарий).'
    ).format(name)
    _send_telegram_message(
        runtime['bot_token'],
        chat_id,
        text,
        reply_markup=keyboard,
        timeout=runtime['timeout'],
        runtime=runtime,
    )
    if inline:
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            'Быстрые кнопки:',
            reply_markup=inline,
            timeout=runtime['timeout'],
            runtime=runtime,
        )


def answer_callback_query(callback_id, text='', show_alert=False, runtime=None):
    payload = {
        'callback_query_id': callback_id,
        'text': (text or '')[:200],
        'show_alert': 'true' if show_alert else 'false',
    }
    return _api_call('answerCallbackQuery', payload, runtime=runtime)


def clear_pending_for_chat(chat_id):
    from prices_car.models import DealCalcTelegramPendingAction
    DealCalcTelegramPendingAction.objects.filter(chat_id=str(chat_id)).delete()


def set_pending_action(chat_id, user, calc, action):
    from prices_car.models import DealCalcTelegramPendingAction

    chat_id = str(chat_id)
    clear_pending_for_chat(chat_id)
    return DealCalcTelegramPendingAction.objects.create(
        chat_id=chat_id,
        user=user,
        calc=calc,
        action=action,
    )


def get_pending_action(chat_id):
    from prices_car.models import DealCalcTelegramPendingAction

    pending = (
        DealCalcTelegramPendingAction.objects
        .select_related('user', 'calc', 'calc__car')
        .filter(chat_id=str(chat_id))
        .order_by('-created_at')
        .first()
    )
    if not pending:
        return None
    if pending.created_at < timezone.now() - PENDING_MAX_AGE:
        pending.delete()
        return None
    return pending


def notify_calc_telegram(
    calc,
    title,
    comment='',
    actions=None,
    recipient_users=None,
    include_open_button=True,
    notify_kind=None,
):
    try:
        if not calc or not getattr(calc, 'pk', None):
            return False

        runtime = get_runtime_config()
        if not runtime['enabled']:
            return False

        chat_ids = []
        seen = set()
        for chat_id in chat_ids_from_users(recipient_users, notify_kind=notify_kind):
            if chat_id not in seen:
                seen.add(chat_id)
                chat_ids.append(chat_id)
        for chat_id in runtime['broadcast_chat_ids']:
            if chat_id not in seen:
                seen.add(chat_id)
                chat_ids.append(chat_id)

        if not chat_ids:
            return False

        text = build_telegram_message(calc, title, comment=comment)
        reply_markup = build_reply_markup(
            calc,
            runtime['public_base_url'],
            actions=actions,
            include_open_button=include_open_button,
        )

        ok_any = False
        for chat_id in chat_ids:
            try:
                if _send_telegram_message(
                    runtime['bot_token'],
                    chat_id,
                    text,
                    reply_markup=reply_markup,
                    timeout=runtime['timeout'],
                    runtime=runtime,
                ):
                    ok_any = True
            except Exception:
                logger.exception(
                    'deal_calc_telegram: send error calc_id=%s chat_id=%s',
                    calc.pk,
                    chat_id,
                )
        return ok_any
    except Exception:
        logger.exception(
            'deal_calc_telegram: notify failed calc_id=%s',
            getattr(calc, 'pk', None),
        )
        return False


def notify_pending_director_telegram(calc, comment='', recipient_users=None):
    number = getattr(calc, 'number', None) or getattr(calc, 'pk', '')
    title = 'Требуется согласование директором ДЦ'
    text = comment or 'Согласование расчета продажи автомобиля #{}'.format(number)
    return notify_calc_telegram(
        calc,
        title,
        comment=text,
        actions=['director_approve', 'director_send_uk', 'director_reject'],
        recipient_users=recipient_users,
        notify_kind=NOTIFY_KIND_PENDING,
    )


def notify_auto_approved_telegram(calc, comment='', recipient_users=None):
    return notify_calc_telegram(
        calc,
        'Согласовано автоматически',
        comment=comment,
        actions=None,
        recipient_users=recipient_users,
        notify_kind=NOTIFY_KIND_AUTO_APPROVED,
    )


def notify_result_telegram(calc, event, comment='', recipient_users=None):
    titles = {
        'director_approve': 'Согласовано директором ДЦ',
        'director_send_uk': 'Отправлено на согласование УК',
        'director_reject': 'Отказ директором ДЦ',
        'uk_approve': 'Согласовано УК',
        'uk_reject': 'Отказ УК',
    }
    title = titles.get(event)
    if not title:
        return False
    actions = None
    if event == 'director_send_uk':
        actions = ['uk_approve', 'uk_reject']
        return notify_calc_telegram(
            calc,
            title,
            comment=comment,
            actions=actions,
            recipient_users=recipient_users,
            # УК-очередь — это действие «требуется согласование»
            notify_kind=NOTIFY_KIND_PENDING,
        )
    return notify_calc_telegram(
        calc,
        title,
        comment=comment,
        actions=actions,
        recipient_users=recipient_users,
        notify_kind=NOTIFY_KIND_RESULTS,
    )


def token_errors_message(exc):
    if isinstance(exc, SignatureExpired):
        return 'Ссылка из Telegram устарела. Откройте КП на портале.'
    if isinstance(exc, BadSignature):
        return 'Некорректная ссылка из Telegram.'
    return 'Не удалось открыть действие из Telegram.'


def handle_bot_callback_query(callback, runtime=None):
    runtime = runtime or get_runtime_config()
    callback_id = callback.get('id')
    data = callback.get('data') or ''
    from_user = callback.get('from') or {}
    message = callback.get('message') or {}
    chat = message.get('chat') or {}

    user, chat_id = resolve_portal_user_by_telegram_ids(
        from_user.get('id'),
        chat.get('id'),
    )
    if not user:
        answer_callback_query(
            callback_id,
            'Telegram не привязан к учётке портала. Укажите chat ID в профиле.',
            show_alert=True,
            runtime=runtime,
        )
        return

    # Очереди рабочего стола
    if data.startswith('ds:'):
        from avtosalon.deal_calc_desktop import SECTION_PENDING, SECTION_UK_REACHED

        section_map = {
            'ds:pending': SECTION_PENDING,
            'ds:uk_reached': SECTION_UK_REACHED,
        }
        section = section_map.get(data)
        if not section:
            answer_callback_query(callback_id, 'Неизвестная очередь.', show_alert=True, runtime=runtime)
            return
        answer_callback_query(callback_id, 'Загружаю…', runtime=runtime)
        clear_pending_for_chat(chat_id)
        send_desktop_section_cards(user, chat_id, section, runtime=runtime)
        return

    calc_id, action = parse_callback_data(data)
    if not calc_id or not action:
        answer_callback_query(callback_id, 'Некорректная кнопка.', show_alert=True, runtime=runtime)
        return

    from prices_car.models import CarCalculations

    try:
        calc = CarCalculations.objects.select_related('car', 'car__unit', 'unit').get(pk=calc_id)
    except CarCalculations.DoesNotExist:
        answer_callback_query(callback_id, 'КП не найдено.', show_alert=True, runtime=runtime)
        return

    label = ACTION_BUTTON_LABELS.get(action, action)
    number = calc.number or calc.pk
    set_pending_action(chat_id, user, calc, action)
    answer_callback_query(callback_id, 'Жду комментарий…', runtime=runtime)
    _send_telegram_message(
        runtime['bot_token'],
        chat_id,
        (
            'КП #{}\nДействие: {}\n\n'
            'Напишите комментарий одним сообщением.\n'
            'Без комментария согласование не выполнится.\n'
            'Отмена: /cancel'
        ).format(number, label),
        timeout=runtime['timeout'],
        force_reply=True,
        runtime=runtime,
    )


def handle_bot_message(message, runtime=None):
    runtime = runtime or get_runtime_config()
    chat = message.get('chat') or {}
    from_user = message.get('from') or {}
    text = (message.get('text') or '').strip()
    if not text:
        return

    user, chat_id = resolve_portal_user_by_telegram_ids(
        from_user.get('id'),
        chat.get('id'),
    )
    # Даже без привязки отвечаем на /start
    if text.startswith('/start') or text == MENU_HOME or text.startswith('/menu'):
        if user:
            send_bot_home(user, chat_id or str(chat.get('id')), runtime=runtime)
        else:
            _send_telegram_message(
                runtime['bot_token'],
                chat.get('id'),
                (
                    'Бот согласования КП портала.\n'
                    'Привязка Telegram только в профиле портала '
                    '(редактирование профиля) или через администратора.\n'
                    '1) Узнайте chat ID у @userinfobot\n'
                    '2) Укажите его в профиле / попросите админа\n'
                    '3) После привязки: /start — меню очередей и согласование'
                ),
                timeout=runtime['timeout'],
                runtime=runtime,
            )
        return

    if not user:
        return

    if text.startswith('/cancel'):
        clear_pending_for_chat(chat_id)
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            'Отменено.',
            timeout=runtime['timeout'],
            runtime=runtime,
        )
        return

    # Кнопки/команды очередей рабочего стола (приоритетнее комментария)
    from avtosalon.deal_calc_desktop import get_desktop_role

    role = get_desktop_role(user)
    section = resolve_menu_section(text, role) if role else None
    if section:
        clear_pending_for_chat(chat_id)
        send_desktop_section_cards(user, chat_id, section, runtime=runtime)
        return

    pending = get_pending_action(chat_id)
    if not pending:
        # Неизвестная команда — подсказка меню
        send_bot_home(user, chat_id, runtime=runtime)
        return

    if pending.user_id != user.pk:
        clear_pending_for_chat(chat_id)
        _send_telegram_message(
            runtime['bot_token'],
            chat_id,
            'Сессия согласования сброшена. Нажмите кнопку ещё раз.',
            timeout=runtime['timeout'],
            runtime=runtime,
        )
        return

    comment = text
    if len(comment) > 2000:
        comment = comment[:2000]

    calc = pending.calc
    action = pending.action
    clear_pending_for_chat(chat_id)

    cumulative_data = None
    if calc.car_id:
        try:
            cumulative_data = calc.car.cumulative_data()
        except Exception:
            cumulative_data = None

    from avtosalon.deal_calc_approval import apply_deal_calc_approval

    ok, message_text = apply_deal_calc_approval(
        user, calc, action, comment, cumulative_data,
    )
    _send_telegram_message(
        runtime['bot_token'],
        chat_id,
        ('✅ ' if ok else '❌ ') + message_text,
        timeout=runtime['timeout'],
        runtime=runtime,
    )


def process_telegram_update(update):
    """Обработать update от Telegram. Никогда не бросает наружу."""
    try:
        runtime = get_runtime_config()
        if not runtime['enabled'] or not runtime['bot_token']:
            return
        if 'callback_query' in update:
            handle_bot_callback_query(update['callback_query'], runtime=runtime)
        elif 'message' in update:
            handle_bot_message(update['message'], runtime=runtime)
    except Exception:
        logger.exception('deal_calc_telegram: process_telegram_update failed')
