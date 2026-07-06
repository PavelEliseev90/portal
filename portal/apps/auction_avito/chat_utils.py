"""
Общий чат ленты Аукцион Авито (slug aav_feed) — изолирован от rlk_* и car_*.
"""
from django.urls import reverse

from chats.models import Chat, ChatMessage

AAV_FEED_CHAT_SLUG = 'aav_feed'
AAV_FEED_CHAT_NAME = 'auction_avito_feed'
SYSTEM_AUTHOR = 'Система'


def get_or_create_feed_chat() -> Chat:
    chat = Chat.objects.filter(slug=AAV_FEED_CHAT_SLUG).first()
    if chat is None:
        chat = Chat.objects.create(name=AAV_FEED_CHAT_NAME, slug=AAV_FEED_CHAT_SLUG)
    return chat


def _lot_feed_label(lot) -> str:
    vehicle = getattr(lot, 'vehicle_avito', None)
    if vehicle and vehicle.brand_name:
        parts = [vehicle.brand_name, vehicle.model_name or '']
        if vehicle.year:
            parts.append(str(vehicle.year))
        return f"{' '.join(p for p in parts if p)} (лот {lot.lot_id})"
    return f"Лот {lot.lot_id}"


def _lot_detail_path(lot) -> str:
    return reverse('auction_avito:lot_detail', kwargs={'pk': lot.pk})


def _format_finish_at(lot) -> str:
    if lot.finish_at:
        return lot.finish_at.strftime('%d.%m.%Y %H:%M')
    return '—'


def broadcast_aav_feed_message(chat, message_text, user=None):
    """Уведомить подписчиков WebSocket о новом сообщении в ленте Авито."""
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
        'message': message_text,
        'username': username,
        'last_name': last_name,
        'first_name': first_name,
        'psevdo_name': eco_name,
        'eco': eco,
        'skip_save': True,
        'estimation_id': 0,
    }
    try:
        from task_manager.views import send_message_socket
        send_message_socket(message=message_json)
    except Exception:
        pass


def post_aav_feed_message(text, user=None) -> ChatMessage:
    chat = get_or_create_feed_chat()
    msg = ChatMessage.objects.create(
        chat=chat,
        content=text,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
    )
    broadcast_aav_feed_message(chat, text, user)
    return msg


def notify_new_lot_in_feed(lot, *, user=None):
    """Новый лот, поступивший на перерасчёт через API."""
    label = _lot_feed_label(lot)
    path = _lot_detail_path(lot)
    finish = _format_finish_at(lot)
    text = (
        f'Новый лот на перерасчёт: {label}\n'
        f'Окончание: {finish}\n'
        f'{path}'
    )
    post_aav_feed_message(text, user=user)


def notify_new_bid_in_feed(lot, new_bid, old_bid=None):
    """Новая наша ставка по лоту."""
    label = _lot_feed_label(lot)
    path = _lot_detail_path(lot)
    try:
        bid_fmt = f'{int(new_bid):,}'.replace(',', ' ')
    except (TypeError, ValueError):
        bid_fmt = str(new_bid)
    text = f'Новая ставка {bid_fmt} ₽ по лоту {label}\n{path}'
    if old_bid is not None:
        try:
            old_fmt = f'{int(old_bid):,}'.replace(',', ' ')
            text = f'Ставка {old_fmt} → {bid_fmt} ₽ по лоту {label}\n{path}'
        except (TypeError, ValueError):
            pass
    post_aav_feed_message(text)


def build_aav_feed_chat_params(request):
    chat = get_or_create_feed_chat()
    messages = chat.get_last_messages()
    if len(messages) > 80:
        messages = messages[-80:]
    profile = getattr(request.user, 'profiles', None)
    return {
        'chat': chat,
        'messages': messages,
        'user': request.user,
        'can_send_messages': not (profile and profile.user_sb),
        'user_eco': bool(profile and profile.eco),
        'eco_name': (profile.eco_name or '') if profile else '',
    }
