from django.urls import path
from checklists import views
from django.views.generic import TemplateView

app_name = 'checkLists'

urlpatterns = [
    
    path('',            views.glav_v1),
    
    ####
    path('glav_new/',   views.glav_v1),
    ####
    #### Отчеты
    path('reports/',                        views.reports),

    #### Отчет по сотрудникам ДЦ
    path('reports/report_dc/',      views.reports_dc),
    #### Отчет по сотрудникам КК (количество созданных чек листов)
    path('reports/reports_kk/',     views.reports_kk),
    path('reports/report_op/',      views.op_report),

    path('glav/',               views.glav_v1),
    path('glav/op/',            views.op),
    
    path('glav/op/doc/',        views.op_doc),
	path('glav/op/op_doc_new/', views.op_doc_new),
    

    path('glav/service_in/',                        views.service_in),
	path('glav/service_in/doc/',                    views.service_in_doc),
	path('glav/service_in/service_in_doc_new/',     views.service_in_doc_new),


    path('glav/service_out/',                       views.service_out),
	path('glav/service_out/doc/',                   views.service_out_doc),
	path('glav/service_out/service_out_doc_new/',   views.service_out_doc_new),

    path('glav/trade_in/',                  views.trade_in),
    path('glav/trade_in/trade_in_new/',     views.trade_in_new),
    path('glav/trade_in/doc/',              views.trade_in_doc),

    path('glav/op_kors/',                   views.op_kors),
    path('glav/op_kors/op_kors_doc/',       views.op_kors_doc),
    path('glav/op_kors/op_kors_doc_new/',   views.op_kors_doc_new),

    path('login/',      views.login),
    path('logout/',     views.logout),
    
    path('listchecklist/',  views.listchecklist),
    path('doc/',            views.doc),

    #### Помощник создания чек листа
    path('new_check_list/', views.new_check_list),
    
]
