from django.shortcuts import render
from powerbi.models import mers_SQL, Bi_logs, StockTZK, MKU_State_Orders, EstimationOP, CumulativeMarginUS, CumulativeMargin, ComparativeReportOPFU, Stock, Cumulative
import datetime as DT
import json
from django.views.decorators.csrf import csrf_exempt
from django.http.response import JsonResponse, HttpResponse
from rest_framework import status
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import models
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


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
    
    Stock.objects.all().delete()
    
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


@csrf_exempt
def Cumulative_refresh(request):
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)
    
    filtr       = data['Filtr']
    date_start  = filtr['ДатаНачала']
    date_end    = filtr['ДатаОкончания']

    count_delite = Cumulative.objects.filter(DataProdazhi__range = [date_start, date_end]).count()
    if count_delite > 0:
        Cumulative.objects.filter(DataProdazhi__range = [date_start, date_end]).delete()

    data    = data['Data']
    
    # Получаем информацию о полях модели
    model_fields = {f.name: f for f in Cumulative._meta.get_fields() if hasattr(f, 'name')}

    for item in data:
        new_record = Cumulative()
        for key, value in item.items():
            # Проверяем, существует ли поле в модели
            if key not in model_fields:
                continue
            
            field = model_fields[key]
            
            # Пропускаем пустые значения
            if value is None or value == '':
                continue
            
            # Обработка DateTimeField
            if isinstance(field, models.DateTimeField):
                try:
                    # Если значение уже datetime объект
                    if isinstance(value, DT.datetime):
                        setattr(new_record, key, value)
                    # Если значение строка, пытаемся распарсить
                    elif isinstance(value, str):
                        if len(value) > 0:
                            # Пробуем разные форматы дат
                            try:
                                parsed_date = DT.datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except:
                                try:
                                    parsed_date = DT.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                except:
                                    try:
                                        parsed_date = DT.datetime.strptime(value, '%Y-%m-%d')
                                    except:
                                        continue
                            setattr(new_record, key, parsed_date)
                except Exception as e:
                    continue
            # Обработка DateField
            elif isinstance(field, models.DateField):
                try:
                    if isinstance(value, DT.date):
                        setattr(new_record, key, value)
                    elif isinstance(value, DT.datetime):
                        setattr(new_record, key, value.date())
                    elif isinstance(value, str) and len(value) > 0:
                        try:
                            parsed_date = DT.datetime.strptime(value, '%Y-%m-%d').date()
                            setattr(new_record, key, parsed_date)
                        except:
                            continue
                except:
                    continue
            # Обработка остальных полей
            else:
                try:
                    # Проверяем, что значение не пустое
                    if isinstance(value, str) and len(value) > 0:
                        setattr(new_record, key, value)
                    elif not isinstance(value, str) and value is not None:
                        setattr(new_record, key, value)
                except:
                    continue
        
        try:
            new_record.save()
        except Exception as e:
            # Пропускаем записи с ошибками
            continue
    
    to_json = {
        'report'    : 'Cumulative',
        'date'      : f'{DT.datetime.now():%Y-%m-%d %H:%M:%S%z}'
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK)

def stock_list(request):
    if not request.user.is_authenticated or not request.user.profiles.korsavto_settings: 
        return render(request, 'errors/403.html')
    """Список записей Stock с поиском и пагинацией"""
    stocks = Stock.objects.all()
    
    # Поиск по PodrazdelenieDC
    podrazdelenie = request.GET.get('podrazdelenie', '').strip()
    if podrazdelenie:
        stocks = stocks.filter(
            Q(PodrazdelenieDC__icontains=podrazdelenie) | 
            Q(City__icontains=podrazdelenie)
        )
    
    # Поиск по VIN
    vin = request.GET.get('vin', '').strip()
    if vin:
        stocks = stocks.filter(VIN__icontains=vin)
    
    # Сортировка
    stocks = stocks.order_by('-id')
    
    # Получаем все поля модели для отображения
    model_fields = []
    for field in Stock._meta.get_fields():
        if hasattr(field, 'verbose_name') and field.verbose_name and not field.many_to_many and not field.one_to_many:
            model_fields.append({
                'name': field.name,
                'verbose_name': field.verbose_name,
            })
    
    # Пагинация по 100 записей
    paginator = Paginator(stocks, 100)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Подготавливаем данные для отображения
    stocks_data = []
    for stock in page_obj:
        stock_row = []
        for field in model_fields:
            value = getattr(stock, field['name'], None)
            # Форматируем даты
            if hasattr(value, 'strftime'):
                stock_row.append(value.strftime('%d.%m.%Y %H:%M') if value else '-')
            else:
                stock_row.append(value if value is not None and value != '' else '-')
        stocks_data.append(stock_row)
    
    context = {
        'page_obj': page_obj,
        'stocks': stocks_data,
        'podrazdelenie': podrazdelenie,
        'vin': vin,
        'total_count': paginator.count,
        'fields': model_fields,
    }
    
    return render(request, 'powerbi/stock_list.html', context)


