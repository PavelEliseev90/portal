from django.shortcuts import render
from powerbi.models import mers_SQL, Bi_logs, StockTZK, MKU_State_Orders, EstimationOP, CumulativeMarginUS, CumulativeMargin, ComparativeReportOPFU, Stock
import datetime as DT
import json
from django.views.decorators.csrf import csrf_exempt
from django.http.response import JsonResponse
from rest_framework import status


def add_statistic(report, add, delite, filtr):
    logs                = Bi_logs()
    logs.bi_model       = report
    logs.count_add      = add
    logs.count_delite   = delite
    logs.date           = DT.datetime.now()
    logs.filtr          = filtr
    logs.save()


@csrf_exempt
def mers_SQL_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = mers_SQL.objects.filter(Period__range = [date_start, date_end]).count()
    if count_delite > 0:
        mers_SQL.objects.filter(Period__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = mers_SQL()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('mers_SQL', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'mers_SQL',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK) 


@csrf_exempt
def StockTZK_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = StockTZK.objects.filter(ZNData__range = [date_start, date_end]).count()
    if count_delite > 0:
        StockTZK.objects.filter(ZNData__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = StockTZK()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('StockTZK', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'StockTZK',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK) 


@csrf_exempt
def MKU_State_Orders_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = MKU_State_Orders.objects.filter(Period__range = [date_start, date_end]).count()
    if count_delite > 0:
        MKU_State_Orders.objects.filter(Period__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = MKU_State_Orders()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('MKU_State_Orders', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'MKU_State_Orders',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK) 


@csrf_exempt
def EstimationOP_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = EstimationOP.objects.filter(OprosData__range = [date_start, date_end]).count()
    if count_delite > 0:
        EstimationOP.objects.filter(OprosData__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = EstimationOP()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('EstimationOP', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'EstimationOP',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK)


@csrf_exempt
def CumulativeMarginUS_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = CumulativeMarginUS.objects.filter(DataProdazhi__range = [date_start, date_end]).count()
    if count_delite > 0:
        CumulativeMarginUS.objects.filter(DataProdazhi__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = CumulativeMarginUS()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('CumulativeMarginUS', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'CumulativeMarginUS',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK) 


@csrf_exempt
def CumulativeMargin_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = CumulativeMargin.objects.filter(SaleDate__range = [date_start, date_end]).count()
    if count_delite > 0:
        CumulativeMargin.objects.filter(SaleDate__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = CumulativeMargin()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('CumulativeMargin', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'CumulativeMargin',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK)   


@csrf_exempt
def ComparativeReportOPFU_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = ComparativeReportOPFU.objects.filter(Period__range = [date_start, date_end]).count()
    if count_delite > 0:
        ComparativeReportOPFU.objects.filter(Period__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    for item in data:
        new_record = ComparativeReportOPFU()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    add_statistic('ComparativeReportOPFU', len(data), count_delite, str(filtr))

    to_json = {
        'report'    : 'ComparativeReportOPFU',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK) 

@csrf_exempt
def Stock_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    Stock.objects.delete()
    
    for item in data:
        new_record = Stock()
        for key, value in item.items():
            if len(str(value)) > 0:
                new_record.__setattr__(key , value)
        new_record.save()
    
    to_json = {
        'report'    : 'Stock',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK)   
    