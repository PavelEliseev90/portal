"""Согласование коммерческих предложений в калькуляции сделки."""
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone

from chats.models import Chat


def _get_profile(user):
    return getattr(user, 'profiles', None)


def get_calc_unit_id(calc):
    if calc.unit_id:
        return calc.unit_id
    if calc.car_id and calc.car.unit_id:
        return calc.car.unit_id
    return None


def user_has_deal_calc_uk_access(user):
    profile = _get_profile(user)
    return bool(profile and profile.price_car_new_all)


def user_is_deal_calc_director_for_calc(user, calc):
    profile = _get_profile(user)
    if not profile or not profile.price_car_new_director:
        return False
    unit_id = get_calc_unit_id(calc)
    if not unit_id:
        return False
    return profile.available_units.filter(pk=unit_id).exists()


def user_can_access_deal_calculation_doc(user, calc):
    if user_has_deal_calc_uk_access(user):
        return True
    return user_is_deal_calc_director_for_calc(user, calc)


def get_calc_min_km_dc(cumulative_data, car):
    """Мин. КМ ДЦ для сравнения с КВП (brand_km.km_min_dc)."""
    brand_km = (cumulative_data or {}).get('brand_km')
    if brand_km is not None:
        km_min_dc = getattr(brand_km, 'km_min_dc', None)
        if km_min_dc is not None:
            return int(km_min_dc)
    return 0


def kvp_above_min_km_dc(calc, cumulative_data):
    kvp = int(calc.kvp or 0)
    min_km_dc = get_calc_min_km_dc(cumulative_data, calc.car)
    return kvp > min_km_dc


def send_calc_rlk_chat_message(calc, user, text):
    if not calc.rlk_id:
        return
    try:
        from task_manager.views import send_message_socket

        chat, _ = Chat.objects.get_or_create(
            name=str(calc.rlk_id),
            slug='rlk_' + str(calc.rlk_id),
        )
        profile = _get_profile(user)
        message_json = {
            'chat_id': str(chat.pk),
            'name': user.username,
            'chat': 'rlk_' + str(calc.rlk_id),
            'message': text,
            'username': user.username,
            'last_name': user.last_name or '',
            'first_name': user.first_name or '',
            'psevdo_name': (profile.eco_name or '') if profile else '',
            'eco': bool(profile and profile.eco),
            'estimation_id': 0,
        }
        send_message_socket(message=message_json)
    except Exception:
        pass


def build_deal_calc_approval_context(user, calc, cumulative_data):
    from prices_car.models import CarCalculations

    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    is_director = user_is_deal_calc_director_for_calc(user, calc)
    is_uk = user_has_deal_calc_uk_access(user)
    kvp_ok = kvp_above_min_km_dc(calc, cumulative_data)
    min_km_dc = get_calc_min_km_dc(cumulative_data, calc.car)

    can_director_approve = (
        is_director
        and status == CarCalculations.SOGLASOVANIE_PENDING
        and kvp_ok
    )
    can_director_send_uk = (
        is_director
        and status == CarCalculations.SOGLASOVANIE_PENDING
        and not kvp_ok
    )
    can_uk_approve = (
        is_uk
        and status == CarCalculations.SOGLASOVANIE_PENDING_UK
    )
    approval_final_without_uk = status == CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED

    return {
        'approval_min_km_dc': min_km_dc,
        'approval_kvp_ok': kvp_ok,
        'approval_uk_required': (
            status == CarCalculations.SOGLASOVANIE_PENDING_UK
            or (
                status == CarCalculations.SOGLASOVANIE_PENDING
                and not kvp_ok
            )
        ),
        'approval_final_without_uk': approval_final_without_uk,
        'approval_is_director': is_director,
        'approval_is_uk': is_uk,
        'approval_can_director_approve': can_director_approve,
        'approval_can_director_send_uk': can_director_send_uk,
        'approval_can_uk_approve': can_uk_approve,
        'approval_status': status,
        'approval_status_label': dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES).get(
            status, status,
        ),
    }


def _approval_redirect(calc_pk):
    return HttpResponseRedirect('/cars/deal/calculation/' + str(calc_pk) + '/')


