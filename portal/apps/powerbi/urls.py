from django.urls import path, include
from django.views.generic import TemplateView
from powerbi import views

app_name = 'powerbi'

urlpatterns = [
   
   path('mers_SQL_refresh/',              views.mers_SQL_refresh),
   path('StockTZK_refresh/',              views.StockTZK_refresh),
   path('MKU_State_Orders_refresh/',      views.MKU_State_Orders_refresh),
   path('EstimationOP_refresh/',          views.EstimationOP_refresh),
   path('CumulativeMarginUS_refresh/',    views.CumulativeMarginUS_refresh),
   path('CumulativeMargin_refresh/',      views.CumulativeMargin_refresh),
   path('ComparativeReportOPFU_refresh/', views.ComparativeReportOPFU_refresh),
   path('Stock_refresh/',                 views.Stock_refresh),
   path('stock/list/',                    views.stock_list, name='stock_list'),
   path('stock/export/',                  views.stock_export_excel, name='stock_export'),
   path('Cumulative_refresh/',             views.Cumulative_refresh),
]