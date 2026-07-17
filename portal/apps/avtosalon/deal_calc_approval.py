"""Согласование коммерческих предложений в калькуляции сделки."""
import logging

import requests
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils import timezone

from chats.models import Chat

logger = logging.getLogger(__name__)

AUTO_APPROVE_USER_ID = 1
AUTO_APPROVE_COMMENT = (
    'Автоматическое согласование: КВП выше итога по правилу '
    'и выше мин. КМ ДЦ, если он задан'
)
LEGACY_AUTO_APPROVE_COMMENT = 'Автоматическое согласование: КВ выше итога по правилу'
LEGACY_AUTO_APPROVE_COMMENT_RULE_MIN = (
    'Автоматическое согласование: КВП выше итога по правилу, '
    'итог по правилу выше мин. КМ ДЦ'
)
URL_HS_ALFA_AUTO      = 'http://k01srv1c10/ralfa01/hs/mb/'

FINAL_SOGLASOVANIE_STATUSES_FOR_1C = frozenset({
    'director_approved',
    'uk_approved',
    'director_rejected',
    'uk_rejected',
})


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
    """КВП выше минимального КМ ДЦ — условие согласования директором без УК."""
    kvp = int(calc.kvp or 0)
    min_km_dc = get_calc_min_km_dc(cumulative_data, calc.car)
    return min_km_dc > 0 and kvp > min_km_dc


def kvp_above_min_dc_if_configured(calc, cumulative_data):
    """КВП выше мин. КМ ДЦ либо порог ДЦ не задан — условие автосогласования."""
    min_km_dc = get_calc_min_km_dc(cumulative_data, calc.car)
    return min_km_dc <= 0 or int(calc.kvp or 0) > min_km_dc


def director_can_approve_without_uk(calc, cumulative_data):
    """Директор согласует без УК, если КВП коммерческого предложения выше мин. КМ ДЦ."""
    return kvp_above_min_km_dc(calc, cumulative_data)


def _get_calc_cumulative_data(calc):
    car = getattr(calc, 'car', None)
    if not car:
        return None, None
    try:
        return car.cumulative_data(), car
    except Exception:
        return None, car


def kvp_above_km_rule(calc, cumulative_data=None):
    """КВП коммерческого предложения выше итога по правилу."""
    from prices_car.km_breakdown import get_km_rule_total

    if cumulative_data is None:
        cumulative_data, _ = _get_calc_cumulative_data(calc)
    km_rule = get_km_rule_total(cumulative_data, calc.car, calc=calc)
    if km_rule is None:
        return False
    return int(calc.kvp or 0) > int(km_rule)


def can_auto_approve_calculation(calc, cumulative_data=None):
    """Автосогласование: КВП выше правила и выше заданного мин. КМ ДЦ."""
    if cumulative_data is None:
        cumulative_data, _ = _get_calc_cumulative_data(calc)
    return (
        kvp_above_km_rule(calc, cumulative_data)
        and kvp_above_min_dc_if_configured(calc, cumulative_data)
    )


def is_auto_approved_calculation(calc):
    from prices_car.models import CarCalculations

    return (
        calc.soglasovanie_status == CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
        and calc.director_approve_user_id == AUTO_APPROVE_USER_ID
        and calc.director_approve_comment in (
            AUTO_APPROVE_COMMENT,
            LEGACY_AUTO_APPROVE_COMMENT,
            LEGACY_AUTO_APPROVE_COMMENT_RULE_MIN,
        )
    )


