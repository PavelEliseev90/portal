from asyncio.windows_events import NULL
from django.db.models import OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.shortcuts import render
from refs.models import RefCity, RefUnit, RefTypeCanceledCheckList
from documents.models import DocRLKEvents, DocZN, DocRLK, DocZNProduct, DocZNWork
from refs.models import RefUnit, RefStaff
from profiles.models import Profiles
import datetime as DT
import datetime
from django.db import models
import json
from django.contrib import auth
from django.template.context_processors import csrf
from django.contrib.auth import login as dj_login
from django.contrib.auth import logout as dj_logout
from django.contrib.auth import authenticate
from . import views
from checklists.models import CheckList, CheckListServiceIn, CheckListServiceOut, CheckListTradeIn, CheckList_op_kors
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Max, Avg, F
from django.core.paginator import Paginator
from recognition.models import Records_voice_recorder_cvc_checklist_tematics, Records_voice_recorder_cvc_checklist, Records_voice_recorder_cvc_tematics, Recognition_Anketa, Records_voice_recorder, Recognition_Tematika_fraza, Recognition_Tematika, Records_voice_recorder_queue
from django.db.models.functions import TruncDate
from pydub import AudioSegment, effects
from django.core.files import File     
import soundfile as sf
from changelog.models import ChangeLog
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

###
##
#
date_start_cvc_power_bi = DT.date.fromisoformat('20230616')

def time_human(time_seconds):
        if time_seconds != None:
            sec = time_seconds
            if sec > 0:
                sec     = sec % (24 * 3600) 
                hour    = time_seconds // 3600 
                sec     %= 3600 
                min     = sec // 60 
                sec     %= 60 
                if hour > 0:
                    return "%02d:%02d:%02d" % (hour, min, sec)
                else:
                    return "%02d:%02d" % (min, sec)
            else:
                return "00:00"
        else:
                return "00:00"
####
###
##
#История изменений
def get_versions(table, id):
	return ChangeLog.objects.filter(model = table).filter(record_id = id).order_by('changed')

###
##
# Главная страничка
def glav_v1(request):	
	if request.user.is_authenticated:
		
		date 	= ''
		cityID 	= ''

		if request.method == "POST":
			if 'date' in request.POST:
				date = request.POST['date']
			if 'select_city' in request.POST:
				cityID = request.POST['select_city']
			
		if len(date) == 0:
			date_period = datetime.datetime.now()
			date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0)
			if date_period.month > 11:
				month_end	= 1
				year_end 	= date_period.year + 1
			else:
				month_end	= date_period.month + 1
				year_end 	= date_period.year
			date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0)
		else:
			dates = date.split('-')
			if len(dates) == 2:
				year 	= int(dates[0])
				month 	= int(dates[1])
				date_period = datetime.datetime.now()
				date_start 	= date_period.replace(year = year, month = month, day = 1, hour = 0, minute=0, second=0)
				if month > 11:
					month_end 	= 1
					year_end 	= year + 1
				else:
					month_end 	= month + 1 
					year_end 	= year
				date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0)			

		if len(cityID) > 0:
			op 			= CheckList.objects.filter(rlk__unit__buauto = False).filter(rlk__unit__city__id = cityID).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('rlk__unit__city')
			op_count 	= CheckList.objects.filter(rlk__unit__buauto = False).filter(rlk__unit__city__id = cityID).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).count()
		
			op_kors 		= CheckList_op_kors.objects.filter(rlk__unit__buauto = True).filter(rlk__unit__city__id = cityID).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('rlk__unit__city')
			op_kors_count 	= CheckList_op_kors.objects.filter(rlk__unit__buauto = True).filter(rlk__unit__city__id = cityID).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).count()
		
			rlk_tradein 		= CheckListTradeIn.objects.filter(rlk__unit__buauto = True).filter(rlk__unit__city__id = cityID).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('rlk__unit__city')
			rlk_tradein_count 	= CheckListTradeIn.objects.filter(rlk__unit__buauto = True).filter(rlk__unit__city__id = cityID).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).count()
		
			zn_in 		= CheckListServiceIn.objects.filter(zn__unit__city__id = cityID).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).values("zn__unit__name").distinct().annotate(count=Count('id')).order_by('zn__unit__city')
			zn_in_count = CheckListServiceIn.objects.filter(zn__unit__city__id = cityID).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).count()
			
			zn_out 			= CheckListServiceOut.objects.filter(zn__unit__city__id = cityID).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).values("zn__unit__name").distinct().annotate(count=Count('id')).order_by('zn__unit__city') 
			zn_out_count 	= CheckListServiceOut.objects.filter(zn__unit__city__id = cityID).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).count()  

		else:
			op 			= CheckList.objects.filter(rlk__unit__buauto = False).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('rlk__unit__city')
			op_count 	= CheckList.objects.filter(rlk__unit__buauto = False).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).count()

			op_kors 		= CheckList_op_kors.objects.filter(rlk__unit__buauto = True).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('rlk__unit__city')
			op_kors_count 	= CheckList_op_kors.objects.filter(rlk__unit__buauto = True).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).count()

			rlk_tradein 		= CheckListTradeIn.objects.filter(rlk__unit__buauto = True).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('rlk__unit__city')
			rlk_tradein_count 	= CheckListTradeIn.objects.filter(rlk__unit__buauto = True).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).count()
		
			zn_in 		= CheckListServiceIn.objects.filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).values("zn__unit__name").distinct().annotate(count=Count('id')).order_by('zn__unit__city')
			zn_in_count = CheckListServiceIn.objects.filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).count()
			
			zn_out 			= CheckListServiceOut.objects.filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).values("zn__unit__name").distinct().annotate(count=Count('id')).order_by('zn__unit__city') 
			zn_out_count 	= CheckListServiceOut.objects.filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lte = date_end).count()  
			

		citys = RefCity.objects.all().order_by("name")

		selected = {
			'citys'	: citys
		}

		filter = {
			"date"		: date_start,
			"cityID"	: cityID
		}
		params = {
			'type'              : 'checklists',
			'nav_selected'		: 0,
			'op_list'			: list(op),
			'op_count'			: op_count,
			'op_kors_list'		: list(op_kors),
			'op_kors_count'		: op_kors_count,
			'zn_in_list'		: list(zn_in),
			'zn_out_list'		: list(zn_out),
			'zn_in_count'		: zn_in_count,
			'zn_out_count'		: zn_out_count,
			'rlk_tradein_list'	: rlk_tradein,
			'rlk_tradein_count'	: rlk_tradein_count,
			'filter'			: filter,
			'selected'			: selected
		}
		return render(request, 'checklist/glav_v1.html', {'params': params})
	return HttpResponseRedirect('/')

# Главная страничка
def reports(request):	
	if request.user.is_authenticated:
		params = {
				'type'			: 'checklists',
				'nav_selected'	: 6,
			}
		return render(request, 'checklist/reports.html', {'params': params})
	return HttpResponseRedirect('/')

###
##
# Отчет по сотрудникам КК (количество созданных чек листов)
def reports_kk(request):
	if request.user.is_authenticated:
		
		error = ""
		
		directions = list()
		directions.append({'id': 1, 'name': 'Отдел продаж'})
		directions.append({'id': 2, 'name': 'Сервис (прием авто)'})
		directions.append({'id': 3, 'name': 'Сервис (выдача авто)'})
		directions.append({'id': 4, 'name': 'Отдел оценки (Корс-авто)'})
		directions.append({'id': 5, 'name': 'Отдел продаж (Корс-авто)'})
		
		direction_id 	= ''
		unit_id			= ''	

		citys 		= RefCity.objects.all().order_by("name")
		city_id 	= ""
		
		date_start 	= ""
		date 		= ""
		date_end 	= ""
		
		if request.GET.get('date', ""):
			date 		= request.GET['date']
			date_start 	= DT.datetime.strptime(date, "%Y-%m")
		else:
			date_start 	= DT.datetime.now().replace(day=1, hour=0, minute=0, second=0)
		
		if 'select_city' in request.GET:
			city_id = request.GET['select_city']
		
		if 'select_direction' in request.GET:
			direction_id = request.GET['select_direction']
		
		if request.GET.get('date_end', ""):
			date_end 	= request.GET['date_end']
			date_ends 	= DT.datetime.strptime(date_end, "%Y-%m-%d") + DT.timedelta(days=1) 
		
		new_date 	= True
		date		= date_start
		units_data 	= list()
		dates_list	= list()
		
		if len(direction_id) > 0:
			
			staffs_kk = get_staff_kk(direction_id = direction_id, date = date_start, staff_id = None)

			while new_date:
				if date_start.month == date.month:
					dates_list.append(date)
					date = date + datetime.timedelta(days=1)
				else:
					new_date = False

			for staff_kk in staffs_kk:
				if staff_kk['user'] != None:
					info_dates 			= list()
					info_staffs 		= list()

					units = get_staff_kk(direction_id = direction_id, date = date_start, staff_id = staff_kk['user'])
					sum_docs_staff = 0
					for unit in units:
						sum_docs_unit = 0
						dates = list()
						for date in dates_list:
							
							info = get_staff_kk_doc(direction_id=direction_id, date = date, staff_id = staff_kk['user'], unit_id = unit['doc__unit'])
							dates.append(info)
							sum_docs_unit = sum_docs_unit + info
						

						info_unit = {
							'unit' 			: unit['doc__unit'],
							'unit_name' 	: unit['doc__unit__name'],
							'dates'			: dates,
							'sum_docs_unit' : sum_docs_unit
						}
						info_dates.append(info_unit)
						sum_docs_staff = sum_docs_staff + sum_docs_unit
					
					for date in dates_list:
						info = get_staff_kk_doc(direction_id=direction_id, date = date, staff_id = staff_kk['user'], unit_id = None)
						info_staffs.append(info)

					info_staff = {
						'staff_name' 		: '' + staff_kk['user__last_name'] + ' ' + staff_kk['user__first_name'],
						'staff_id'			: staff_kk['user'],
						'info_dates'		: info_dates,
						'info_staffs'		: info_staffs,
						'sum_docs_staff' 	: sum_docs_staff
					}
					units_data.append(info_staff)
		else:
			error = "Выберите пожалуйста город, а я по нему для Вас сформирую отчет"

		filtr = {
			'date' 			: date_start,
			'city_id'		: city_id,
			'direction_id'	: direction_id
		}

		selected = {
			'citys'			: citys,
			#'units'			: select_units,
			'directions' 	: directions
		}

		params = {
				'type'          : 'checklists',
				'nav_selected'  : 6,
				"error"			: error,
				'filtr'			: filtr,
				'selected'		: selected,
				'units_data'	: units_data,
				'dates_list'	: dates_list
			}
		
		return render(request, 'checklist/reports_kk.html', {"params": params})
	return HttpResponseRedirect('/')

###
##
# Отчет по сотрудникам ДЦ
def reports_dc(request):
	if request.user.is_authenticated:
		
		error = ""
		
		directions = list()
		directions.append({'id': 1, 'name': 'Отдел продаж'})
		directions.append({'id': 2, 'name': 'Сервис (прием авто)'})
		directions.append({'id': 3, 'name': 'Сервис (выдача авто)'})
		directions.append({'id': 4, 'name': 'Отдел оценки (Корс-авто)'})
		directions.append({'id': 5, 'name': 'Отдел продаж (Корс-авто)'})
		
		direction_id 	= ''
		unit_id			= ''	

		citys 		= RefCity.objects.all().order_by("name")
		city_id 	= ""
		
		select_unit_id = None
		
		date_start 	= ""
		date 		= ""
		date_end 	= ""
		
		if request.GET.get('date', ""):
			date 		= request.GET['date']
			date_start 	= DT.datetime.strptime(date, "%Y-%m")
		else:
			date_start 	= DT.datetime.now().replace(day=1, hour=0, minute=0, second=0)
		
		if 'select_city' in request.GET:
			city_id = request.GET['select_city']
		
		if 'select_direction' in request.GET:
			direction_id = request.GET['select_direction']
		
		if request.GET.get('date_end', ""):
			date_end 	= request.GET['date_end']
			date_ends 	= DT.datetime.strptime(date_end, "%Y-%m-%d") + DT.timedelta(days=1) 
		
		if 'select_unit' in request.GET:
			select_unit_id = request.GET['select_unit']

		new_date 	= True
		date		= date_start
		units_data 	= list()
		dates_list	= list()
		
		if len(city_id) > 0:
			units = get_inits(city_id = city_id, direction_id = direction_id)

			while new_date:
				if date_start.month == date.month:
					dates_list.append(date)
					date = date + datetime.timedelta(days=1)
				else:
					new_date = False
			
			for unit in units:

				if select_unit_id != None and str(unit['unit']) != select_unit_id:
					continue

				sum_docs 			= 0
				sum_check 			= 0
				sum_check_percent 	= 0 
				info_dates 			= list()
				info_staffs 		= list()

				staffs = get_stafs_report(direction_id=direction_id, unit_id= unit['unit'], date = date_start)
				for staff in staffs:
					sum_docs_staff 			= 0
					sum_check_staff 		= 0
					sum_percent_staff		= 0
					sum_check_percent_staff = 0
					dates = list()
					for date in dates_list:
						info = get_docs_report(direction_id=direction_id, unit_id= unit['unit'], date=date.strftime("%Y-%m-%d"), staff_id = staff['staff'])
						sum_docs_staff 				= sum_docs_staff + info['docs']
						sum_check_staff 			= sum_check_staff + info['check']
						sum_check_percent_staff 	= sum_check_percent_staff + info['percent_check_sum']
						
						dates.append(info)
					if sum_docs_staff > 0:
						sum_percent_staff = int(sum_check_staff / sum_docs_staff * 100)
					if sum_check_percent_staff > 0:
						sum_check_percent_staff = int(sum_check_percent_staff / sum_check_staff)
					
					info_staff = {
						'staff' 					: staff,
						'dates'						: dates,
						'sum_docs_staff' 			: sum_docs_staff,
						'sum_check_staff'			: sum_check_staff,
						'sum_percent_staff'			: sum_percent_staff,
						'sum_check_percent_staff' 	: sum_check_percent_staff
					}
					info_staffs.append(info_staff)

				for date in dates_list:
					info = get_docs_report(direction_id=direction_id, unit_id= unit['unit'], date=date.strftime("%Y-%m-%d"), staff_id = None)
					sum_docs 			= sum_docs + info['docs']
					sum_check 			= sum_check + info['check']
					if sum_check > 0:
						sum_check_percent	= sum_check_percent + info['percent_check_sum'] 
					info_dates.append(info)
				
				sum_percent = 0
				if sum_docs > 0:
					sum_percent = int(sum_check / sum_docs * 100) 
				if sum_check_percent > 0:
					sum_check_percent = int(sum_check_percent / sum_check)
				param_unit = {
					'unit_name' 	: unit['unit__name'],
					'unit_id' 		: unit['unit'],
					'unit_city_id' 	: unit['unit__city__id'],
					'info_dates'	: info_dates,
					'staffs'		: info_staffs,
					'sum_docs'		: sum_docs,
					'sum_check'		: sum_check,
					'sum_percent'	: sum_percent,
					'sum_check_percent' : sum_check_percent
				}
				units_data.append(param_unit)
		else:
			error = "Выберите пожалуйста город, а я по нему для Вас сформирую отчет"

		filtr = {
			'date' 			: date_start,
			'city_id'		: city_id,
			'direction_id'	: direction_id
		}

		selected = {
			'citys'			: citys,
			'directions' 	: directions
		}

		params = {
				'type'          : 'checklists',
				'nav_selected'  : 6,
				"error"			: error,
				'filtr'			: filtr,
				'selected'		: selected,
				'units_data'	: units_data,
				'dates_list'	: dates_list
			}
		
		return render(request, 'checklist/reports_dc.html', {"params": params})
	return HttpResponseRedirect('/')


###
def checkList(request):
	if request.user.is_authenticated:
		return HttpResponseRedirect('/checklists/glav/')
		units = RefUnit.objects.all().order_by("name")
		profiles = request.user.profiles
		save = ""
		unitID = ""
		stafID = ""
		dateID = ""
		rlkID = ""
		checkListO = ""
		rlks = ""
		stafs = ""
		v1_2 = ""
		date = ""

		if request.method == "POST":
			unitID = request.POST["select_unit"]
			if "select_staff" in request.POST:
				stafID = request.POST["select_staff"]
			if "date" in request.POST:
				date = request.POST["date"]
			if "select_rlk" in request.POST:
				rlkID = request.POST["select_rlk"]
				if len(rlkID) > 0:	
					checkListQ = CheckList.objects.filter(rlk__id = rlkID)
					if len(checkListQ) > 0:
						checkListO = checkListQ[0]
			
			if len(date) > 0:
				dateID = DT.datetime.strptime(date, "%Y-%m-%d").date()
				dateIDT = dateID + DT.timedelta(days=1)
				unitO = RefUnit.objects.get(id = unitID)
				rlks = DocRLK.objects.filter(unit = unitO)
				if len(stafID) >0:
					stafO = RefStaff.objects.get(id = stafID)
					rlks = rlks.filter(staff = stafO)
				rlks = rlks.filter(dataTime__range = (dateID, dateIDT))
				rlks = rlks.order_by("dataTime")
			
			if "save" in request.POST:
				user = request.user
			    
				save = request.POST["save"]
				rlkO = DocRLK.objects.get(id= rlkID)
				checkListQ = list(CheckList.objects.filter(rlk = rlkO))
				if len(checkListQ) > 0:
					checkListO = checkListQ[0]
				else:
					checkListO = CheckList()
					checkListO.dataTimeCreate = DT.datetime.now()

				checkListO.dataTime = DT.datetime.now()
				checkListO.user = user
				checkListO.rlk = rlkO
				
				if request.POST["v1_1"]:
					checkListO.v1_1 = request.POST["v1_1"]
				if request.POST["v1_2"]:
					checkListO.v1_2 = request.POST["v1_2"] 
				if request.POST["v1_3"]:
					checkListO.v1_3 = request.POST["v1_3"] 
				if request.POST["v1_4"]:
					checkListO.v1_4 = request.POST["v1_4"] 

				if request.POST["v2_1"]:
					checkListO.v2_1 = request.POST["v2_1"]
				if request.POST["v2_2"]:
					checkListO.v2_2 = request.POST["v2_2"]
				if request.POST["v2_3"]:
					checkListO.v2_3 = request.POST["v2_3"]
				if request.POST["v2_4"]:
					checkListO.v2_4 = request.POST["v2_4"]
				if request.POST["v2_5"]:
					checkListO.v2_5 = request.POST["v2_5"]
				if request.POST["v2_6"]:
					checkListO.v2_6 = request.POST["v2_6"]

				if request.POST["v3_1"]:
					checkListO.v3_1 = request.POST["v3_1"]
				if request.POST["v3_2"]:
					checkListO.v3_2 = request.POST["v3_2"]
				if request.POST["v3_3"]:
					checkListO.v3_3 = request.POST["v3_3"]
				if request.POST["v3_4"]:
					checkListO.v3_4 = request.POST["v3_4"]
				if request.POST["v3_5"]:
					checkListO.v3_5 = request.POST["v3_5"]

				if request.POST["v4_1"]:
					checkListO.v4_1 = request.POST["v4_1"]
				if request.POST["v4_2"]:
					checkListO.v4_2 = request.POST["v4_2"]
				if request.POST["v4_3"]:
					checkListO.v4_3 = request.POST["v4_3"]
				if request.POST["v4_4"]:
					checkListO.v4_4 = request.POST["v4_4"]

				if request.POST["v5_1"]:
					checkListO.v5_1 = request.POST["v5_1"]
				if request.POST["v5_2"]:
					checkListO.v5_2 = request.POST["v5_2"]
				if request.POST["v5_3"]:
					checkListO.v5_3 = request.POST["v5_3"]
				if request.POST["v5_4"]:
					checkListO.v5_4 = request.POST["v5_4"]
				if request.POST["v5_5"]:
					checkListO.v5_5 = request.POST["v5_5"]

				if request.POST["v6_1"]:
					checkListO.v6_1 = request.POST["v6_1"]
				if request.POST["v6_2"]:
					checkListO.v6_2 = request.POST["v6_2"]
				if request.POST["v6_3"]:
					checkListO.v6_3 = request.POST["v6_3"]

				if request.POST["v7_1"]:
					checkListO.v7_1 = request.POST["v7_1"]
				if request.POST["v7_2"]:
					checkListO.v7_2 = request.POST["v7_2"]
				if request.POST["v7_3"]:
					checkListO.v7_3 = request.POST["v7_3"]
				if request.POST["v7_4"]:
					checkListO.v7_4 = request.POST["v7_4"]

				if request.POST["v8_1"]:
					checkListO.v8_1 = request.POST["v8_1"]
				if request.POST["v8_2"]:
					checkListO.v8_2 = request.POST["v8_2"]
				if request.POST["v8_3"]:
					checkListO.v8_3 = request.POST["v8_3"]
				if request.FILES['audio']:
					myfile = request.FILES['audio']
					checkListO.audio = myfile
				if request.POST["comment"]:
					checkListO.comment = request.POST["comment"]
				if profiles.view_checklist == False:
					checkListO.save()
					rlkO.listened = True
					rlkO.save()

			unitObjects = RefUnit.objects.get(id=unitID)
			stafs = list(RefStaff.objects.filter(unit = unitObjects).order_by("name"))
		return render(request, 'checklist/checklist.html', {'profiles': profiles, 'request': request, "checkListO":checkListO, "save":save ,"units": units, 'unitID': unitID, 'rlkID': rlkID, "stafs": stafs, "stafID": stafID, "v1_2": v1_2, "date": date, "rlks":rlks})
	return HttpResponseRedirect('/')


