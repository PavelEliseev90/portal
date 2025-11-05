from rest_framework import serializers
from register.models import RegInteractivOcenka
from datetime import datetime


class RegInteractivOcenkaSerializer(serializers.ModelSerializer):
    
    bcp         = serializers.SerializerMethodField('get_bcp')
    zna         = serializers.SerializerMethodField('get_zna')

    def get_bcp(self, foo):
        return foo.get_bcp()
    
    def get_zna(self, foo):
        return foo.get_zna()
    
    class Meta:
        
        model = RegInteractivOcenka
        fields = [field.name for field in model._meta.fields]
        fields.append('bcp')
        fields.append('zna')
        depth = 4