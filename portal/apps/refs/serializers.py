from rest_framework import serializers
from refs.models import AutoruModel, AutoruComplectation, AutoruMark, AutoruModification, RefManufacturer, AutoruModificationSpecifications, RefCarsOrganization, RefOrganization, RefFilial, RefUnit, RefStore, RefTypeReceptionCarsOrganization
from datetime import datetime


class RefTypeReceptionCarsOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefTypeReceptionCarsOrganization
        fields = '__all__'
        depth = 1


class RefOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefOrganization
        fields = '__all__'
        depth = 1


class RefFilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefFilial
        fields = '__all__'
        depth = 1


class RefUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefUnit
        fields = '__all__'
        depth = 1


class RefStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefStore
        fields = '__all__'
        depth = 1


class RefManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefManufacturer
        fields = ['pk', 'name', 'name_rus', 'search_fields']
        depth = 1

class AutoruMarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoruMark
        fields = '__all__'
        depth = 1


class AutoruModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoruModel
        fields = '__all__'
        depth = 1


class AutoruModificationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = AutoruModification
        fields = '__all__'
        depth = 1


class AutoruComplectationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoruComplectation
        fields = '__all__'
        depth = 1


class RefCarsOrganizationSerializer(serializers.ModelSerializer):
    
    logo_mark   = serializers.SerializerMethodField('g_logo')
    prev        = serializers.SerializerMethodField('g_photo')

    def g_logo(self, foo):
        return foo.logo()
    
    def g_photo(self, foo):
        return foo.get_photo()

    class Meta:
        model = RefCarsOrganization
        
        fields = [field.name for field in model._meta.fields]
        fields.append('logo_mark')
        fields.append('prev')

        depth = 1