def glav(request):
	if request.user.is_authenticated:
		op = CheckList.objects.filter(rlk__unit__buauto = False).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('-count')
		op_count = CheckList.objects.all().count()
		
		rlk_tradein = CheckListTradeIn.objects.filter(rlk__unit__buauto = True).values("rlk__unit__name").distinct().annotate(count=Count('id')).order_by('-count')
		rlk_tradein_count = CheckListTradeIn.objects.all().count()
		
		zn_in = CheckListServiceIn.objects.values("zn__unit__name").distinct().annotate(count=Count('id')).order_by('-count')
		zn_in_count = CheckListServiceIn.objects.all().count()
		
		zn_out = CheckListServiceOut.objects.values("zn__unit__name").distinct().annotate(count=Count('id')).order_by('-count') 
		zn_out_count = CheckListServiceOut.objects.all().count()  
		
		params = {
			'op_list': list(op),
			'zn_in_list': list(zn_in),
			'zn_out_list': list(zn_out),
			'op_count': op_count,
			'zn_in_count': zn_in_count,
			'zn_out_count': zn_out_count,
			'rlk_tradein_list': rlk_tradein,
			'rlk_tradein_count': rlk_tradein_count,
			'sad': CheckList.objects.all().count()
		}
		return render(request, 'checklist/glav.html', {'params': params})
	return HttpResponseRedirect('/')


def doc(request):
	if request.user.is_authenticated:
		profiles = request.user.profiles
		if request.GET.get('checkid', ""):
			checkid = request.GET['checkid']
			if len(checkid) != 0:
				rlks = CheckList.objects.get(id = checkid)
				return render(request, 'checklist/docchecklist.html', {'profiles':profiles, 'request': request, "checkListO":rlks, "checkListO":rlks, "rlkID": 'rlks.rlk.id'})
		else:
			HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')


def listchecklist(request):
	if request.user.is_authenticated:
		return HttpResponseRedirect('../glav')

		units = RefUnit.objects.all().order_by("name")
		profiles = request.user.profiles
		save = ""
		unitID = ""
		stafID = ""
		dateID = ""
		rlkID = ""
		checkListO = ""
		rlks = ""
		stafs = ""
		date = ""
		date_end = ""
		staffsKK = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		staffKKID = ""
		rlks = CheckList.objects.all()
		nomer = ""
		if request.GET.get('nomer', ""):
			nomer = request.GET['nomer']
			rlks = rlks.filter(rlk__nomer__contains = nomer)
		if request.GET.get('select_unit', ""):
			unitID = request.GET['select_unit']
			rlks = rlks.filter(rlk__unit = RefUnit.objects.get(id = unitID))
			stafs = RefStaff.objects.filter(unit = RefUnit.objects.get(id = unitID)).order_by('name')
		if request.GET.get('select_staffKK', ""):
			staffKKID = request.GET['select_staffKK']
			rlks = rlks.filter(user = Profiles.objects.get(id = staffKKID).user)
		if request.GET.get('select_staff', ""):
			stafID = request.GET["select_staff"]
			rlks = rlks.filter(rlk__staff = RefStaff.objects.get(id = stafID))
		if request.GET.get('date', ""):
			date = request.GET['date']
			dateID = DT.datetime.strptime(date, "%Y-%m-%d")
			rlks = rlks.filter(rlk__dataTime__gte = dateID)
		if request.GET.get('date_end', ""):
			date_end = request.GET['date_end']
			date_ends = DT.datetime.strptime(date_end, "%Y-%m-%d") + DT.timedelta(days=1) 
			rlks = rlks.filter(rlk__dataTime__lte = date_ends)
		page = 0
		if request.GET.get('page', ""):
			page = int(request.GET['page'])
		
		rlks = rlks.order_by("rlk__dataTime")
		count = len(rlks)
		if count == 0:
			countPage = 0
		else:
			countPage = int(count / 25) + 1

		if page == 0:
			rlks = rlks[0:25]
		else:
			page = page - 1
			page = page * 25
			pageEnd = page + 25
			rlks = rlks[page:pageEnd]
		rlks = list(rlks)
		return render(request, 'checklist/checklistlist.html', {'nomer':nomer, 'staffKKID':staffKKID, 'staffsKK': staffsKK, 'countPage': range(countPage), 'count': count, 'profiles': profiles, 'request': request, "units": units, 'unitID': unitID, "stafs": stafs, "stafID": stafID, "date_end": date_end, "date": date, "rlks":rlks, "dateID": date})
	return HttpResponseRedirect('/')


def login(request):
	return HttpResponseRedirect('/')
	if request.method == "POST":
		loginUser = ""
		passwordUser = ""
		error = ""
		if "login" in request.POST:
				loginUser = request.POST["login"]
		if "password" in request.POST:
				passwordUser = request.POST["password"]
		user = authenticate(username=loginUser, password=passwordUser)
		if user is not None:
			if user.is_active:
				dj_login(request, user)
				return HttpResponseRedirect('/checklist/glav')
			else:
				error = "Пароль действителен, но учетная запись была отключена!"
		else:
			error = "Имя пользователя и пароль неверные."
		return render(request, 'checklist/login.html', {"login": loginUser, 'password': passwordUser, "error": error})	
	return render(request, 'checklist/login.html')


def logout(request):
	dj_logout(request)
	return HttpResponseRedirect('/')


###
##
# Отдел продаж
def op(request):
	if request.user.is_authenticated:
		
		count_filtr_dop = 0
		countListRecord = 25
		
		if request.GET.get('select_count', 25):
			countListRecord = int(request.GET.get('select_count', 25))

		units 		= RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by("name")
		profiles 	= request.user.profiles
		save 		= ""
		unitID 		= ""
		stafID 		= ""
		dateID 		= ""
		rlkID 		= ""
		checkListO 	= ""
		rlks 		= ""
		stafs 		= ""
		date 		= ""
		date_end 	= ""
		staffsKK 	= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		staffKKID 	= ""
		rlks 		= CheckList.objects.all()
		
		nomer 		= ""
		select_close 			= 0
		select_canceled 		= 0
		select_checklist_cvc 	= 0
		select_checklist_cheked = 0
		
		rlks_list = DocRLK.objects.filter(unit__buauto = False)

		if request.GET.get('nomer', ""):
			nomer 			= request.GET['nomer']
			rlks_list 		= rlks_list.filter(nomer__contains = nomer)
		if request.GET.get('select_unit', ""):
			unitID 		= request.GET['select_unit']
			rlks_list 	= rlks_list.filter(unit = RefUnit.objects.get(id = unitID))
			stafs 		= rlks_list.values('staff', 'staff__name').distinct().order_by('staff__name')
		
		if request.GET.get('select_staffKK', ""):
			staffKKID 	= request.GET['select_staffKK']
			rlks 		= rlks.filter(user = Profiles.objects.get(id = staffKKID).user)
		if request.GET.get('select_staff', ""):
			stafID 		= request.GET["select_staff"]
			rlks_list 	= rlks_list.filter(staff = RefStaff.objects.get(id = stafID))
		
		if request.GET.get('date', ""):
			date 		= request.GET['date']
			dateID 		= DT.datetime.strptime(date, "%Y-%m-%d")
			rlks_list 	= rlks_list.filter(dataTime__gte = dateID)
		
		if request.GET.get('date_end', ""):
			date_end 	= request.GET['date_end']
			date_ends 	= DT.datetime.strptime(date_end, "%Y-%m-%d") + DT.timedelta(days=1) 
			rlks_list 	= rlks_list.filter(dataTime__lte = date_ends)
		
		if request.GET.get('select_close_today', ""):
			select_close_today = int(request.GET['select_close_today'])
			if select_close_today == 1:
				rlks = rlks.filter(rlk__archiveDayToDay = True)
			elif select_close_today == 2:
				rlks = rlks.filter(rlk__archiveDayToDay = False)
			select_close = select_close_today 
		
		subquery_cvc  			= Subquery(Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(rlk__dataTime__gte = date_start_cvc_power_bi).filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
		subquery_kg  			= Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
		subquery_canceled_cvc  	= Coalesce(Subquery(Records_voice_recorder_cvc_checklist.objects.filter(rlk__dataTime__gte = date_start_cvc_power_bi).filter(rlk_id = OuterRef(name='id')).values('canceled')[:1]), False)
		subquery_canceled_kg  	= Coalesce(Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('canceled')[:1]), False)
		
		if request.GET.get('select_checklist_cvc', ""):
			select_checklist_cvc = int(request.GET['select_checklist_cvc'])
			if select_checklist_cvc == 1:
				rlks = rlks.filter(cheklist_cvc__gte = 1)
			elif select_checklist_cvc == 2:
				rlks = rlks.filter(cheklist_cvc = None)
			select_checklist_cvc = select_checklist_cvc

		if request.GET.get('select_checklist_cheked', ""):
			select_checklist_cheked = int(request.GET['select_checklist_cheked'])
			if select_checklist_cheked == 1:
				rlks = rlks.filter(cheked = True)
			elif select_checklist_cheked == 2:
				rlks = rlks.filter(cheked = False)
			select_checklist_cheked = select_checklist_cheked 

		criterion1 = Q(cheklist_cvc = None)
		criterion2 = Q(cheklist_kg = None)
		
		rlks_list   = rlks_list.annotate(cheklist_cvc = subquery_cvc)
		rlks_list   = rlks_list.annotate(cheklist_kg = subquery_kg)
		rlks_list   = rlks_list.annotate(canceled_cvc = subquery_canceled_cvc)
		rlks_list   = rlks_list.annotate(canceled_kg = subquery_canceled_kg)

		rlks_list 	= rlks_list.exclude(criterion1 & criterion2)

		if request.GET.get('select_canceled', ""):
			select_canceled = int(request.GET['select_canceled'])
			if select_canceled == 1:
				canceled_kg 	= Q(canceled_kg = True)
				canceled_cvc 	= Q(canceled_cvc = True)
				rlks_list = rlks_list.filter(canceled_cvc or canceled_kg)
			elif select_canceled == 2:
				canceled_kg 	= Q(canceled_kg = False)
				canceled_cvc 	= Q(canceled_cvc = False)
				rlks_list = rlks_list.filter(canceled_cvc or canceled_kg) | rlks_list.filter(canceled_cvc = True).filter(cheklist_kg__gt = 0)
			select_canceled = select_canceled 

		page = 0
		if request.GET.get('page', ""):
			page = int(request.GET['page'])
		
		# Ответы на вопросы
		list_filter_or 		= list()
		list_filter_and 	= list()
		for key in request.GET.keys():
			if key.startswith('v') and len(key) == 4:
				value = int(request.GET.get(key))
				
				if value == 1:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					rlks = rlks.filter(**kw)
				elif value == 2:
					name_fields = key + '__lte'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					rlks = rlks.filter(**kw)
				elif value == 3:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				elif value == 4:
					name_fields = key + ''
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				#count_filtr_dop = count_filtr_dop + 1
		
		qyery = Q(result__gte = 0)
		
		#if len(list_filter_and) > 0:
	#		for filter_and in list_filter_and:
	#			qyery.add(filter_and, Q.AND)
		
		if len(list_filter_or) > 0:
			for filter_or in list_filter_or:
				qyery.add(filter_or, Q.OR)
		
		rlks = rlks.filter(qyery)

		count_filtr_dop = len(list_filter_and) + len(list_filter_or)
		
		rlks_list 	= rlks_list.order_by("-dataTime")
		counts 		= rlks_list.count()
		
		paginator 	= Paginator(rlks_list, countListRecord)
		page_number = request.GET.get('page')
		page_obj 	= paginator.get_page(page_number)
		
		filds_razdel 	= list()
		fields			= list()
		razdel = ''
		meta_fields = CheckList._meta.get_fields()
		for meta_field in meta_fields:
			name = meta_field.__dict__['name']
			if name.startswith('v'): 
				
				if name[1:2] != razdel:
					if len(fields) > 0:
						info = {
							'razdel': razdel,
							'fields': fields
						}
						filds_razdel.append(info)
					fields = list()
					razdel = name[1:2]
				
				field = {
					'id' 			: name,
					'razdel' 		: name.replace('v',''),
					'name'			: meta_field.__dict__['verbose_name'],
					'name_human'	: name.replace('v','').replace('_', '.'),
					'value'			: request.GET.get(name, 0)
				}
				fields.append(field)
		if len(fields) > 0:
			info = {
				'razdel': razdel,
				'fields': fields
			}
			filds_razdel.append(info)
			fields = list()
			razdel = razdel

		filtr = {
			'unitID'					: unitID,
			'staffID'					: stafID,
			'staffKKID'					: staffKKID,
			'nomer'						: nomer,
			'dateStart'					: date, 
			'dateEnd'					: date_end,
			'select_close'				: select_close,
			'select_canceled'			: select_canceled,
			'select_checklist_cvc' 		: select_checklist_cvc,
			'select_checklist_cheked' 	: select_checklist_cheked
		}

		select = {
			'units'		: units,
			'staffs'	: stafs,
			'staffsKK'	: staffsKK,
			
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'		: 1,
			'profiles'			: profiles,
			'request'			: request,
			'select'			: select,
			'filtr'				: filtr,
			'counts'			: counts,
			'page_obj'			: page_obj,
			'fields'			: filds_razdel,
			'count_filtr_dop' 	: count_filtr_dop,
			'select_count'		: countListRecord
		}
		'''
		params = {
			'type'              : 'checklists',
			'nav_selected'		: 1,
			'select_canceled'	: select_canceled,
			'select_close'		: select_close, 
			'nomer'				: nomer,
			'counts'			: counts, 
			'staffKKID'			: staffKKID, 
			'staffsKK'			: staffsKK, 
			'profiles'			: profiles, 
			'units'				: units, 
			'unitID'			: unitID, 
			'stafs'				: stafs, 
			'stafID'			: stafID, 
			'date_end'			: date_end, 
			'date'				: date, 
			'rlks'				: rlks, 
			'dateID'			: date,
			'page_obj'			: page_obj
		}
		'''
		return render(request, 'checklist/op.html', {'params': params})
	return HttpResponseRedirect('/')


