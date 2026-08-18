from rest_framework import serializers
from documents.models import DocRLK, DocLO
from datetime import datetime


class DocLOSerializer(serializers.ModelSerializer):

    class Meta:
        model = DocLO
        fields = [field.name for field in model._meta.fields]
        depth = 1


class DocRLKSerializer(serializers.ModelSerializer):
    
    estimation                      = serializers.SerializerMethodField('g_estimation')
    estimation_vin                  = serializers.SerializerMethodField('g_estimation_vin')
    estimation_modification_info    = serializers.SerializerMethodField('g_estimation_modification_info')
    estimation_start_formated       = serializers.SerializerMethodField('g_estimation_start_formated')
    estimation_end_formated         = serializers.SerializerMethodField('g_estimation_end_formated')
    estimation_year                 = serializers.SerializerMethodField('g_estimation_year')
    estimation_status               = serializers.SerializerMethodField('g_estimation_status')
    estimation_staff_uin            = serializers.SerializerMethodField('g_estimation_staff_uin')

    def g_estimation(self, foo):
       return foo.estimation()
    
    def g_estimation_vin(self, foo):
        return foo.estimation_vin()

    def g_estimation_modification_info(self, foo):
        return foo.estimation_modification_info()

    def g_estimation_end_formated(self, foo):
        return foo.estimation_end_formated()    

    def g_estimation_start_formated(self, foo):
        return foo.estimation_start_formated()    

    def g_estimation_year(self, foo):
        return foo.estimation_year()   

    def g_estimation_status(self, foo):
        return foo.estimation_status()    

    def g_estimation_staff_uin(self, foo):
        return foo.estimation_staff_uin()        

    class Meta:
        model = DocRLK
        
        fields = [field.name for field in model._meta.fields]
        fields.append('estimation')
        fields.append('estimation_vin')
        fields.append('estimation_modification_info')
        fields.append('estimation_start_formated')
        fields.append('estimation_end_formated')
        fields.append('estimation_year')
        fields.append('estimation_status')
        fields.append('estimation_staff_uin')
    
        depth = 1