def recalculate_deal_calculation_km(calc, user):
    """
    Пересчёт расчётного КМ и повторная проверка автосогласования.
    Только для price_car_new_all. Ручные согласования/отказы не трогаем;
    ошибочное автосогласование сбрасываем и переоцениваем.
    """
    from prices_car.km_raschet import (
        apply_km_raschet_to_calculation,
        calculation_has_applied_trade_in,
    )
    from prices_car.models import CarCalculations

    if not user_has_deal_calc_uk_access(user):
        return False, 'Недостаточно прав для пересчёта.'

    car = getattr(calc, 'car', None)
    if not car:
        return False, 'У КП не указан автомобиль.'

    apply_km_raschet_to_calculation(calc, car)
    update_fields = ['km_raschet']

    reset_auto = is_auto_approved_calculation(calc)
    if reset_auto:
        calc.soglasovanie_status = CarCalculations.SOGLASOVANIE_PENDING
        calc.director_approve_user = None
        calc.director_approve_date = None
        calc.director_approve_comment = ''
        update_fields.extend([
            'soglasovanie_status',
            'director_approve_user',
            'director_approve_date',
            'director_approve_comment',
        ])

    calc.save(update_fields=update_fields)

    cumulative_data = None
    try:
        cumulative_data = car.cumulative_data()
    except Exception:
        pass

    auto_ok = try_auto_approve_calculation(
        calc, send_chat=True, cumulative_data=cumulative_data,
    )

    with_ti = calculation_has_applied_trade_in(calc)
    km = calc.km_raschet
    km_txt = f'{int(km):,}'.replace(',', ' ') if km is not None else '—'
    ti_txt = 'с trade-in' if with_ti else 'без trade-in'
    if auto_ok:
        msg = f'Пересчитано ({ti_txt}): расч. КМ {km_txt} ₽. Автосогласование применено.'
    elif reset_auto:
        msg = (
            f'Пересчитано ({ti_txt}): расч. КМ {km_txt} ₽. '
            'Автосогласование снято — условия больше не выполняются.'
        )
    else:
        msg = f'Пересчитано ({ti_txt}): расч. КМ {km_txt} ₽.'
    return True, msg


def try_auto_approve_calculation(calc, send_chat=False, cumulative_data=None):
    """Автосогласование под пользователем id=1, если КВ > итога по правилу."""
    from prices_car.models import CarCalculations

    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    if status not in (
        CarCalculations.SOGLASOVANIE_PENDING,
        CarCalculations.SOGLASOVANIE_AWAITING_1C,
        '',
    ):
        return False
    if cumulative_data is None:
        cumulative_data, _ = _get_calc_cumulative_data(calc)
    if not can_auto_approve_calculation(calc, cumulative_data):
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
            + ' согласовано автоматически. КВП выше итога по правилу '
            + 'и выше мин. КМ ДЦ, если он задан.',
        )
    notify_auto_approved_calculation_email(calc)
    return True


def notify_auto_approved_calculation_email(calc):
    """Письмо директорам ДЦ подразделения об автоматическом согласовании КП."""
    from prices_car.models import EmailPushCar

    car = calc.car
    if not car:
        return
    unit_id = get_calc_unit_id(calc)
    if not unit_id:
        return

    number = calc.number or calc.pk
    comment = (
        'Коммерческое предложение #{} согласовано автоматически. '
        'КВП выше итога по правилу и выше мин. КМ ДЦ, если он задан.'
    ).format(number)
    sent = False
    try:
        for user in User.objects.filter(
            is_active=True,
            profiles__price_car_new_director=True,
            profiles__available_units__pk=unit_id,
        ).distinct():
            if not (user.email or '').strip():
                continue
            EmailPushCar.objects.create(
                car=car,
                user=user,
                email=user.email,
                comment=comment,
                price=False,
                calc=calc,
            )
            sent = True
        if sent:
            _trigger_calc_email_send()
    except Exception:
        logger.exception(
            'notify_auto_approved_calculation_email failed calc_id=%s',
            calc.pk,
        )