def stock_export_excel(request):
    
    if not request.user.is_authenticated or not request.user.profiles.korsavto_settings: 
        return render(request, 'errors/403.html')
    
    """Экспорт Stock в Excel"""
    stocks = Stock.objects.all()
    
    # Применяем те же фильтры, что и в списке
    podrazdelenie = request.GET.get('podrazdelenie', '').strip()
    if podrazdelenie:
        stocks = stocks.filter(
            Q(PodrazdelenieDC__icontains=podrazdelenie) | 
            Q(City__icontains=podrazdelenie)
        )
    
    vin = request.GET.get('vin', '').strip()
    if vin:
        stocks = stocks.filter(VIN__icontains=vin)
    
    stocks = stocks.order_by('-id')
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock"
    
    # Получаем все поля модели
    model_fields = Stock._meta.get_fields()
    field_names = []
    field_verbose_names = []
    
    for field in model_fields:
        if hasattr(field, 'verbose_name') and field.verbose_name and not field.many_to_many and not field.one_to_many:
            field_names.append(field.name)
            field_verbose_names.append(field.verbose_name)
    
    # Заголовки с наименованиями полей
    ws.append(field_verbose_names)
    
    # Стили для заголовков
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Данные
    for stock in stocks:
        row = []
        for field_name in field_names:
            value = getattr(stock, field_name, '')
            # Форматируем даты
            if hasattr(value, 'strftime'):
                value = value.strftime('%d.%m.%Y %H:%M:%S') if value else ''
            row.append(value)
        ws.append(row)
    
    # Автоподбор ширины столбцов
    for col in range(1, len(field_verbose_names) + 1):
        column_letter = get_column_letter(col)
        max_length = 0
        for cell in ws[column_letter]:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Создаем ответ
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="stock_export.xlsx"'
    
    wb.save(response)
    return response


def cumulative_list(request):
    
    if not request.user.is_authenticated or not request.user.profiles.korsavto_settings: 
        return render(request, 'errors/403.html')
    
    """Список записей Cumulative с поиском и пагинацией"""
    cumulatives = Cumulative.objects.all()
    
    # Поиск по DataProdazhi
    data_prodazhi_start = request.GET.get('data_prodazhi_start', '').strip()
    data_prodazhi_end = request.GET.get('data_prodazhi_end', '').strip()
    if data_prodazhi_start:
        try:
            from datetime import datetime
            date_start = datetime.strptime(data_prodazhi_start, '%Y-%m-%d')
            if data_prodazhi_end:
                date_end = datetime.strptime(data_prodazhi_end, '%Y-%m-%d')
                cumulatives = cumulatives.filter(DataProdazhi__range=[date_start, date_end])
            else:
                cumulatives = cumulatives.filter(DataProdazhi__gte=date_start)
        except:
            pass
    
    # Поиск по VIN
    vin = request.GET.get('vin', '').strip()
    if vin:
        cumulatives = cumulatives.filter(VIN__icontains=vin)
    
    # Поиск по Marka
    marka = request.GET.get('marka', '').strip()
    if marka:
        cumulatives = cumulatives.filter(Marka__icontains=marka)
    
    # Поиск по TipProdazhi
    tip_prodazhi = request.GET.get('tip_prodazhi', '').strip()
    if tip_prodazhi:
        cumulatives = cumulatives.filter(TipProdazhi__icontains=tip_prodazhi)
    
    # Поиск по PodrazdelenieDTs
    podrazdelenie = request.GET.get('podrazdelenie', '').strip()
    if podrazdelenie:
        cumulatives = cumulatives.filter(PodrazdelenieDTs__icontains=podrazdelenie)
    
    # Сортировка
    cumulatives = cumulatives.order_by('-id')
    
    # Получаем все поля модели для отображения
    model_fields = []
    for field in Cumulative._meta.get_fields():
        if hasattr(field, 'verbose_name') and field.verbose_name and not field.many_to_many and not field.one_to_many:
            model_fields.append({
                'name': field.name,
                'verbose_name': field.verbose_name,
            })
    
    # Пагинация по 100 записей
    paginator = Paginator(cumulatives, 100)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Подготавливаем данные для отображения
    cumulatives_data = []
    for cumulative in page_obj:
        cumulative_row = []
        for field in model_fields:
            value = getattr(cumulative, field['name'], None)
            # Форматируем даты
            if hasattr(value, 'strftime'):
                cumulative_row.append(value.strftime('%d.%m.%Y %H:%M') if value else '-')
            else:
                cumulative_row.append(value if value is not None and value != '' else '-')
        cumulatives_data.append(cumulative_row)
    
    context = {
        'page_obj': page_obj,
        'cumulatives': cumulatives_data,
        'data_prodazhi_start': data_prodazhi_start,
        'data_prodazhi_end': data_prodazhi_end,
        'vin': vin,
        'marka': marka,
        'tip_prodazhi': tip_prodazhi,
        'podrazdelenie': podrazdelenie,
        'total_count': paginator.count,
        'fields': model_fields,
    }
    
    return render(request, 'powerbi/cumulative_list.html', context)


