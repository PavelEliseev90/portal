from django.contrib.auth import get_user_model

from chats.models import Chat
from documents.models import DocRLK
from refs.models import RefStaff

User = get_user_model()


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


def resolve_user_by_staff_uin(uin):
    """Пользователь портала по УИН сотрудника из 1С (RefStaff.uin → domain_login)."""
    uin = (uin or '').strip()
    if not uin:
        return None
    staff = RefStaff.objects.filter(uin=uin).first()
    if staff is None or not (staff.domain_login or '').strip():
        return None
    return User.objects.filter(username__iexact=staff.domain_login.strip()).first()


def user_can_access_rlk_op_chat(user, rlk):
    if not user.is_authenticated:
        return False
    profile = getattr(user, 'profiles', None)
    if profile and (profile.price_car_new or profile.price_car_new_settings):
        return True
    if rlk.staff_id and rlk.staff.domain_login:
        if user.username.lower() == rlk.staff.domain_login.strip().lower():
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
