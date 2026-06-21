"""История перерасчётов ценообразования интерактивной оценки."""
import contextvars
import json

from django.utils import timezone

from refs.models import RefStaff

PRICE_CALCULATION_LABELS = {
    'kors': '1C / Kors',
    'autohub_k': 'Автохаб +К',
    'autohub': 'Автохаб',
    'avito': 'Авито / Автотека',
    'custom': 'Ручной расчёт',
}

TRIGGER_LABELS = {
    'price_after_kd': 'Согласование после КД',
    'price_remote': 'Дистанционная оценка',
    'save_auto_price': 'Сохранение автоматических цен',
    'save_custom_price': 'Сохранение согласованных цен',
}

_history_context = contextvars.ContextVar('interactive_price_history_context', default=None)


class InteractivePriceHistoryContext:
    def __init__(self, user=None, trigger='', save_history=False):
        self.user = user
        self.trigger = trigger or ''
        self.save_history = bool(save_history)


class interactive_price_history_context:
    def __init__(self, user=None, trigger='', save_history=True):
        self._token = None
        self._context = InteractivePriceHistoryContext(
            user=user,
            trigger=trigger,
            save_history=save_history,
        )

    def __enter__(self):
        self._token = _history_context.set(self._context)
        return self._context

    def __exit__(self, exc_type, exc, tb):
        if self._token is not None:
            _history_context.reset(self._token)
        return False


def get_interactive_price_history_context():
    return _history_context.get()


def resolve_history_params(user=None, trigger='', save_history=None):
    ctx = get_interactive_price_history_context()
    if save_history is None:
        save_history = ctx.save_history if ctx else False
    if user is None and ctx:
        user = ctx.user
    if not trigger and ctx:
        trigger = ctx.trigger
    return user, trigger, bool(save_history)