def notify_director_users_calculation_approval(calculation_object, car_object, unit_object):
    """Email директорам ДЦ (price_car_new_director + unit)."""
    from prices_car.models import EmailPushCar

    sent = False
    try:
        users_soglasovanie = User.objects.filter(
            is_active=True,
            profiles__available_units__pk=unit_object.id,
            profiles__price_car_new_director=True,
        ).distinct()
        for uusr in users_soglasovanie:
            if uusr.email:
                EmailPushCar.objects.create(
                    car=car_object,
                    user=uusr,
                    email=uusr.email,
                    comment=(
                        'Согласование расчета продажи автомобиля #'
                        + str(calculation_object.number)
                    ),
                    price=False,
                    calc=calculation_object,
                )
                sent = True
        if sent:
            _trigger_calc_email_send()
    except Exception:
        logger.exception(
            'notify_director_users_calculation_approval failed calc_id=%s',
            calculation_object.pk,
        )


def _actor_display_name(user):
    if not user:
        return ''
    profile = _get_profile(user)
    if profile and profile.eco_name:
        return profile.eco_name
    return user.get_full_name() or user.username


def _build_soglasovanie_email_comment(calc, title, result_comment, actor_user=None):
    number = calc.number or calc.pk
    parts = ['КП #{}: {}'.format(number, title)]
    actor_name = _actor_display_name(actor_user)
    if actor_name:
        parts.append('Исполнитель: {}'.format(actor_name))
    text = (result_comment or '').strip()
    if text:
        parts.append('Комментарий: {}'.format(text))
    return '. '.join(parts)


def _enqueue_calc_soglasovanie_email(calc, user, comment):
    from prices_car.models import EmailPushCar

    car = calc.car
    if not car or not user or not (user.email or '').strip():
        return False
    EmailPushCar.objects.create(
        car=car,
        user=user,
        email=user.email,
        comment=comment,
        price=False,
        calc=calc,
    )
    return True


def _collect_calc_result_recipients(calc, actor_user=None, include_director=True):
    """Автор, менеджер КП и директор, отправивший в УК (без исполнителя действия)."""
    recipients = []
    seen = set()
    actor_id = actor_user.pk if actor_user else None

    def add(user):
        if not user or not user.is_active or not (user.email or '').strip():
            return
        if user.pk in seen or user.pk == actor_id:
            return
        seen.add(user.pk)
        recipients.append(user)

    if calc.user_id:
        add(calc.user)
    for staff in (calc.author, calc.staff):
        if staff and staff.domain_login:
            add(User.objects.filter(username__iexact=staff.domain_login, is_active=True).first())
    if include_director and calc.director_approve_user_id:
        add(calc.director_approve_user)
    return recipients


def _collect_director_approve_email_recipients(calc, actor_user=None):
    """Автор КП и директора ДЦ подразделения (без исполнителя согласования)."""
    recipients = []
    seen = set()
    actor_id = actor_user.pk if actor_user else None

    def add(user):
        if not user or not user.is_active or not (user.email or '').strip():
            return
        if user.pk in seen or user.pk == actor_id:
            return
        seen.add(user.pk)
        recipients.append(user)

    if calc.author and calc.author.domain_login:
        add(User.objects.filter(username__iexact=calc.author.domain_login, is_active=True).first())
    elif calc.user_id:
        add(calc.user)

    unit_id = get_calc_unit_id(calc)
    if unit_id:
        for user in User.objects.filter(
            is_active=True,
            profiles__price_car_new_director=True,
            profiles__available_units__pk=unit_id,
        ).distinct():
            add(user)
    return recipients


def _trigger_calc_email_send():
    try:
        from task_manager.views import start_send_push_car
        start_send_push_car()
    except Exception:
        pass


