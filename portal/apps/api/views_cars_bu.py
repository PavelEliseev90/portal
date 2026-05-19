from django.shortcuts import render
from asyncio.windows_events import NULL
import random
import os
from itertools import groupby
from django.utils.translation import activate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from collections import defaultdict
from decimal import Decimal
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.http.response import JsonResponse
from rest_framework.authentication import BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import api_view
import json
from django.contrib.auth.models import User, Group
import datetime as DT
import requests
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from api.views import get_unit, get_organization, get_store, get_stage_price, get_group_price, get_model_object
import tempfile
from django.core import files
from datetime import datetime
from django.db.models import Min, Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField

from prices_car_bu.models import CalculatedCumulativeData
from documents.models import DocCarAgreement, DocCarShipment

@api_view(['GET'])
def calculated_cumulative_data(request):

    agreements = DocCarAgreement.objects.all()
    agreements = agreements.filter(unit__buato = True, active = True)

    date_start      = request.GET.get('date_start', '')
    if date_start != '':
        agreements = agreements.filter(dataTime__gte = date_start)
    
    date_end        = request.GET.get('date_end', '')
    if date_end != '':
        agreements = agreements.filter(dataTime__lte = date_end)

    unit_name        = request.GET.get('unit_name', '')
    if unit_name != '':
        agreements = agreements.filter(unit__name__icontains = unit_name)

    number        = request.GET.get('number', '')
    if number != '':
        agreements = agreements.filter(nomer__icontains = number)

    customer        = request.GET.get('customer', '')
    if customer != '':
        agreements = agreements.filter(client__name__icontains = customer)

    city        = request.GET.get('city', '')
    if city != '':
        agreements = agreements.filter(client__city__name__icontains = city)

    subquery_shipment    = DocCarShipment.objects.filter(agreement__id = OuterRef(name='id'))

    answer = {
           'ok' : True
        }
    
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)