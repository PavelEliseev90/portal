"""
Чаты Аукцион Авито:
- aav_feed — общая лента (уведомления по всем лотам)
- aav_lot_{pk} — чат конкретного лота
"""
import re

from django.urls import reverse

from chats.models import Chat, ChatMessage

AAV_FEED_CHAT_SLUG = 'aav_feed'
AAV_FEED_CHAT_NAME = 'auction_avito_feed'
SYSTEM_AUTHOR = 'Система'

LOT_PK_SUFFIX_RE = re.compile(r'\n?@@lot_pk:(\d+)@@\s*$')
LOT_PATH_RE = re.compile(r'/auction_avito/lots/(\d+)/?')


def _lot_chat_slug(lot_pk: int) -> str:
    return f'aav_lot_{lot_pk}'


def strip_lot_metadata(content: str) -> str:
    if not content:
        return ''
    text = LOT_PK_SUFFIX_RE.sub('', content)
    text = LOT_PATH_RE.sub('', text)
    return text.strip()


def extract_lot_pk(content: str):
    if not content:
        return None
    match = LOT_PK_SUFFIX_RE.search(content)
    if match:
        return int(match.group(1))
    match = LOT_PATH_RE.search(content)
    if match:
        return int(match.group(1))
    return None


def append_lot_pk(content: str, lot_pk: int) -> str:
    return f'{content}\n@@lot_pk:{lot_pk}@@'


def enrich_chat_messages(messages):
    for message in messages:
        display = strip_lot_metadata(message.content)
        message.aav_display_content = display
        message.aav_display_html = display.replace('\n', '<br>')
        message.aav_lot_pk = extract_lot_pk(message.content)
    return messages


def get_or_create_feed_chat() -> Chat:
    chat = Chat.objects.filter(slug=AAV_FEED_CHAT_SLUG).first()
    if chat is None:
        chat = Chat.objects.create(name=AAV_FEED_CHAT_NAME, slug=AAV_FEED_CHAT_SLUG)
    return chat


def get_or_create_lot_chat(lot) -> Chat:
    slug = _lot_chat_slug(lot.pk)
    chat = Chat.objects.filter(slug=slug).first()
    if chat is None:
        chat = Chat.objects.create(name=str(lot.lot_id), slug=slug)
    return chat


def _lot_feed_label(lot) -> str:
    vehicle = getattr(lot, 'vehicle_avito', None)
    if vehicle and vehicle.brand_name:
        parts = [vehicle.brand_name, vehicle.model_name or '']
        if vehicle.year:
            parts.append(str(vehicle.year))
        return f"{' '.join(p for p in parts if p)} (лот {lot.lot_id})"
    return f"Лот {lot.lot_id}"


def _format_finish_at(lot) -> str:
    if lot.finish_at:
        return lot.finish_at.strftime('%d.%m.%Y %H:%M')
    return '—'


def broadcast_aav_message(chat, message_text, user=None, lot_pk=None):
    """Уведомить подписчиков WebSocket о новом сообщении."""
    if lot_pk is None:
        lot_pk = extract_lot_pk(message_text)
    display_text = strip_lot_metadata(message_text)

    if user and getattr(user, 'is_authenticated', False):
        profile = getattr(user, 'profiles', None)
        eco = bool(profile and profile.eco)
        eco_name = (profile.eco_name or '') if profile else ''
        username = user.username
        last_name = user.last_name or ''
        first_name = user.first_name or ''
    else:
        eco = False
        eco_name = SYSTEM_AUTHOR
        username = SYSTEM_AUTHOR
        last_name = ''
        first_name = ''

    message_json = {
        'chat_id': str(chat.pk),
        'name': username,
        'chat': chat.slug or '',
        'message': display_text,
        'username': username,
        'last_name': last_name,
        'first_name': first_name,
        'psevdo_name': eco_name,
        'eco': eco,
        'skip_save': True,
        'estimation_id': 0,
        'lot_pk': lot_pk,
    }
    try:
        from task_manager.views import send_message_socket
        send_message_socket(message=message_json)
    except Exception:
        pass


