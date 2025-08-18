from rest_framework import serializers
from register.models import RegInteractivOcenka
from datetime import datetime


class RegInteractivOcenkaSerializer(serializers.ModelSerializer):
    class Meta:
        
        model = RegInteractivOcenka
        fields = [field.name for field in model._meta.fields]
       
        depth = 4