@csrf_exempt
def op_doc(request):
	if request.user.is_authenticated:
		profiles 				= request.user.profiles
		checklist_cvc_detail 	= dict()
		checklist_cvc			= ''

		if request.method == 'POST':
			checkid 	= request.POST["checkid"]
			rlk 		= DocRLK.objects.get(id = checkid)
			if CheckList.objects.filter(rlk = rlk).count() == 1:
				checkListO 	= CheckList.objects.get(rlk = rlk)
			else:
				checkListO 	= CheckList()

			rlkO 		= rlk

			if "save" in request.POST:
			
				if checkListO.rlk != rlkO:
					checkListO.rlk = rlkO
				
				# Ответы на вопросы
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value_str = request.POST.get(key)
						if len(value_str) == 0:
							value = 0
						else:
							value = int(value_str)
						if checkListO.__getattribute__(key) != int(value):
							checkListO.__setattr__(key, value)

				if 'audio' in request.FILES:
					if request.FILES['audio']:
						myfile 	= request.FILES['audio']
						checkListO.audio = myfile
				
				# Комментарий
				comment = ''
				if request.POST["comment"]:
					comment = request.POST["comment"]
				if checkListO.comment != comment:		
					checkListO.comment = comment
				
				# Тип отмены
				if 'select_type_canceled' in request.POST:
					select_type_canceled = request.POST["select_type_canceled"]
					if len(select_type_canceled) > 0:
						checkListO.canceledType = RefTypeCanceledCheckList.objects.get(pk = select_type_canceled)
					else:
						checkListO.canceledType = None

				# Комментарий причины отмены
				comment_canceled = ''
				if request.POST["comment_canceled"]:
					comment_canceled = request.POST["comment_canceled"]
				if checkListO.comment_canceled != comment_canceled:		
					checkListO.comment_canceled = comment_canceled
			
				# Отменен
				canceled = False
				if "canceled" in request.POST:
					if request.POST["canceled"]:
						canceled = True
				else:
					canceled = False
				if checkListO.canceled != canceled: 
					checkListO.canceled = canceled

				# Проверен
				cheked_user = False
				if "cheked_user" in request.POST:
					if request.POST["cheked_user"]:
						cheked_user = True
				else:
					cheked_user = False
				if checkListO.cheked != cheked_user: 
					if checkListO.cheked_user == None:
						checkListO.cheked = True
						checkListO.cheked_user = request.user
				
				if profiles.view_checklist == False:
					checkListO.save()
					if "close_to_day" in request.POST:
						if request.POST["close_to_day"]:
							rlkO.archiveDayToDay = request.POST["close_to_day"]
					else:
						rlkO.archiveDayToDay = False
					rlkO.listened = True
					rlkO.save()

				rlks = checkListO
				
				params = {
					'type'              : 'checklists',
					'nav_selected'	: 1,
					'profiles'		: profiles, 
					'request'		: request, 
					"checkListO"	: rlks, 
					"rlkID"			: 'rlks.rlk.id'}
				return HttpResponseRedirect('/checklists/glav/op/doc/?checkid=' + checkid)
			return HttpResponseRedirect('/checklists/glav/op/doc/?checkid=' + checkid)
		else:	
			if request.GET.get('checkid', ""):
				checkid = request.GET['checkid']
				start_record_seconds 	= 0
				end_record_seconds		= 0
				start_record_human		= 0
				if len(checkid) != 0:
					rlk 					= DocRLK.objects.get(id = checkid)
					versions				= list()
					data_list 				= list()
					checkListO				= CheckList()
					audio_voice_recorder 	= ''

					if CheckList.objects.filter(rlk = rlk).count() == 1:
						checkListO 	= CheckList.objects.get(rlk = rlk)
						versions 	= get_versions('CheckList', checkListO.id)
						audio_voice_recorder = checkListO.audio_voice_recorder
						if checkListO.audio_voice_recorder:
							if len(checkListO.audio_voice_recorder.data_json) > 0:
								data_json   = json.loads(checkListO.audio_voice_recorder.data_json)
								conf 		= data_json['conf']
								prev 		= 0
								text 		= ''
								for inf in conf:
									if inf['start'] - prev > 1:
										data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
										text = inf['data']['word']
										prev = inf['start']
									else:
										text = text + ' ' + inf['data']['word']
										prev = inf['start']
					
					checklist_cvc 	= get_checklist_cvc(rlk.id)
					if checklist_cvc != '':
						checklist_cvc_detail = checklist_cvc.detail_chelist()
						if audio_voice_recorder == '':
							audio_voice_recorder = checklist_cvc.records
							start_record_seconds  	= (checklist_cvc.time_start - checklist_cvc.records.date).seconds
							end_record_seconds 		= (checklist_cvc.time_start - checklist_cvc.records.date).seconds + checklist_cvc.duration
							start_record_human    	= time_human((checklist_cvc.time_start - checklist_cvc.records.date).seconds)
						if start_record_seconds == 0 and audio_voice_recorder != '':
							start_record_seconds  	= (checklist_cvc.time_start - checklist_cvc.records.date).seconds
							end_record_seconds 		= (checklist_cvc.time_start - checklist_cvc.records.date).seconds + checklist_cvc.duration
							start_record_human    	= time_human((checklist_cvc.time_start - checklist_cvc.records.date).seconds)
							
					params = {
						'type'              		: 'checklists',
						'nav_selected'				: 1,
						'profiles'					: profiles, 
						'rlk'						: rlk,
						'start_record_seconds'  	: start_record_seconds,
						'end_record_seconds'    	: end_record_seconds,
						'start_record_human'    	: start_record_human,				
						'request'					: request, 
						"checkListO"				: checkListO,
						'data_list'					: data_list, 
						'audio_voice'				: audio_voice_recorder,
						"rlkID"						: str(checkid),
						'versions'					: versions,
						'checklist_cvc'				: checklist_cvc,
						'checklist_cvc_detail'		: checklist_cvc_detail,
						"type_canceled"				: RefTypeCanceledCheckList.objects.all().order_by('name')
						}
					version_checklist = "3"
					if checkListO.version_checklist > 0:
						version_checklist = str(checkListO.version_checklist)
					name = "doc_direction_1_saves" + version_checklist + ".html"
					
					return render(request, 'checklist/' + name, {'params':params})
			else:
				HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')


@csrf_exempt
def op_doc_new(request):
	if request.user.is_authenticated:
		checklist_cvc_detail = dict()
		profiles 	= request.user.profiles	
		units 		= RefUnit.objects.filter(buauto = False).order_by("name")
			
		save 		= ""
		unitID 		= ""
		stafID 		= ""
		dateID 		= ""
		rlkID 		= ""
		checkListO 	= ""
		rlks 		= ""
		stafs 		= ""
		date 		= ""
		doc 		= ""
		audios		= list()
		audio_voice = '' 
		data_list 	= list()
		checklist_cvc = ''	
		start_record_seconds 	= 0
		end_record_seconds		= 0
		start_record_human		= 0
				
		if request.method == "GET":
			if 'check_new_cvc' in request.GET:
				check_new_cvc = request.GET['check_new_cvc']
				checklist_cvc = Records_voice_recorder_cvc_checklist.objects.get(pk = check_new_cvc) 
				start_record_seconds  	= (checklist_cvc.time_start - checklist_cvc.records.date).seconds
				end_record_seconds 		= (checklist_cvc.time_start - checklist_cvc.records.date).seconds + checklist_cvc.duration
				start_record_human    	= time_human((checklist_cvc.time_start - checklist_cvc.records.date).seconds)
				checklist_cvc_detail = checklist_cvc.detail_chelist()

				rlkID	= str(checklist_cvc.rlk.id)
				unitID 	= checklist_cvc.rlk.unit.id
				stafID	= str(checklist_cvc.rlk.staff.id)
				date 	= checklist_cvc.rlk.dataTime.strftime("%Y-%m-%d")
				dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
				dateIDT = dateID + DT.timedelta(days=1)
				doc 	= checklist_cvc.rlk
				audios 	= get_audio(doc.dataTime.strftime("%Y-%m-%d"), doc.staff)
				audio_voice = checklist_cvc.records
				if len(rlkID) > 0:	
					checkListQ = CheckList.objects.filter(rlk__id = rlkID)
					if len(checkListQ) > 0:
						checkListO = checkListQ[0]
				rlks 	= DocRLK.objects.filter(unit__id = unitID)
				if len(stafID) > 0:
					stafO 	= RefStaff.objects.get(id = stafID)
					rlks 	= rlks.filter(staff = stafO)
				rlks 	= rlks.filter(dataTime__range = (dateID, dateIDT))
				rlks 	= rlks.order_by("dataTime")
				stafs 	= RefStaff.objects.filter(units__in = [unitID]).order_by("name") | RefStaff.objects.filter(id= stafID).order_by("name")
				stafs	= stafs.distinct().order_by("name")
		if request.method == "POST":
			
			if 'audio_id_strip' in request.POST:
				audio_voice_id 	= request.POST["audio_id_strip"]
				times   	= request.POST["audio_times"]
				time_start  = convert_time_to_sec(times.split('-')[0].strip())
				time_end    = convert_time_to_sec(times.split('-')[1].strip())
				answer      = record_strip(audio_voice_id, time_start, time_end, times)
				audio_voice = Records_voice_recorder.objects.get(pk = answer)

			unitID = request.POST["select_unit"]
			
			if "select_staff" in request.POST:
				stafID = request.POST["select_staff"]
			
			if "date" in request.POST:
				date = request.POST["date"]
			
			if "select_rlk" in request.POST:
				rlkID 	= request.POST["select_rlk"]
				if len(rlkID) > 0:
					doc 	= DocRLK.objects.get(id= rlkID)
					audios 	= get_audio(doc.dataTime.strftime("%Y-%m-%d"), doc.staff)
					if len(rlkID) > 0:	
						checkListQ = CheckList.objects.filter(rlk__id = rlkID)
						if len(checkListQ) > 0:
							checkListO = checkListQ[0]
			
			if len(date) > 0:
				dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
				dateIDT = dateID + DT.timedelta(days=1)
				unitO 	= RefUnit.objects.get(id = unitID)
				rlks 	= DocRLK.objects.filter(unit = unitO)
				if len(stafID) >0:
					stafO 	= RefStaff.objects.get(id = stafID)
					rlks 	= rlks.filter(staff = stafO)
				rlks 	= rlks.filter(dataTime__range = (dateID, dateIDT))
				rlks 	= rlks.order_by("dataTime")
			
			if 'audio_id' in request.POST:
				audio_id = request.POST["audio_id"]
				if len(audio_id)>0:
					audio_voice = Records_voice_recorder.objects.get(pk = request.POST["audio_id"])
			
			if 'audio_user_cheked' in request.POST:
				audio_user_cheked 	= request.POST["audio_user_cheked"]
				list_audio_user 	= audio_user_cheked.split('|')
				if len(list_audio_user) == 2:
					audio_voice 	= Records_voice_recorder.objects.get(pk = list_audio_user[1])	
				else:
					answer 			= record_connects(list_audio_user)
					audio_voice 	= Records_voice_recorder.objects.get(pk = answer)


			if audio_voice != '':
				if len(audio_voice.data_json) > 0:
					data_json   = json.loads(audio_voice.data_json)
					conf 		= data_json['conf']
					data_list 	= list()
					prev 		= 0
					text 		= ''
					for inf in conf:
						if inf['start'] - prev > 1:
							data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
							text = inf['data']['word']
							prev = inf['start']
						else:
							text = text + ' ' + inf['data']['word']
							prev = inf['start']
	

			if "save" in request.POST:
				user = request.user
				
				save 		= request.POST["save"]
				rlkO 		= DocRLK.objects.get(id= rlkID)
				checkListQ 	= list(CheckList.objects.filter(rlk = rlkO))
				
				if len(checkListQ) > 0:
					checkListO = checkListQ[0]
				else:
					checkListO = CheckList()
					checkListO.dataTimeCreate = DT.datetime.now()

				checkListO.dataTime 	= DT.datetime.now()
				checkListO.user 		= user
				checkListO.rlk 			= rlkO
				
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value_str = request.POST.get(key)
						if len(value_str) == 0:
							value = 0
						else:
							value = int(value_str)
						if checkListO.__getattribute__(key) != int(value):
							checkListO.__setattr__(key, value)
							
				if 'audio' in request.FILES:
					if request.FILES['audio']:
						myfile 				= request.FILES['audio']
						checkListO.audio 	= myfile
				
				if request.POST["comment"]:
					checkListO.comment = request.POST["comment"]
				# Тип отмены
				if 'select_type_canceled' in request.POST:
					select_type_canceled = request.POST["select_type_canceled"]
					if len(select_type_canceled) > 0:
						checkListO.canceledType = RefTypeCanceledCheckList.objects.get(pk = select_type_canceled)
					else:
						checkListO.canceledType = None

				# Комментарий причины отмены
				comment_canceled = ''
				if request.POST["comment_canceled"]:
					comment_canceled = request.POST["comment_canceled"]
				if checkListO.comment_canceled != comment_canceled:		
					checkListO.comment_canceled = comment_canceled

				if request.POST["comment_canceled"]:
					checkListO.comment_canceled = request.POST["comment_canceled"]
				
				if 'audio_id' in request.POST:
					audio_id = request.POST["audio_id"]
					if len(audio_id)>0:
						audio_voice = Records_voice_recorder.objects.get(pk = request.POST["audio_id"])
						checkListO.audio_voice_recorder = audio_voice

				if profiles.view_checklist == False:
					
					if 'select_type_canceled' in request.POST:
						select_type_canceled = request.POST["select_type_canceled"]
					checkListO.version_checklist = 3
					checkListO.save()
					
					if "close_to_day" in request.POST:
						if request.POST["close_to_day"]:
							rlkO.archiveDayToDay = request.POST["close_to_day"]
					rlkO.listened = True
					rlkO.save()
					return HttpResponseRedirect('/checklists/glav/op/doc/?checkid=' + str(checkListO.id))

			unitObjects 	= RefUnit.objects.get(id=unitID)
			stafs 			= list(RefStaff.objects.filter(units__in = [unitID]).order_by("name"))
			if len(rlkID) > 0: 
				checklists_cvc 	= Records_voice_recorder_cvc_checklist.objects.filter(rlk__id = rlkID)
				if len(checklists_cvc) > 0:
					checklist_cvc = checklists_cvc[0]
					start_record_seconds  	= (checklist_cvc.time_start - checklist_cvc.records.date).seconds
					end_record_seconds 		= (checklist_cvc.time_start - checklist_cvc.records.date).seconds + checklist_cvc.duration
					start_record_human    	= time_human((checklist_cvc.time_start - checklist_cvc.records.date).seconds)

		params = {
			'type'              : 'checklists',
			'nav_selected'		: 1,
			'audio_voice'		: audio_voice,
			'profiles'			: profiles, 
			'request'			: request, 
			"checkListO"		: checkListO, 
			"save"				: save ,
			"units"				: units, 
			'unitID'			: unitID, 
			'rlkID'				: rlkID, 
			"stafs"				: stafs, 
			"stafID"			: stafID, 
			"date"				: date, 
			"rlks"				: rlks,
			"doc"				: doc,
			"audios"			: audios,
			"data_list"			: data_list,
			"checklist_cvc"				: checklist_cvc,
			'start_record_seconds'  	: start_record_seconds,
			'end_record_seconds'    	: end_record_seconds,
			'start_record_human'    	: start_record_human,				
			"checklist_cvc_detail"		: checklist_cvc_detail,
			"type_canceled"		: RefTypeCanceledCheckList.objects.all().order_by('name')
			}
		return render(request, 'checklist/doc_direction_13.html', {'params':params})
	return HttpResponseRedirect('/')


###
##
# Сервис прием автомобиля
def service_in(request):
	if request.user.is_authenticated:
		save = ""
		count_filtr_dop = 0
		countListRecord = 25
		if request.GET.get('select_count', 25):
			countListRecord = int(request.GET.get('select_count', 25))

		profiles = request.user.profiles
		
		unitID = ""
		unitsSelect = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by("name") 
		
		staffID = ""
		staffsSelect = ""

		staffKKID = ""
		staffsKK = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		
		service_in = CheckListServiceIn.objects.all()
		nomer = ""
		
		dateStart = ""
		dateEnd = ""

		if request.GET.get('nomer', ""):
			nomer = request.GET['nomer']
			service_in = service_in.filter(zn__nomer__contains = nomer)
		if request.GET.get('select_unit', ""):
			unitID = request.GET['select_unit']
			service_in 		= service_in.filter(zn__unit = RefUnit.objects.get(id = unitID))
			staffsSelect 	= list(RefStaff.objects.filter(units__in = [unitID]).order_by('name'))
		if request.GET.get('select_staffKK', ""):
			staffKKID = request.GET['select_staffKK']
			service_in = service_in.filter(user = Profiles.objects.get(id = staffKKID).user)
		if request.GET.get('select_staff', ""):
			staffID = request.GET["select_staff"]
			service_in = service_in.filter(zn__master = RefStaff.objects.get(id = staffID))
		if request.GET.get('date_start', ""):
			dateStart = request.GET['date_start']
			dateID = DT.datetime.strptime(dateStart, "%Y-%m-%d")
			service_in = service_in.filter(zn__dataTime__gte = dateID)
		if request.GET.get('date_end', ""):
			dateEnd = request.GET['date_end']
			date_ends = DT.datetime.strptime(dateEnd, "%Y-%m-%d") + DT.timedelta(days=1) 
			service_in = service_in.filter(zn__dataTime__lte = date_ends)
		
		list_filter_or 		= list()
		list_filter_and 	= list()
		for key in request.GET.keys():
			if key.startswith('v') and len(key) == 4:
				value = int(request.GET.get(key))
				
				if value == 1:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					service_in = service_in.filter(**kw)
				elif value == 2:
					name_fields = key + '__lte'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					service_in = service_in.filter(**kw)
				elif value == 3:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				elif value == 4:
					name_fields = key + ''
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				#count_filtr_dop = count_filtr_dop + 1
		
		qyery = Q(result__gte = 0)
		
		#if len(list_filter_and) > 0:
	#		for filter_and in list_filter_and:
	#			qyery.add(filter_and, Q.AND)
		
		if len(list_filter_or) > 0:
			for filter_or in list_filter_or:
				qyery.add(filter_or, Q.OR)
		
		service_in 		= service_in.filter(qyery)

		count_filtr_dop = len(list_filter_and) + len(list_filter_or)
		
		service_in 	= service_in.order_by("-zn__dataTime")
		count 		= service_in.count()
		paginator 	= Paginator(service_in, countListRecord)
	
		page_number = request.GET.get('page')
		page_obj 	= paginator.get_page(page_number)
		
		filds_razdel 	= list()
		fields			= list()
		razdel = ''
		meta_fields = CheckListServiceIn._meta.get_fields()
		for meta_field in meta_fields:
			name = meta_field.__dict__['name']
			if name.startswith('v'): 
				
				if name[1:2] != razdel:
					if len(fields) > 0:
						info = {
							'razdel': razdel,
							'fields': fields
						}
						filds_razdel.append(info)
					fields = list()
					razdel = name[1:2]
				
				field = {
					'id' 			: name,
					'razdel' 		: name.replace('v',''),
					'name'			: meta_field.__dict__['verbose_name'],
					'name_human'	: name.replace('v','').replace('_', '.'),
					'value'			: request.GET.get(name, 0)
				}
				fields.append(field)
		if len(fields) > 0:
			info = {
				'razdel': razdel,
				'fields': fields
			}
			filds_razdel.append(info)
			fields = list()
			razdel = razdel

		filtr = {
			'unitID'		: unitID,
			'staffID'		: staffID,
			'staffKKID'		: staffKKID,
			'nomer'			: nomer,
			'dateStart'		: dateStart, 
			'dateEnd'		: dateEnd
		}

		select = {
			'units'		: unitsSelect,
			'staffs'	: staffsSelect,
			'staffsKK'	: staffsKK
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'		: 2,
			'profiles'			: profiles,
			'request'			: request,
			'select'			: select,
			'filtr'				: filtr,
			'count'				: count,
			'page_obj'			: page_obj,
			'fields'			: filds_razdel,
			'count_filtr_dop' 	: count_filtr_dop,
			'select_count'		: countListRecord
		}
		return render(request, 'checklist/service_in.html', {'params': params})
	return HttpResponseRedirect('/')


@csrf_exempt
def service_in_doc(request):
	if request.user.is_authenticated:
		profiles = request.user.profiles
		audio_voice = '' 
		data_list 	= list()

		if request.GET.get('checkid', ""):
			checkid = request.GET['checkid']
			if len(checkid) != 0:
				rlks 		= CheckListServiceIn.objects.get(id = checkid)
				versions 	= get_versions('CheckListServiceIn', checkid)
				
				if rlks.audio_voice_recorder:
					audio_voice = rlks.audio_voice_recorder
					if len(rlks.audio_voice_recorder.data_json) > 0:
						data_json   = json.loads(rlks.audio_voice_recorder.data_json)
						conf 		= data_json['conf']
						prev 		= 0
						text 		= ''
						for inf in conf:
							if inf['start'] - prev > 1:
								data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
								text = inf['data']['word']
								prev = inf['start']
							else:
								text = text + ' ' + inf['data']['word']
								prev = inf['start']
								
				if request.POST.get('save', ""):
					save = request.POST["save"]
					if save:
					
						comment = ''
						if request.POST["comment"]:
							comment = request.POST["comment"]
						
						if rlks.comment != comment:
							rlks.comment = comment 
						
						# Ответы на вопросы
						for key in request.POST.keys():
							if key.startswith('v') and len(key) == 4:
								value = request.POST.get(key)
								
								if str(rlks.__getattribute__(key)) != value:
									if (key == 'v3_4' or key == 'v3_5' or key == 'v3_6' or key == 'v3_7' or key == 'v3_8'): 
										rlks.__setattr__(key, value)
									else:
										rlks.__setattr__(key, int(value))
						
						if "canceled" in request.POST:
							if request.POST["canceled"]:
								rlks.canceled = True
							else:
								rlks.canceled = False
						else:
							rlks.canceled = False
						
						if 'audio' in request.FILES:
							if request.FILES['audio']:
								myfile = request.FILES['audio']
								rlks.audio = myfile
						rlks.save()
						return HttpResponseRedirect(request.build_absolute_uri())
				
				params = {
					'type'              : 'checklists',
			'nav_selected'	: 2,
					'direction_id'	: '2',
					'audio_voice'	: audio_voice,
					'profiles'		: profiles, 
					'request'		: request, 
					"checkListO"	: rlks, 
					"rlkID"			: 'rlks.rlk.id',
					"data_list"		: data_list,
					'works'			: DocZNWork.objects.filter(zn = rlks.zn),
					'versions'		: versions,
					'products'		: DocZNProduct.objects.filter(zn = rlks.zn)
				}

				return render(request, 'checklist/doc_direction_2_saves.html', {'params': params})
		else:
			HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')