def notify_calc_soglasovanie_result_email(calc, event, result_comment, actor_user):
    """
    Письмо с результатом согласования КП.
    event: director_approve | director_send_uk | director_reject | uk_approve | uk_reject
    """
    titles = {
        'director_approve': 'Согласовано директором ДЦ',
        'director_send_uk': 'Отправлено на согласование УК',
        'director_reject': 'Отказ в согласовании директором ДЦ',
        'uk_approve': 'Согласовано УК',
        'uk_reject': 'Отказ в согласовании УК',
    }
    title = titles.get(event)
    if not title or not calc.car_id:
        return

    comment = _build_soglasovanie_email_comment(calc, title, result_comment, actor_user)
    sent = False

    try:
        if event == 'director_send_uk':
            users_uk = User.objects.filter(
                is_active=True,
                profiles__price_car_new_all=True,
            ).distinct()
            for user in users_uk:
                if _enqueue_calc_soglasovanie_email(calc, user, comment):
                    sent = True
        elif event == 'director_approve':
            for user in _collect_director_approve_email_recipients(calc, actor_user=actor_user):
                if _enqueue_calc_soglasovanie_email(calc, user, comment):
                    sent = True
        else:
            include_director = event in ('uk_approve', 'uk_reject')
            for user in _collect_calc_result_recipients(
                calc, actor_user=actor_user, include_director=include_director,
            ):
                if _enqueue_calc_soglasovanie_email(calc, user, comment):
                    sent = True
        if sent:
            _trigger_calc_email_send()
    except Exception:
        logger.exception('calc soglasovanie email failed calc_id=%s event=%s', calc.pk, event)


def notify_uk_users_calculation_approval(calc, car_object=None, result_comment='', actor_user=None):
    """Email всем с price_car_new_all — устаревший вызов, делегирует в notify_calc_soglasovanie_result_email."""
    notify_calc_soglasovanie_result_email(
        calc,
        'director_send_uk',
        result_comment or 'Требуется согласование УК',
        actor_user,
    )


def notify_calculation_soglasovanie_from_1c(calculation_object, car_object, rlk_object, unit_object):
    """Устаревший вызов: делегирует в prepare_calculation_soglasovanie_from_1c."""
    return prepare_calculation_soglasovanie_from_1c(
        calculation_object, car_object, rlk_object, unit_object,
    )


def _send_auto_approved_soglasovanie_chat(calculation_object, rlk_object):
    try:
        from website.views import send_web_socket_message

        chat, _ = Chat.objects.get_or_create(
            name=str(rlk_object.id),
            slug='rlk_' + str(rlk_object.id),
        )
        user = User.objects.get(pk=AUTO_APPROVE_USER_ID)
        text = (
            'Коммерческое предложение #'
            + str(calculation_object.number)
            + ' согласовано автоматически. КВП выше итога по правилу '
            + 'и выше мин. КМ ДЦ, если он задан.'
        )
        send_web_socket_message(
            group='rlk_' + str(rlk_object.id),
            chat=chat,
            user=user,
            text=text,
        )
    except Exception:
        pass


def _send_pending_soglasovanie_notifications(calculation_object, car_object, rlk_object, unit_object):
    """Чат и email директорам после подтверждения отправки на согласование из 1С."""
    text = (
        'Коммерческое предложение #'
        + str(calculation_object.number)
        + ' отправлено на согласование. '
        + (calculation_object.comment or '')
    )
    try:
        user = User.objects.get(pk=AUTO_APPROVE_USER_ID)
        send_calc_rlk_chat_message(calculation_object, user, text)
    except Exception:
        logger.exception(
            'pending soglasovanie chat failed calc_id=%s rlk_id=%s',
            calculation_object.pk,
            getattr(rlk_object, 'pk', None),
        )

    notify_director_users_calculation_approval(
        calculation_object, car_object, unit_object,
    )


