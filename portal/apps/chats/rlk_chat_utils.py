from django.contrib.auth import get_user_model
from django.db.models import Q

from chats.models import Chat
from documents.models import DocRLK
from refs.models import RefStaff

User = get_user_model()

RLK_CHAT_PATH = '/cars/deal/rlk-chat'
RLK_CHAT_1C_SESSION_FLAG = 'rlk_chat_1c_session'
RLK_CHAT_USER_ID_KEY = 'rlk_chat_user_id'
RLK_CHAT_CHAT_ID_KEY = 'rlk_chat_chat_id'


def is_rlk_chat_request(request):
    return (request.path_info or '').startswith(RLK_CHAT_PATH)


def is_rlk_chat_1c_session(request):
    return bool(request.session.get(RLK_CHAT_1C_SESSION_FLAG))


def is_1c_rlk_chat_entry(request, staff_uin=None):
    """Вход из 1С: путь /1c/... или УИН сотрудника в ссылке."""
    if staff_uin is None:
        staff_uin = extract_rlk_chat_request(request)['staff_uin']
    path = request.path_info or ''
    if path.startswith(f'{RLK_CHAT_PATH}/1c/'):
        return True
    return bool((staff_uin or '').strip())

def extract_rlk_chat_request(request):
    """УИН сотрудника и РЛК из path, query, POST или сессии чата 1С."""
    staff_uin = (
        request.GET.get('uin')
        or request.GET.get('staff_uin')
        or request.POST.get('uin')
        or request.POST.get('staff_uin')
        or ''
    ).strip()
    rlk_uin = (
        request.GET.get('rlk_uin')
        or request.POST.get('rlk_uin')
        or ''
    ).strip()

    path = request.path_info or ''
    prefix_1c = f'{RLK_CHAT_PATH}/1c/'
    if path.startswith(prefix_1c):
        rest = path[len(prefix_1c):].strip('/')
        parts = [part for part in rest.split('/') if part]
        if len(parts) >= 1 and not staff_uin:
            staff_uin = parts[0].strip()
        if len(parts) >= 2 and not rlk_uin:
            rlk_uin = parts[1].strip()

    if not staff_uin:
        staff_uin = (request.session.get('rlk_chat_staff_uin') or '').strip()
    if not rlk_uin:
        rlk_uin = (request.session.get('rlk_chat_rlk_uin') or '').strip()

    return {
        'staff_uin': staff_uin,
        'rlk_uin': rlk_uin,
    }


def store_rlk_chat_session(request, staff_uin, rlk_uin, chat_id=None):
    staff_uin = (staff_uin or '').strip()
    rlk_uin = (rlk_uin or '').strip()
    if staff_uin:
        request.session['rlk_chat_staff_uin'] = staff_uin
    if rlk_uin:
        request.session['rlk_chat_rlk_uin'] = rlk_uin
    if chat_id:
        request.session[RLK_CHAT_CHAT_ID_KEY] = int(chat_id)
    request.session.modified = True


def bind_rlk_chat_1c_session(request, staff_uin):
    """
    Сессия чата 1С без django.contrib.auth.login — не трогает current_session_key
  и не разлогинивает пользователя в обычном браузере.
    """
    user = resolve_user_by_staff_uin(staff_uin)
    if user is None:
        return None
    request.session[RLK_CHAT_1C_SESSION_FLAG] = True
    request.session[RLK_CHAT_USER_ID_KEY] = user.pk
    store_rlk_chat_session(request, staff_uin, request.session.get('rlk_chat_rlk_uin', ''))
    request.session.save()
    return user


def get_rlk_chat_user(request):
    """Пользователь чата: изолированная сессия 1С или обычный вход в портал."""
    if is_rlk_chat_1c_session(request):
        user_id = request.session.get(RLK_CHAT_USER_ID_KEY)
        if not user_id:
            return None
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return None
        staff_uin = (request.session.get('rlk_chat_staff_uin') or '').strip()
        if staff_uin and resolve_user_by_staff_uin(staff_uin) != user:
            return None
        return user
    if request.user.is_authenticated:
        return request.user
    return None


def build_rlk_chat_page_url(staff_uin, rlk_uin, rlk_id=None):
    staff_uin = (staff_uin or '').strip()
    rlk_uin = (rlk_uin or '').strip()
    if staff_uin and rlk_uin:
        return f'{RLK_CHAT_PATH}/1c/{staff_uin}/{rlk_uin}/'
    if rlk_id and staff_uin:
        return f'{RLK_CHAT_PATH}/{rlk_id}/?uin={staff_uin}'
    if staff_uin and rlk_uin:
        return f'{RLK_CHAT_PATH}/?rlk_uin={rlk_uin}&uin={staff_uin}'
    return f'{RLK_CHAT_PATH}/'


