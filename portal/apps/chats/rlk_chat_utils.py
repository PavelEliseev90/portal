from django.contrib.auth import get_user_model
from django.db.models import Q

from chats.models import Chat
from documents.models import DocRLK
from refs.models import RefStaff

User = get_user_model()

RLK_CHAT_PATH = '/cars/deal/rlk-chat'


def is_rlk_chat_request(request):
    return (request.path_info or '').startswith(RLK_CHAT_PATH)


def extract_rlk_chat_request(request):
    """УИН сотрудника и РЛК из query (?uin, ?rlk_uin) или пути /1c/{uin}/{rlk_uin}/."""
    staff_uin = (request.GET.get('uin') or request.GET.get('staff_uin') or '').strip()
    rlk_uin = (request.GET.get('rlk_uin') or '').strip()

    path = request.path_info or ''
    prefix_1c = f'{RLK_CHAT_PATH}/1c/'
    if path.startswith(prefix_1c):
        rest = path[len(prefix_1c):].strip('/')
        parts = [part for part in rest.split('/') if part]
        if len(parts) >= 1 and not staff_uin:
            staff_uin = parts[0].strip()
        if len(parts) >= 2 and not rlk_uin:
            rlk_uin = parts[1].strip()

    return {
        'staff_uin': staff_uin,
        'rlk_uin': rlk_uin,
    }


def login_user_for_rlk_chat(request, staff_uin):
    """Вход по УИН сотрудника из 1С; возвращает User или None."""
    user = resolve_user_by_staff_uin(staff_uin)
    if user is None:
        return None
    from django.contrib.auth import login

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session.save()
    return user


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

    Портал: price_car_new / price_car_new_settings / price_car_new_all,
    менеджер РЛК (domain_login или УИН).

    Ссылка из 1С (?uin=...&rlk_uin=...): сотрудник из uin совпадает
    с текущим пользователем портала — достаточно для доступа;
    дополнительно: УИН = менеджер РЛК или участник CarCalculations по РЛК.
    """
    if not user.is_authenticated:
        return False

    staff_uin = (staff_uin or '').strip()
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

    if from_1c and user_matches_link:
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


def build_rlk_chat_params(request, rlk):
    chat = get_or_create_rlk_chat(rlk)
    return {
        'chat': chat,
        'messages': chat.get_last_messages(),
        'user': request.user,
        'rlk': rlk,
    }