def prepare_calculation_soglasovanie_from_1c(calculation_object, car_object, rlk_object, unit_object):
    """
    После загрузки КП из 1С: автосогласование или ожидание подтверждения в 1С.
    Уведомления директорам и чат — только при автосогласовании или после submit из 1С.
    """
    from prices_car.models import CarCalculations

    cumulative_data = None
    if car_object:
        try:
            cumulative_data = car_object.cumulative_data()
        except Exception:
            pass

    current_status = calculation_object.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    # «pending» — дефолт модели при создании КП, это ещё не отправка директору.
    # После submit тот же статус имеет date_start_soglasovanie и уже означает
    # реальную очередь директора — повторная загрузка не должна её сбрасывать.
    in_approval_pipeline = (
        (
            current_status == CarCalculations.SOGLASOVANIE_PENDING
            and calculation_object.date_start_soglasovanie is not None
        )
        or current_status in {
            CarCalculations.SOGLASOVANIE_PENDING_UK,
            CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
            CarCalculations.SOGLASOVANIE_UK_APPROVED,
            CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
            CarCalculations.SOGLASOVANIE_UK_REJECTED,
        }
    )

    if in_approval_pipeline:
        return False

    auto_approved = try_auto_approve_calculation(
        calculation_object,
        send_chat=False,
        cumulative_data=cumulative_data,
    )

    if auto_approved:
        _send_auto_approved_soglasovanie_chat(calculation_object, rlk_object)
        return True

    calculation_object.soglasovanie_status = CarCalculations.SOGLASOVANIE_AWAITING_1C
    calculation_object.save(update_fields=['soglasovanie_status'])
    return False


def submit_calculation_soglasovanie_from_1c(calculation_object, car_object, rlk_object, unit_object):
    """Подтверждение отправки на согласование из 1С — уведомления директорам и чат."""
    from prices_car.models import CarCalculations

    if is_auto_approved_calculation(calculation_object):
        return True

    status = calculation_object.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    if (
        status == CarCalculations.SOGLASOVANIE_PENDING
        and calculation_object.date_start_soglasovanie is not None
    ):
        # Уже подтверждено из 1С и отправлено директорам (повторный вызов).
        return True
    if status not in (
        CarCalculations.SOGLASOVANIE_AWAITING_1C,
        CarCalculations.SOGLASOVANIE_PENDING,
    ):
        logger.warning(
            'submit_calculation_soglasovanie_from_1c skipped calc_id=%s status=%s',
            calculation_object.pk,
            status,
        )
        return False

    now = timezone.now()
    calculation_object.soglasovanie_status = CarCalculations.SOGLASOVANIE_PENDING
    calculation_object.date_start_soglasovanie = now
    calculation_object.save(update_fields=['soglasovanie_status', 'date_start_soglasovanie'])

    _send_pending_soglasovanie_notifications(
        calculation_object, car_object, rlk_object, unit_object,
    )
    return True


def build_calculation_soglasovanie_api_response(calc):
    """Данные согласования для ответа API 1С после загрузки КП."""
    from prices_car.models import CarCalculations
    from prices_car.km_breakdown import get_km_rule_total
    from prices_car.km_raschet import calculation_has_applied_trade_in

    calc.refresh_from_db()
    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    km_rule_total = None
    km_min_dc = 0
    cumulative_data = None
    if calc.car_id:
        try:
            cumulative_data = calc.car.cumulative_data()
            km_rule_total = get_km_rule_total(cumulative_data, calc.car, calc=calc)
            km_min_dc = get_calc_min_km_dc(cumulative_data, calc.car)
        except Exception:
            pass

    # Не подменяем отсутствующий итог правила порогом ДЦ: это разные этапы согласования.
    km_min_calculated = km_rule_total

    return {
        'soglasovanie_status': status,
        'soglasovanie_status_label': dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES).get(
            status, status,
        ),
        'soglasovanie_auto_approved': is_auto_approved_calculation(calc),
        'requires_soglasovanie_confirm': status == CarCalculations.SOGLASOVANIE_AWAITING_1C,
        'km_raschet': calc.km_raschet,
        'km_min_dc': km_min_dc or None,
        'km_rule_total': km_rule_total,
        'km_min_calculated': km_min_calculated,
        'km_rule_with_trade_in': calculation_has_applied_trade_in(calc),
        'kvp_above_km_rule': (
            km_rule_total is not None
            and int(calc.kvp or 0) > int(km_rule_total)
        ),
        'kvp_above_min_dc': km_min_dc > 0 and int(calc.kvp or 0) > int(km_min_dc),
        'auto_min_dc_ok': km_min_dc <= 0 or int(calc.kvp or 0) > int(km_min_dc),
        'kvp': calc.kvp,
    }


