# -*- coding: utf-8 -*-
"""Поиск автомобиля организации на складе по оценке / РЛ."""
from __future__ import annotations

from documents.models import DocLO
from refs.models import RefCarsOrganization


def get_warehouse_car(interactiv_rlk, estimation):
    """RefCarsOrganization через DocLO или VIN оценки."""
    car = None
    rlk = getattr(interactiv_rlk, 'rlk', None)
    if rlk is not None:
        lo = DocLO.objects.filter(rlk=rlk).order_by('-id').first()
        if lo is not None:
            car = (
                RefCarsOrganization.objects.filter(lo=lo)
                .order_by('-date_refresh')
                .first()
            )
    if car is None and estimation is not None:
        vin = (estimation.vin or '').strip()
        if vin:
            car = (
                RefCarsOrganization.objects.filter(vin=vin)
                .order_by('-quantity', '-date_refresh')
                .first()
            )
    return car