def _resolve_staff(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return RefStaff.objects.filter(domain_login=user.username).first()


def _json_safe_price_result(price_result):
    if not price_result:
        return {}
    data = dict(price_result)
    data.pop('estimation_settings', None)
    return data


def _snapshot_soglasovanie_fields(soglasovanie):
    if soglasovanie is None:
        return {}
    return {
        'price_auto_1': soglasovanie.price_auto_1 or 0,
        'price_auto_2': soglasovanie.price_auto_2 or 0,
        'price_auto_3': soglasovanie.price_auto_3 or 0,
        'price_auto_bcp_1': soglasovanie.price_auto_bcp_1 or 0,
        'price_auto_bcp_2': soglasovanie.price_auto_bcp_2 or 0,
        'price_auto_bcp_3': soglasovanie.price_auto_bcp_3 or 0,
        'price_zna_1': soglasovanie.price_zna_1 or 0,
        'price_zna_2': soglasovanie.price_zna_2 or 0,
        'price_zna_3': soglasovanie.price_zna_3 or 0,
        'price_before_kd': soglasovanie.price_before_kd or 0,
        'price_after_kd': soglasovanie.price_after_kd or 0,
        'price_bcp': soglasovanie.price_bcp or 0,
        'discount_torg': soglasovanie.discount_torg or 0,
        'finance_price': soglasovanie.finance_price or 0,
        'zachita_ot_ubitka': soglasovanie.zachita_ot_ubitka or 0,
    }


def record_interactive_price_recalculation(
    estimation,
    soglasovanie,
    type_calculation,
    price_result,
    user=None,
    trigger='',
    save_history=None,
    is_success=True,
    error_message='',
):
    from register.models import RegInteractivOcenkaPrice

    user, trigger, save_history = resolve_history_params(user, trigger, save_history)
    if not save_history or soglasovanie is None:
        return None

    soglasovanie.refresh_from_db()
    safe_result = _json_safe_price_result(price_result)
    snapshot = _snapshot_soglasovanie_fields(soglasovanie)

    record = RegInteractivOcenkaPrice(
        date=timezone.now(),
        price_calculation=type_calculation or '',
        trigger=trigger or type_calculation or '',
        page_soglasovanie=soglasovanie,
        estimation=estimation,
        author=user if user and getattr(user, 'is_authenticated', False) else None,
        user=_resolve_staff(user),
        is_success=is_success,
        error_message=error_message or '',
        estimation_price=(safe_result.get('estimation_price') if safe_result else 0) or 0,
        estimation_price_do_kd=(safe_result.get('estimation_price_do_kd') if safe_result else 0) or 0,
        zna=(safe_result.get('zna') if safe_result else 0) or 0,
        zg=str(safe_result.get('zg') or '') if safe_result else '',
        kf=str(safe_result.get('kf') or '') if safe_result else '',
        cna_expenses=(safe_result.get('cna_expenses') if safe_result else 0) or 0,
        amount_podgotovka=(safe_result.get('amount_podgotovka') if safe_result else 0) or 0,
        amount_ss=(safe_result.get('amount_ss') if safe_result else 0) or 0,
        amount_mcu=(safe_result.get('amount_mcu') if safe_result else 0) or 0,
        amount_recovery=(
            (safe_result.get('amount_podgotovka') or 0)
            + (safe_result.get('amount_ss') or 0)
            + (safe_result.get('amount_mcu') or 0)
        ) if safe_result else 0,
        discount_torg=(safe_result.get('discount_torg') if safe_result else snapshot.get('discount_torg')) or 0,
        finance_price=(safe_result.get('finance_price') if safe_result else snapshot.get('finance_price')) or 0,
        zachita_ot_ubitka=(safe_result.get('zachita_ot_ubitka') if safe_result else snapshot.get('zachita_ot_ubitka')) or 0,
        raw_calculation_json=safe_result,
        **snapshot,
    )
    record.text_json = json.dumps(safe_result, ensure_ascii=False, default=str)
    record.save()
    return record


def get_price_recalc_history_for_estimation(estimation, limit=50):
    from register.models import RegInteractivOcenkaPrice

    if estimation is None:
        return []

    qs = (
        RegInteractivOcenkaPrice.objects
        .filter(estimation=estimation)
        .select_related('author', 'user', 'page_soglasovanie')
        .order_by('-date', '-id')[:limit]
    )
    rows = []
    for item in qs:
        author_name = ''
        if item.author_id:
            author_name = item.author.get_full_name() or item.author.username
        elif item.user_id:
            author_name = item.user.name
        rows.append({
            'id': item.pk,
            'date': item.date,
            'type_calculation': item.price_calculation,
            'type_label': PRICE_CALCULATION_LABELS.get(item.price_calculation, item.price_calculation or '—'),
            'trigger': item.trigger,
            'trigger_label': TRIGGER_LABELS.get(item.trigger, item.trigger or '—'),
            'author_name': author_name or '—',
            'is_success': item.is_success,
            'error_message': item.error_message or '',
            'estimation_price': item.estimation_price or 0,
            'estimation_price_do_kd': item.estimation_price_do_kd or 0,
            'cna_expenses': item.cna_expenses or 0,
            'zna': item.zna or 0,
            'zg': item.zg or '',
            'kf': item.kf or '',
            'price_auto_1': item.price_auto_1 or 0,
            'price_auto_2': item.price_auto_2 or 0,
            'price_auto_3': item.price_auto_3 or 0,
            'price_auto_bcp_1': item.price_auto_bcp_1 or 0,
            'price_auto_bcp_2': item.price_auto_bcp_2 or 0,
            'price_auto_bcp_3': item.price_auto_bcp_3 or 0,
            'price_zna_1': item.price_zna_1 or 0,
            'price_zna_2': item.price_zna_2 or 0,
            'price_zna_3': item.price_zna_3 or 0,
            'price_before_kd': item.price_before_kd or 0,
            'price_after_kd': item.price_after_kd or 0,
            'comment': item.comment or '',
        })
    return rows