def _format_1c_datetime(value):
    if not value:
        return ''
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.strftime('%Y-%m-%dT%H:%M:%S')


def _staff_uin_for_user(user):
    if not user:
        return ''
    from refs.models import RefStaff

    staff = RefStaff.objects.filter(domain_login__iexact=user.username).first()
    if staff and staff.uin:
        return staff.uin
    return ''


def should_send_calculation_soglasovanie_to_1c(calc):
    """Конечные статусы для 1С, кроме автоматического согласования."""
    from prices_car.models import CarCalculations

    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    if status not in FINAL_SOGLASOVANIE_STATUSES_FOR_1C:
        return False
    if status == CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED:
        return is_auto_approved_calculation(calc)
    return True


def build_calculation_soglasovanie_1c_payload(calc):
    """Конечное состояние согласования для обмена с 1С."""
    from prices_car.models import CarCalculations

    status = calc.soglasovanie_status or CarCalculations.SOGLASOVANIE_PENDING
    status_label = dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES).get(status, status)
    approved = status in (
        CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
        CarCalculations.SOGLASOVANIE_UK_APPROVED,
    )
    rejected = status in (
        CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
        CarCalculations.SOGLASOVANIE_UK_REJECTED,
    )

    comment_soglasovanie = ''
    rejection = ''
    date_success = ''
    approver_user = None

    if status in (
        CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
        CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
    ):
        comment_soglasovanie = calc.director_approve_comment or ''
        rejection = comment_soglasovanie if rejected else ''
        date_success = _format_1c_datetime(calc.director_approve_date or calc.date_success)
        approver_user = calc.director_approve_user
    elif status in (
        CarCalculations.SOGLASOVANIE_UK_APPROVED,
        CarCalculations.SOGLASOVANIE_UK_REJECTED,
    ):
        comment_soglasovanie = calc.uk_approve_comment or ''
        rejection = comment_soglasovanie if rejected else ''
        date_success = _format_1c_datetime(calc.uk_approve_date or calc.date_success)
        approver_user = calc.uk_approve_user
    
    return {
        'Type': 'ChangeKP',
        'Uin': calc.uin or '',
        'Number': calc.number or '',
        'SoglasovanieStatus': status,
        'SoglasovanieStatusLabel': status_label,
        'Success': approved,
        'Rejected': rejected,
        'Date_success': date_success,
        'CommentSoglasovanie': comment_soglasovanie if approved else '',
        'CanceledComment': rejection,
        'ApproverUin': _staff_uin_for_user(approver_user),
        'ApproverName': (
            (getattr(getattr(approver_user, 'profiles', None), 'eco_name', None) or '')
            or (approver_user.get_full_name() if approver_user else '')
        ),
    }