@csrf_exempt
def service_in_doc_new(request):
	if request.user.is_authenticated:
		
		save = False
		
		profiles 	= request.user.profiles
		
		unitID 		= ""
		units 	 	= RefUnit.objects.filter(buauto = False).order_by("name") 
		
		staffID 		= ""
		staffsSelect 	= ""

		staffIDKK 	= ""
		staffsKK 	= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		
		nomer 		= ""
		
		znSelect 	= ""
		znID 		= ""
		zn 			= ""
		date 		= ""
		doc 		= ""
		audios		= list()
		audio_voice = '' 
		data_list 	= list()	

		
		if 'audio_id_strip' in request.POST:
			audio_voice_id 	= request.POST["audio_id_strip"]
			times   	= request.POST["audio_times"]
			time_start  = convert_time_to_sec(times.split('-')[0].strip())
			time_end    = convert_time_to_sec(times.split('-')[1].strip())
			answer      = record_strip(audio_voice_id, time_start, time_end, times)
			audio_voice = Records_voice_recorder.objects.get(pk = answer)

		if request.POST.get('select_unit', ""):
			unitID 			= request.POST['select_unit']
			staffsSelect 	= DocZN.objects.filter(unit__id = unitID).values('master', 'master__id', 'master__name').distinct().order_by('master__name')
			#staffsSelect 	= list(RefStaff.objects.filter(units__in = [unitID]).order_by('name'))
			#staffsSelect	= get_stafs(direction_id = '2', unit_id= unitID, date = date)
		
		if request.POST.get('select_staff', ""):
			staffID = request.POST["select_staff"]

		if request.POST.get('date', ""):
			date 	= request.POST["date"]
			dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
			dateIDT = dateID + DT.timedelta(days=1)
			if len(staffID) >0:
				znSelect = DocZN.objects.filter(dataTime__range = (dateID, dateIDT)).annotate(check = Count('DocZN__zn', distinct=True))
				znSelect = list(znSelect.filter(unit = RefUnit.objects.get(id = unitID)).filter(master__id = staffID))	

		audio_voice = '' 
		if 'audio_id' in request.POST:
			audio_voice = Records_voice_recorder.objects.get(pk = request.POST["audio_id"])

		if request.POST.get('select_zn', ""):
			znID 	= request.POST['select_zn']
			zn 		= DocZN.objects.get(pk = znID)
			doc 	= zn
			audios 	= get_audio(zn.dataTime.strftime("%Y-%m-%d"), zn.master)
			
		if request.POST.get('save', ""):
			save = request.POST["save"]
			if save:
				service_in 					= CheckListServiceIn()
				service_in.dataTimeCreate 	= DT.datetime.now()
				service_in.dataTime 		= DT.datetime.now()
				service_in.user 			= request.user
				service_in.zn 				= DocZN.objects.get(id = znID)
				if request.POST["comment"]:
					service_in.comment = request.POST["comment"] 
				
				# Ответы на вопросы
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value = request.POST.get(key)
						
						if str(service_in.__getattribute__(key)) != value:
							if (key == 'v3_4' or key == 'v3_5' or key == 'v3_6' or key == 'v3_7' or key == 'v3_8'): 
								service_in.__setattr__(key, value)
							else:
								service_in.__setattr__(key, int(value))
				'''
				if request.POST["v1_1"]:
					service_in.v1_1 = request.POST["v1_1"]
				if request.POST["v1_2"]:
					service_in.v1_2 = request.POST["v1_2"]
				if request.POST["v1_3"]:
					service_in.v1_3 = request.POST["v1_3"]
				if request.POST["v1_4"]:
					service_in.v1_4 = request.POST["v1_4"]
				if request.POST["v1_5"]:
					service_in.v1_5 = request.POST["v1_5"]
				if request.POST["v1_6"]:
					service_in.v1_6 = request.POST["v1_6"]

				if request.POST["v2_1"]:
					service_in.v2_1 = request.POST["v2_1"]
				if request.POST["v2_2"]:
					service_in.v2_2 = request.POST["v2_2"]
				if request.POST["v2_3"]:
					service_in.v2_3 = request.POST["v2_3"]
				if request.POST["v2_4"]:
					service_in.v2_4 = request.POST["v2_4"]
				if request.POST["v2_5"]:
					service_in.v2_5 = request.POST["v2_5"]
				if request.POST["v2_6"]:
					service_in.v2_6 = request.POST["v2_6"]
				if request.POST["v2_7"]:
					service_in.v2_7 = request.POST["v2_7"]

				if request.POST["v3_1"]:
					service_in.v3_1 = request.POST["v3_1"]
				if request.POST["v3_2"]:
					service_in.v3_2 = request.POST["v3_2"]
				if request.POST["v3_3"]:
					service_in.v3_3 = request.POST["v3_3"]
				if request.POST["v3_4"]:
					service_in.v3_4 = request.POST["v3_4"]
				if request.POST["v3_5"]:
					service_in.v3_5 = request.POST["v3_5"]
				if request.POST["v3_6"]:
					service_in.v3_6 = request.POST["v3_6"]
				if request.POST["v3_7"]:
					service_in.v3_7 = request.POST["v3_7"]
				if request.POST["v3_8"]:
					service_in.v3_8 = request.POST["v3_8"]

				if request.POST["v4_1"]:
					service_in.v4_1 = request.POST["v4_1"]
				if request.POST["v4_2"]:
					service_in.v4_2 = request.POST["v4_2"]
				if request.POST["v4_3"]:
					service_in.v4_3 = request.POST["v4_3"]
				
				if request.POST["v5_1"]:
					service_in.v5_1 = request.POST["v5_1"]
				if request.POST["v5_2"]:
					service_in.v5_2 = request.POST["v5_2"]
				if request.POST["v5_3"]:
					service_in.v5_3 = request.POST["v5_3"]
				'''

				if 'audio' in request.FILES:
					if request.FILES['audio']:
						myfile = request.FILES['audio']
						service_in.audio = myfile

				if 'audio_id' in request.POST:
					audio_voice = Records_voice_recorder.objects.get(pk = request.POST["audio_id"])
					service_in.audio_voice_recorder = audio_voice

				service_in.save()

				return HttpResponseRedirect('/checklists/glav/service_in')
				#return render(request, 'checklist/service_in.html')

		if 'audio_id' in request.POST:
			audio_id = request.POST["audio_id"]
			if len(audio_id)>0:
				audio_voice = Records_voice_recorder.objects.get(pk = request.POST["audio_id"])
			
		if 'audio_user_cheked' in request.POST:
			audio_user_cheked = request.POST["audio_user_cheked"]
			list_audio_user = audio_user_cheked.split('|')
			if len(list_audio_user) == 2:
				audio_voice = Records_voice_recorder.objects.get(pk = list_audio_user[1])	
			else:
				answer = record_connects(list_audio_user)
				audio_voice = Records_voice_recorder.objects.get(pk = answer)


		if audio_voice != '':
			if len(audio_voice.data_json) > 0:
				data_json   = json.loads(audio_voice.data_json)
				conf 		= data_json['conf']
				data_list 	= list()
				prev 		= 0
				text 		= ''
				for inf in conf:
					if inf['start'] - prev > 1:
						data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
						text = inf['data']['word']
						prev = inf['start']
					else:
						text = text + ' ' + inf['data']['word']
						prev = inf['start']
			
		filtr = {
			'unitID'	: unitID,
			'staffID'	: staffID,
			'nomer'		: nomer,
			'date'		: date,
			'znID'		: znID
		}

		select = {
			'units'		: units,
			'staffs'	: staffsSelect,
			'zn'		: znSelect
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'	: 2,
			'audio_voice'	: audio_voice,
			'profiles'		: profiles,
			'request'		: request,
			'select'		: select,
			'filtr'			: filtr,
			'zn'			: zn,
			"doc"			: doc,
			"audios"		: audios,
			"data_list"		: data_list
			
		}
		return render(request, 'checklist/doc_direction_2.html', {'params': params})
	else:
		HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')

###
##
# Сервис выдача автомобиля
def service_out(request):
	if request.user.is_authenticated:
		save = ""
		count_filtr_dop = 0
		countListRecord = 25
		if request.GET.get('select_count', 25):
			countListRecord = int(request.GET.get('select_count', 25))

		profiles = request.user.profiles
		
		unitID = ""
		unitsSelect = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by("name") 
		
		staffID = ""
		staffsSelect = ""

		staffKKID = ""
		staffsKK = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		
		service_in = CheckListServiceOut.objects.all()
		nomer = ""
		
		dateStart = ""
		dateEnd = ""

		if request.GET.get('nomer', ""):
			nomer 			= request.GET['nomer']
			service_in 		= service_in.filter(zn__nomer__contains = nomer)
		if request.GET.get('select_unit', ""):
			unitID 			= request.GET['select_unit']
			service_in 		= service_in.filter(zn__unit = RefUnit.objects.get(id = unitID))
			staffsSelect 	= list(RefStaff.objects.filter(units__in = [unitID]).order_by('name'))
		if request.GET.get('select_staffKK', ""):
			staffKKID 		= request.GET['select_staffKK']
			service_in 		= service_in.filter(user = Profiles.objects.get(id = staffKKID).user)
		if request.GET.get('select_staff', ""):
			staffID 		= request.GET["select_staff"]
			service_in 		= service_in.filter(zn__masterOut = RefStaff.objects.get(id = staffID))
		if request.GET.get('date_start', ""):
			dateStart 	= request.GET['date_start']
			dateID 		= DT.datetime.strptime(dateStart, "%Y-%m-%d")
			service_in 	= service_in.filter(zn__dataTime__gte = dateID)
		if request.GET.get('date_end', ""):
			dateEnd 	= request.GET['date_end']
			date_ends 	= DT.datetime.strptime(dateEnd, "%Y-%m-%d") + DT.timedelta(days=1) 
			service_in 	= service_in.filter(zn__dataTime__lte = date_ends)
		
		
		list_filter_or 		= list()
		list_filter_and 	= list()
		for key in request.GET.keys():
			if key.startswith('v') and len(key) == 4:
				value = int(request.GET.get(key))
				
				if value == 1:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					service_in = service_in.filter(**kw)
				elif value == 2:
					name_fields = key + '__lte'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					service_in = service_in.filter(**kw)
				elif value == 3:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				elif value == 4:
					name_fields = key + ''
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				#count_filtr_dop = count_filtr_dop + 1
		
		qyery = Q(result__gte = 0)
		
		#if len(list_filter_and) > 0:
		#		for filter_and in list_filter_and:
		#			qyery.add(filter_and, Q.AND)
		
		if len(list_filter_or) > 0:
			for filter_or in list_filter_or:
				qyery.add(filter_or, Q.OR)
		
		service_in 		= service_in.filter(qyery)

		count_filtr_dop = len(list_filter_and) + len(list_filter_or)

		service_in 	= service_in.order_by("-zn__dataTime")
		count 		= service_in.count()
		paginator 	= Paginator(service_in, countListRecord)
	
		page_number = request.GET.get('page')
		page_obj 	= paginator.get_page(page_number)

		filds_razdel 	= list()
		fields			= list()
		razdel = ''
		meta_fields = CheckListServiceOut._meta.get_fields()
		for meta_field in meta_fields:
			name = meta_field.__dict__['name']
			if name.startswith('v'): 
				
				if name[1:2] != razdel:
					if len(fields) > 0:
						info = {
							'razdel': razdel,
							'fields': fields
						}
						filds_razdel.append(info)
					fields = list()
					razdel = name[1:2]
				
				field = {
					'id' 			: name,
					'razdel' 		: name.replace('v',''),
					'name'			: meta_field.__dict__['verbose_name'],
					'name_human'	: name.replace('v','').replace('_', '.'),
					'value'			: request.GET.get(name, 0)
				}
				fields.append(field)
		if len(fields) > 0:
			info = {
				'razdel': razdel,
				'fields': fields
			}
			filds_razdel.append(info)
			fields = list()
			razdel = razdel

		filtr = {
			'unitID'			: unitID,
			'staffID'			: staffID,
			'staffKKID'			: staffKKID,
			'nomer'				: nomer,
			'dateStart'			: dateStart, 
			'dateEnd'			: dateEnd
		}

		select = {
			'units'		: unitsSelect,
			'staffs'	: staffsSelect,
			'staffsKK'	: staffsKK
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'	: 3,
			'profiles'		: profiles,
			'request'		: request,
			'select'		: select,
			'filtr'			: filtr,
			'count'			: count,
			'page_obj'		: page_obj,
			'fields'			: filds_razdel,
			'count_filtr_dop' 	: count_filtr_dop,
			'select_count'		: countListRecord
		}
		return render(request, 'checklist/service_out.html', {'params': params})
	return HttpResponseRedirect('/')


@csrf_exempt
def service_out_doc(request):
	if request.user.is_authenticated:
		profiles = request.user.profiles
		if request.GET.get('checkid', ""):
			checkid = request.GET['checkid']
			if len(checkid) != 0:
				rlks 		= CheckListServiceOut.objects.get(id = checkid)
				versions 	= get_versions('CheckListServiceOut', checkid)
				doc		= rlks.zn
				if request.POST.get('save', ""):
					save = request.POST["save"]
					if save:
						#rlks.dataTime = DT.datetime.now()
						#rlks.user = request.user
						
						comment = ''
						if request.POST["comment"]:
							comment = request.POST["comment"]
						
						if rlks.comment != comment:
							rlks.comment = comment 
						
						# Ответы на вопросы
						for key in request.POST.keys():
							if key.startswith('v') and len(key) == 4:
								value = request.POST.get(key)
								
								if str(rlks.__getattribute__(key)) != value:
									rlks.__setattr__(key, value)

						if 'canceled' in request.POST:
							rlks.canceled = True
						else:
							rlks.canceled = False

						if 'audio' in request.FILES:	
							if request.FILES['audio']:
								myfile = request.FILES['audio']
								rlks.audio = myfile

						rlks.save()
				params = {
					'type'              : 'checklists',
			'nav_selected': 3,
					'profiles'		: profiles,
					'doc'			: doc,
					'versions'		: versions, 
					'request'		: request, 
					"checkListO"	: rlks, 
					"rlkID"			: 'rlks.rlk.id'
				}
				return render(request, 'checklist/doc_direction_3_saves.html', {'params': params})
		else:
			HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')


@csrf_exempt
def service_out_doc_new(request):
	if request.user.is_authenticated:
		
		save = False
		
		profiles 	= request.user.profiles
		doc		 	= ''
		unitID 		= ""
		unitsSelect = RefUnit.objects.filter(buauto = False).order_by("name") 
		
		staffID 		= ""
		staffsSelect 	= ""

		staffIDKK 	= ""
		staffsKK 	= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		
		nomer 	= ""
		
		znSelect 	= ""
		znID 		= ""
		
		date 	= ""
		
		if request.POST.get('select_unit', ""):
			unitID 			= request.POST['select_unit']
			#staffsSelect 	= list(RefStaff.objects.filter(units__in = [unitID]).order_by('name'))
			staffsSelect 	= DocZN.objects.filter(unit__id = unitID).values('master', 'master__id', 'master__name').distinct().order_by('master__name')
		if request.POST.get('select_staff', ""):
			staffID 	= request.POST["select_staff"]
		if request.POST.get('date', ""):
			date 	= request.POST["date"]
			dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
			dateIDT = dateID + DT.timedelta(days=1)
			if len(staffID) > 0:
				znSelect = DocZN.objects.filter(dataTime__range = (dateID, dateIDT)).annotate(check = Count('DocZN_out__zn', distinct=True))
				znSelect = list(znSelect.filter(unit = RefUnit.objects.get(id = unitID)).filter(master = RefStaff.objects.get(id=staffID)))	
			
		if request.POST.get('select_zn', ""):
			znID 	= request.POST['select_zn']
			doc 	= DocZN.objects.get(pk = znID)
		
		if request.POST.get('save', ""):
			save = request.POST["save"]
			if save:
				checkListServiceOut 				= CheckListServiceOut()
				checkListServiceOut.dataTimeCreate 	= DT.datetime.now()
				checkListServiceOut.dataTime 		= DT.datetime.now()
				checkListServiceOut.user 			= request.user
				checkListServiceOut.zn 				= DocZN.objects.get(id = znID)
				
				if request.POST["comment"]:
					checkListServiceOut.comment = request.POST["comment"] 
				
				# Ответы на вопросы
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value = request.POST.get(key)
						if key == 'v2_1': 
							checkListServiceOut.__setattr__(key, value)
						else:
							checkListServiceOut.__setattr__(key, int(value))
						
				if request.FILES['audio']:
					myfile = request.FILES['audio']
					checkListServiceOut.audio = myfile
				checkListServiceOut.save()
				
				return HttpResponseRedirect('/checklists/glav/service_out')

		filtr = {
			'unitID'	: unitID,
			'staffID'	: staffID,
			'nomer'		: nomer,
			'date'		: date,
			'znID'		: znID
		}

		select = {
			'units'		: unitsSelect,
			'staffs'	: staffsSelect,
			'zn'		: znSelect
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'	: 3,
			'profiles'		: profiles,
			'request'		: request,
			'select'		: select,
			'doc'			: doc,
			'filtr'			: filtr
		}
		return render(request, 'checklist/doc_direction_3.html', {'params':params})
	else:
		HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')

###
##
# Отдел продаж КорсАвто

