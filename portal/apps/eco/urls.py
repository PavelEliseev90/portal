from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('',                                    views.list_eco_online),
    path('funnel/',                             views.tradein_funnel, name='tradein_funnel'),
    path('efficiency/',                         views.eco_efficiency_analysis, name='eco_efficiency'),
    path('staff-performance/',                  views.staff_performance_analysis, name='staff_performance'),
    path('pricing-report/',                     views.interactive_pricing_report, name='interactive_pricing_report'),
    path('interactive-evaluations/',            views.interactive_evaluations_report, name='interactive_evaluations_report'),
    path('js/get_chats_list/',                  views.get_chats_list),
    path('js/post_chats_list/',                 views.post_chats_list),
    path('js/get_chats_list_online/',           views.get_chats_list_online),
    path('js/get_chats_list_online_info/<id>/', views.get_chats_list_online_info, name='id'),
    path('js/get_users_list_online/<id>/',      views.get_users_list_online, name='id'),

    path('monitors/',                           views.eco_monitors),
    path('<id>/',                               views.doc, name='id'),
    
    path('online/',                             views.list_eco_online),
    path('online/js/get_chats_list/',           views.get_chats_list),
    path('online/js/get_chats_list_online/',    views.get_chats_list_online),
    path('online/<id>/',                        views.doc, name='id'),

]