def build_rlk_chat_poll_url(staff_uin=None, rlk_uin=None):
    return f'{RLK_CHAT_PATH}/poll/'


def build_rlk_chat_send_url():
    return f'{RLK_CHAT_PATH}/send/'


def resolve_rlk_chat_poll(request):
    """
    Лёгкая авторизация poll: сессия 1С + chat_id, без поиска РЛК и RefStaff.
    Полный resolve — только при первом запросе без chat_id в сессии.
    """
    chat_id = request.session.get(RLK_CHAT_CHAT_ID_KEY)
    user_id = request.session.get(RLK_CHAT_USER_ID_KEY)

    if is_rlk_chat_1c_session(request) and chat_id and user_id:
        user = User.objects.filter(pk=user_id).only(
            'id', 'username', 'first_name', 'last_name',
        ).first()
        if user:
            return {
                'error': None,
                'chat_id': int(chat_id),
                'chat_user': user,
            }

    ctx = resolve_rlk_chat_access(request)
    if ctx.get('error'):
        return ctx
    chat = ctx['chat_params']['chat']
    store_rlk_chat_session(
        request, ctx['staff_uin'], ctx['rlk_uin'], chat_id=chat.pk,
    )
    return {
        'error': None,
        'chat_id': chat.pk,
        'chat_user': ctx['chat_user'],
    }


def fetch_new_rlk_chat_messages(chat_id, after_id, current_user_id, limit=30):
    """Только новые сообщения; при отсутствии — быстрый ответ без выборки текста."""
    from chats.models import ChatMessage

    after_id = int(after_id or 0)
    if after_id > 0:
        if not ChatMessage.objects.filter(chat_id=chat_id, pk__gt=after_id).exists():
            return [], after_id

    messages = list(
        ChatMessage.objects.filter(chat_id=chat_id, pk__gt=after_id)
        .select_related('user')
        .only('pk', 'content', 'date', 'user_id', 'user__first_name', 'user__last_name')
        .order_by('pk')[:limit]
    )
    return serialize_rlk_chat_messages(messages, current_user_id)


def resolve_rlk_chat_access(request, rlk_id=None, staff_uin=None, rlk_uin=None):
    """
    Общая авторизация и поиск РЛК для страницы чата и HTTP-poll.
    Возвращает dict или None при ошибке (вызывающий отдаёт нужный HttpResponse).
    """
    from django.shortcuts import get_object_or_404

    parsed = extract_rlk_chat_request(request)
    staff_uin = parsed['staff_uin'] or (staff_uin or '').strip()
    rlk_uin = parsed['rlk_uin'] or (rlk_uin or '').strip()
    from_1c = is_1c_rlk_chat_entry(request, staff_uin)

    chat_user = get_rlk_chat_user(request)
    error_response = None

    if chat_user is None:
        if from_1c and staff_uin:
            chat_user = bind_rlk_chat_1c_session(request, staff_uin)
            if chat_user is None:
                error_response = 'uin_auth'
        elif request.user.is_authenticated:
            chat_user = request.user
        else:
            error_response = 'login'

    if error_response:
        return {
            'error': error_response,
            'staff_uin': staff_uin,
            'rlk_uin': rlk_uin,
            'from_1c': from_1c,
        }

    if rlk_id:
        rlk = get_object_or_404(
            DocRLK.objects.select_related('unit', 'staff'),
            pk=rlk_id,
        )
        if not rlk_uin:
            rlk_uin = (rlk.uin or '').strip()
    else:
        if not rlk_uin:
            return {'error': 'access', 'staff_uin': staff_uin, 'rlk_uin': rlk_uin, 'from_1c': from_1c}
        rlk = resolve_rlk_by_uin(rlk_uin)
        if rlk is None:
            return {'error': 'not_found', 'staff_uin': staff_uin, 'rlk_uin': rlk_uin, 'from_1c': from_1c}

    if not user_can_access_rlk_op_chat(
        chat_user, rlk, staff_uin=staff_uin, from_1c=from_1c,
    ):
        return {'error': 'access', 'staff_uin': staff_uin, 'rlk_uin': rlk_uin, 'from_1c': from_1c}

    chat_params = build_rlk_chat_params(request, rlk, user=chat_user)
    store_rlk_chat_session(request, staff_uin, rlk_uin, chat_id=chat_params['chat'].pk)
    return {
        'error': None,
        'chat_user': chat_user,
        'rlk': rlk,
        'staff_uin': staff_uin,
        'rlk_uin': rlk_uin,
        'from_1c': from_1c,
        'chat_params': chat_params,
    }


