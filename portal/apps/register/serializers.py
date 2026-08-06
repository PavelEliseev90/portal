from rest_framework import serializers
from register.models import (
    RegInteractivOcenka,
    RegInteractivOcenkaReception,
    RegInteractivOcenkaSoglasovanie,
    RegInteractivOcenkaRLK,
)
from datetime import datetime
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Min

class RegInteractivOcenkaSerializer(serializers.ModelSerializer):
    
    bcp         = serializers.SerializerMethodField('get_bcp')
    zna         = serializers.SerializerMethodField('get_zna')

    def get_bcp(self, foo):        
        bcp = 0
        datas = RegInteractivOcenkaRLK.objects.filter(estimation = foo).filter(Q(page_soglasovanie__price_auto_bcp_1__gt = 0) | Q(page_soglasovanie__price_auto_bcp_2__gt = 0) | Q(page_soglasovanie__price_auto_bcp_3__gt = 0))
        for data in datas:
            if data.page_soglasovanie != None:
                if data.page_soglasovanie.price_auto_bcp_1 > 0:
                    bcp = data.page_soglasovanie.price_auto_bcp_1
                elif data.page_soglasovanie.price_auto_bcp_2 > 0:
                    bcp = data.page_soglasovanie.price_auto_bcp_2
                elif data.page_soglasovanie.price_auto_bcp_3 > 0:
                    bcp = data.page_soglasovanie.price_auto_bcp_3
         
        return bcp
        
    
    def get_zna(self, foo):
        zna = 0
        datas = RegInteractivOcenkaRLK.objects.filter(estimation = foo).filter(page_soglasovanie__price_auto_bcp_1__gt = 0, page_soglasovanie__price_auto_bcp_2__gt = 0, page_soglasovanie__price_auto_bcp_3__gt = 0)
        for data in datas:
            if data.page_soglasovanie != None:
                if data.page_soglasovanie.price_zna_1 > 0:
                    zna = data.page_soglasovanie.price_zna_1
                elif data.page_soglasovanie.price_zna_2 > 0:
                    zna = data.page_soglasovanie.price_zna_2
                elif data.page_soglasovanie.price_zna_3 > 0:
                    zna = data.page_soglasovanie.price_zna_3
        return zna
    
    class Meta:
        
        model = RegInteractivOcenka
        fields = [field.name for field in model._meta.fields]
        fields.append('bcp')
        fields.append('zna')
        depth = 4


class RegInteractivOcenkaRLKSerializer(serializers.ModelSerializer):
    
    class Meta:
        
        model = RegInteractivOcenkaRLK
        fields = [field.name for field in model._meta.fields]
        depth = 1


class RegInteractivOcenkaSoglasovanieSerializer(serializers.ModelSerializer):
    
    class Meta:
        
        model = RegInteractivOcenkaSoglasovanie
        fields = [field.name for field in model._meta.fields]
        depth = 1


class RegInteractivOcenkaReceptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = RegInteractivOcenkaReception
        fields = [field.name for field in model._meta.fields]
        depth = 1