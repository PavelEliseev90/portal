
from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import  include, path
from telephony import views

app_name = 'telephony'

urlpatterns = [
    
    path('recognitions/',                               views.telephony_recognitions),
    path('recognitions/success/',                       views.telephony_queue_success),
    path('recognitions/success/<id>/',                  views.telephony_queue_success_unit, name='id'),
    path('recognitions/success/<slug:id>/<slug:pk>/',   views.telephony_queue_success_unit_doc, name='slug'),
 
    path('recognitions/tematiks/',                                      views.telephony_tematiks),
    path('recognitions/tematiks/<id>/',                                 views.telephony_tematiks_edit, name='id'),
    path('recognitions/tematiks/<slug:id>/delete_fraza/<slug:pk>/',     views.telephony_tematiks_edit_delete_fraza, name='slug'),
    
    path('recognitions/questions/',                     views.telephony_questions),
    path('recognitions/questions/<id>/',                views.telephony_questions_edit, name='id'),

    path('recognitions/queue/',                         views.telephony_queue),
    path('recognitions/queue/<id>/',                    views.telephony_queue_view, name='id'),

    #path('recognitions/quequ_test/',                    views.quequ),
    path('recognitions/queue/',                         views.telephony_queue),
    
    path('recognitions/dictonarys/',                    views.dictonarys),
    path('recognitions/dictonarys/<id>/',               views.dictonary_edit, name='id'),

    path('recognitions/refresh_history/',               views.refresh_history),

]
