from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('',                                    views.list_eco_online),
    path('funnel/',                             views.tradein_funnel_new, name='tradein_funnel'),
    path('funnel/rejected/',                    views.tradein_funnel_rejected, name='tradein_funnel_rejected'),
    path('efficiency/',                         views.eco_efficiency_analysis_new, name='eco_efficiency'),
    path('efficiency/analyst/<int:analyst_id>/', views.eco_analyst_detail, name='eco_analyst_detail'),
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