def cumulative_export_excel(request):
    """Экспорт Cumulative в Excel"""
    if not request.user.is_authenticated or not request.user.profiles.korsavto_settings: 
        return render(request, 'errors/403.html')
    
    cumulatives = Cumulative.objects.all()
    
    # Применяем те же фильтры, что и в списке
    data_prodazhi_start = request.GET.get('data_prodazhi_start', '').strip()
    data_prodazhi_end = request.GET.get('data_prodazhi_end', '').strip()
    if data_prodazhi_start:
        try:
            from datetime import datetime
            date_start = datetime.strptime(data_prodazhi_start, '%Y-%m-%d')
            if data_prodazhi_end:
                date_end = datetime.strptime(data_prodazhi_end, '%Y-%m-%d')
                cumulatives = cumulatives.filter(DataProdazhi__range=[date_start, date_end])
            else:
                cumulatives = cumulatives.filter(DataProdazhi__gte=date_start)
        except:
            pass
    
    vin = request.GET.get('vin', '').strip()
    if vin:
        cumulatives = cumulatives.filter(VIN__icontains=vin)
    
    marka = request.GET.get('marka', '').strip()
    if marka:
        cumulatives = cumulatives.filter(Marka__icontains=marka)
    
    tip_prodazhi = request.GET.get('tip_prodazhi', '').strip()
    if tip_prodazhi:
        cumulatives = cumulatives.filter(TipProdazhi__icontains=tip_prodazhi)
    
    podrazdelenie = request.GET.get('podrazdelenie', '').strip()
    if podrazdelenie:
        cumulatives = cumulatives.filter(PodrazdelenieDTs__icontains=podrazdelenie)
    
    cumulatives = cumulatives.order_by('-id')
    
    # Создаем Excel файл
    wb = Workbook()
    ws = wb.active
    ws.title = "Cumulative"
    
    # Получаем все поля модели
    model_fields = Cumulative._meta.get_fields()
    field_names = []
    field_verbose_names = []
    
    for field in model_fields:
        if hasattr(field, 'verbose_name') and field.verbose_name and not field.many_to_many and not field.one_to_many:
            field_names.append(field.name)
            field_verbose_names.append(field.verbose_name)
    
    # Заголовки с наименованиями полей
    ws.append(field_verbose_names)
    
    # Стили для заголовков
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Данные
    for cumulative in cumulatives:
        row = []
        for field_name in field_names:
            value = getattr(cumulative, field_name, '')
            # Форматируем даты
            if hasattr(value, 'strftime'):
                value = value.strftime('%d.%m.%Y %H:%M:%S') if value else ''
            row.append(value)
        ws.append(row)
    
    # Автоподбор ширины столбцов
    for col in range(1, len(field_verbose_names) + 1):
        column_letter = get_column_letter(col)
        max_length = 0
        for cell in ws[column_letter]:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Создаем ответ
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="cumulative_export.xlsx"'
    
    wb.save(response)
    return response
    