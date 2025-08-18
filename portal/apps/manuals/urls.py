from django.urls import path

from manuals import views

app_name = 'manuals'


urlpatterns = [

    path("", 						views.manuals),
	path("manual_edit/", 			views.manual_edit),
	path('<slug>/',					views.manual_slug, name='slug'),
	path('manual/<pk>/',			views.manual, name='pk')
	

]
