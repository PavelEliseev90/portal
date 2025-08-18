from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'recognition'

urlpatterns = [ 
    path('',                    views.start),
    path('op/',                 views.op),
    path('op/<id>/',            views.op_detail, name='id'),
    path('op/<slug:id>/<slug:pk>/', views.op_detail_recognition, name='slug'),
    
    path('tematiks/',           views.tematiks),
    path('tematiks_op/',        views.tematiks_op),
    path('tematiks_op/<id>',    views.tematiks_op_edit, name='id'),
    path('questions/',          views.records_questions),
    path('questions/<id>/',     views.records_questions_edit, name='id'),

    path('<id>',                views.recognition, name='id'),

    path('check_lists/',                                    views.check_lists),
    path('check_lists/<id>',                                views.check_lists_edit,  name='id'),
    path('check_lists/<slug:id>/question/<slug:pk>',        views.check_lists_edit_question, name='slug'),

    #контроль
    path('control/',                            views.control),
    path('control_excel/',                      views.control_excel),
    path('control/<id>/',                       views.control_detail, name='id'),
    path('control_excel/<id>/',                 views.control_detail_excel,  name='id'),
    path('control/<slug:id>/<slug:doc_id>/',    views.control_detail_doc, name='slug'),
    
    #cvc
    path('cvc_op/',                     views.cvc_op),
    path('cvc_op/<id>/',                views.cvc_op_detail, name='id'),
    path('cvc_tematiks_op_quequ/',      views.cvc_tematiks_op_quequ),
    path('cvc_op/<slug:id>/<slug:pk>/', views.cvc_op_detail_recognition, name='slug'),
    path('cvc_tematiks_op/',            views.cvc_tematiks_op),
    path('cvc_tematiks_op/<id>',        views.cvc_tematiks_op_edit, name='id'),
    path('report_cvc_kg_op/',           views.report_cvc_kg_op),
    path('report_cvc_kg_op_xls/',       views.report_cvc_kg_op_xls),
    path('cvc_get_info/',               views.cvc_get_info_cvc),

]