def op_kors(request):
	if request.user.is_authenticated:
		
		count_filtr_dop = 0
		countListRecord = 25
		if request.GET.get('select_count', 25):
			countListRecord = int(request.GET.get('select_count', 25))

		units 		= RefUnit.objects.filter(buauto = True).filter(name__icontains = "КорсАвто").order_by("name")
		profiles 	= request.user.profiles
		save 		= ""
		unitID 		= ""
		stafID 		= ""
		dateID 		= ""
		rlkID 		= ""
		checkListO 	= ""
		stafs 		= ""
		date 		= ""
		date_end 	= ""
		staffsKK 	= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		staffKKID 	= ""
		
		rlks 	 	= CheckList_op_kors.objects.all()
		rlks_list 	= DocRLK.objects.filter(unit__buauto = True)
		
		nomer 					= ""
		select_close 			= 0
		select_canceled 		= 0
		select_checklist_cvc 	= 0
		select_checklist_cheked = 0

		if request.GET.get('nomer', ""):
			nomer = request.GET['nomer']
			rlks_list = rlks_list.filter(nomer__contains = nomer)
		
		if request.GET.get('select_unit', ""):
			unitID 		= request.GET['select_unit']
			rlks_list 	= rlks_list.filter(unit = RefUnit.objects.get(id = unitID))
			stafs 		= rlks_list.values('staff', 'staff__name').distinct().order_by('staff__name')
		
		if request.GET.get('select_staffKK', ""):
			staffKKID = request.GET['select_staffKK']
			rlks = rlks.filter(user = Profiles.objects.get(id = staffKKID).user)
		
		if request.GET.get('select_staff', ""):
			stafID = request.GET["select_staff"]
			rlks_list = rlks_list.filter(rlk__staff = RefStaff.objects.get(id = stafID))

		if request.GET.get('date_start', ""):
			date 		= request.GET['date_start']
			dateID 		= DT.datetime.strptime(date, "%Y-%m-%d")
			rlks_list 	= rlks_list.filter(dataTime__gte = dateID)
		
		if request.GET.get('date_end', ""):
			date_end 	= request.GET['date_end']
			date_ends 	= DT.datetime.strptime(date_end, "%Y-%m-%d") + DT.timedelta(days=1) 
			rlks_list 	= rlks_list.filter(dataTime__lte = date_ends)

		if request.GET.get('select_close_today', ""):
			select_close_today = int(request.GET['select_close_today'])
			if select_close_today == 1:
				rlks_list = rlks_list.filter(archiveDayToDay = True)
			elif select_close_today == 2:
				rlks_list = rlks_list.filter(archiveDayToDay = False)
			select_close = select_close_today 

		if request.GET.get('select_canceled', ""):
			select_canceled = int(request.GET['select_canceled'])
			if select_canceled == 1:
				rlks = rlks.filter(canceled = True)
			elif select_canceled == 2:
				rlks = rlks.filter(canceled = False)
			select_canceled = select_canceled 
		
		subquery_cvc  			= Subquery(Records_voice_recorder_cvc_checklist.objects.filter(direction = 5).filter(success = True).filter(rlk__dataTime__gte = date_start_cvc_power_bi).filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
		subquery_kg  			= Subquery(CheckList_op_kors.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
		subquery_canceled_cvc  	= Coalesce(Subquery(Records_voice_recorder_cvc_checklist.objects.filter(direction = 5).filter(rlk__dataTime__gte = date_start_cvc_power_bi).filter(rlk_id = OuterRef(name='id')).values('canceled')[:1]), False)
		subquery_canceled_kg  	= Coalesce(Subquery(CheckList_op_kors.objects.filter(rlk_id = OuterRef(name='id')).values('canceled')[:1]), False)
		
		rlks_list   = rlks_list.annotate(cheklist_cvc = subquery_cvc)
		rlks_list   = rlks_list.annotate(cheklist_kg = subquery_kg)
		rlks_list   = rlks_list.annotate(canceled_cvc = subquery_canceled_cvc)
		rlks_list   = rlks_list.annotate(canceled_kg = subquery_canceled_kg)

		criterion1 = Q(cheklist_cvc = None)
		criterion2 = Q(cheklist_kg = None)

		rlks_list 	= rlks_list.exclude(criterion1 & criterion2)

		if request.GET.get('select_checklist_cvc', ""):
			select_checklist_cvc = int(request.GET['select_checklist_cvc'])
			if select_checklist_cvc == 1:
				rlks_list = rlks_list.filter(cheklist_cvc__gte = 1)
			elif select_checklist_cvc == 2:
				rlks_list = rlks_list.filter(cheklist_cvc = None)
			select_checklist_cvc = select_checklist_cvc

		if request.GET.get('select_checklist_cheked', ""):
			select_checklist_cheked = int(request.GET['select_checklist_cheked'])
			if select_checklist_cheked == 1:
				rlks = rlks.filter(cheked = True)
			elif select_checklist_cheked == 2:
				rlks = rlks.filter(Q(cheked = False) | Q(cheked = None))
			select_checklist_cheked = select_checklist_cheked 

		
		if request.GET.get('select_canceled', ""):
			select_canceled = int(request.GET['select_canceled'])
			if select_canceled == 1:
				canceled_kg 	= Q(canceled_kg = True)
				canceled_cvc 	= Q(canceled_cvc = True)
				rlks_list = rlks_list.filter(canceled_cvc or canceled_kg)
			elif select_canceled == 2:
				canceled_kg 	= Q(canceled_kg = False)
				canceled_cvc 	= Q(canceled_cvc = False)
				rlks_list = rlks_list.filter(canceled_cvc or canceled_kg) | rlks_list.filter(canceled_cvc = True).filter(cheklist_kg__gt = 0)
			select_canceled = select_canceled 

		page = 0
		if request.GET.get('page', ""):
			page = int(request.GET['page'])

		# Ответы на вопросы
		list_filter_or 		= list()
		list_filter_and 	= list()
		for key in request.GET.keys():
			if key.startswith('v') and len(key) == 4:
				value = int(request.GET.get(key))
				
				if value == 1:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					rlks = rlks.filter(**kw)
				elif value == 2:
					name_fields = key + '__lte'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					rlks = rlks.filter(**kw)
				elif value == 3:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				elif value == 4:
					name_fields = key + ''
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				#count_filtr_dop = count_filtr_dop + 1
		
		qyery = Q(result__gte = 0)
		
		#if len(list_filter_and) > 0:
	#		for filter_and in list_filter_and:
	#			qyery.add(filter_and, Q.AND)
		
		if len(list_filter_or) > 0:
			for filter_or in list_filter_or:
				qyery.add(filter_or, Q.OR)
		
		rlks = rlks.filter(qyery)

		count_filtr_dop = len(list_filter_and) + len(list_filter_or)
		
		rlks_list 	= rlks_list.order_by("-dataTime")
		counts 		= rlks_list.count()
		
		paginator 	= Paginator(rlks_list, countListRecord)
		page_number = request.GET.get('page')
		page_obj 	= paginator.get_page(page_number)

		filds_razdel 	= list()
		fields			= list()
		razdel = ''
		meta_fields = CheckList_op_kors._meta.get_fields()
		for meta_field in meta_fields:
			name = meta_field.__dict__['name']
			if name.startswith('v'): 
				
				if name[1:2] != razdel:
					if len(fields) > 0:
						info = {
							'razdel': razdel,
							'fields': fields
						}
						filds_razdel.append(info)
					fields = list()
					razdel = name[1:2]
				
				field = {
					'id' 			: name,
					'razdel' 		: name.replace('v',''),
					'name'			: meta_field.__dict__['verbose_name'],
					'name_human'	: name.replace('v','').replace('_', '.'),
					'value'			: request.GET.get(name, 0)
				}
				fields.append(field)
		if len(fields) > 0:
			info = {
				'razdel': razdel,
				'fields': fields
			}
			filds_razdel.append(info)
			fields = list()
			razdel = razdel


		filtr 	= {
			'date_end'					: date_end, 
			'date_start'				: date,
			'unitID'					: unitID,
			'stafID'					: stafID,  
			'staffKKID'					: staffKKID,
			'nomer'						: nomer, 
			'select_close'				: select_close,
			'select_canceled'			: select_canceled,
			'select_checklist_cvc' 		: select_checklist_cvc,
			'select_checklist_cheked' 	: select_checklist_cheked
		}
		
		select 	= {
			'units'		: units,
			'staffs'	: stafs, 
			'staffsKK'	: staffsKK, 	
		}

		params 	= {
			'type'              : 'checklists',
			'nav_selected'		: 5,
			'select'			: select,
			'filtr'				: filtr,
			'select_canceled'	: select_canceled,
			'select_close'		: select_close, 
			'counts'			: counts, 
			'profiles'			: profiles, 
			'rlks'				: rlks, 
			'dateID'			: date,
			'page_obj'			: page_obj,
			'fields'			: filds_razdel,
			'count_filtr_dop' 	: count_filtr_dop,
			'select_count'		: countListRecord
		}

		return render(request, 'checklist/trade_in_op.html', {'params': params})
	return HttpResponseRedirect('/')


@csrf_exempt
def op_kors_doc(request):
	if request.user.is_authenticated:
			
		cityID 		= ""
		citys 		= RefCity.objects.all().order_by("name")
		
		units 		= RefUnit.objects.filter(buauto = True).filter(name__icontains = "КорсАвто").order_by("name")
		profiles 	= request.user.profiles
		save 		= ""
		unitID 		= ""
		stafID 		= ""
		dateID 		= ""
		rlkID 		= ""
		checkListO 	= ""
		rlks 		= ""
		stafs 		= ""
		date 		= ""
		audio_voice = ''

		if request.method == "POST":
			if not "save" in request.POST:
				unitID = request.POST["select_unit"]
				if "select_staff" in request.POST:
					stafID = request.POST["select_staff"]
				if "date" in request.POST:
					date = request.POST["date"]
				if "select_rlk" in request.POST:
					rlkID = request.POST["select_rlk"]
					if len(rlkID) > 0:	
						checkListQ = CheckList_op_kors.objects.filter(rlk__id = rlkID)
						if len(checkListQ) > 0:
							checkListO = checkListQ[0]
				
				if len(date) > 0:
					dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
					dateIDT = dateID + DT.timedelta(days=1)
					unitO 	= RefUnit.objects.get(id = unitID)
					rlks 	= DocRLK.objects.filter(unit = unitO)
					if len(stafID) >0:
						stafO 	= RefStaff.objects.get(id = stafID)
						rlks 	= rlks.filter(staff = stafO)
					rlks = rlks.filter(dataTime__range = (dateID, dateIDT))
					rlks = rlks.order_by("dataTime")
				
				
				if 'audio_id' in request.POST:
					audio_id 	= request.POST["audio_id"]
					if len(audio_id) > 0:
						audio_voice = Records_voice_recorder.objects.get(pk = audio_id)
						checkListO.audio_voice_recorder = audio_voice

			if "save" in request.POST:
				
				user 	= request.user
				rlkID 	= request.POST["checkid"]
				rlkO 	= DocRLK.objects.get(id= rlkID)
				
				checkListQ = list(CheckList_op_kors.objects.filter(rlk = rlkO))
				
				if len(checkListQ) > 0:
					checkListO = checkListQ[0]
				else:
					checkListO 		= CheckList_op_kors()
					checkListO.rlk 	= rlkO
					checkListO.user = request.user
					checkListO.dataTimeCreate = DT.datetime.now()

				comment = ''
				if request.POST["comment"]:
					comment = request.POST["comment"]
				
				if checkListO.comment != comment:
					checkListO.comment = comment 
				
				# Ответы на вопросы
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value = int(request.POST.get(key))
						
						if str(checkListO.__getattribute__(key)) != value:
							checkListO.__setattr__(key, value)

				if 'canceled' in request.POST:
					checkListO.canceled = True
				else:
					checkListO.canceled = False

				if 'audio' in request.FILES:
					if request.FILES['audio']:
						myfile = request.FILES['audio']
						checkListO.audio = myfile
				
				if "canceled" in request.POST:
					checkListO.canceled = True
				else:
					checkListO.canceled = False
				# Комментарий
				comment = ''
				if request.POST["comment"]:
					comment = request.POST["comment"]
				if checkListO.comment != comment:		
					checkListO.comment = comment
				
				# Тип отмены
				if 'select_type_canceled' in request.POST:
					select_type_canceled = request.POST["select_type_canceled"]
					if len(select_type_canceled) > 0:
						checkListO.canceledType = RefTypeCanceledCheckList.objects.get(pk = select_type_canceled)
					else:
						checkListO.canceledType = None
				
				# Комментарий причины отмены
				comment_canceled = ''
				if request.POST["comment_canceled"]:
					comment_canceled = request.POST["comment_canceled"]
				if checkListO.comment_canceled != comment_canceled:		
					checkListO.comment_canceled = comment_canceled
			
				# Отменен
				canceled = False
				if "canceled" in request.POST:
					if request.POST["canceled"]:
						canceled = True
				else:
					canceled = False
				if checkListO.canceled != canceled: 
					checkListO.canceled = canceled

				# Проверен
				cheked_user = False
				if "cheked_user" in request.POST:
					if request.POST["cheked_user"]:
						cheked_user = True
				else:
					cheked_user = False
				if checkListO.cheked != cheked_user: 
					if checkListO.cheked_user == None:
						checkListO.cheked 		= True
						checkListO.cheked_user 	= request.user
				
				checkListO.version_checklist = 2
				
				if profiles.view_checklist == False:
					checkListO.save()
					if "close_to_day" in request.POST:
						if request.POST["close_to_day"]:
							rlkO.archiveDayToDay = request.POST["close_to_day"]
					else:
						rlkO.archiveDayToDay = False
					rlkO.listened = True
					rlkO.save()
					#checkListO = CheckList_op_kors.objects.get(pk= checkListO.id)
					return HttpResponseRedirect('?checkid=' + str(rlkO.id))

			unitObjects = RefUnit.objects.get(id=unitID)
			stafs 		= list(RefStaff.objects.filter(unit = unitObjects).order_by("name"))

		if request.GET.get('checkid', ""):
				checkid = request.GET['checkid']
				start_record_seconds 	= 0
				end_record_seconds		= 0
				start_record_human		= 0
				if len(checkid) != 0:
					rlk 					= DocRLK.objects.get(id = checkid)
					versions				= list()
					data_list 				= list()
					checkListO				= CheckList_op_kors()
					audio_voice_recorder 	= ''

					if CheckList_op_kors.objects.filter(rlk = rlk).count() == 1:
						checkListO 	= CheckList_op_kors.objects.get(rlk = rlk)
						versions 	= get_versions('CheckList_op_kors', checkListO.id)
						audio_voice_recorder = checkListO.audio_voice_recorder
						if checkListO.audio_voice_recorder:
							if len(checkListO.audio_voice_recorder.data_json) > 0:
								data_json   = json.loads(checkListO.audio_voice_recorder.data_json)
								conf 		= data_json['conf']
								prev 		= 0
								text 		= ''
								for inf in conf:
									if inf['start'] - prev > 1:
										data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
										text = inf['data']['word']
										prev = inf['start']
									else:
										text = text + ' ' + inf['data']['word']
										prev = inf['start']
					
					checklist_cvc 	= get_checklist_cvc(rlk.id)
					checklist_cvc_detail = None
					if checklist_cvc != '':
						checklist_cvc_detail = checklist_cvc.detail_chelist()
						if audio_voice_recorder == '':
							audio_voice_recorder = checklist_cvc.records
							start_record_seconds  	= (checklist_cvc.time_start - checklist_cvc.records.date).seconds
							end_record_seconds 		= (checklist_cvc.time_start - checklist_cvc.records.date).seconds + checklist_cvc.duration
							start_record_human    	= time_human((checklist_cvc.time_start - checklist_cvc.records.date).seconds)
						if start_record_seconds == 0 and audio_voice_recorder != '':
							start_record_seconds  	= (checklist_cvc.time_start - checklist_cvc.records.date).seconds
							end_record_seconds 		= (checklist_cvc.time_start - checklist_cvc.records.date).seconds + checklist_cvc.duration
							start_record_human    	= time_human((checklist_cvc.time_start - checklist_cvc.records.date).seconds)
							
					params = {
							'type'              		: 'checklists',
							'nav_selected'				: 5,
							'profiles'					: profiles, 
							'rlk'						: rlk,
							'start_record_seconds'  	: start_record_seconds,
							'end_record_seconds'    	: end_record_seconds,
							'start_record_human'    	: start_record_human,				
							'request'					: request, 
							"checkListO"				: checkListO,
							'data_list'					: data_list, 
							'audio_voice'				: audio_voice_recorder,
							"rlkID"						: str(checkid),
							'versions'					: versions,
							'checklist_cvc'				: checklist_cvc,
							'checklist_cvc_detail'		: checklist_cvc_detail,
							"type_canceled"				: RefTypeCanceledCheckList.objects.all().order_by('name')
						}
					version_checklist = "2"
					if checkListO.version_checklist > 0:
						version_checklist = str(checkListO.version_checklist)
					name = "doc_direction_5_saves" + version_checklist + ".html"
					
					return render(request, 'checklist/' + name, {'params':params})
			
		'''	
		elif request.method == "GET":

			if "checkid" in request.GET:
				checkListO = CheckList_op_kors.objects.get(pk = request.GET["checkid"])
				unitID 	= checkListO.rlk.unit.id
				stafID 	= checkListO.rlk.staff.id
				stafs 	= list(RefStaff.objects.filter(units__in = [unitID]).order_by("name"))
				date 	= checkListO.rlk.dataTime.strftime("%Y-%m-%d")
				rlks 	= DocRLK.objects.filter(unit__id = unitID)
				stafO 	= RefStaff.objects.get(id = stafID)
				rlks 	= rlks.filter(staff = stafO)
				dateIDT = checkListO.rlk.dataTime + DT.timedelta(days=1)
				rlks 	= rlks.filter(dataTime__range = (date, dateIDT))
				rlks 	= rlks.order_by("dataTime")
				rlkID 	= str(checkListO.rlk.id)
		'''
		filtr = {
			'cityID'	: cityID,
			'unitID'	: unitID,
			'staffID'	: stafID,
			'date'		: date,
			'rlkID'		: rlkID
		}

		select = {
			'citys'		: citys,
			'units'		: units,
			'staffs'	: stafs,
			'rlks'		: rlks
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'	: 5,
			'profiles'		: profiles,
			'request'		: request,
			'select'		: select,
			'filtr'			: filtr,
			'doc'			: checkListO.rlk,
			'versions' 		: get_versions('CheckList_op_kors', checkListO.id),
			'checkListO'	: checkListO,
			'audio_voice'	: checkListO.audio_voice_recorder
		}
		return render(request, 'checklist/doc_direction_5_saves.html', {'params': params})
	return HttpResponseRedirect('/')


@csrf_exempt
def op_kors_doc_new(request):
	if request.user.is_authenticated:
		
		cityID 	= ""
		citys 	= RefCity.objects.all().order_by("name")
		
		units 		= RefUnit.objects.filter(buauto = True).filter(name__icontains = "КорсАвто").order_by("name")
		profiles 	= request.user.profiles
		save 		= ""
		unitID 		= ""
		staffID 		= ""
		dateID 		= ""
		rlkID 		= ""
		checkListO 	= ""
		rlks 		= ""
		stafs 		= ""
		date 		= ""
		audio_voice = ''
		rlk			= ""

		if request.method == "POST":
			unitID = request.POST["select_unit"]
			if "select_staff" in request.POST:
				staffID 	= request.POST["select_staff"]
			if "date" in request.POST:
				date = request.POST["date"]
			if "select_rlk" in request.POST:
				rlkID = request.POST["select_rlk"]
				if len(rlkID) > 0:	
					checkListQ = CheckList_op_kors.objects.filter(rlk__id = rlkID)
					if len(checkListQ) > 0:
						checkListO = checkListQ[0]
			
			if len(date) > 0:
				dateID = DT.datetime.strptime(date, "%Y-%m-%d").date()
				dateIDT = dateID + DT.timedelta(days=1)
				unitO = RefUnit.objects.get(id = unitID)
				rlks = DocRLK.objects.filter(unit = unitO)
				if len(staffID) >0:
					stafO = RefStaff.objects.get(id = staffID)
					rlks = rlks.filter(staff = stafO)
				rlks = rlks.filter(dataTime__range = (dateID, dateIDT))
				rlks = rlks.order_by("dataTime")
			
			 
			if 'audio_id' in request.POST:
				audio_id = request.POST["audio_id"]
				if len(audio_id) > 0:
					audio_voice = Records_voice_recorder.objects.get(pk = audio_id)

			if "save" in request.POST:
				user = request.user
			    
				save = request.POST["save"]
				rlkO = DocRLK.objects.get(id= rlkID)
				checkListQ = list(CheckList_op_kors.objects.filter(rlk = rlkO))
				if len(checkListQ) > 0:
					checkListO = checkListQ[0]
				else:
					checkListO = CheckList_op_kors()
					checkListO.dataTimeCreate = DT.datetime.now()

				checkListO.dataTime = DT.datetime.now()
				checkListO.user = user
				checkListO.rlk = rlkO
				
				# Ответы на вопросы
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value = int(request.POST.get(key))
						
						if str(checkListO.__getattribute__(key)) != value:
							checkListO.__setattr__(key, value)
				
				if 'audio' in request.FILES:
					if request.FILES['audio']:
						myfile = request.FILES['audio']
						checkListO.audio = myfile
				
				if 'audio_id' in request.POST:
					audio_id = request.POST["audio_id"]
					if len(audio_id) > 0:
						audio_voice = Records_voice_recorder.objects.get(pk = audio_id)
						checkListO.audio_voice_recorder = audio_voice

				if request.POST["comment"]:
					checkListO.comment = request.POST["comment"]
				
				if "canceled" in request.POST:
					checkListO.canceled = True
				else:
					checkListO.canceled = False
				
				if profiles.view_checklist == False:
					checkListO.save()
					if "close_to_day" in request.POST:
						if request.POST["close_to_day"]:
							rlkO.archiveDayToDay = request.POST["close_to_day"]
					else:
						rlkO.archiveDayToDay = False
					rlkO.listened = True
					rlkO.save()
					checkListO = CheckList_op_kors.objects.get(pk= checkListO.id)
					return HttpResponseRedirect('?checkid=' + str(checkListO.id))

			stafs = list(RefStaff.objects.filter(units__in = [unitID]).order_by("name"))
			
		elif request.method == "GET":
			if "checkid" in request.GET:
				checkListO 	= CheckList_op_kors.objects.get(pk = request.GET["checkid"])
				unitID 		= checkListO.rlk.unit.id
				staffID 	= checkListO.rlk.staff.id
				stafs 		= list(RefStaff.objects.filter(units__in = [unitID]).order_by("name"))
				date 		= checkListO.rlk.dataTime.strftime("%Y-%m-%d")
				rlks 		= DocRLK.objects.filter(unit__id = unitID)
				stafO 		= RefStaff.objects.get(id = staffID)
				rlks 		= rlks.filter(staff = stafO)
				dateIDT 	= checkListO.rlk.dataTime + DT.timedelta(days=1)
				rlks 		= rlks.filter(dataTime__range = (date, dateIDT))
				rlks 		= rlks.order_by("dataTime")
				rlkID 		= str(checkListO.rlk.id)
		
		filtr = {
			'cityID'	: cityID,
			'unitID'	: unitID,
			'staffID'	: staffID,
			'date'		: date,
			'rlkID'		: rlkID
		}

		select = {
			'citys'		: citys,
			'units'		: units,
			'staffs'	: stafs,
			'rlks'		: rlks
		}

		params = {
			'type'          : 'checklists',
			'nav_selected'	: 5,
			'profiles'		: profiles,
			'request'		: request,
			'audio_voice'	: audio_voice,
			'select'		: select,
			'filtr'			: filtr,
			'doc'			: rlk, 
			'checkListO'	: checkListO
		}
		
		'''
		params = {
			'type'           : 'checklists',
			'nav_selected'	: 5,
			'audio_voice'	: audio_voice,
			'profiles'		: profiles, 
			'request'		: request, 
			"checkListO"	: checkListO, 
			"save"			: save ,
			"units"			: units, 
			'unitID'		: unitID, 
			'rlkID'			: rlkID, 
			"stafs"			: stafs, 
			"stafID"		: stafID, 
			"date"			: date, 
			"rlks"			: rlks}
		'''
		return render(request, 'checklist/doc_direction_5.html', {'params':params})
	return HttpResponseRedirect('/')


def op_report(request):
	if request.user.is_authenticated:
		
		citys = RefCity.objects.all().order_by("name")
		city_id 	= ""
		
		date_start 	= ""
		rlks 		= ""
		date 		= ""
		date_end 	= ""
		
		rlks 		= DocRLK.objects.filter(unit__buauto = False)
		
		if request.GET.get('date', ""):
			date 		= request.GET['date']
			date_start 	= DT.datetime.strptime(date, "%Y-%m-%d")
		else:
			date_start 	= DT.datetime.now().replace(day=1, hour=0, minute=0, second=0)
		
		rlks 	= rlks.filter(dataTime__gte = date_start)

		if 'select_city' in request.GET:
			city_id = request.GET['select_city']
			rlks 	= rlks.filter(unit__city__id = city_id) 
		
		if request.GET.get('date_end', ""):
			date_end 	= request.GET['date_end']
			date_ends 	= DT.datetime.strptime(date_end, "%Y-%m-%d") + DT.timedelta(days=1) 
			rlks 		= rlks.filter(dataTime__lte = date_ends)
		
		rlks = rlks.order_by("-dataTime")
		
		answer_list = list()
		units 		= rlks.values('unit').order_by('unit__name').distinct()
		
		for unit in units:
			unit_object 	= RefUnit.objects.get(pk = unit['unit'])
			rlksUnit 		= rlks.filter(unit=unit_object).order_by('staff__name').values('staff').distinct()
			count 			= rlks.filter(unit=unit_object).count()
			countActive 	= rlks.filter(unit=unit_object).filter(archiveDayToDay = False).count()
			countNoActive 	= rlks.filter(unit=unit_object).filter(archiveDayToDay = True).count()
			staff_list 		= list()
			
			staffData = {
				'staff'			: "Не указан",
				'countStaffDoc'	: rlks.filter(unit=unit_object).filter(staff__id = 63).count(),
				'countActive'	: rlks.filter(unit=unit_object).filter(staff__id = 63).filter(archiveDayToDay = False).count(),
				'countNoActive'	: rlks.filter(unit=unit_object).filter(staff__id = 63).filter(archiveDayToDay = True).count()
			}
			staff_list.append(staffData)
			
			for rlksStaff in rlksUnit:
				if rlksStaff['staff'] != None:
					staff 			= RefStaff.objects.get(pk=rlksStaff['staff'])
					countStaffDoc 	= rlks.filter(staff = staff).count()
					staffData = {
						'staff'			: staff.name,
						'countStaffDoc'	: countStaffDoc,
						'countActive'	: rlks.filter(unit=unit_object).filter(staff = staff).filter(archiveDayToDay = False).count(),
						'countNoActive'	: rlks.filter(unit=unit_object).filter(staff = staff).filter(archiveDayToDay = True).count()
					}
					staff_list.append(staffData)
			
			unit_answer = {
				'unit'			: unit_object,
				'staffs'		: staff_list,
				'count'			: count,
				'countActive'	: countActive,
				'countNoActive'	: countNoActive
			}
			answer_list.append(unit_answer)

		filtr = {
			'date' 		: date_start,
			'city_id'	: city_id
		}
		selected = {
			'citys': citys
		}
		params = {
			'type'          : 'checklists',
			'nav_selected'	: 6,
			"rlks"			: rlks,
			'date'			: date,
			'dateEnd'		: date_end,
			'answer_list'	: answer_list,
			'filtr'			: filtr,
			'selected'		: selected
		}
		return render(request, 'checklist/op_report.html', {"params": params})
	return HttpResponseRedirect('/')


###
##
# КорсАвто оценка
def trade_in(request):
	if request.user.is_authenticated:
		
		count_filtr_dop = 0
		countListRecord = 25
		if request.GET.get('select_count', 25):
			countListRecord = int(request.GET.get('select_count', 25))

		profiles = request.user.profiles
		
		unitID 			= ""
		unitsSelect 	= RefUnit.objects.filter(buauto = True).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by("name")
		
		staffID 		= ""
		staffsSelect 	= ""

		staffKKID 		= ""
		staffsKK 		= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		
		trade_in 		= CheckListTradeIn.objects.all()
		nomer 			= ""
		
		dateStart 		= ""
		dateEnd 		= ""

		cityID 		= ""
		citys 		= RefCity.objects.exclude(name = "").order_by("name")

		if request.GET.get('select_city', ""):
			cityID 			= request.GET['select_city']
			trade_in 		= trade_in.filter(rlk__unit__city__id = cityID)
			unitsSelect 	= unitsSelect.filter(city__id = cityID)
		if request.GET.get('nomer', ""):
			nomer 			= request.GET['nomer']
			trade_in 		= trade_in.filter(rlk__nomer__contains = nomer)
		if request.GET.get('select_unit', ""):
			unitID 			= request.GET['select_unit']
			trade_in 		= trade_in.filter(rlk__unit = RefUnit.objects.get(id = unitID))
			staffsSelect 	= list(RefStaff.objects.filter(units__in = [unitID]).order_by('name'))
		if request.GET.get('select_staffKK', ""):
			staffKKID 		= request.GET['select_staffKK']
			trade_in 		= trade_in.filter(user = Profiles.objects.get(id = staffKKID).user)
		if request.GET.get('select_staff', ""):
			staffID 		= request.GET["select_staff"]
			trade_in 		= trade_in.filter(rlk__staff = RefStaff.objects.get(id = staffID))
		if request.GET.get('date_start', ""):
			dateStart 		= request.GET['date_start']
			dateID 			= DT.datetime.strptime(dateStart, "%Y-%m-%d")
			trade_in 		= trade_in.filter(rlk__dataTime__gte = dateID)
		if request.GET.get('date_end', ""):
			dateEnd 		= request.GET['date_end']
			date_ends 		= DT.datetime.strptime(dateEnd, "%Y-%m-%d") + DT.timedelta(days=1) 
			trade_in 		= trade_in.filter(rlk__dataTime__lte = date_ends)
		
		list_filter_or 		= list()
		list_filter_and 	= list()
		for key in request.GET.keys():
			if key.startswith('v') and len(key) == 4:
				value = int(request.GET.get(key))
				
				if value == 1:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					trade_in = trade_in.filter(**kw)
				elif value == 2:
					name_fields = key + '__lte'
					kw = {name_fields: 0}
					list_filter_and.append(Q((name_fields, 0)))
					trade_in = trade_in.filter(**kw)
				elif value == 3:
					name_fields = key + '__gt'
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				elif value == 4:
					name_fields = key + ''
					kw = {name_fields: 0}
					list_filter_or.append(Q((name_fields, 0)))
					#service_in = service_in | service_in.filter(**kw)
				#count_filtr_dop = count_filtr_dop + 1
		
		qyery = Q(result__gte = 0)
		
		#if len(list_filter_and) > 0:
		#		for filter_and in list_filter_and:
		#			qyery.add(filter_and, Q.AND)
		
		if len(list_filter_or) > 0:
			for filter_or in list_filter_or:
				qyery.add(filter_or, Q.OR)
		
		trade_in 			= trade_in.filter(qyery)

		count_filtr_dop = len(list_filter_and) + len(list_filter_or)


		trade_in 	= trade_in.order_by("-rlk__dataTime")
		count 		= trade_in.count()
		
		paginator 	= Paginator(trade_in, countListRecord)
	
		page_number = request.GET.get('page')
		page_obj 	= paginator.get_page(page_number)

		filds_razdel 	= list()
		fields			= list()
		razdel = ''
		meta_fields = CheckListTradeIn._meta.get_fields()
		for meta_field in meta_fields:
			name = meta_field.__dict__['name']
			if name.startswith('v'): 
				
				if name[1:2] != razdel:
					if len(fields) > 0:
						info = {
							'razdel': razdel,
							'fields': fields
						}
						filds_razdel.append(info)
					fields = list()
					razdel = name[1:2]
				
				field = {
					'id' 			: name,
					'razdel' 		: name.replace('v',''),
					'name'			: meta_field.__dict__['verbose_name'],
					'name_human'	: name.replace('v','').replace('_', '.'),
					'value'			: request.GET.get(name, 0)
				}
				fields.append(field)
		if len(fields) > 0:
			info = {
				'razdel': razdel,
				'fields': fields
			}
			filds_razdel.append(info)
			fields = list()
			razdel = razdel

		filtr = {
			'cityID'		: cityID,
			'unitID'		: unitID,
			'staffID'		: staffID,
			'staffKKID'		: staffKKID,
			'nomer'			: nomer,
			'dateStart'		: dateStart, 
			'dateEnd'		: dateEnd
		}

		select = {
			'units'		: unitsSelect,
			'citys'		: citys,
			'staffs'	: staffsSelect,
			'staffsKK'	: staffsKK
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'		: 4,
			'profiles'			: profiles,
			'page_obj'			: page_obj,
			'request'			: request,
			'select'			: select,
			'filtr'				: filtr,
			'count'				: count,
			'fields'			: filds_razdel,
			'count_filtr_dop' 	: count_filtr_dop,
			'select_count'		: countListRecord
		}
		return render(request, 'checklist/trade_in.html', {'params': params})
	return HttpResponseRedirect('/')


@csrf_exempt
def trade_in_doc(request):
	if request.user.is_authenticated:
		
		save 		= False
		checkListO 	= ""
		profiles 	= request.user.profiles
		
		unitID 		= ""
		unitsSelect = RefUnit.objects.filter(buauto = True).order_by("name") 
		
		staffID 		= ""
		staffsSelect 	= ""

		staffIDKK 	= ""
		staffsKK 	= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		cityID 		= ""
		citys 		= RefCity.objects.all().order_by("name")
		
		nomer 	= ""
		
		rlkSelect 	= ""
		rlkID 		= ""
		rlk 		= ""
		date 		= ""
		versions 	= list()

		if request.method == "GET":
			if request.GET.get('checkid', ""):
				checkid = request.GET['checkid']
				if len(checkid) != 0:
					rlks 			= CheckListTradeIn.objects.get(id = checkid)
					checkListO 		= rlks
					rlkID 			= str(rlks.rlk.id)
					rlk  			= DocRLK.objects.get(pk=rlkID)
					unitID 			= str(rlks.rlk.unit.id)
					cityID 			= str(rlks.rlk.unit.city.id)
					staffID 		= rlks.rlk.staff.id
					nomer 			= rlks.rlk.nomer
					staffsSelect 	= list(RefStaff.objects.filter(units__in = [rlks.rlk.unit.id]).order_by('name'))
					date 			= rlks.rlk.dataTime.date()
					dateID 			= date
					dateIDT 		= dateID + DT.timedelta(days=1)
					date 			= date.strftime("%Y-%m-%d")
					rlkSelect 		= DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).annotate(check = Count('rlkCheckTradeIn', distinct=True))
					rlkSelect 		= list(rlkSelect.filter(unit = RefUnit.objects.get(id = unitID)).filter(staff = RefStaff.objects.get(id=staffID)))
					versions		= get_versions('CheckListTradeIn', checkid)
		else:
			if request.POST.get('select_city', ""):
				cityID 			= request.POST['select_city']
				#staffsSelect 	= list(RefStaff.objects.filter(units__buauto = True).filter(units__city__id = cityID).order_by('name'))
				city 			= RefCity.objects.get(pk = cityID) 
				#unit 			= RefUnit.objects.get(pk = unit_id)
				staffsSelect    = DocRLK.objects.filter(unit__city = city).filter(Q(type_id = 7) | Q(type = None)).values('staff').distinct().order_by('staff')
			if request.POST.get('select_unit', ""):
				unitID 			= request.POST['select_unit']
				staffsSelect 	= list(RefStaff.objects.filter(unit__buauto = True).order_by('name'))
			if request.POST.get('select_staff', ""):
				staffID 		= request.POST["select_staff"]
			if request.POST.get('date', ""):
				date 			= request.POST["date"]
				dateID 			= DT.datetime.strptime(date, "%Y-%m-%d").date()
				dateIDT 		= dateID + DT.timedelta(days=1)
				if len(staffID) >0:
					rlkSelect = DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).annotate(check = Count('rlkCheckTradeIn', distinct=True))
					rlkSelect = list(rlkSelect.filter(unit__in = RefUnit.objects.filter(city__id = cityID)).filter(staff = RefStaff.objects.get(id=staffID)))	
				
			if request.POST.get('select_rlk', ""):
				rlkID 		= request.POST['select_rlk']
				rlk 		= DocRLK.objects.get(pk=rlkID)
				versions 	= get_versions('CheckListTradeIn', rlkID)
			
			if request.POST.get('save', ""):
				save = request.POST["save"]
				if save:
					check = request.GET.get('checkid', "")
					if len(check) > 0:
						checkListServiceOut = CheckListTradeIn.objects.get(pk = check)
						
					comment = ''
					if request.POST["comment"]:
						comment = request.POST["comment"]
					
					if checkListServiceOut.comment != comment:
						checkListServiceOut.comment = comment 
					
					# Ответы на вопросы
					for key in request.POST.keys():
						if key.startswith('v') and len(key) == 4:
							value = int(request.POST.get(key))
							
							if str(checkListServiceOut.__getattribute__(key)) != value:
								checkListServiceOut.__setattr__(key, value)
					
					if "canceled" in request.POST:
						if request.POST["canceled"]:
							checkListServiceOut.canceled = True
						else:
							checkListServiceOut.canceled = False
					else:
						checkListServiceOut.canceled = False

					if 'audio' in request.FILES:
						if request.FILES['audio']:
							myfile = request.FILES['audio']
							checkListServiceOut.audio = myfile

					checkListServiceOut.save()
					return HttpResponseRedirect('/checklists/glav/trade_in')

		filtr = {
			'cityID'	: cityID,
			'unitID'	: unitID,
			'staffID'	: staffID,
			'nomer'		: nomer,
			'date'		: date,
			'rlkID'		: rlkID
		}

		select = {
			'citys'		: citys,
			'units'		: unitsSelect,
			'staffs'	: staffsSelect,
			'rlks'		: rlkSelect, 
			'rlkDoc'	: rlk
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'	: 4,
			'profiles'		: profiles,
			'request'		: request,
			'select'		: select,
			'filtr'			: filtr,
			'doc'			: rlk,
			'checkListO'	: checkListO,
			'versions'		: versions
		}
		return render(request, 'checklist/doc_direction_4_saves.html', {'params': params})
	else:
		HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')


