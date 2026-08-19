from rest_framework import serializers
from refs.models import AutoruModel, AutoruComplectation, AutoruMark, AutoruModification, RefManufacturer, AutoruModificationSpecifications, RefCarsOrganization, RefOrganization, RefFilial, RefUnit, RefStore, RefTypeReceptionCarsOrganization
from datetime import datetime


PRICE_GROUP_SUFFIXES = ('_200', '_400', '_700', '_1200', '_2000', '_3000', '_5000', '_5001')


def ref_unit_price_group_field_names():
    """Поля RefUnit с настройками ценовых групп (200, 400, …) — не для выгрузки 2КК."""
    names = []
    for field in RefUnit._meta.get_fields():
        name = getattr(field, 'name', None)
        if not name:
            continue
        if any(name.endswith(suffix) for suffix in PRICE_GROUP_SUFFIXES):
            names.append(name)
    return names


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
        exclude = ref_unit_price_group_field_names()


class RefUnitKolesaExportSerializer(RefUnitSerializer):
    """Подразделение для JSON 2КК / БУ колёс — без ценовых групп."""
    pass


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
