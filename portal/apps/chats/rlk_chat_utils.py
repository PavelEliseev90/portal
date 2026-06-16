from django.contrib.auth import get_user_model
from django.db.models import Q

from chats.models import Chat
from documents.models import DocRLK
from refs.models import RefStaff

User = get_user_model()

RLK_CHAT_PATH = '/cars/deal/rlk-chat'
RLK_CHAT_1C_SESSION_FLAG = 'rlk_chat_1c_session'
RLK_CHAT_USER_ID_KEY = 'rlk_chat_user_id'


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


def store_rlk_chat_session(request, staff_uin, rlk_uin):
    staff_uin = (staff_uin or '').strip()
    rlk_uin = (rlk_uin or '').strip()
    if staff_uin:
        request.session['rlk_chat_staff_uin'] = staff_uin
    if rlk_uin:
        request.session['rlk_chat_rlk_uin'] = rlk_uin
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
