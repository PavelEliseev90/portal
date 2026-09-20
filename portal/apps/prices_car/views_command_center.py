# -*- coding: utf-8 -*-
"""
Представления (Views) для Центра управления ценообразованием и дисконтами новых автомобилей.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from prices_car.command_center_service import (
    export_plans_template_excel,
    get_all_units_command_center_overview,
    get_command_center_full_context,
    get_first_day_of_month,
    import_plans_from_excel,
    rebuild_dc_command_center_showcase,
    simulate_deal_calculation,
)
from prices_car.models import (
    DcKeyModel,
    DcMonthlyPlan,
    PriceCarBrand,
    PriceCarKmDiscount,
)
from refs.models import AutoruModel, RefCarsOrganization, RefTypeSaleCarsOrganization, RefUnit


@login_required
def command_center_dashboard(request):
    """Главный экран: Центр управления ценообразованием и дисконтами новых АМ."""
    # Определение периода (первый день месяца)
    month_str = request.GET.get('month')
    if month_str:
        try:
            month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            month_start = get_first_day_of_month()
    else:
        month_start = get_first_day_of_month()

    # Доступные ДЦ
    units_qs = RefUnit.objects.filter(buauto=False).order_by('name')

    # Выбор текущего ДЦ
    unit_id_str = request.GET.get('unit_id')
    current_unit = None
    if unit_id_str:
        try:
            current_unit = units_qs.filter(id=int(unit_id_str)).first()
        except ValueError:
            pass

    # Если не выбран, пробуем взять ДЦ пользователя или первый доступный
    if not current_unit and hasattr(request.user, 'user_staff'):
        staff = request.user.user_staff
        if staff and staff.unit and not staff.unit.buauto:
            current_unit = staff.unit

    if not current_unit:
        current_unit = units_qs.first()

    # Данные Рабочего стола директора и оперативные счетчики согласований
    from avtosalon.deal_calc_approval import AUTO_APPROVE_USER_ID
    from avtosalon.deal_calc_desktop import (
        build_desktop_context,
        resolve_desktop_user,
        user_has_deal_calc_director_desktop_access,
    )
    from prices_car.models import CarCalculations
    from django.db.models import Avg, Q
    from django.urls import reverse

    view_user = resolve_desktop_user(request)
    desktop_ctx = build_desktop_context(view_user, request_user=request.user)

    today_date = timezone.localtime(timezone.now()).date() if timezone.is_aware(timezone.now()) else timezone.now().date()
    uid_suffix = f"?user_id={view_user.pk}" if view_user.pk != request.user.pk else ""

    calc_base_url = reverse('prices_car:calculations_list') + uid_suffix
    director_desktop_url = reverse('prices_car:new_cars_director_desktop') + uid_suffix

    unit_approvals = {
        'pending_count': 0,
        'auto_approved_today': 0,
        'manual_approved_today': 0,
        'uk_pending_today': 0,
        'rejected_today': 0,
        'month_calcs_count': 0,
        'month_avg_kvp': 0,
        'calculations_list_url': calc_base_url,
        'director_desktop_url': director_desktop_url,
        'has_director_access': user_has_deal_calc_director_desktop_access(request.user),
    }

    context = {
        'all_units': units_qs,
        'current_unit': current_unit,
        'month_str': month_start.strftime('%Y-%m'),
        'director_desktop': desktop_ctx,
    }

    if current_unit:
        cc_context = get_command_center_full_context(current_unit, month_start)
        context.update(cc_context)

        # Расчет показателей по согласованиям для выбранного ДЦ
        base_unit_calcs = CarCalculations.objects.filter(active=True, unit=current_unit)

        unit_approvals['pending_count'] = base_unit_calcs.filter(
            Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING) |
            Q(soglasovanie_status='') |
            Q(soglasovanie_status__isnull=True)
        ).count()

        unit_approvals['auto_approved_today'] = base_unit_calcs.filter(
            soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
            director_approve_date__date=today_date,
            director_approve_user_id=AUTO_APPROVE_USER_ID,
        ).count()

        unit_approvals['manual_approved_today'] = base_unit_calcs.filter(
            soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
            director_approve_date__date=today_date,
        ).exclude(director_approve_user_id=AUTO_APPROVE_USER_ID).count()

        unit_approvals['uk_pending_today'] = base_unit_calcs.filter(
            soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK,
        ).count()

        unit_approvals['rejected_today'] = base_unit_calcs.filter(
            soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
                CarCalculations.SOGLASOVANIE_UK_REJECTED,
            ],
            director_approve_date__date=today_date,
        ).count()

        month_calcs = base_unit_calcs.filter(
            date__year=month_start.year,
            date__month=month_start.month,
        )
        unit_approvals['month_calcs_count'] = month_calcs.count()
        avg_res = month_calcs.filter(
            soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
        ).aggregate(avg_kvp=Avg('kvp'))
        unit_approvals['month_avg_kvp'] = round(avg_res.get('avg_kvp') or 0)

    context['unit_approvals'] = unit_approvals

    return render(request, 'prices_car/command_center.html', context)


@login_required
@require_POST
def api_save_dc_plan(request):
    """Сохранение плана ДЦ, плана импортера и тактики ценообразования."""
    try:
        data = json.loads(request.body)
        unit_id = int(data.get('unit_id'))
        month_str = data.get('month')
        month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)

        plan_dc = max(int(data.get('plan_dc_qty', 0)), 0)
        plan_imp = max(int(data.get('plan_importer_qty', 0)), 0)
        plan_km_rub = max(int(data.get('plan_km_rub', 0)), 0)
        plan_revenue_rub = max(int(data.get('plan_revenue_rub', 0)), 0)
        tactic = data.get('tactic', DcMonthlyPlan.TACTIC_BALANCED)

        unit = get_object_or_404(RefUnit, id=unit_id)
        plan, _ = DcMonthlyPlan.objects.update_or_create(
            unit=unit,
            month=month_start,
            defaults={
                'plan_dc_qty': plan_dc,
                'plan_importer_qty': plan_imp,
                'plan_km_rub': plan_km_rub,
                'plan_revenue_rub': plan_revenue_rub,
                'tactic': tactic,
                'author': request.user,
            },
        )
        # Мгновенно обновляем срез витрины для этого ДЦ
        rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)

        return JsonResponse({
            'success': True,
            'plan_id': plan.id,
            'plan_dc_qty': plan.plan_dc_qty,
            'plan_importer_qty': plan.plan_importer_qty,
            'plan_km_rub': plan.plan_km_rub,
            'plan_revenue_rub': plan.plan_revenue_rub,
            'tactic': plan.tactic,
            'tactic_display': plan.get_tactic_display(),
            'message': 'Планы и тактика успешно сохранены',
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=400)


@login_required
@require_POST
def api_apply_recommendation(request):
    """Применение рекомендации умного помощника в 1 клик."""
    try:
        data = json.loads(request.body)
        action_type = data.get('action_type')
        unit_id = int(data.get('unit_id'))
        month_str = data.get('month')
        month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        unit = get_object_or_404(RefUnit, id=unit_id)

        # 1. Переключение тактики
        if action_type == 'set_tactic':
            new_tactic = data.get('tactic')
            plan, _ = DcMonthlyPlan.objects.get_or_create(unit=unit, month=month_start)
            plan.tactic = new_tactic
            plan.author = request.user
            plan.save()
            rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)
            return JsonResponse({'success': True, 'message': f'Тактика изменена на «{plan.get_tactic_display()}»'})

        # 2. Создание правила дисконта
        elif action_type in ('create_discount', 'create_yellow_discount', 'create_consignment_discount'):
            discount_pct = float(data.get('discount_percent', 0.0))
            discount_rub = int(data.get('discount_rub', 0))
            days_cons = data.get('days_consignment_left_lte')
            if days_cons is not None:
                days_cons = int(days_cons)
            is_yellow = bool(data.get('is_yellow_car', False))
            is_key_model = bool(data.get('is_key_model', False))
            model_id = data.get('model_id')
            comment = data.get('comment', 'Авто-рекомендация Центра управления')

            # Срок действия: до конца текущего месяца
            today = timezone.now().date()
            import calendar
            _, last_day = calendar.monthrange(month_start.year, month_start.month)
            date_to = month_start.replace(day=last_day)
            date_from = today if today.month == month_start.month else month_start

            # Определение бренда
            brand = None
            model = None
            if model_id:
                model = AutoruModel.objects.filter(id=int(model_id)).first()
                if model and model.mark:
                    brand = PriceCarBrand.objects.filter(marks=model.mark).first()

            if not brand:
                brand = PriceCarBrand.objects.first()

            if not brand:
                return JsonResponse({'success': False, 'error': 'Не найден бренд ценообразования'}, status=400)

            discount_obj = PriceCarKmDiscount.objects.create(
                brand=brand,
                model=model,
                unit=unit,
                discount_percent=discount_pct,
                discount_rub=discount_rub,
                days_consignment_left_lte=days_cons,
                is_yellow_car=is_yellow,
                is_key_model=is_key_model,
                comment=comment,
                date_from=date_from,
                date_to=date_to,
            )
            rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)

            return JsonResponse({
                'success': True,
                'discount_id': discount_obj.id,
                'message': f'Правило дисконта {discount_pct}% успешно создано и активировано!',
            })

        return JsonResponse({'success': False, 'error': 'Неизвестный тип действия'}, status=400)

    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=400)


@login_required
@require_POST
def api_toggle_autopilot(request):
    """Включение / выключение режима автопилота дисконтов для ДЦ."""
    try:
        data = json.loads(request.body)
        unit_id = int(data.get('unit_id'))
        month_str = data.get('month')
        month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        enabled = bool(data.get('enabled', False))

        unit = get_object_or_404(RefUnit, id=unit_id)
        plan, _ = DcMonthlyPlan.objects.get_or_create(
            unit=unit,
            month=month_start,
            defaults={'tactic': DcMonthlyPlan.TACTIC_BALANCED},
        )
        plan.is_autopilot = enabled
        plan.author = request.user
        plan.save(update_fields=['is_autopilot', 'author', 'updated_at'])

        logs = []
        if enabled:
            from prices_car.command_center_service import sync_autopilot_for_unit
            logs = sync_autopilot_for_unit(unit, month_start, plan=plan)

        rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)

        return JsonResponse({
            'success': True,
            'is_autopilot': plan.is_autopilot,
            'logs': logs,
            'message': f"Автопилот {'включен' if enabled else 'выключен'}." + (f" Применено авто-правил: {len(logs)}" if logs else ""),
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=400)


@login_required
@require_POST
def api_toggle_key_model(request):
    """Добавление или удаление ключевой модели ДЦ на месяц."""
    try:
        data = json.loads(request.body)
        unit_id = int(data.get('unit_id'))
        model_id = int(data.get('model_id'))
        month_str = data.get('month')
        action = data.get('action', 'add')  # 'add' or 'remove'
        target_qty = int(data.get('target_qty', 0))

        month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        unit = get_object_or_404(RefUnit, id=unit_id)
        model = get_object_or_404(AutoruModel, id=model_id)

        plan, _ = DcMonthlyPlan.objects.get_or_create(unit=unit, month=month_start)

        if action == 'add':
            km, created = DcKeyModel.objects.update_or_create(
                plan=plan,
                model=model,
                defaults={'target_qty': target_qty},
            )
            rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)
            return JsonResponse({
                'success': True,
                'action': 'added',
                'model_name': model.name,
                'message': f'Модель «{model.name}» добавлена в ключевые модели месяца',
            })
        else:
            DcKeyModel.objects.filter(plan=plan, model=model).delete()
            rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)
            return JsonResponse({
                'success': True,
                'action': 'removed',
                'model_name': model.name,
                'message': f'Модель «{model.name}» удалена из ключевых',
            })

    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=400)


@login_required
@require_POST
def api_save_brand_consignment(request):
    """Сохранение бесплатного срока консигнации по бренду."""
    try:
        data = json.loads(request.body)
        brand_id = int(data.get('brand_id'))
        days = max(int(data.get('free_consignment_days', 90)), 1)

        brand = get_object_or_404(PriceCarBrand, id=brand_id)
        brand.free_consignment_days = days
        brand.save(update_fields=['free_consignment_days'])

        return JsonResponse({
            'success': True,
            'brand_id': brand.id,
            'days': brand.free_consignment_days,
            'message': f'Срок консигнации для {brand.name} установлен: {days} дн.',
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=400)


@login_required
def export_plans_excel(request):
    """Скачивание шаблона Excel с планами ДЦ."""
    month_str = request.GET.get('month')
    if month_str:
        try:
            month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            month_start = get_first_day_of_month()
    else:
        month_start = get_first_day_of_month()

    buf = export_plans_template_excel(month_start)
    filename = f"Планы_ДЦ_{month_start:%m_%Y}.xlsx"
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def import_plans_excel(request):
    """Загрузка планов ДЦ из Excel файла."""
    month_str = request.POST.get('month')
    unit_id = request.POST.get('unit_id', '')

    if month_str:
        try:
            month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            month_start = get_first_day_of_month()
    else:
        month_start = get_first_day_of_month()

    file_obj = request.FILES.get('plans_file')
    if not file_obj:
        messages.error(request, 'Файл Excel не выбран.')
        return redirect(f'/prices_car/command_center/?unit_id={unit_id}&month={month_start:%Y-%m}')

    try:
        updated, created, errors = import_plans_from_excel(file_obj, month_start, author=request.user)
        rebuild_dc_command_center_showcase(month_start=month_start)
        msg = f'Импорт планов завершен: обновлено {updated}, создано {created}.'
        if errors:
            msg += f' Ошибок: {len(errors)} (проверьте корректность названий ДЦ).'
            messages.warning(request, msg)
        else:
            messages.success(request, msg)
    except Exception as ex:
        messages.error(request, f'Ошибка обработки файла Excel: {ex}')

    return redirect(f'/prices_car/command_center/?unit_id={unit_id}&month={month_start:%Y-%m}')


@login_required
def deal_simulator_dashboard(request):
    """Тестовый стенд расчета сделки (симулятор правил, дисконтов и тактик)."""
    units_qs = RefUnit.objects.filter(buauto=False).order_by('name')
    unit_id_str = request.GET.get('unit_id')
    current_unit = None
    if unit_id_str:
        try:
            current_unit = units_qs.filter(id=int(unit_id_str)).first()
        except ValueError:
            pass
    if not current_unit and hasattr(request.user, 'user_staff'):
        staff = request.user.user_staff
        if staff and staff.unit and not staff.unit.buauto:
            current_unit = staff.unit
    if not current_unit:
        current_unit = units_qs.first()

    cars_qs = RefCarsOrganization.objects.none()
    if current_unit:
        cars_qs = RefCarsOrganization.objects.filter(
            unit=current_unit,
            is_new=True,
        ).exclude(quantity=0).select_related(
            'modification_autoru__model__mark',
            'complectation_autoru',
            'type_sale',
        ).order_by('mark', 'model')

    car_id_str = request.GET.get('car_id')
    selected_car = None
    if car_id_str:
        try:
            selected_car = cars_qs.filter(id=int(car_id_str)).first()
        except ValueError:
            pass
    if not selected_car:
        selected_car = cars_qs.first()

    sales_channels = RefTypeSaleCarsOrganization.objects.all().order_by('name')

    month_start = get_first_day_of_month()
    plan = None
    if current_unit:
        plan = DcMonthlyPlan.objects.filter(unit=current_unit, month=month_start).first()

    initial_calc = None
    if selected_car:
        initial_calc = simulate_deal_calculation(
            car_id=selected_car.id,
            unit_id=current_unit.id if current_unit else None,
            type_sale_id=selected_car.type_sale_id,
            tactic_override=plan.tactic if plan else None,
            is_yellow_override=selected_car.is_yellow,
            sale_price=selected_car.price,
            with_trade_in=False,
            with_credit=False,
        )

    context = {
        'all_units': units_qs,
        'current_unit': current_unit,
        'cars': cars_qs,
        'selected_car': selected_car,
        'sales_channels': sales_channels,
        'current_plan': plan,
        'initial_calc': initial_calc,
    }
    return render(request, 'prices_car/deal_simulator.html', context)


@login_required
@require_POST
def api_simulate_deal(request):
    """AJAX расчет сделки на тестовом стенде в реальном времени."""
    try:
        data = json.loads(request.body)
        car_id = data.get('car_id')
        unit_id = data.get('unit_id')
        type_sale_id = data.get('type_sale_id')
        tactic_override = data.get('tactic')
        is_yellow_override = data.get('is_yellow')
        is_key_model_override = data.get('is_key_model')
        sale_price = data.get('sale_price')
        discount_amount = data.get('discount_amount', 0)
        with_trade_in = bool(data.get('with_trade_in', False))
        tradein_margin = data.get('tradein_margin', 0)
        with_credit = bool(data.get('with_credit', False))
        opfu_amount = data.get('opfu_amount', 0)
        dop_margin = data.get('dop_margin', 0)
        work_margin = data.get('work_margin', 0)
        insurance_margin = data.get('insurance_margin', 0)

        result = simulate_deal_calculation(
            car_id=car_id,
            unit_id=unit_id,
            type_sale_id=type_sale_id,
            tactic_override=tactic_override,
            is_yellow_override=is_yellow_override,
            is_key_model_override=is_key_model_override,
            sale_price=sale_price,
            discount_amount=discount_amount,
            with_trade_in=with_trade_in,
            tradein_margin=tradein_margin,
            with_credit=with_credit,
            opfu_amount=opfu_amount,
            dop_margin=dop_margin,
            work_margin=work_margin,
            insurance_margin=insurance_margin,
        )
        return JsonResponse(result)
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=400)


@login_required
def command_center_units_overview(request):
    """
    Экран мониторинга всех ДЦ: список дилерских центров с автопилотом,
    темпом контрактования, рекомендациями и складскими рисками по городам.
    """
    profile = getattr(request.user, 'profiles', None)
    has_access = bool(
        request.user.is_superuser or
        (profile and (profile.price_car_new or profile.price_car_new_director or profile.price_car_new_all))
    )
    if not has_access:
        return render(request, 'errors/403.html', {'params': {'type': 'home', 'request': request}}, status=403)

    month_str = request.GET.get('month')
    if month_str:
        try:
            month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            month_start = get_first_day_of_month()
    else:
        month_start = get_first_day_of_month()

    filters = {
        'city_id': request.GET.get('city_id', 'all'),
        'autopilot': request.GET.get('autopilot', 'all'),
        'recommendations': request.GET.get('recommendations', 'all'),
        'pace': request.GET.get('pace', 'all'),
        'quadrant': request.GET.get('quadrant', 'all'),
        'search': request.GET.get('search', ''),
    }

    overview_data = get_all_units_command_center_overview(month_start, filters=filters)

    context = {
        'month_start': month_start,
        'month_str': month_start.strftime('%Y-%m'),
        'overview': overview_data,
        'filters': filters,
        'is_uk': bool(request.user.is_superuser or (profile and profile.price_car_new_all)),
    }
    return render(request, 'prices_car/command_center_units.html', context)


@login_required
def command_center_sync_showcase_view(request):
    """
    Принудительная синхронизация / пересчёт витрины данных сети ДЦ за выбранный месяц.
    """
    month_str = request.GET.get('month') or request.POST.get('month')
    if month_str:
        try:
            month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            month_start = get_first_day_of_month()
    else:
        month_start = get_first_day_of_month()

    updated = rebuild_dc_command_center_showcase(month_start=month_start)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'updated': updated,
            'month': month_start.strftime('%Y-%m'),
            'message': f'Витрина данных сети ДЦ обновлена ({updated} ДЦ).',
        })

    messages.success(
        request,
        f'Витрина данных сети ДЦ за {month_start.strftime("%Y-%m")} успешно обновлена ({updated} ДЦ).'
    )
    return redirect(f'/prices_car/command_center/units/?month={month_start.strftime("%Y-%m")}')


