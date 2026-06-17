"""Согласование коммерческих предложений в калькуляции сделки."""
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils import timezone

from chats.models import Chat

AUTO_APPROVE_USER_ID = 1
AUTO_APPROVE_COMMENT = 'Автоматическое согласование: КВ выше расчетного КМ по правилу'


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


def kvp_above_km_raschet(calc):
    """КВ выше расчетного КМ по правилу — согласование не требуется."""
    if calc.km_raschet is None:
        return False
    return int(calc.kvp or 0) > int(calc.km_raschet)


def is_auto_approved_calculation(calc):
    from prices_car.models import CarCalculations

    return (
        calc.soglasovanie_status == CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
        and calc.director_approve_user_id == AUTO_APPROVE_USER_ID
        and calc.director_approve_comment == AUTO_APPROVE_COMMENT
    )


def try_auto_approve_calculation(calc, send_chat=False):
    """Автосогласование под пользователем id=1, если КВ > расчетного КМ."""
    from prices_car.models import CarCalculations

    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    if status != CarCalculations.SOGLASOVANIE_PENDING:
        return False
    if not kvp_above_km_raschet(calc):
        return False

    user = User.objects.filter(pk=AUTO_APPROVE_USER_ID).first()
    if not user:
        return False

    now = timezone.now()
    calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
    calc.director_approve_user = user
    calc.director_approve_date = now
    calc.director_approve_comment = AUTO_APPROVE_COMMENT
    calc.date_success = now
    calc.save(update_fields=[
        'soglasovanie_status',
        'director_approve_user',
        'director_approve_date',
        'director_approve_comment',
        'date_success',
    ])

    if send_chat:
        number = calc.number or calc.pk
        send_calc_rlk_chat_message(
            calc,
            user,
            'Коммерческое предложение #' + str(number)
            + ' согласовано автоматически. КВ выше расчетного КМ по правилу.',
        )
    return True


def notify_director_users_calculation_approval(calculation_object, car_object, unit_object):
    """Email директорам ДЦ (price_car_new_director + unit)."""
    from prices_car.models import EmailPushCar

    try:
        users_soglasovanie = User.objects.filter(
            is_active=True,
            profiles__available_units__pk=unit_object.id,
            profiles__price_car_new_director=True,
        ).distinct()
        for uusr in users_soglasovanie:
            if uusr.email:
                new_message = EmailPushCar()
                new_message.car = car_object
                new_message.user = uusr
                new_message.email = uusr.email
                new_message.comment = (
                    'Согласование расчета продажи автомобиля #'
                    + str(calculation_object.number)
                )
                new_message.price = False
                new_message.calc = calculation_object
                new_message.save()
    except Exception:
        pass


def notify_uk_users_calculation_approval(calc, car_object=None):
    """Email всем с price_car_new_all («Ценообразование новых всех ДЦ»)."""
    from prices_car.models import EmailPushCar

    car = car_object or calc.car
    if not car:
        return

    try:
        users_uk = User.objects.filter(
            is_active=True,
            profiles__price_car_new_all=True,
        ).distinct()
        for uusr in users_uk:
            if uusr.email:
                new_message = EmailPushCar()
                new_message.car = car
                new_message.user = uusr
                new_message.email = uusr.email
                new_message.comment = 'Требуется согласование УК'
                new_message.price = False
                new_message.calc = calc
                new_message.save()
    except Exception:
        pass


def notify_calculation_soglasovanie_from_1c(calculation_object, car_object, rlk_object, unit_object):
    """После загрузки КП из 1С: автосогласование или уведомление директоров."""
    auto_approved = try_auto_approve_calculation(calculation_object, send_chat=False)

    try:
        from website.views import send_web_socket_message

        chat, _ = Chat.objects.get_or_create(
            name=str(rlk_object.id),
            slug='rlk_' + str(rlk_object.id),
        )
        user = User.objects.get(pk=AUTO_APPROVE_USER_ID)
        if auto_approved:
            text = (
                'Коммерческое предложение #'
                + str(calculation_object.number)
                + ' согласовано автоматически. КВ выше расчетного КМ по правилу.'
            )
        else:
            text = (
                'Коммерческое предложение #'
                + str(calculation_object.number)
                + ' отправлено на согласование. '
                + (calculation_object.comment or '')
            )
        send_web_socket_message(
            group='rlk_' + str(rlk_object.id),
            chat=chat,
            user=user,
            text=text,
        )
    except Exception:
        pass

    if auto_approved:
        return True

    notify_director_users_calculation_approval(
        calculation_object, car_object, unit_object,
    )

    return False


