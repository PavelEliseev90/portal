from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'eco'

urlpatterns = [

    path('1c/<str:staff_uin>/<str:rlk_ref>/', views.eco_1c_entry, name='eco_1c'),

    path('',                                    views.list_eco_online),
    path('funnel/',                             views.tradein_funnel_new, name='tradein_funnel'),
    path('funnel/analytics/',                   views.tradein_funnel_analytics,         name='tradein_funnel_analytics'),
    path('funnel/analytics/detail/',            views.tradein_funnel_analytics_detail,  name='tradein_funnel_analytics_detail'),
    path('funnel/analytics/export/',            views.tradein_funnel_analytics_export,  name='tradein_funnel_analytics_export'),
    path('funnel/rejected_1/',                  views.tradein_funnel_analytics_rejected, name='tradein_funnel_analytics_rejected'),
    path('funnel/rejected/',                    views.tradein_funnel_rejected, name='tradein_funnel_rejected'),
    path('funnel/deal-analysis/',               views.tradein_funnel_deal_analysis, name='tradein_funnel_deal_analysis'),
    path('funnel/deal-analysis/export/',        views.tradein_funnel_deal_analysis_export, name='tradein_funnel_deal_analysis_export'),
    path('funnel/export/',                      views.tradein_funnel_export, name='tradein_funnel_export'),
    path('funnel/analytics/analysts/',         views.eco_analysts_performance, name='eco_analysts_performance'),
    path('funnel/analytics/appraisers/',       views.eco_appraisers_performance, name='eco_appraisers_performance'),
    path('efficiency/',                         views.eco_efficiency_analysis_new, name='eco_efficiency'),
    path('efficiency/analyst/<int:analyst_id>/', views.eco_analyst_detail, name='eco_analyst_detail'),
    path('staff-performance/',                  views.staff_performance_analysis, name='staff_performance'),
    path('pricing-report/',                     views.interactive_pricing_report, name='interactive_pricing_report'),
    path('price-calculator/',                   views.price_calculator, name='price_calculator'),
    path('price-recalc-history/',               views.price_recalc_history_report, name='price_recalc_history_report'),
    path('interactive-evaluations/',            views.interactive_evaluations_report, name='interactive_evaluations_report'),

    path('estimation-zg/',                      views.estimation_zg_analytics, name='estimation_zg_analytics'),
    path('estimation-zg/detail/',               views.estimation_zg_detail, name='estimation_zg_detail'),
    path('autohub-zg/',                         views.autohub_zg_analytics, name='autohub_zg_analytics'),
    path('sales-zg/',                          views.sales_zg_analytics, name='sales_zg_analytics'),
    path('sales-zg/detail/',                   views.sales_zg_detail, name='sales_zg_detail'),
    path('market-trends/',                      views.market_model_trends, name='market_model_trends'),
    path('market-trends/model/',                views.market_model_detail, name='market_model_detail'),
    path('market-trends/month/',                views.market_model_month_detail, name='market_model_month_detail'),
    path('market-trends/car/<slug:slug>/',      views.market_car_trends, name='market_car_trends'),
    path('funnel/simple-export/',               views.tradein_funnel_simple_export, name='tradein_funnel_simple_export'),
    path('js/get_chats_list/',                  views.get_chats_list),
    path('js/post_chats_list/',                 views.post_chats_list),
    path('js/get_chats_list_online/',           views.get_chats_list_online),
    path('js/get_chats_list_online_info/<id>/', views.get_chats_list_online_info, name='id'),
    path('js/get_users_list_online/<id>/',      views.get_users_list_online, name='id'),

    path('monitors/',                           views.eco_monitors),
    path('<int:id>/create_control_diagnostic/', views.create_control_diagnostic, name='create_control_diagnostic'),
    path('<int:id>/control_diagnostic/<int:cd_id>/comparison/', views.control_diagnostic_comparison, name='control_diagnostic_comparison'),
    path('<int:id>/control_diagnostic/<int:cd_id>/edit/', views.control_diagnostic_edit, name='control_diagnostic_edit'),
    path('<int:id>/control_diagnostic/<int:cd_id>/control_diagnostic_salon/', views.control_diagnostic_salon, name='control_diagnostic_salon'),
    path('<int:id>/control_diagnostic/<int:cd_id>/control_diagnostic_body/', views.control_diagnostic_body, name='control_diagnostic_body'),
    
    path('express-auction/matrix/',             views.express_auction_matrix, name='express_auction_matrix'),
    path('<id>/price_increase_request/',        views.price_increase_request, name='price_increase_request'),
    path('<id>/chat_email_notify/',             views.chat_email_notify_participants, name='chat_email_notify'),
    path('<id>/',                               views.doc, name='id'),
    
    path('online/',                             views.list_eco_online),
    path('online/js/get_chats_list/',           views.get_chats_list),
    path('online/js/get_chats_list_online/',    views.get_chats_list_online),
    path('online/<id>/',                        views.doc, name='id'),

]
