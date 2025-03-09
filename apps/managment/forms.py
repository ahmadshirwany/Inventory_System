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
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-users',  # Add class for Select2
            'multiple': 'multiple',  # Ensure multiple selection
        })
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
            # 'users' is defined above with SelectMultiple
        }
        help_texts = {
            'name': 'Name of the warehouse',
            'type': 'Type of warehouse',
            'location': 'Geographical location of the warehouse',
            'total_capacity': 'Total storage capacity in square meters',
            'available_space': 'Available storage space in square meters',
            'zone_layout': 'Description or diagram of the warehouse zone layout',
            'users': 'Select users associated with this warehouse',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.is_superuser:
                self.fields['users'].queryset = CustomUser.objects.all()
            else:
                self.fields['users'].queryset = CustomUser.objects.filter(owner=user)
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
        exclude = [
            'warehouse', 'total_value', 'weight_quantity_kg', 'status', 'exit_date',
            'manufacturing_date', 'expiration_date', 'supplier_code', 'variety_or_species',
            'packaging_condition', 'quality_standards', 'storage_temperature', 'humidity_rate',
            'co2', 'o2', 'n2', 'ethylene_management', 'nutritional_info', 'regulatory_codes',
            'product_type', 'lot_number'
        ]

    def __init__(self, *args,warehouse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if warehouse is None and self.instance and self.instance.pk and self.instance.warehouse:
            warehouse = self.instance.warehouse
        if warehouse and warehouse.ownership:
            self.fields['farmer'].queryset = CustomUser.objects.filter(
                is_farmer=True,
                owner=warehouse.ownership
            )

        # Common attributes for all fields
        common_attrs = {
            'class': 'form-control form-control-lg',  # Larger inputs for better visibility
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',  # Softer edges and shadow
        }

        # SKU
        self.fields['sku'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'e.g., SKU-12345',
            'required': True,
            'aria-label': 'Stock Keeping Unit',
        })

        # Barcode
        self.fields['barcode'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'e.g., 012345678905',
            'required': True,
            'aria-label': 'Barcode',
        })

        # Product Name (assuming it's a dropdown due to choices)
        self.fields['product_name'].widget.attrs.update({
            'class': 'form-select form-select-lg',  # Use form-select for dropdowns
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'required': True,
            'aria-label': 'Product Name',
        })

        # Weight Quantity
        self.fields['weight_quantity'].widget.attrs.update({
            **common_attrs,
            'step': '0.01',
            'min': '0',
            'placeholder': 'e.g., 500.00 (in default units)',
            'required': True,
            'aria-label': 'Weight or Quantity',
        })

        # Quantity in Stock
        self.fields['quantity_in_stock'].widget.attrs.update({
            **common_attrs,
            'min': '0',
            'placeholder': 'e.g., 100',
            'required': True,
            'aria-label': 'Quantity in Stock',
        })

        # Unit Price
        self.fields['unit_price'].widget.attrs.update({
            **common_attrs,
            'step': '0.01',
            'min': '0',
            'placeholder': 'e.g., 19.99',
            'required': True,
            'aria-label': 'Unit Price',
        })

        # Harvest Date
        self.fields['harvest_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            **common_attrs,
            'placeholder': 'Select harvest date',
            'aria-label': 'Harvest Date',
        })

        # Entry Date
        self.fields['entry_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            **common_attrs,
            'value': timezone.now().date().isoformat(),
            'required': True,
            'aria-label': 'Entry Date',
        })

        # Farmer (assuming it's a dropdown ForeignKey)
        self.fields['farmer'].widget.attrs.update({
            'class': 'form-select form-select-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'aria-label': 'Farmer',
        })

        # Notes/Comments
        self.fields['notes_comments'].widget.attrs.update({
            'class': 'form-control',
            'rows': '4',
            'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'placeholder': 'Add any additional notes or comments...',
            'aria-label': 'Notes or Comments',
        })

        # Set non-required fields
        self.fields['harvest_date'].required = False
        self.fields['farmer'].required = False
        self.fields['notes_comments'].required = False

    def clean(self):
        cleaned_data = super().clean()
        product_name = cleaned_data.get('product_name')
        if product_name:
            metadata = get_product_metadata()
            product_data = metadata.get(product_name, {})
            if not cleaned_data.get('notes_comments') and product_data.get('notes_comments'):
                cleaned_data['notes_comments'] = product_data['notes_comments']
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.supplier_code = instance.supplier_code or "N/A"
        instance.variety_or_species = instance.variety_or_species or "N/A"
        instance.packaging_condition = instance.packaging_condition or "N/A"
        if self.cleaned_data.get('weight_quantity'):
            instance.weight_quantity_kg = round(self.cleaned_data['weight_quantity'] / 1000, 2)
        instance.status = 'In Stock'
        if self.cleaned_data.get('unit_price') and self.cleaned_data.get('quantity_in_stock'):
            instance.total_value = self.cleaned_data['unit_price'] * self.cleaned_data['quantity_in_stock']

        metadata = get_product_metadata()
        product_data = metadata.get(self.cleaned_data['product_name'], {})
        instance.product_type = product_data.get('product_type', instance.product_type)

        date_from_form = self.cleaned_data.get('harvest_date')
        if date_from_form:
            if instance.product_type == 'Raw':
                instance.harvest_date = date_from_form
                instance.manufacturing_date = None
            elif instance.product_type == 'Processed':
                instance.manufacturing_date = date_from_form
                instance.harvest_date = None

        if instance.storage_temperature is None and product_data.get('storage_temperature'):
            temp_str = product_data['storage_temperature']
            temp_values = [float(x) for x in temp_str.split("-") if x.strip()]
            instance.storage_temperature = f"{sum(temp_values) / len(temp_values):.2f}" if temp_values else None

        if instance.humidity_rate is None and product_data.get('humidity_rate'):
            humidity_str = product_data['humidity_rate']
            humidity_cleaned = ''.join(c for c in humidity_str if c.isdigit() or c == '-' or c == '.')
            humidity_values = [float(x) for x in humidity_cleaned.split("-") if x.strip()]
            instance.humidity_rate = f"{sum(humidity_values) / len(humidity_values):.2f}" if humidity_values else humidity_cleaned or None

        if instance.co2 is None and product_data.get('CO2 (%)'):
            try:
                instance.co2 = f"{float(product_data['CO2 (%)'].replace('<', '').replace('>', '').strip()):.2f}"
            except Exception:
                instance.co2 = None

        if instance.o2 is None and product_data.get('O2 (%)'):
            try:
                instance.o2 = f"{float(product_data['O2 (%)'].replace('<', '').replace('>', '').strip()):.2f}"
            except Exception:
                instance.o2 = None

        if instance.n2 is None and product_data.get('n2') and product_data['n2'] != 'Balance':
            try:
                instance.n2 = f"{float(product_data['n2'].replace('<', '').replace('>', '').strip()):.2f}"
            except Exception:
                instance.n2 = None

        if not instance.ethylene_management and product_data.get('ethylene_management'):
            instance.ethylene_management = product_data['ethylene_management']

        if commit:
            instance.save()
        return instance