from django.urls import path

from mykors import views


app_name = 'mykors'

urlpatterns = [
    path('online-docs/ingest/', views.ingest_online_doc, name='online_doc_ingest'),
]