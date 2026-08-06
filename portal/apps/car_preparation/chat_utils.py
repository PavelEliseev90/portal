"""
Чаты подготовки автомобилей:
- prep_feed — общая лента по всем подготовкам
- prep_{pk} — чат конкретной подготовки

Паттерн как у Avito / RLK OP: сначала ChatMessage в БД, затем WebSocket (skip_save).
"""
from __future__ import annotations

import re

from chats.models import Chat, ChatMessage

PREP_FEED_SLUG = 'prep_feed'
PREP_FEED_NAME = 'car_preparation_feed'
SYSTEM_AUTHOR = 'Система'
PREP_PK_SUFFIX_RE = re.compile(r'\n?@@prep_pk:(\d+)@@\s*$')


def _prep_chat_slug(preparation_id: int) -> str:
    return f'prep_{preparation_id}'


def append_prep_pk(content: str, prep_pk: int) -> str:
    return f'{content}\n@@prep_pk:{prep_pk}@@'


def strip_prep_metadata(content: str) -> str:
    if not content:
        return ''
    return PREP_PK_SUFFIX_RE.sub('', content).strip()


def extract_prep_pk(content: str):
    if not content:
        return None
    match = PREP_PK_SUFFIX_RE.search(content)
    return int(match.group(1)) if match else None


def _car_label(preparation) -> str:
    car = getattr(preparation, 'car', None)
    if not car:
        return f'Подготовка #{preparation.pk}'
    parts = []
    mark = getattr(car, 'mark', None) or ''
    model = getattr(car, 'model', None) or ''
    name = getattr(car, 'name', None) or ''
    vin = getattr(car, 'vin', None) or ''
    if mark or model:
        parts.append(f'{mark} {model}'.strip())
    elif name:
        parts.append(name)
    if vin:
        parts.append(f'VIN {vin}')
    unit = getattr(preparation, 'unit', None)
    if unit and getattr(unit, 'name', None):
        parts.append(unit.name)
    return ' · '.join(parts) if parts else f'Подготовка #{preparation.pk}'


def get_or_create_feed_chat() -> Chat:
    chat = Chat.objects.filter(slug=PREP_FEED_SLUG).first()
    if chat is None:
        chat = Chat.objects.create(name=PREP_FEED_NAME, slug=PREP_FEED_SLUG)
    return chat


def get_or_create_prep_chat(preparation) -> Chat:
    slug = _prep_chat_slug(preparation.pk)
    chat = Chat.objects.filter(slug=slug).first()
    if chat is None:
        chat = Chat.objects.create(name=str(preparation.pk), slug=slug)
    return chat


def broadcast_prep_message(chat, message_text, user=None, prep_pk=None):
    display_text = strip_prep_metadata(message_text)
    if user and getattr(user, 'is_authenticated', False):
        profile = getattr(user, 'profiles', None)
        eco = bool(profile and getattr(profile, 'eco', False))
        eco_name = (getattr(profile, 'eco_name', None) or '') if profile else ''
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
        'prep_pk': prep_pk,
        'channel': 'prep',
    }
    try:
        from task_manager.views import send_message_socket
        send_message_socket(message=message_json)
    except Exception:
        pass


def post_prep_feed_message(text, *, prep_pk=None, user=None) -> ChatMessage:
    chat = get_or_create_feed_chat()
    content = append_prep_pk(text, prep_pk) if prep_pk else text
    msg = ChatMessage.objects.create(
        chat=chat,
        content=content,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
    )
    broadcast_prep_message(chat, content, user=user, prep_pk=prep_pk)
    return msg


def post_prep_message(preparation, text, user=None, *, also_feed=True) -> ChatMessage:
    """Сообщение в чат подготовки (+ опционально в общую ленту)."""
    chat = get_or_create_prep_chat(preparation)
    msg = ChatMessage.objects.create(
        chat=chat,
        content=text,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
    )
    broadcast_prep_message(chat, text, user=user, prep_pk=preparation.pk)
    if also_feed:
        label = _car_label(preparation)
        feed_text = f'{label}\n{text}'
        post_prep_feed_message(feed_text, prep_pk=preparation.pk, user=user)
    return msg


def post_prep_system_event(preparation, text, user=None, *, also_feed=True) -> ChatMessage:
    """Системное событие (user=None если не передан)."""
    return post_prep_message(preparation, text, user=user, also_feed=also_feed)


def get_prep_chat_messages(chat, *, limit=200):
    qs = (
        ChatMessage.objects.filter(chat=chat)
        .select_related('user', 'user__profiles')
        .order_by('date', 'id')
    )
    messages = list(qs[:limit] if limit else qs)
    for message in messages:
        display = strip_prep_metadata(message.content)
        message.content_html = display.replace('\n', '<br>')
        message.display_content = display
    return messages


def notify_preparation_created(preparation, user=None):
    post_prep_system_event(
        preparation,
        f'Создана подготовка #{preparation.pk}\n{_car_label(preparation)}',
        user=user,
    )


def notify_package_added(preparation, prep_package, stats=None, user=None):
    stats = stats or {}
    created = stats.get('created_works', prep_package.work_items.count())
    post_prep_system_event(
        preparation,
        (
            f'Добавлен пакет «{prep_package.name}»\n'
            f'Маршрут: {prep_package.get_route_type_display()}\n'
            f'Работ создано: {created}'
        ),
        user=user,
    )


def notify_package_confirmed(preparation, prep_package, confirmed=True, user=None):
    action = 'подтверждён' if confirmed else 'снято подтверждение с пакета'
    post_prep_system_event(
        preparation,
        f'Пакет «{prep_package.name}» {action}',
        user=user,
    )


def notify_work_order_created(preparation, work_order, user=None):
    zone = work_order.repair_zone.name if work_order.repair_zone_id else 'без ремзоны'
    items = work_order.items.count()
    post_prep_system_event(
        preparation,
        (
            f'Создан заказ-наряд {work_order.number or work_order.pk}\n'
            f'«{work_order.title}»\n'
            f'Зона: {zone}; работ: {items}'
        ),
        user=user,
    )


def notify_work_started(preparation, item, user=None):
    performer = ''
    if item.performer_id:
        performer = getattr(item.performer, 'name', '') or str(item.performer)
    work_name = item.work.name if item.work_id else 'работа'
    post_prep_system_event(
        preparation,
        f'Взято в работу: «{work_name}»' + (f'\nИсполнитель: {performer}' if performer else ''),
        user=user,
        also_feed=True,
    )


def notify_work_completed(preparation, item, user=None):
    work_name = item.work.name if item.work_id else 'работа'
    photos = item.photos.count() if hasattr(item, 'photos') else 0
    extra = f'\nФото: {photos}' if photos else ''
    post_prep_system_event(
        preparation,
        f'Выполнено: «{work_name}»{extra}',
        user=user,
    )


def notify_photo_uploaded(preparation, item, user=None):
    work_name = item.work.name if item.work_id else 'работа'
    post_prep_system_event(
        preparation,
        f'Добавлено фото к работе «{work_name}»',
        user=user,
        also_feed=False,
    )


def notify_quality_check(preparation, user=None):
    post_prep_system_event(
        preparation,
        'Подготовка передана на контроль качества',
        user=user,
    )


def notify_preparation_completed(preparation, user=None):
    post_prep_system_event(
        preparation,
        'Контроль качества пройден — подготовка завершена',
        user=user,
    )


def notify_user_comment(preparation, text, user=None):
    post_prep_message(
        preparation,
        f'Комментарий:\n{text}',
        user=user,
        also_feed=True,
    )