@csrf_exempt
def trade_in_new(request):
	if request.user.is_authenticated:
		save 		= False
		checkListO 	= ""
		profiles 	= request.user.profiles
		
		unitID 		= ""
		unitsSelect = RefUnit.objects.filter(buauto = True).order_by("name") 
		
		staffID 		= ""
		staffsSelect 	= ""

		staffIDKK 	= ""
		staffsKK 	= Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
		
		cityID 	= ""
		citys 	= RefCity.objects.all().order_by("name")
		
		nomer 		= ""
		rlkSelect 	= ""
		rlkID 		= ""
		rlk 		= ""

		date = ""
		
		if request.POST.get('select_city', ""):
			cityID 			= request.POST['select_city']
			#staffsSelect 	= list(RefStaff.objects.filter(units__buauto = True).filter(units__city__id = cityID).order_by('name'))
			cityID 			= request.POST['select_city']
			#staffsSelect 	= list(RefStaff.objects.filter(units__buauto = True).filter(units__city__id = cityID).order_by('name'))
			city 			= RefCity.objects.get(pk = cityID) 
			#unit 			= RefUnit.objects.get(pk = unit_id)
			staffsSelect   	= DocRLK.objects.filter(unit__city = city).filter(Q(type_id = 7) | Q(type = None)).values('staff__id', 'staff__name').distinct().order_by('staff__name')
		if request.POST.get('select_unit', ""):
			unitID 			= request.POST['select_unit']
			#staffsSelect 	= list(RefStaff.objects.filter(units__buauto = True).order_by('name'))
		if request.POST.get('select_staff', ""):
			staffID 		= request.POST["select_staff"]
		if request.POST.get('date', ""):
			date 		= request.POST["date"]
			dateID 		= DT.datetime.strptime(date, "%Y-%m-%d").date()
			dateIDT 	= dateID + DT.timedelta(days=1)
			if len(staffID) >0:
				rlkSelect = DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).annotate(check = Count('rlkCheckTradeIn', distinct=True))
				rlkSelect = list(rlkSelect.filter(unit__in = RefUnit.objects.filter(city__id = cityID)).filter(staff = RefStaff.objects.get(id=staffID)))	
			
		if request.POST.get('select_rlk', ""):
			rlkID 	= request.POST['select_rlk']
			rlk 	= DocRLK.objects.get(pk = rlkID)
			if CheckListTradeIn.objects.filter(rlk = DocRLK.objects.get(pk = rlkID)).count() > 0:
				checkListO = CheckListTradeIn.objects.filter(rlk = DocRLK.objects.get(pk = rlkID))[0]
		
		if request.POST.get('save', ""):
			save = request.POST["save"]
			if save:
				if 'check' in request.POST:
					check = request.POST['check']
					if len(check) > 0:
						checkListServiceOut = CheckListTradeIn.objects.get(pk = check)
					else:
						checkListServiceOut = CheckListTradeIn()
				else:
					checkListServiceOut = CheckListTradeIn()

				checkListServiceOut.dataTimeCreate 	= DT.datetime.now()
				checkListServiceOut.dataTime 		= DT.datetime.now()
				checkListServiceOut.user 			= request.user
				checkListServiceOut.rlk 			= DocRLK.objects.get(id = rlkID)
				
				if request.POST["comment"]:
					checkListServiceOut.comment = request.POST["comment"] 
				
				# Ответы на вопросы
				for key in request.POST.keys():
					if key.startswith('v') and len(key) == 4:
						value = int(request.POST.get(key))
						
						if str(checkListServiceOut.__getattribute__(key)) != value:
							checkListServiceOut.__setattr__(key, value)
				
				if request.POST.get('canceled', ""):
					checkListServiceOut.canceled = True
				else:
					checkListServiceOut.canceled = False

				if 'audio' in request.FILES:
					if request.FILES['audio']:
						myfile = request.FILES['audio']
						checkListServiceOut.audio = myfile

				checkListServiceOut.save()
				return HttpResponseRedirect('/checklists/glav/trade_in')

		filtr = {
			'cityID'	: cityID,
			'unitID'	: unitID,
			'staffID'	: staffID,
			'nomer'		: nomer,
			'date'		: date,
			'rlkID'		: rlkID
		}

		select = {
			'citys'		: citys,
			'units'		: unitsSelect,
			'staffs'	: staffsSelect,
			'rlks'		: rlkSelect
		}

		params = {
			'type'              : 'checklists',
			'nav_selected'	: 4,
			'profiles'		: profiles,
			'request'		: request,
			'select'		: select,
			'filtr'			: filtr,
			'doc'			: rlk, 
			'checkListO'	: checkListO
		}
		return render(request, 'checklist/doc_direction_4.html', {'params':params})
	else:
		HttpResponseRedirect('../listchecklist')
	return HttpResponseRedirect('/')


