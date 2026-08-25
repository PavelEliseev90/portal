# -*- coding: utf-8 -*-
"""Пользовательские инструкции по интерактивной оценке."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def estimation_appraiser_help(request):
    """Инструкция оценщика: от рабочего листа до приёма автомобиля."""
    return render(request, 'estimations/estimation_appraiser_help.html', {'params': {}})
