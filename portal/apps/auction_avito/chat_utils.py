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


AAV_FEED_PAGE_SIZE = 20


def get_aav_chat_messages(chat, *, newest_first=False, limit=None, before_id=None):
    from django.db.models import Q

    qs = (
        ChatMessage.objects
        .filter(chat=chat)
        .select_related('user', 'user__profiles')
        .order_by('-date', '-id')
    )
    if before_id:
        try:
            ref = ChatMessage.objects.get(pk=before_id, chat=chat)
            qs = qs.filter(
                Q(date__lt=ref.date) | (Q(date=ref.date) & Q(pk__lt=ref.pk)),
            )
        except ChatMessage.DoesNotExist:
            pass

    if limit:
        messages = list(qs[:limit])
    else:
        messages = list(qs)
        if not newest_first:
            messages.reverse()

    enrich_chat_messages(messages)
    return messages


def serialize_aav_chat_message(message, current_user=None):
    if not hasattr(message, 'aav_display_html'):
        enrich_chat_messages([message])
    is_owner = bool(
        message.user
        and getattr(message.user, 'profiles', None)
        and message.user.profiles.eco
    )
    if not message.user:
        author = SYSTEM_AUTHOR
    else:
        profile = getattr(message.user, 'profiles', None)
        if profile and profile.eco_name:
            author = profile.eco_name
        else:
            author = f'{message.user.last_name or ""} {message.user.first_name or ""}'.strip() or message.user.username
    return {
        'id': message.pk,
        'html': message.aav_display_html,
        'lot_pk': message.aav_lot_pk,
        'is_owner': is_owner,
        'author': author,
        'date': message.date.strftime('%d.%m.%Y %H:%M') if message.date else '',
    }


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
        return ' '.join(p for p in parts if p)
    return 'Автомобиль'


def _lot_feed_venue_label(lot) -> str:
    venue = getattr(lot, 'venue', None)
    if venue is not None:
        label = getattr(venue, 'display_label', None) or venue.name
        if label:
            return label
    return (lot.seller_place_name or '').strip() or '—'


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
    venue = _lot_feed_venue_label(lot)
    finish = _format_finish_at(lot)
    feed_text = (
        f'Новый лот на перерасчёт: {label}\n'
        f'Площадка: {venue}\n'
        f'Окончание: {finish}'
    )
    lot_text = feed_text
    post_aav_feed_message(feed_text, user=user, lot_pk=lot.pk)
    post_aav_lot_message(lot, lot_text, user=user)


def notify_new_bid_in_feed(lot, new_bid, old_bid=None):
    """Новая наша ставка по лоту."""
    label = _lot_feed_label(lot)
    venue = _lot_feed_venue_label(lot)
    try:
        bid_fmt = f'{int(new_bid):,}'.replace(',', ' ')
    except (TypeError, ValueError):
        bid_fmt = str(new_bid)
    feed_text = f'Новая ставка {bid_fmt} ₽: {label}\nПлощадка: {venue}'
    if old_bid is not None:
        try:
            old_fmt = f'{int(old_bid):,}'.replace(',', ' ')
            feed_text = f'Ставка {old_fmt} → {bid_fmt} ₽: {label}\nПлощадка: {venue}'
        except (TypeError, ValueError):
            pass
    post_aav_feed_message(feed_text, lot_pk=lot.pk)
    post_aav_lot_message(lot, feed_text)


def notify_bid_placed(lot, bid_amount, bid_made_at=None, *, user=None):
    """Явная фиксация новой ставки из внешнего API/1С."""
    label = _lot_feed_label(lot)
    venue = _lot_feed_venue_label(lot)
    try:
        bid_fmt = f'{int(bid_amount):,}'.replace(',', ' ')
    except (TypeError, ValueError):
        bid_fmt = str(bid_amount)

    if bid_made_at:
        try:
            bid_time = bid_made_at.strftime('%d.%m.%Y %H:%M')
        except Exception:
            bid_time = str(bid_made_at)
    else:
        bid_time = '—'

    text = (
        f'Сделана ставка {bid_fmt} ₽: {label}\n'
        f'Площадка: {venue}\n'
        f'Время ставки: {bid_time}'
    )
    post_aav_feed_message(text, user=user, lot_pk=lot.pk)
    post_aav_lot_message(lot, text, user=user)


def _build_chat_params(request, chat, *, newest_first=False, initial_limit=None):
    if newest_first:
        limit = initial_limit or AAV_FEED_PAGE_SIZE
        messages = get_aav_chat_messages(chat, newest_first=True, limit=limit)
        total = ChatMessage.objects.filter(chat=chat).count()
        has_more = total > len(messages)
    else:
        messages = chat.get_last_messages()
        if len(messages) > 80:
            messages = messages[-80:]
        enrich_chat_messages(messages)
        has_more = False

    profile = getattr(request.user, 'profiles', None)
    return {
        'chat': chat,
        'messages': messages,
        'has_more_messages': has_more,
        'user': request.user,
        'can_send_messages': not (profile and profile.user_sb),
        'user_eco': bool(profile and profile.eco),
        'eco_name': (profile.eco_name or '') if profile else '',
    }


def build_aav_feed_chat_params(request):
    return _build_chat_params(
        request,
        get_or_create_feed_chat(),
        newest_first=True,
        initial_limit=AAV_FEED_PAGE_SIZE,
    )


def build_aav_feed_embed(request):
    params = build_aav_feed_chat_params(request)
    params.update({
        'title': 'Лента Аукцион Авито',
        'open_button_label': 'Чат Авито',
        'send_url': reverse('auction_avito:feed_chat_send'),
        'messages_url': reverse('auction_avito:feed_chat_messages'),
        'prefix': 'aav_feed',
        'clickable_lots': True,
        'newest_first': True,
        'page_size': AAV_FEED_PAGE_SIZE,
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