def broadcast_aav_feed_message(chat, message_text, user=None, lot_pk=None):
    broadcast_aav_message(chat, message_text, user=user, lot_pk=lot_pk)


def post_aav_feed_message(text, user=None, lot_pk=None) -> ChatMessage:
    chat = get_or_create_feed_chat()
    content = append_lot_pk(text, lot_pk) if lot_pk else text
    msg = ChatMessage.objects.create(
        chat=chat,
        content=content,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
    )
    broadcast_aav_feed_message(chat, content, user, lot_pk=lot_pk)
    return msg


def post_aav_lot_message(lot, text, user=None) -> ChatMessage:
    chat = get_or_create_lot_chat(lot)
    msg = ChatMessage.objects.create(
        chat=chat,
        content=text,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
    )
    broadcast_aav_message(chat, text, user)
    return msg


def notify_new_lot_in_feed(lot, *, user=None):
    """Новый лот, поступивший на перерасчёт через API."""
    label = _lot_feed_label(lot)
    finish = _format_finish_at(lot)
    feed_text = (
        f'Новый лот на перерасчёт: {label}\n'
        f'Окончание: {finish}'
    )
    lot_text = feed_text
    post_aav_feed_message(feed_text, user=user, lot_pk=lot.pk)
    post_aav_lot_message(lot, lot_text, user=user)


def notify_new_bid_in_feed(lot, new_bid, old_bid=None):
    """Новая наша ставка по лоту."""
    label = _lot_feed_label(lot)
    try:
        bid_fmt = f'{int(new_bid):,}'.replace(',', ' ')
    except (TypeError, ValueError):
        bid_fmt = str(new_bid)
    feed_text = f'Новая ставка {bid_fmt} ₽ по лоту {label}'
    if old_bid is not None:
        try:
            old_fmt = f'{int(old_bid):,}'.replace(',', ' ')
            feed_text = f'Ставка {old_fmt} → {bid_fmt} ₽ по лоту {label}'
        except (TypeError, ValueError):
            pass
    post_aav_feed_message(feed_text, lot_pk=lot.pk)
    post_aav_lot_message(lot, feed_text)


def _build_chat_params(request, chat):
    messages = chat.get_last_messages()
    if len(messages) > 80:
        messages = messages[-80:]
    enrich_chat_messages(messages)
    profile = getattr(request.user, 'profiles', None)
    return {
        'chat': chat,
        'messages': messages,
        'user': request.user,
        'can_send_messages': not (profile and profile.user_sb),
        'user_eco': bool(profile and profile.eco),
        'eco_name': (profile.eco_name or '') if profile else '',
    }


def build_aav_feed_chat_params(request):
    return _build_chat_params(request, get_or_create_feed_chat())


def build_aav_feed_embed(request):
    params = build_aav_feed_chat_params(request)
    params.update({
        'title': 'Лента Аукцион Авито',
        'open_button_label': 'Чат Авито',
        'send_url': reverse('auction_avito:feed_chat_send'),
        'prefix': 'aav_feed',
        'clickable_lots': True,
        'lot_detail_url_template': '/auction_avito/lots/__pk__/',
        'empty_text': 'В чате пока нет сообщений. Здесь появятся новые лоты и ставки.',
    })
    return params


def build_aav_lot_chat_params(request, lot):
    params = _build_chat_params(request, get_or_create_lot_chat(lot))
    params['lot'] = lot
    return params


def build_aav_lot_embed(request, lot):
    params = build_aav_lot_chat_params(request, lot)
    params.update({
        'title': f'Чат лота {lot.lot_id}',
        'open_button_label': 'Чат лота',
        'send_url': reverse('auction_avito:lot_chat_send', kwargs={'pk': lot.pk}),
        'prefix': 'aav_lot',
        'clickable_lots': False,
        'empty_text': 'Пока нет сообщений по этому лоту.',
    })
    return params