def build_calculation_soglasovanie_api_response(calc):
    """Данные согласования для ответа API 1С после загрузки КП."""
    from prices_car.models import CarCalculations

    calc.refresh_from_db()
    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    return {
        'soglasovanie_status': status,
        'soglasovanie_status_label': dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES).get(
            status, status,
        ),
        'soglasovanie_auto_approved': is_auto_approved_calculation(calc),
        'km_raschet': calc.km_raschet,
        'kvp': calc.kvp,
    }


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
    can_director_reject = (
        is_director
        and status == CarCalculations.SOGLASOVANIE_PENDING
    )
    can_uk_reject = (
        is_uk
        and status == CarCalculations.SOGLASOVANIE_PENDING_UK
    )
    approval_final_without_uk = status == CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
    approval_auto_approved = is_auto_approved_calculation(calc)
    approval_kvp_above_raschet = kvp_above_km_raschet(calc)

    return {
        'approval_min_km_dc': min_km_dc,
        'approval_kvp_ok': kvp_ok,
        'approval_kvp_above_raschet': approval_kvp_above_raschet,
        'approval_auto_approved': approval_auto_approved,
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
        'approval_can_director_reject': can_director_reject,
        'approval_can_uk_reject': can_uk_reject,
        'approval_status': status,
        'approval_status_label': dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES).get(
            status, status,
        ),
    }


def _approval_redirect(calc_pk):
    return HttpResponseRedirect('/cars/deal/calculation/' + str(calc_pk) + '/')


def _require_comment(request, comment, error_message='Укажите комментарий к согласованию.'):
    comment = (comment or '').strip()
    if not comment:
        messages.error(request, error_message)
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
        notify_uk_users_calculation_approval(calc)
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

    if action == 'director_reject':
        if not user_is_deal_calc_director_for_calc(request.user, calc):
            messages.error(request, 'Нет прав на отказ в согласовании директором ДЦ.')
            return _approval_redirect(calc.pk)
        if calc.soglasovanie_status != CarCalculations.SOGLASOVANIE_PENDING:
            messages.error(request, 'КП уже обработано директором.')
            return _approval_redirect(calc.pk)
        comment = _require_comment(
            request, comment, error_message='Укажите причину отказа от согласования.',
        )
        if comment is None:
            return _approval_redirect(calc.pk)

        now = timezone.now()
        calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED
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
            'Отказ в согласовании директором ДЦ: ' + comment,
        )
        messages.success(request, 'Отказ в согласовании зарегистрирован.')
        return _approval_redirect(calc.pk)

    if action == 'uk_reject':
        if not user_has_deal_calc_uk_access(request.user):
            messages.error(request, 'Нет прав на отказ в согласовании УК.')
            return _approval_redirect(calc.pk)
        if calc.soglasovanie_status != CarCalculations.SOGLASOVANIE_PENDING_UK:
            messages.error(request, 'КП не ожидает согласования УК.')
            return _approval_redirect(calc.pk)
        comment = _require_comment(
            request, comment, error_message='Укажите причину отказа от согласования.',
        )
        if comment is None:
            return _approval_redirect(calc.pk)

        now = timezone.now()
        calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_UK_REJECTED
        calc.uk_approve_user = request.user
        calc.uk_approve_date = now
        calc.uk_approve_comment = comment
        calc.save(update_fields=[
            'soglasovanie_status',
            'uk_approve_user',
            'uk_approve_date',
            'uk_approve_comment',
        ])
        send_calc_rlk_chat_message(
            calc,
            request.user,
            'Отказ в согласовании УК: ' + comment,
        )
        messages.success(request, 'Отказ в согласовании УК зарегистрирован.')
        return _approval_redirect(calc.pk)

    return None
