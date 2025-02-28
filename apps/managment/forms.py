from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django import forms
from .models import Warehouse,Product,get_product_metadata
from apps.authentication.models import CustomUser
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

@login_required
def update_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after changing the password
            return redirect("profile")  # Redirect to the profile page after successful password change
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "accounts/user_profile.html",
        {"current_user": request.user, "form": form}
    )


class WarehouseForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Warehouse
        fields = [
            'name',
            'type',
            'location',
            'total_capacity',
            'available_space',
            'zone_layout',
            'users',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'total_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'available_space': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'zone_layout': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'users': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'name': 'Name of the warehouse',
            'type': 'Type of warehouse',
            'location': 'Geographical location of the warehouse',
            'total_capacity': 'Total storage capacity in square meters',
            'available_space': 'Available storage space in square meters',
            'zone_layout': 'Description or diagram of the warehouse zone layout',
            'users': 'Users associated with this warehouse',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['users'].queryset = (
                user.users_manageable.all()
                if hasattr(user, 'users_manageable')
                else CustomUser.objects.none()
            )
            # Store the creator for the pre_save signal
            self.instance.creator = user

    def clean(self):
        cleaned_data = super().clean()
        total_capacity = cleaned_data.get('total_capacity')
        available_space = cleaned_data.get('available_space')

        if total_capacity is not None and available_space is not None:
            if total_capacity < 0 or available_space < 0:
                raise ValidationError("Capacity values cannot be negative")
            if total_capacity < available_space:
                raise ValidationError({
                    'total_capacity': "Total capacity must be greater than available space",
                    'available_space': "Available space cannot exceed total capacity"
                })
        return cleaned_data
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['warehouse', 'total_value', 'weight_quantity_kg', 'status', 'exit_date',
                   'manufacturing_date', 'expiration_date', 'supplier_code', 'variety_or_species',
                   'packaging_condition', 'quality_standards', 'storage_temperature', 'humidity_rate',
                   'co2', 'o2', 'n2', 'ethylene_management', 'nutritional_info', 'regulatory_codes']
        # Note: 'lot_number' is no longer excluded, so it’s included by default

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize widgets for better UX
        self.fields['sku'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter unique SKU',
            'required': True
        })
        self.fields['product_name'].widget.attrs.update({
            'class': 'form-control',
            'required': True
        })
        self.fields['product_type'].widget.attrs.update({
            'class': 'form-control',
            'required': True
        })
        self.fields['weight_quantity'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter weight (default units)',
            'required': True
        })
        self.fields['quantity_in_stock'].widget.attrs.update({
            'class': 'form-control',
            'min': '0',
            'placeholder': 'Enter stock quantity',
            'required': True
        })
        self.fields['unit_price'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter price per unit',
            'required': True
        })
        self.fields['harvest_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
        self.fields['entry_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'value': timezone.now().date().isoformat(),
            'required': True
        })
        self.fields['lot_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter lot number (optional)'
        })
        self.fields['farmer'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['notes_comments'].widget.attrs.update({
            'class': 'form-control',
            'rows': '3',
            'placeholder': 'Add any additional notes'
        })

        # Make some fields optional
        self.fields['harvest_date'].required = False
        self.fields['lot_number'].required = False
        self.fields['farmer'].required = False
        self.fields['notes_comments'].required = False

    def clean(self):
        cleaned_data = super().clean()
        product_name = cleaned_data.get('product_name')

        # Populate metadata-based fields if not provided
        if product_name:
            metadata = get_product_metadata()
            product_data = metadata.get(product_name, {})

            if not cleaned_data.get('notes_comments') and product_data.get('notes_comments'):
                cleaned_data['notes_comments'] = product_data['notes_comments']
            if not cleaned_data.get('product_type') and product_data.get('product_type'):
                cleaned_data['product_type'] = product_data['product_type']

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Auto-calculate weight_quantity_kg
        if self.cleaned_data.get('weight_quantity'):
            instance.weight_quantity_kg = self.cleaned_data['weight_quantity'] / 1000

        # Set default status
        instance.status = 'In Stock'

        # Calculate total_value
        if self.cleaned_data.get('unit_price') and self.cleaned_data.get('quantity_in_stock'):
            instance.total_value = self.cleaned_data['unit_price'] * self.cleaned_data['quantity_in_stock']

        # Populate metadata-based fields
        metadata = get_product_metadata()
        product_data = metadata.get(self.cleaned_data['product_name'], {})
        for field in ['storage_temperature', 'humidity_rate', 'co2', 'o2', 'n2', 'ethylene_management']:
            if field in product_data and getattr(instance, field) is None:
                setattr(instance, field, product_data[field])

        if commit:
            instance.save()
        return instance