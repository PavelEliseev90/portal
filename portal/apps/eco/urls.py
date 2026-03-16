from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('',                                    views.list_eco_online),
    path('funnel/',                             views.tradein_funnel_new, name='tradein_funnel'),
    path('funnel/analytics/',                   views.tradein_funnel_analytics,         name='tradein_funnel_analytics'),
    path('funnel/analytics/detail/',            views.tradein_funnel_analytics_detail,  name='tradein_funnel_analytics_detail'),
    path('funnel/analytics/export/',            views.tradein_funnel_analytics_export,  name='tradein_funnel_analytics_export'),
    path('funnel/rejected/',                    views.tradein_funnel_rejected, name='tradein_funnel_rejected'),
    path('funnel/export/',                      views.tradein_funnel_export, name='tradein_funnel_export'),
    path('funnel/analytics/analysts/',         views.eco_analysts_performance, name='eco_analysts_performance'),
    path('funnel/analytics/appraisers/',       views.eco_appraisers_performance, name='eco_appraisers_performance'),
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
    path('<int:id>/create_control_diagnostic/', views.create_control_diagnostic, name='create_control_diagnostic'),
    path('<int:id>/control_diagnostic/<int:cd_id>/comparison/', views.control_diagnostic_comparison, name='control_diagnostic_comparison'),
    path('<int:id>/control_diagnostic/<int:cd_id>/edit/', views.control_diagnostic_edit, name='control_diagnostic_edit'),
    path('<id>/',                               views.doc, name='id'),
    
    path('online/',                             views.list_eco_online),
    path('online/js/get_chats_list/',           views.get_chats_list),
    path('online/js/get_chats_list_online/',    views.get_chats_list_online),
    path('online/<id>/',                        views.doc, name='id'),

]
