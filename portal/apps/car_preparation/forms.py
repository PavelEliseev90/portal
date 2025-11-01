from django import forms

from .models import CarPreparationResource, RefPreparationMaterial, PreparationMaterialMovement


class CarPreparationResourceForm(forms.ModelForm):
    class Meta:
        model = CarPreparationResource
        fields = [
            'resource_type', 'performer', 'name', 'code', 'unit', 'is_active',
            'max_concurrent_works', 'work_start_time', 'work_end_time', 'work_days',
        ]
        widgets = {
            'resource_type': forms.Select(attrs={'class': 'form-control'}),
            'performer': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_concurrent_works': forms.NumberInput(attrs={'class': 'form-control'}),
            'work_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'work_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'work_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class RefPreparationMaterialForm(forms.ModelForm):
    class Meta:
        model = RefPreparationMaterial
        fields = ['name', 'code', 'uom', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'uom': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PreparationMaterialMovementForm(forms.ModelForm):
    class Meta:
        model = PreparationMaterialMovement
        fields = ['date', 'unit', 'material', 'qty', 'movement_type', 'work_item', 'comment']
        widgets = {
            'date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-control'}),
            'qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'work_item': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.TextInput(attrs={'class': 'form-control'}),
        }