def serialize_rlk_chat_messages(messages, current_user_id):
    items = []
    last_id = 0
    for message in messages:
        user = message.user
        author = ''
        if user:
            author = f'{user.last_name or ""} {user.first_name or ""}'.strip()
        content = message.content or ''
        items.append({
            'id': message.pk,
            'author': author,
            'text': content.replace('\n', '<br>'),
            'date': message.date.strftime('%d.%m.%Y %H:%M'),
            'own': message.user_id == current_user_id,
        })
        if message.pk > last_id:
            last_id = message.pk
    return items, last_id


def user_matches_staff_uin(user, staff_uin):
    if not user or not staff_uin:
        return False
    link_staff = _staff_by_uin(staff_uin)
    return bool(link_staff and _user_matches_domain_login(user, link_staff.domain_login))


def _username_candidates_from_domain_login(domain_login):
    domain_login = (domain_login or '').strip()
    if not domain_login:
        return []
    candidates = [domain_login]
    if '\\' in domain_login:
        candidates.append(domain_login.split('\\')[-1])
    if '@' in domain_login:
        candidates.append(domain_login.split('@')[0])
    seen = set()
    result = []
    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def _user_matches_domain_login(user, domain_login):
    if not user or not domain_login:
        return False
    username = (user.username or '').strip().lower()
    for candidate in _username_candidates_from_domain_login(domain_login):
        if username == candidate.lower():
            return True
    return False


def _get_user_profile(user):
    try:
        return user.profiles
    except Exception:
        return None


def _staff_by_uin(staff_uin):
    staff_uin = (staff_uin or '').strip()
    if not staff_uin:
        return None
    return RefStaff.objects.filter(uin__iexact=staff_uin).first()


def get_or_create_rlk_chat(rlk):
    """Чат по РЛК — тот же slug, что у интерактивной оценки (rlk_{pk})."""
    slug = 'rlk_' + str(rlk.pk)
    chat = Chat.objects.filter(slug=slug).first()
    if chat is None:
        chat = Chat.objects.create(name=rlk.pk, slug=slug, rlk_id=rlk.pk)
    elif not chat.rlk_id:
        chat.rlk_id = rlk.pk
        chat.save(update_fields=['rlk_id'])
    return chat


def resolve_rlk_by_uin(rlk_uin):
    rlk_uin = (rlk_uin or '').strip()
    if not rlk_uin:
        return None
    qs = DocRLK.objects.select_related('unit', 'staff').filter(uin__iexact=rlk_uin)
    rlk = qs.filter(eco=False).order_by('-pk').first()
    if rlk is None:
        rlk = qs.order_by('-pk').first()
    return rlk


def resolve_user_by_staff_uin(uin):
    """Пользователь портала по УИН сотрудника из 1С (RefStaff.uin → domain_login)."""
    staff = _staff_by_uin(uin)
    if staff is None or not (staff.domain_login or '').strip():
        return None
    for candidate in _username_candidates_from_domain_login(staff.domain_login):
        user = User.objects.filter(username__iexact=candidate).first()
        if user:
            return user
    return None


def user_can_access_rlk_op_chat(user, rlk, staff_uin=None, from_1c=False):
    """
    Доступ к чату РЛК ОП.

    1С: достаточно валидного УИН → пользователь (контроль доступа в 1С).
    Портал: price_car_new / настройки / менеджер РЛК / участник калькуляции.
    """
    if not user:
        return False

    staff_uin = (staff_uin or '').strip()

    if from_1c:
        return bool(staff_uin and resolve_user_by_staff_uin(staff_uin) == user)

    if not getattr(user, 'is_authenticated', True):
        return False

    link_staff = _staff_by_uin(staff_uin)
    user_matches_link = bool(
        link_staff and _user_matches_domain_login(user, link_staff.domain_login)
    )

    profile = _get_user_profile(user)
    if profile and (
        profile.price_car_new
        or profile.price_car_new_settings
        or profile.price_car_new_all
    ):
        return True

    if rlk.staff_id and _user_matches_domain_login(user, rlk.staff.domain_login):
        return True

    if user_matches_link and rlk.staff_id:
        if (rlk.staff.uin or '').strip().lower() == staff_uin.lower():
            return True

    if user_matches_link and staff_uin:
        from prices_car.models import CarCalculations

        if CarCalculations.objects.filter(rlk_id=rlk.pk).filter(
            Q(author_id=link_staff.pk) | Q(staff_id=link_staff.pk)
        ).exists():
            return True

    return False


def build_rlk_chat_params(request, rlk, user=None):
    chat_user = user or get_rlk_chat_user(request) or request.user
    chat = get_or_create_rlk_chat(rlk)
    profile = _get_user_profile(chat_user)
    return {
        'chat': chat,
        'messages': chat.get_last_messages(),
        'user': chat_user,
        'rlk': rlk,
        'can_send_messages': not (profile and profile.user_sb),
        'user_eco': bool(profile and profile.eco),
        'eco_name': (profile.eco_name or '') if profile else '',
    }
