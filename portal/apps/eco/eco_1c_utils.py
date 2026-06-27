from django.contrib.auth import get_user_model

from chats.rlk_chat_utils import resolve_rlk_by_uin, resolve_user_by_staff_uin
from documents.models import DocRLK

User = get_user_model()

ECO_PATH = '/eco'
ECO_1C_ENTRY_PREFIX = f'{ECO_PATH}/1c/'
ECO_1C_SESSION_FLAG = 'eco_1c_session'
ECO_1C_USER_ID_KEY = 'eco_1c_user_id'


def is_eco_request(request):
    return (request.path_info or '').startswith(ECO_PATH)


def is_eco_1c_session(request):
    return bool(request.session.get(ECO_1C_SESSION_FLAG))


def is_1c_eco_entry(request, staff_uin=None):
    if staff_uin is None:
        staff_uin = extract_eco_1c_request(request)['staff_uin']
    path = request.path_info or ''
    if path.startswith(ECO_1C_ENTRY_PREFIX):
        return True
    return bool((staff_uin or '').strip())


def extract_eco_1c_request(request):
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
    if path.startswith(ECO_1C_ENTRY_PREFIX):
        rest = path[len(ECO_1C_ENTRY_PREFIX):].strip('/')
        parts = [part for part in rest.split('/') if part]
        if len(parts) >= 1 and not staff_uin:
            staff_uin = parts[0].strip()
        if len(parts) >= 2 and not rlk_uin:
            rlk_uin = parts[1].strip()

    if not staff_uin:
        staff_uin = (request.session.get('eco_1c_staff_uin') or '').strip()
    if not rlk_uin:
        rlk_uin = (request.session.get('eco_1c_rlk_uin') or '').strip()

    return {
        'staff_uin': staff_uin,
        'rlk_uin': rlk_uin,
    }


def resolve_rlk_ref(rlk_ref):
    rlk_ref = (rlk_ref or '').strip()
    if not rlk_ref:
        return None
    if rlk_ref.isdigit():
        return DocRLK.objects.filter(pk=int(rlk_ref)).select_related('unit', 'staff').first()
    return resolve_rlk_by_uin(rlk_ref)


def store_eco_1c_session(request, staff_uin, rlk_uin='', rlk_id=None):
    staff_uin = (staff_uin or '').strip()
    rlk_uin = (rlk_uin or '').strip()
    if staff_uin:
        request.session['eco_1c_staff_uin'] = staff_uin
    if rlk_uin:
        request.session['eco_1c_rlk_uin'] = rlk_uin
    if rlk_id:
        request.session['eco_1c_rlk_id'] = int(rlk_id)
    request.session.modified = True


def bind_eco_1c_session(request, staff_uin):
    """
    Сессия ECO из 1С без django.contrib.auth.login — не трогает current_session_key
    и не разлогинивает пользователя в обычном браузере.
    """
    user = resolve_user_by_staff_uin(staff_uin)
    if user is None:
        return None
    request.session[ECO_1C_SESSION_FLAG] = True
    request.session[ECO_1C_USER_ID_KEY] = user.pk
    store_eco_1c_session(
        request,
        staff_uin,
        request.session.get('eco_1c_rlk_uin', ''),
    )
    request.session.save()
    return user


def get_eco_1c_user_from_session(request):
    if not is_eco_1c_session(request):
        return None
    user_id = request.session.get(ECO_1C_USER_ID_KEY)
    if not user_id:
        return None
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return None
    staff_uin = (request.session.get('eco_1c_staff_uin') or '').strip()
    if staff_uin and resolve_user_by_staff_uin(staff_uin) != user:
        return None
    return user


def get_eco_user(request):
    user = get_eco_1c_user_from_session(request)
    if user is not None:
        return user
    if request.user.is_authenticated:
        return request.user
    return None


def build_eco_1c_url(staff_uin, rlk_ref, page='9'):
    staff_uin = (staff_uin or '').strip()
    rlk_ref = (rlk_ref or '').strip()
    page = (page or '9').strip() or '9'
    return f'{ECO_1C_ENTRY_PREFIX}{staff_uin}/{rlk_ref}/?page={page}'


def user_can_access_eco(user, rlk, staff_uin=None, from_1c=False):
    if not user:
        return False

    staff_uin = (staff_uin or '').strip()

    if from_1c:
        return bool(staff_uin and resolve_user_by_staff_uin(staff_uin) == user)

    return bool(getattr(user, 'is_authenticated', True))


def resolve_eco_1c_access(request, rlk_id=None, staff_uin=None, rlk_uin=None, rlk_ref=None):
    from django.shortcuts import get_object_or_404

    parsed = extract_eco_1c_request(request)
    staff_uin = parsed['staff_uin'] or (staff_uin or '').strip()
    rlk_uin = parsed['rlk_uin'] or (rlk_uin or '').strip()
    from_1c = is_1c_eco_entry(request, staff_uin)

    eco_user = get_eco_user(request)
    error_response = None

    if eco_user is None:
        if from_1c and staff_uin:
            eco_user = bind_eco_1c_session(request, staff_uin)
            if eco_user is None:
                error_response = 'uin_auth'
        elif request.user.is_authenticated:
            eco_user = request.user
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
    elif rlk_ref:
        rlk = resolve_rlk_ref(rlk_ref)
        if rlk is None:
            return {
                'error': 'not_found',
                'staff_uin': staff_uin,
                'rlk_uin': rlk_uin or rlk_ref,
                'from_1c': from_1c,
            }
        if not rlk_uin:
            rlk_uin = (rlk.uin or '').strip()
    else:
        if not rlk_uin:
            return {
                'error': 'access',
                'staff_uin': staff_uin,
                'rlk_uin': rlk_uin,
                'from_1c': from_1c,
            }
        rlk = resolve_rlk_by_uin(rlk_uin)
        if rlk is None:
            return {
                'error': 'not_found',
                'staff_uin': staff_uin,
                'rlk_uin': rlk_uin,
                'from_1c': from_1c,
            }

    if not user_can_access_eco(
        eco_user, rlk, staff_uin=staff_uin, from_1c=from_1c,
    ):
        return {
            'error': 'access',
            'staff_uin': staff_uin,
            'rlk_uin': rlk_uin,
            'from_1c': from_1c,
        }

    store_eco_1c_session(request, staff_uin, rlk_uin, rlk_id=rlk.pk)
    return {
        'error': None,
        'eco_user': eco_user,
        'rlk': rlk,
        'staff_uin': staff_uin,
        'rlk_uin': rlk_uin,
        'from_1c': from_1c,
    }


def try_bind_eco_1c_user(request):
    """Пользователь 1С для /eco/: активная сессия или ?uin= в ссылке."""
    if not is_eco_request(request):
        return None

    path = request.path_info or ''
    if path.startswith(ECO_1C_ENTRY_PREFIX):
        return None

    if is_eco_1c_session(request):
        return get_eco_1c_user_from_session(request)

    staff_uin = (
        request.GET.get('uin')
        or request.GET.get('staff_uin')
        or ''
    ).strip()
    if staff_uin and not request.user.is_authenticated:
        user = bind_eco_1c_session(request, staff_uin)
        if user is None:
            return None
        parts = [part for part in path.strip('/').split('/') if part]
        if len(parts) >= 2 and parts[0] == 'eco' and parts[1].isdigit():
            store_eco_1c_session(request, staff_uin, rlk_id=int(parts[1]))
        return user

    return None