####Новый функционал

@csrf_exempt
def new_check_list(request):
	if request.user.is_authenticated:
		params = {}
		if request.method == "GET":
			if not 'city' in request.GET:
				citys 	= RefCity.objects.filter(area__id__gte = 0).order_by('name')
				params 	= {
					'type'	: 'checklists', 
	       			'citys'	: citys, 
					'step'	: 1}
				return render(request, 'checklist/new_check_list.html', {'params':params})
			if not 'direction' in request.GET: 
				city_id = request.GET['city']
				city = RefCity.objects.get(pk = city_id)	
				params 			= {'type': 'checklists', 'city_name': city.name, 'step': 2}
				return render(request, 'checklist/new_check_list.html', {'params':params})
			if not 'unit' in request.GET: 
				city_id 		= request.GET['city']
				city 			= RefCity.objects.get(pk = city_id)	
				direction_id 	= request.GET['direction']
				direction_name 	= get_direction_name(direction_id)
				units 			= get_inits(city_id, direction_id)
				params 			= {'type': 'checklists', 'city_name': city.name, 'direction_id':direction_id, 'direction_name':direction_name, 'step': 3, 'units': units}
				return render(request, 'checklist/new_check_list.html', {'params':params})
			if not 'date' in request.GET: 
				city_id 		= request.GET['city']
				city 			= RefCity.objects.get(pk = city_id)	
				direction_id 	= request.GET['direction']
				direction_name 	= get_direction_name(direction_id)
				unit_id 		= request.GET['unit']
				unit 			= RefUnit.objects.get(pk = unit_id)
				days 			= get_days(direction_id, unit_id)
				params 			= {'type': 'checklists', 'city_name': city.name, 'direction_id':direction_id, 'direction_name':direction_name, 'unit': unit, 'days':days, 'step': 4}
				return render(request, 'checklist/new_check_list.html', {'params':params})
			if not 'staff' in request.GET: 
				city_id 		= request.GET['city']
				city 			= RefCity.objects.get(pk = city_id)	
				direction_id 	= request.GET['direction']
				direction_name 	= get_direction_name(direction_id)
				unit_id 		= request.GET['unit']
				unit 			= RefUnit.objects.get(pk = unit_id)
				date 			= request.GET['date']
				staffs 			= get_stafs(direction_id, unit_id, date)
				params 			= {'type': 'checklists', 'city_name': city.name, 'direction_id':direction_id, 'direction_name':direction_name, 'date': date, 'unit': unit, 'staffs':staffs, 'step': 5}
				return render(request, 'checklist/new_check_list.html', {'params':params})
			if not 'docs' in request.GET: 
				city_id 		= request.GET['city']
				city 			= RefCity.objects.get(pk = city_id)	
				direction_id 	= request.GET['direction']
				direction_name 	= get_direction_name(direction_id)
				unit_id 		= request.GET['unit']
				unit 			= RefUnit.objects.get(pk = unit_id)
				date 			= request.GET['date']
				staff_id 		= request.GET['staff']
				staff 			= RefStaff.objects.get(pk = staff_id)
				docs 			= get_docs(direction_id, unit_id, date, staff_id)
				audios			= get_audio(date, staff)
				params = {'type': 'checklists', 'city_name': city.name, 
					'direction_id':direction_id, 
					'direction_name':direction_name, 
					'date': date, 
					'unit': unit, 
					'staff': staff, 
					'staff_id':staff_id, 
					'docs': docs,
					'audios': audios, 
					'step': 6
					}
				return render(request, 'checklist/new_check_list.html', {'params':params})
		return render(request, 'checklist/new_check_list.html')	
	else:
		return HttpResponseRedirect('/')


####Служебные функции
def get_direction_name(direction_id):
	if direction_id == '1':
		return 'Отдел продаж'
	elif direction_id == '2':
		return 'Сервис (прием авто)'
	elif direction_id == '3':
		return 'Сервис (выдача авто)'
	elif direction_id == '4':
		return 'Отдел оценки (Корс-авто)'
	elif direction_id == '5':
		return 'Отдел продаж (Корс-авто)'


def get_inits(city_id, direction_id):
	if direction_id == '1':
		units = DocRLK.objects.filter(unit__buauto = False).filter(unit__city__id = city_id).values('unit', 'unit__name', 'unit__city__id').distinct().order_by('unit__name')
		return units
	elif direction_id == '2' or direction_id == '3':
		units = DocZN.objects.filter(unit__city__id = city_id).filter(active = True).values('unit', 'unit__name', 'unit__city__id').distinct().order_by('unit__name')
		return units
	elif direction_id == '4':
		units = DocRLK.objects.filter(unit__buauto = True).filter(type_id = 7).filter(unit__city__id = city_id).values('unit', 'unit__name', 'unit__city__id').distinct().order_by('unit__name')
		return units
	elif direction_id == '5':
		units = DocRLK.objects.filter(unit__buauto = True).filter(unit__city__id = city_id).values('unit', 'unit__name', 'unit__city__id').distinct().order_by('unit__name')
		return units


def get_days(direction_id, unit_id):
	date_end = DT.datetime.now().date()
	date_start = date_end - DT.timedelta(days=30)
	if direction_id == "1":
		days = DocRLK.objects.filter(unit_id = unit_id).filter(staff__isnull = False).exclude(staff__name = '').filter(dataTime__range = (date_start, date_end)).annotate(zn = Count(Subquery(CheckList.objects.filter(rlk_id=OuterRef(name='id')).values('id')[:1], output_field=models.IntegerField()))).values(days=TruncDate('dataTime')).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('-days')
	elif direction_id == "2":
		days = DocZN.objects.filter(unit_id = unit_id).filter(active = True).filter(master__isnull = False).exclude(master__name = '').filter(dataTime__range = (date_start, date_end)).annotate(zn = Count(Subquery(CheckListServiceIn.objects.filter(zn_id=OuterRef(name='id')).values('id')[:1], output_field=models.IntegerField()))).values(days=TruncDate('dataTime')).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).order_by('-days')
	elif direction_id == '3':
		days = DocZN.objects.filter(unit_id = unit_id).filter(active = True).filter(master__isnull = False).exclude(master__name = '').filter(dataTime__range = (date_start, date_end)).annotate(zn = Count(Subquery(CheckListServiceOut.objects.filter(zn_id=OuterRef(name='id')).values('id')[:1], output_field=models.IntegerField()))).values(days=TruncDate('dataTime')).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).order_by('-days')
	elif direction_id == "4":
		#days = DocRLK.objects.filter(unit_id = unit_id).filter(type_id = 7).filter(staff__isnull = False).exclude(staff__name = '').filter(dataTime__range = (date_start, date_end)).annotate(zn = Count(Subquery(CheckListTradeIn.objects.filter(rlk_id=OuterRef(name='id')).values('id'), output_field=models.IntegerField()))).values(days=TruncDate('dataTime')).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('-days')
		unit = RefUnit.objects.get(pk = unit_id)
		days = DocRLK.objects.filter(unit__city = unit.city).filter(Q(type_id = 7) | Q(type = None)).filter(staff__isnull = False).exclude(staff__name = '').filter(dataTime__range = (date_start, date_end)).annotate(zn = Count(Subquery(CheckListTradeIn.objects.filter(rlk_id=OuterRef(name='id')).values('id')[:1], output_field=models.IntegerField()))).values(days=TruncDate('dataTime')).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('-days')
	elif direction_id == "5":
		days = DocRLK.objects.filter(unit_id = unit_id).filter(staff__isnull = False).exclude(staff__name = '').filter(dataTime__range = (date_start, date_end)).annotate(zn = Count(Subquery(CheckList_op_kors.objects.filter(rlk_id=OuterRef(name='id')).values('id')[:1], output_field=models.IntegerField()))).values(days=TruncDate('dataTime')).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('-days')
	
	return days
	

def get_stafs(direction_id, unit_id, date):
	
	if len(date) > 0:
		dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
	else:
		dateID	= DT.datetime.now().strptime(date, "%Y-%m-%d").date()

	dateIDT = dateID + DT.timedelta(days=1)
	
	if direction_id == "1":
		staffs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).values('staff', 'staff__name').annotate(zn = Count(Subquery(CheckList.objects.filter(rlk_id=OuterRef(name='id')).values('id'), output_field=models.IntegerField()))).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('staff__name')
	elif direction_id == '2':
		staffs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).filter(active = True).values(staff = F('master'), staff__name =F('master__name')).annotate(zn = Count(Subquery(CheckListServiceIn.objects.filter(zn_id=OuterRef(name='id')).values('id'), output_field=models.IntegerField()))).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('staff__name')
	elif direction_id == '3':
		staffs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).filter(active = True).values(staff = F('master'), staff__name =F('master__name')).annotate(zn = Count(Subquery(CheckListServiceOut.objects.filter(zn_id=OuterRef(name='id')).values('id'), output_field=models.IntegerField()))).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('staff__name')
	elif direction_id == "4":
		unit = RefUnit.objects.get(pk = unit_id)
		staffs = DocRLK.objects.filter(unit__city = unit.city).filter(Q(type_id = 7) | Q(type = None)).filter(dataTime__range = (dateID, dateIDT)).values('staff', 'staff__name').annotate(zn = Count(Subquery(CheckListTradeIn.objects.filter(rlk_id=OuterRef(name='id')).values('id'), output_field=models.IntegerField()))).annotate(count_docs=Count('id')).annotate(count_listened=F('zn')).distinct().order_by('staff__name')
	elif direction_id == "5":
		staffs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).values('staff', 'staff__name').annotate(zn = Count(Subquery(CheckList_op_kors.objects.filter(rlk_id=OuterRef(name='id')).values('id'), output_field=models.IntegerField()))).annotate(count_listened=F('zn')).annotate(count_docs=Count('id')).distinct().order_by('staff__name')

	return staffs


def get_docs(direction_id, unit_id, date, staff_id):
	dateID 	= DT.datetime.strptime(date, "%Y-%m-%d").date()
	dateIDT = dateID + DT.timedelta(days=1)
	answer 	= list()
	if direction_id == "1":
		docs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).filter(staff_id = staff_id).order_by('dataTime')
		for doc in docs:
			check_lists = CheckList.objects.filter(rlk = doc)
			check_list = ''
			if len(check_lists) > 0:
				check_list = check_lists[0]
			doc_info = {
				'check_list': check_list,
				'doc'		: doc,
				'events'	: DocRLKEvents.objects.filter(rlk = doc).order_by('dataTime')
			}
			answer.append(doc_info) 
	elif direction_id == "2":	
		docs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).filter(active = True).filter(typeRemont__tizer = True).filter(master_id = staff_id).order_by('dateStart', 'dataTime')
		for doc in docs:
			check_lists = CheckListServiceIn.objects.filter(zn = doc)
			check_list = ''
			if len(check_lists) > 0:
				check_list = check_lists[0]
			doc_info = {
				'check_list': check_list,
				'doc': doc,
				'works': DocZNWork.objects.filter(zn = doc),
				'products': DocZNProduct.objects.filter(zn = doc)
			}
			answer.append(doc_info)
	elif direction_id == '3':
		docs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).filter(active = True).filter(typeRemont__tizer = True).filter(master_id = staff_id).order_by('dateStart', 'dataTime')
		for doc in docs:
			check_lists = CheckListServiceOut.objects.filter(zn = doc)
			check_list = ''
			if len(check_lists) > 0:
				check_list = check_lists[0]
			doc_info = {
				'check_list': check_list,
				'doc': doc,
				'works': DocZNWork.objects.filter(zn = doc),
				'products': DocZNProduct.objects.filter(zn = doc)
			}
			answer.append(doc_info)
	elif direction_id == "4":
		docs 	= DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).filter(staff_id = staff_id).order_by('dataTime')
		for doc in docs:
			check_lists = CheckListTradeIn.objects.filter(rlk = doc)
			check_list = ''
			if len(check_lists) > 0:
				check_list = check_lists[0]
			doc_info = {
				'check_list': check_list,
				'doc': doc
			}
			answer.append(doc_info) 
	elif direction_id == "5":
		docs 	= DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).filter(staff_id = staff_id).order_by('dataTime')
		for doc in docs:
			check_lists = CheckList_op_kors.objects.filter(rlk = doc)
			check_list = ''
			if len(check_lists) > 0:
				check_list = check_lists[0]
			doc_info = {
				'check_list': check_list,
				'doc': doc
			}
			answer.append(doc_info)
	
	return answer