def _require_comment(request, comment):
    comment = (comment or '').strip()
    if not comment:
        messages.error(request, 'Укажите комментарий к согласованию.')
        return None
    return comment


def handle_deal_calc_approval_post(request, calc, cumulative_data):
    from prices_car.models import CarCalculations

    action = (request.POST.get('approval_action') or '').strip()
    comment = request.POST.get('approval_comment', '')

    if action == 'director_approve':
        if not user_is_deal_calc_director_for_calc(request.user, calc):
            messages.error(request, 'Нет прав на согласование директором ДЦ.')
            return _approval_redirect(calc.pk)
        if calc.soglasovanie_status != CarCalculations.SOGLASOVANIE_PENDING:
            messages.error(request, 'КП уже обработано директором.')
            return _approval_redirect(calc.pk)
        if not kvp_above_min_km_dc(calc, cumulative_data):
            messages.error(request, 'КВП не выше мин. КМ ДЦ — отправьте на согласование в УК.')
            return _approval_redirect(calc.pk)
        comment = _require_comment(request, comment)
        if comment is None:
            return _approval_redirect(calc.pk)

        now = timezone.now()
        calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
        calc.director_approve_user = request.user
        calc.director_approve_date = now
        calc.director_approve_comment = comment
        calc.date_success = now
        calc.save(update_fields=[
            'soglasovanie_status',
            'director_approve_user',
            'director_approve_date',
            'director_approve_comment',
            'date_success',
        ])
        send_calc_rlk_chat_message(
            calc,
            request.user,
            'Согласовано директором ДЦ ' + comment,
        )
        messages.success(request, 'Коммерческое предложение согласовано. Дополнительное согласование УК не требуется.')
        return _approval_redirect(calc.pk)

    if action == 'director_send_uk':
        if not user_is_deal_calc_director_for_calc(request.user, calc):
            messages.error(request, 'Нет прав на отправку в УК.')
            return _approval_redirect(calc.pk)
        if calc.soglasovanie_status != CarCalculations.SOGLASOVANIE_PENDING:
            messages.error(request, 'КП уже обработано директором.')
            return _approval_redirect(calc.pk)
        if kvp_above_min_km_dc(calc, cumulative_data):
            messages.error(request, 'КВП выше мин. КМ ДЦ — согласуйте без отправки в УК.')
            return _approval_redirect(calc.pk)
        comment = _require_comment(request, comment)
        if comment is None:
            return _approval_redirect(calc.pk)

        now = timezone.now()
        calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_PENDING_UK
        calc.director_approve_user = request.user
        calc.director_approve_date = now
        calc.director_approve_comment = comment
        calc.save(update_fields=[
            'soglasovanie_status',
            'director_approve_user',
            'director_approve_date',
            'director_approve_comment',
        ])
        send_calc_rlk_chat_message(
            calc,
            request.user,
            'Отправлено на согласование директором ДЦ в УК ' + comment,
        )
        messages.success(request, 'Отправлено на согласование в УК.')
        return _approval_redirect(calc.pk)

    if action == 'uk_approve':
        if not user_has_deal_calc_uk_access(request.user):
            messages.error(request, 'Нет прав на согласование УК.')
            return _approval_redirect(calc.pk)
        if calc.soglasovanie_status != CarCalculations.SOGLASOVANIE_PENDING_UK:
            messages.error(request, 'КП не ожидает согласования УК.')
            return _approval_redirect(calc.pk)
        comment = _require_comment(request, comment)
        if comment is None:
            return _approval_redirect(calc.pk)

        now = timezone.now()
        calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_UK_APPROVED
        calc.uk_approve_user = request.user
        calc.uk_approve_date = now
        calc.uk_approve_comment = comment
        calc.date_success = now
        calc.save(update_fields=[
            'soglasovanie_status',
            'uk_approve_user',
            'uk_approve_date',
            'uk_approve_comment',
            'date_success',
        ])
        send_calc_rlk_chat_message(
            calc,
            request.user,
            'Согласовано УК ' + comment,
        )
        messages.success(request, 'Коммерческое предложение согласовано УК.')
        return _approval_redirect(calc.pk)

    return None
