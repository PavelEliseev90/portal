from rest_framework import serializers
from avtosalon.models import Avtohub
from datetime import datetime


class AvtohubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avtohub
        fields = '__all__'
        depth = 1