def get_docs_report(direction_id, unit_id, date, staff_id):
	
	# тут нужна полная дата
	date_python = DT.datetime.strptime(date, "%Y-%m-%d")
	
	# здесь достаточно дня
	dateID 		= DT.datetime.strptime(date, "%Y-%m-%d").date()
	dateIDT = dateID + DT.timedelta(days=1)
	
	answer 	= list()
	
	sounds = 0
	
	# Если берем информацию по сотрудникам то будем проверять есть ли загруженные записи
	if staff_id != None:
		user_domain_login = RefStaff.objects.get(pk= staff_id).domain_login.lower() # при сравнении доменных имен все сравниваем в нижнем регистре так как в домене заведены абы как
		if len(user_domain_login) > 0:
			sounds 		= Records_voice_recorder.objects.filter(user__username__iexact = user_domain_login).filter(date__range = (date_python, date_python.replace(hour=23, minute=59, second=59))).count()	
	
	if direction_id == "1":
		if staff_id == None:
			docs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).exclude(staff = None)
		else:
			docs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).filter(staff_id = staff_id).exclude(staff = None)
		
		# Подзапрос на количество чек листов
		subquery    	= Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField()) 
		# 
		
		# Подзапрос на сумму чек листа по документу 
		subquery_sum    = Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1], output_field = models.IntegerField())
		# 
		
		docs        	= docs.annotate(check = Count(subquery))
		docs        	= docs.annotate(check_percent = Sum(subquery_sum))
		check 			= docs.aggregate(Sum('check'))['check__sum']
		percent_check	= docs.aggregate(Sum('check_percent'))['check_percent__sum']
		
		if check == None:
			check = 0
		count = docs.count()
		
		percent_check_sum = 0  

		if percent_check == None:
			percent_check = 0
		else:
			percent_check_sum 	= percent_check
			percent_check 		= int(percent_check / check)

		if count > 0:
			percent = int(check / count * 100)
		else:
			percent = 0	
		
		doc_info 	= {
			'direction'			: direction_id,
			'date'				: dateID,
			'docs' 				: count,
			'check' 			: check,
			'percent' 			: percent,
			'percent_check' 	: percent_check,
			'percent_check_sum' : percent_check_sum,
			'sounds'			: sounds
		} 

		return doc_info		
	
	elif direction_id == "2":	
		if staff_id == None:
			docs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).exclude(master = None).filter(typeRemont__tizer = True).filter(active = True).order_by('dateStart', 'dataTime')
		else:
			docs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).exclude(master = None).filter(typeRemont__tizer = True).filter(active = True).filter(master_id = staff_id).order_by('dateStart', 'dataTime')	
		
		# Подзапрос на количество чек листов
		subquery    	= Subquery(CheckListServiceIn.objects.filter(zn_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField()) 
		# 
		
		# Подзапрос на сумму чек листа по документу 
		subquery_sum    = Subquery(CheckListServiceIn.objects.filter(zn_id = OuterRef(name='id')).values('result')[:1], output_field = models.IntegerField())
		# 
		
		docs        	= docs.annotate(check = Count(subquery))
		docs        	= docs.annotate(check_percent = Sum(subquery_sum))
		check 			= docs.aggregate(Sum('check'))['check__sum']
		percent_check	= docs.aggregate(Sum('check_percent'))['check_percent__sum']
		
		if check == None:
			check = 0
		count = docs.count()
		
		percent_check_sum = 0  

		if percent_check == None:
			percent_check = 0
		else:
			percent_check_sum 	= percent_check
			percent_check 		= int(percent_check / check)

		if count > 0:
			percent = int(check / count * 100)
		else:
			percent = 0	
		
		doc_info 	= {
			'direction'			: direction_id,
			'date'				: dateID,
			'docs' 				: count,
			'check' 			: check,
			'percent' 			: percent,
			'percent_check' 	: percent_check,
			'percent_check_sum' : percent_check_sum,
			'sounds'			: sounds
		} 
 
		return doc_info

	elif direction_id == '3':
		if staff_id == None:
			docs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).exclude(master = None).filter(typeRemont__tizer = True).filter(active = True).order_by('dateStart', 'dataTime')
		else:
			docs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (dateID, dateIDT)).exclude(masterOut = None).filter(typeRemont__tizer = True).filter(active = True).filter(masterOut_id = staff_id).order_by('dateStart', 'dataTime')	
		
		# Подзапрос на количество чек листов
		subquery    	= Subquery(CheckListServiceOut.objects.filter(zn_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField()) 
		# 
		
		# Подзапрос на сумму чек листа по документу 
		subquery_sum    = Subquery(CheckListServiceOut.objects.filter(zn_id = OuterRef(name='id')).values('result')[:1], output_field = models.IntegerField())
		# 
		
		docs        	= docs.annotate(check = Count(subquery))
		docs        	= docs.annotate(check_percent = Sum(subquery_sum))
		check 			= docs.aggregate(Sum('check'))['check__sum']
		percent_check	= docs.aggregate(Sum('check_percent'))['check_percent__sum']
		
		if check == None:
			check = 0
		count = docs.count()
		
		percent_check_sum = 0  

		if percent_check == None:
			percent_check = 0
		else:
			percent_check_sum 	= percent_check
			percent_check 		= int(percent_check / check)

		if count > 0:
			percent = int(check / count * 100)
		else:
			percent = 0	
		
		doc_info 	= {
			'direction'			: direction_id,
			'date'				: dateID,
			'docs' 				: count,
			'check' 			: check,
			'percent' 			: percent,
			'percent_check' 	: percent_check,
			'percent_check_sum' : percent_check_sum,
			'sounds'			: sounds
		} 

		return doc_info

	elif direction_id == "4":
		city_id = RefUnit.objects.get(pk = unit_id).city.id
		if staff_id == None:
			docs = DocRLK.objects.filter(unit__buauto = True).filter(type_id = 7).filter(unit__city__id = city_id).filter(dataTime__range = (dateID, dateIDT)).exclude(staff = None)
		else:
			docs = DocRLK.objects.filter(unit__buauto = True).filter(type_id = 7).filter(unit__city__id = city_id).filter(dataTime__range = (dateID, dateIDT)).filter(staff_id = staff_id).exclude(staff = None)
		
		# Подзапрос на количество чек листов
		subquery    	= Subquery(CheckListTradeIn.objects.filter(rlk_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField()) 
		# 
		
		# Подзапрос на сумму чек листа по документу 
		subquery_sum    = Subquery(CheckListTradeIn.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1], output_field = models.IntegerField())
		# 
		
		docs        	= docs.annotate(check = Count(subquery))
		docs        	= docs.annotate(check_percent = Sum(subquery_sum))
		check 			= docs.aggregate(Sum('check'))['check__sum']
		percent_check	= docs.aggregate(Sum('check_percent'))['check_percent__sum']
		
		if check == None:
			check = 0
		count = docs.count()
		
		percent_check_sum = 0  

		if percent_check == None:
			percent_check = 0
		else:
			percent_check_sum 	= percent_check
			percent_check 		= int(percent_check / check)

		if count > 0:
			percent = int(check / count * 100)
		else:
			percent = 0	
		
		doc_info 	= {
			'direction'			: direction_id,
			'date'				: dateID,
			'docs' 				: count,
			'check' 			: check,
			'percent' 			: percent,
			'percent_check' 	: percent_check,
			'percent_check_sum' : percent_check_sum,
			'sounds'			: sounds
		}

		return doc_info	

	elif direction_id == "5":
		if staff_id == None:
			docs = DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).exclude(staff = None)
		else:
			docs = DocRLK.objects.filter(dataTime__range = (dateID, dateIDT)).filter(staff_id = staff_id).exclude(staff = None)
		# Подзапрос на количество чек листов
		subquery    	= Subquery(CheckList_op_kors.objects.filter(rlk_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField()) 
		# 
		
		# Подзапрос на сумму чек листа по документу 
		subquery_sum    = Subquery(CheckList_op_kors.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1], output_field = models.IntegerField())
		# 
		
		docs        	= docs.annotate(check = Count(subquery))
		docs        	= docs.annotate(check_percent = Sum(subquery_sum))
		check 			= docs.aggregate(Sum('check'))['check__sum']
		percent_check	= docs.aggregate(Sum('check_percent'))['check_percent__sum']
		
		if check == None:
			check = 0
		count = docs.count()
		
		percent_check_sum = 0  

		if percent_check == None:
			percent_check = 0
		else:
			percent_check_sum 	= percent_check
			percent_check 		= int(percent_check / check)

		if count > 0:
			percent = int(check / count * 100)
		else:
			percent = 0	
		
		doc_info 	= {
			'direction'			: direction_id,
			'date'				: dateID,
			'docs' 				: count,
			'check' 			: check,
			'percent' 			: percent,
			'percent_check' 	: percent_check,
			'percent_check_sum' : percent_check_sum,
			'sounds'			: sounds
		}

		return doc_info

	return answer


def get_stafs_report(direction_id, unit_id, date):

	date_period = date
	date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
	if date_period.month > 11:
		month_end	= 1
		year_end 	= date_period.year + 1
	else:
		month_end	= date_period.month + 1
		year_end 	= date_period.year
	date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
	
	if direction_id == "1":
		unit = RefUnit.objects.get(pk = unit_id)
		ib = unit.ib
		if ib.base.find('alfa') > 0:
			staffs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (date_start, date_end)).exclude(staff = None).filter(type__id = 20).values('staff', 'staff__name', 'type__name').distinct().order_by('staff__name')
		else: 
			staffs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (date_start, date_end)).exclude(staff = None).filter(type__id = 2).values('staff', 'staff__name', 'type__name').distinct().order_by('staff__name')

	elif direction_id == '2':
		staffs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (date_start, date_end)).exclude(master = None).filter(typeRemont__tizer = True).filter(active = True).values(staff = F('master'), staff__name =F('master__name')).distinct().order_by('staff__name')
	elif direction_id == '3':
		staffs = DocZN.objects.filter(unit_id = unit_id).filter(dataTime__range = (date_start, date_end)).exclude(masterOut = None).filter(typeRemont__tizer = True).filter(active = True).values(staff = F('masterOut'), staff__name =F('masterOut__name')).distinct().order_by('staff__name')
	elif direction_id == "4":
		unit = RefUnit.objects.get(pk = unit_id)
		staffs = DocRLK.objects.filter(unit__city = unit.city).filter(Q(type_id = 7) | Q(type = None)).filter(dataTime__range = (date_start, date_end)).values('staff', 'staff__name').distinct().order_by('staff__name')
	elif direction_id == "5":
		staffs = DocRLK.objects.filter(unit_id = unit_id).filter(dataTime__range = (date_start, date_end)).values('staff', 'staff__name').distinct().order_by('staff__name')

	return staffs


def get_staff_kk(direction_id, date, staff_id):
	
	mount_dict 	= get_date_start_end(date)
	# здесь достаточно дня
	date_start 	= mount_dict['date_start']
	date_end 	= mount_dict['date_end']
	
	answer 	= list()
	
	doc_info = ''
	
	if direction_id == "1":
		if staff_id == None:
			doc_info = CheckList.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).values('user', 'user__first_name', 'user__last_name').distinct().order_by('user__last_name')
		else:
			doc_info = CheckList.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user__id = staff_id).annotate(doc__unit = F('rlk__unit'), doc__unit__name = F('rlk__unit__name')).values('doc__unit', 'doc__unit__name').distinct().order_by('rlk__unit')
		return doc_info		
	
	elif direction_id == "2":	
		if staff_id == None:
			doc_info = CheckListServiceIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).values('user', 'user__first_name', 'user__last_name').distinct().order_by('user__last_name')
		else:
			doc_info = CheckListServiceIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user__id = staff_id).annotate(doc__unit =F('zn__unit'), doc__unit__name = F('zn__unit__name')).values('doc__unit', 'doc__unit__name').distinct().order_by('zn__unit')
		return doc_info	
 

	elif direction_id == '3':
		if staff_id == None:
			doc_info = CheckListServiceOut.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).values('user', 'user__first_name', 'user__last_name').distinct().order_by('user__last_name')
		else:
			doc_info = CheckListServiceOut.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user__id = staff_id).annotate(doc__unit =F('zn__unit'), doc__unit__name = F('zn__unit__name')).values('doc__unit', 'doc__unit__name').distinct().order_by('zn__unit')
		return doc_info	

		return doc_info

	elif direction_id == "4":
		if staff_id == None:
			doc_info = CheckListTradeIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).values('user', 'user__first_name', 'user__last_name').distinct().order_by('user__last_name')
		else:
			doc_info = CheckListTradeIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user__id = staff_id).annotate(doc__unit = F('rlk__unit'), doc__unit__name = F('rlk__unit__name')).values('doc__unit', 'doc__unit__name').distinct().order_by('rlk__unit')
		return doc_info	

	elif direction_id == "5":
		if staff_id == None:
			doc_info = CheckList_op_kors.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).values('user', 'user__first_name', 'user__last_name').distinct().order_by('user__last_name')
		else:
			doc_info = CheckList_op_kors.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user__id = staff_id).annotate(doc__unit = F('rlk__unit'), doc__unit__name = F('rlk__unit__name')).values('doc__unit', 'doc__unit__name').distinct().order_by('rlk__unit')
		return doc_info	

		return doc_info

	return answer


def get_staff_kk_doc(direction_id, date, staff_id, unit_id):
	
	date_start 	= date
	date_end 	= date.replace(hour = 23, minute = 59, second = 59)
	
	doc_info = 0
	
	if direction_id == "1":
		if unit_id == None:
			doc_info = CheckList.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).count()
		else:
			doc_info = CheckList.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).filter(rlk__unit__id = unit_id).count()
		return doc_info		
	
	elif direction_id == "2":	
		if unit_id == None:
			doc_info = CheckListServiceIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).count()
		else:
			doc_info = CheckListServiceIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).filter(zn__unit__id = unit_id).count()
		return doc_info	

	elif direction_id == '3':
		if unit_id == None:
			doc_info = CheckListServiceOut.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).count()
		else:
			doc_info = CheckListServiceOut.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).filter(zn__unit__id = unit_id).count()
		return doc_info	

	elif direction_id == "4":
		if unit_id == None:
			doc_info = CheckListTradeIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).count()
		else:
			doc_info = CheckListTradeIn.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).filter(rlk__unit__id = unit_id).count()
		return doc_info

	elif direction_id == "5":
		if unit_id == None:
			doc_info = CheckList_op_kors.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).count()
		else:
			doc_info = CheckList_op_kors.objects.filter(dataTimeCreate__range = (date_start, date_end)).filter(canceled = False).filter(user = staff_id).filter(rlk__unit__id = unit_id).count()
		return doc_info

	return 0


def get_audio(date, user):
	
	dateID = DT.datetime.strptime(date, "%Y-%m-%d").date()
	dateIDT = dateID + DT.timedelta(days=1)
	audios = list()
	
	user_bases = User.objects.filter(username__iexact = user.domain_login.lower())
	if len(user_bases) == 1:
		user_base = user_bases[0]
		list_audios = Records_voice_recorder.objects.filter(date__range = (dateID, dateIDT)).filter(user = user_base).order_by('date')
		for audio in list_audios:
			text = ''
			if len(audio.data_json) > 0:
				text_json = json.loads(audio.data_json)
				text = text_json['data']
			audio_data = {
				'audio': audio,
				'text': list(text)
			}
			audios.append(audio_data)
	return audios


def get_date_in_name(name):
    date = ''
    dates = name.split('.')
    if len(dates) == 2:
        date_str = dates[0]
        if len(date_str) == 14:
            try:
                date = datetime.datetime.strptime(date_str,'%Y%m%d%H%M%S')
            except:
                date = '' 
    return date 


def convert_to_preferred_format(sec): 
    sec = int(sec)
    if sec > 0:
        sec = sec % (24 * 3600) 
        hour = sec // 3600 
        sec %= 3600 
        min = sec // 60 
        sec %= 60 
        if hour > 0:
            return "%02d:%02d:%02d" % (hour, min, sec)
        else:
            return "%02d:%02d" % (min, sec)
    else:
        return "00:00"


def convert_time_to_sec(time_str): 
    list_time = time_str.split(':')
    if len(list_time) == 2:
        hh = 0
        mm = int(time_str.split(':')[0].strip())
        ss = int(time_str.split(':')[1].strip())
    elif len(list_time) == 3:
        hh = int(time_str.split(':')[0].strip())
        mm = int(time_str.split(':')[1].strip())
        ss = int(time_str.split(':')[2].strip())
    sec = ss + (mm * 60) + (hh * 60)
    return sec


def record_strip(id, start, end, times):
    recognition = Records_voice_recorder.objects.get(pk = id)
    name        = recognition.name
    audio_path  = recognition.audio.url
    path_static = r'C:/django_project/kors/kors'
    path_audio  = r'C:/django_project/kors/kors' + audio_path
    path_temp   = path_static + "/temp/"

    AudioSegment.converter  = path_static + "/static/ffmpeg/bin/ffmpeg.exe"
    AudioSegment.ffmpeg     = path_static + "/static/ffmpeg/bin/ffmpeg.exe"
    AudioSegment.ffprobe    = path_static + "/static/ffmpeg/bin/ffprobe.exe"

    mp3 = False
    if name.find('.mp3')> 0:
        sound   = AudioSegment.from_mp3(path_audio)
        mp3     = True
        name_save = path_temp + name.replace('.mp3', '')
    else:
        sound = AudioSegment.from_file(path_audio)
        name_save = path_temp + name.replace('.wav', '')

    start_ms    = start * 1000
    end_ms      = end * 1000
    sound_save  = sound[start_ms:end_ms]
    
    duration = len(sound_save) / 1000

    if mp3:
        name_save = name_save  + '.mp3'
    else:
        name_save = name_save  + '.wav'

    sound_save.export(name_save)

    recognition_new             = Records_voice_recorder()
    recognition_new.user        = recognition.user
    recognition_new.date        = recognition.date
    recognition_new.name        = recognition.name + ' / ' + times
    recognition_new.recognition = recognition.recognition
    recognition_new.time        = duration
    
    with open(name_save, 'rb') as fi:
        file = File(fi, name=name)
        recognition_new.audio.save(name, file)

    if len(recognition.data_json) > 0:
        data_json       = json.loads(recognition.data_json)
        conf            = data_json['conf']
        new_data_list   = list()
        for inf in conf:
            start_inf_mc = inf['start'] * 1000
            if start_inf_mc >= start_ms and start_inf_mc <= end_ms:
                new_inf = inf
                new_inf['start']            = round((start_inf_mc - start_ms) / 1000, 2)
                new_inf['data']['start']    = round((inf['data']['start'] * 1000  - start_ms) / 1000, 2)
                new_inf['data']['end']      = round(((inf['data']['end'] * 1000) - start_ms) / 1000, 2)
                new_data_list.append(new_inf)
        data_json['conf'] = new_data_list 
        
        data            = data_json['data']
        new_data_list   = list()
        for inf in data:
            start_inf_mc = convert_time_to_sec(inf['start']) * 1000
            if start_inf_mc >= start_ms and start_inf_mc <= end_ms:
                new_data = inf
                new_data['start']  = round((start_inf_mc - start_ms) / 1000, 2)
                new_data_list.append(new_data)
        data_json['data']           = new_data_list
        recognition_new.data_json   = str(data_json).replace("'", '"')
    recognition_new.save()

    return recognition_new.id


def record_connects(ids):
	
	path_static = r'C:/django_project/kors/kors'
	
	AudioSegment.converter  = path_static + "/static/ffmpeg/bin/ffmpeg.exe"
	AudioSegment.ffmpeg     = path_static + "/static/ffmpeg/bin/ffmpeg.exe"
	AudioSegment.ffprobe    = path_static + "/static/ffmpeg/bin/ffprobe.exe"
	
	path_temp   	= path_static + "/temp/"
	
	list_audios 	= list()
	duration	 	= 0
	for id in ids:
		if len(id) > 0:
			recognition = Records_voice_recorder.objects.get(pk = id)
			name        = recognition.name
			audio_path  = recognition.audio.url
			path_audio  = r'C:/django_project/kors/kors' + audio_path
			sound   	= AudioSegment.from_file(path_audio)
			duration 	= duration + recognition.time
			list_audios.append(sound)

	audio_save = AudioSegment.empty()
	for sound in list_audios:
		audio_save = audio_save + sound
	
	name_save = path_temp + 'test_coonect.wav'
	
	audio_save.export(name_save)

	recognition_new             = Records_voice_recorder()
	recognition_new.user        = recognition.user
	recognition_new.date        = recognition.date
	recognition_new.name        = recognition.name
	recognition_new.recognition = recognition.recognition
	recognition_new.time        = duration
	name = 'text'
	with open(name_save, 'rb') as fi:
		file = File(fi, name=name)
		recognition_new.audio.save(name, file)

	recognition_new.save()

	return recognition_new.id


def get_date_start_end(date_period):
	date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
	if date_start.month > 11:
		month_end	= 1
		year_end 	= date_start.year + 1
	else:
		month_end	= date_start.month + 1
		year_end 	= date_start.year
	date_end 	= date_start.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)

	result = {
		'date_start' 	: date_start,
		'date_end'		: date_end
	}

	return result
  
def get_checklist_cvc(rlk_id):
	checklist = Records_voice_recorder_cvc_checklist.objects.filter(rlk = rlk_id)
	if len(checklist)>0:
		return checklist[0]
	return ''