def send_calculation_soglasovanie_result_to_1c(calc):
    """Отправка конечного статуса согласования КП в 1С."""
    if not should_send_calculation_soglasovanie_to_1c(calc):
        return False
    if not (calc.uin or '').strip():
        logger.warning('calculation soglasovanie 1C skip: empty uin, calc_id=%s', calc.pk)
        return False

    payload = build_calculation_soglasovanie_1c_payload(calc)
    
    js_data = payload 

    try:
        response = requests.post(
            URL_HS_ALFA_AUTO,
            json=js_data,
            timeout=60,
        )
        if response.status_code != 200:
            logger.warning(
                'calculation soglasovanie 1C HTTP %s calc_id=%s body=%s',
                response.status_code,
                calc.pk,
                response.text[:500],
            )
            return False
        return True
    except Exception:
        logger.exception('calculation soglasovanie 1C failed calc_id=%s', calc.pk)
        return False


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
    min_km_dc = get_calc_min_km_dc(cumulative_data, calc.car)
    kvp_ok = kvp_above_km_rule(calc, cumulative_data)
    director_can_approve = director_can_approve_without_uk(calc, cumulative_data)
    approval_auto_approved = is_auto_approved_calculation(calc)

    can_director_approve = (
        is_director
        and status == CarCalculations.SOGLASOVANIE_PENDING
        and director_can_approve
    )
    can_director_send_uk = (
        is_director
        and status == CarCalculations.SOGLASOVANIE_PENDING
        and not approval_auto_approved
        and not director_can_approve
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
    approval_kvp_above_km_rule = kvp_above_km_rule(calc, cumulative_data)
    approval_auto_min_dc_ok = kvp_above_min_dc_if_configured(calc, cumulative_data)
    approval_can_auto_approve = can_auto_approve_calculation(calc, cumulative_data)
    km_rule_total = None
    if cumulative_data:
        from prices_car.km_breakdown import get_km_rule_total
        km_rule_total = get_km_rule_total(cumulative_data, calc.car, calc=calc)

    return {
        'approval_min_km_dc': min_km_dc,
        'approval_kvp_ok': kvp_ok,
        'approval_director_can_approve': director_can_approve,
        'approval_kvp_above_km_rule': approval_kvp_above_km_rule,
        'approval_auto_min_dc_ok': approval_auto_min_dc_ok,
        'approval_can_auto_approve': approval_can_auto_approve,
        'approval_km_rule_total': km_rule_total,
        'approval_auto_approved': approval_auto_approved,
        'approval_uk_required': (
            status == CarCalculations.SOGLASOVANIE_PENDING_UK
            or (
                status == CarCalculations.SOGLASOVANIE_PENDING
                and not approval_auto_approved
                and not director_can_approve
            )
        ),
        'approval_awaiting_1c': status == CarCalculations.SOGLASOVANIE_AWAITING_1C,
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
        if not director_can_approve_without_uk(calc, cumulative_data):
            min_km_dc = get_calc_min_km_dc(cumulative_data, calc.car)
            if min_km_dc <= 0:
                messages.error(request, 'Мин. КМ ДЦ не задан или равен 0 — директор ДЦ не может согласовать это КП, отправьте его в УК с комментарием.')
            else:
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
        notify_calc_soglasovanie_result_email(calc, 'director_approve', comment, request.user)
        send_calculation_soglasovanie_result_to_1c(calc)
        messages.success(request, 'Коммерческое предложение согласовано. Дополнительное согласование УК не требуется.')
        return _approval_redirect(calc.pk)

    if action == 'director_send_uk':
        if not user_is_deal_calc_director_for_calc(request.user, calc):
            messages.error(request, 'Нет прав на отправку в УК.')
            return _approval_redirect(calc.pk)
        if calc.soglasovanie_status != CarCalculations.SOGLASOVANIE_PENDING:
            messages.error(request, 'КП уже обработано директором.')
            return _approval_redirect(calc.pk)
        if director_can_approve_without_uk(calc, cumulative_data):
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
        notify_calc_soglasovanie_result_email(calc, 'director_send_uk', comment, request.user)
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
        notify_calc_soglasovanie_result_email(calc, 'uk_approve', comment, request.user)
        send_calculation_soglasovanie_result_to_1c(calc)
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
        notify_calc_soglasovanie_result_email(calc, 'director_reject', comment, request.user)
        send_calculation_soglasovanie_result_to_1c(calc)
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
        notify_calc_soglasovanie_result_email(calc, 'uk_reject', comment, request.user)
        send_calculation_soglasovanie_result_to_1c(calc)
        messages.success(request, 'Отказ в согласовании УК зарегистрирован.')
        return _approval_redirect(calc.pk)

    return None
