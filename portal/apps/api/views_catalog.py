from django.shortcuts import render
from asyncio.windows_events import NULL
import random
import os
from itertools import groupby
from django.utils.translation import activate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from collections import defaultdict
from django.contrib.auth.models import Group
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

import datetime as DT
import base64
from email import header
from itertools import product
import requests
from fake_headers import Headers
import fake_proxy
import qrcode
import urllib.parse
import io
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from refs.models import RefManufacturer
import tempfile
from django.core import files
from datetime import datetime
from django.db.models import Q
from refs.serializers import RefManufacturerSerializer


@api_view(['GET', 'POST'])
def manufacturer(request):
    
    list_info   = list()
    
    main            = RefManufacturer.objects.all().order_by('name')
    main_dop        = list()

    name = request.GET.get('name', '')

    if name != '':
        main_objects        = main.filter(name__icontains = name)
        main_dop_objects    = main.filter(search_fields__icontains = name) 
        list_info_main_objects      = RefManufacturerSerializer(list(main_objects), many=True)
        list_info_main_dop_objects  = RefManufacturerSerializer(list(main_dop_objects), many=True)
        answer = {
            'objects'       : list_info_main_objects.data,
            'objects_dop'   : list_info_main_dop_objects.data  
        }
        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    list_info_main_objects      = RefManufacturerSerializer(list(main), many=True)
        
    answer = {
        'objects'       : list_info_main_objects.data,
        'objects_dop'   : main_dop  
    }
    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)

