from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django import forms
from .models import Warehouse,Product,get_product_metadata,ItemRequest
from apps.authentication.models import CustomUser
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
import decimal
from decimal import Decimal

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
    client = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-users',  # Add class for Select2
            'multiple': 'multiple',  # Ensure multiple selection
        })
    )
    farmer = forms.ModelMultipleChoiceField(
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
            'client',  # Add client
            'farmer',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'total_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'available_space': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'zone_layout': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            # 'users' is defined above with SelectMultiple
            'users': forms.SelectMultiple(attrs={'class': 'form-control select2-users', 'multiple': 'multiple'}),
            'client': forms.SelectMultiple(attrs={'class': 'form-control select2-users', 'multiple': 'multiple'}),
            'farmer': forms.SelectMultiple(attrs={'class': 'form-control select2-users', 'multiple': 'multiple'}),
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
        # If this is an existing instance (editing a warehouse)
        if self.instance and self.instance.pk:
            warehouse_owner = self.instance.ownership if hasattr(self.instance, 'ownership') else None
            if warehouse_owner:
                base_qs = CustomUser.objects.filter(owner=warehouse_owner)
                self.fields['users'].queryset = base_qs
                self.fields['client'].queryset = base_qs.filter(is_client=True)
                self.fields['farmer'].queryset = base_qs.filter(is_farmer=True)
                # Set initial values from existing warehouse.users
                current_users = self.instance.users.all()
                self.fields['users'].initial = current_users
                self.fields['client'].initial = current_users.filter(is_client=True)
                self.fields['farmer'].initial = current_users.filter(is_farmer=True)
        elif user:
            base_qs = CustomUser.objects.filter(owner=user)
            self.fields['users'].queryset = base_qs
            self.fields['client'].queryset = base_qs.filter(is_client=True)
            self.fields['farmer'].queryset = base_qs.filter(is_farmer=True)
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
        users = cleaned_data.get('users', [])
        clients = cleaned_data.get('client', [])
        farmers = cleaned_data.get('farmer', [])
        all_users = set(users) | set(clients) | set(farmers)  # Union of all selected users
        cleaned_data['users'] = list(all_users)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # Save the combined users list to the users field
            self.instance.users.set(self.cleaned_data['users'])
        return instance

PACKAGING_CONDITIONS = {
    "Bacs alimentaires hermétiques": "kgs",
    "Barquette": "kgs",
    "Barquette aérée": "kgs",
    "Barquette PET": "kgs",
    "Barquette PET perforée": "kgs",
    "Barquette ventilée": "kgs",
    "Bidon plastique": "liters",
    "Bocal hermétique": "liters",
    "Boîte": "kgs",
    "Boîte hermétique": "kgs",
    "Botte ou filet": "kgs",
    "Bouteille": "liters",
    "Bouteille hermétique": "liters",
    "Cageots": "kgs",
    "Cageots ajourés": "kgs",
    "Caisse ajourée": "kgs",
    "Caisse carton": "kgs",
    "Caisse en bois": "kgs",
    "Caisse plastique": "kgs",
    "Caisse plastique ajourée": "kgs",
    "Caisse rigide": "kgs",
    "Caisse rigide ventilée": "kgs",
    "Carton perforé": "kgs",
    "Cartons ventilés, alvéolés ou avec mousse": "kgs",
    "Contenants opaques": "kgs",
    "Emballage sous vide": "kgs",
    "Filet en polypropylène": "kgs",
    "Panier rigide": "kgs",
    "Papier absorbant": "kgs",
    "Plastique alimentaire": "kgs",
    "Plastique hermétique": "kgs",
    "Plateau": "kgs",
    "Plateau carton avec alvéoles": "kgs",
    "Plateaux avec séparateurs": "kgs",
    "Pot en verre": "kgs",
    "Pot hermétique": "kgs",
    "Sac kraft": "kgs",
    "Sac aéré": "kgs",
    "Sac alimentaire en jute": "kgs",
    "Sac alimentaires": "kgs",
    "Sac aluminium": "kgs",
    "Sac en filet": "kgs",
    "Sac en jute": "kgs",
    "Sac en polypropylène": "kgs",
    "Sac en toile": "kgs",
    "Sac plastique doublé": "kgs",
    "Sac tissé": "kgs",
    "Sachet alimentaire": "kgs",
    "Sachet aluminium": "kgs",
    "Sachet aluminium opaque": "kgs",
    "Sachet hermétique": "kgs",
    "Sachet kraft": "kgs",
    "Sachet opaque scellé": "kgs",
    "Sachet plastique": "kgs",
    "Sachet plastique alimentaire": "kgs",
    "Sachet plastique multicouche": "kgs",
    "Sachet plastique opaque": "kgs",
    "Sachet scellé": "kgs",
    "Sachet scellé avec absorption d'humidité": "kgs",
    "Sachet scellé sous vide": "kgs",
    "Sachets hermétiques": "kgs",
    "Sachets hermétiques scellés": "kgs",
    "Sachets plastiques alimentaires": "kgs",
    "Sacs en toile": "kgs",
    "Sacs en toile alimentaire": "kgs",
    "Sacs kraft": "kgs",
    "Sacs sous vide": "kgs",
    "Sans conditionnement- En Vrac": "kgs",
    "Seau hermétique": "liters"
}
CATEGORY_CHOICES = [
    ('', 'Select a category'),
    ('cereal', 'Cereal'),
    ('fruit jam', 'Confiture de fruit'),
    ('flour', 'Farine'),
    ('fruit flour', 'Farine de fruit'),
    ('hibiscus flower', 'Fleur d’hibiscus'),
    ('fruit', 'Fruit'),
    ('gum resin', 'Gomme / Résine'),
    ('seed', 'Graine'),
    ('medicinal seed', 'Graine médicinale'),
    ('herb', 'Herbe'),
    ('juice', 'Jus'),
    ('vegetable', 'Légume'),
    ('vegetable spice', 'Légume / Épice'),
    ('leaf vegetable', 'Légume-feuille'),
    ('processed vegetable', 'Légume transformé'),
    ('legume', 'Légumineuse'),
    ('vegetable fat', 'Matière grasse végétale'),
    ('nut', 'Noix'),
    ('nut legume mix', 'Noix / Légumineuse'),
    ('nut paste', 'Pâte de noix'),
    ('medicinal plant', 'Plante médicinale'),
    ('spice powder', 'Poudre d’épice'),
    ('fruit powder', 'Poudre de fruit'),
    ('vegetable powder', 'Poudre de légume'),
    ('root powder', 'Poudre de racine'),
    ('medicinal powder', 'Poudre médicinale'),
    ('plant powder', 'Poudre végétale'),
    ('animal product', 'Produit animal'),
    ('tree product', 'Produit d’arbre'),
    ('seed product', 'Produit de graine'),
    ('bee product', 'Produit de l’abeille'),
    ('fish product', 'Produit de poisson'),
    ('fruit pulp', 'Pulpe de fruit'),
    ('root', 'Racine'),
    ('spice root', 'Racine d’épice'),
    ('syrup', 'Sirop'),
    ('tuber', 'Tubercule'),
    ('spice', 'Épice'),
]
CATEGORY_CHOICES = [CATEGORY_CHOICES[0]] + sorted(
    CATEGORY_CHOICES[1:], key=lambda x: x[1].lower()
)
Product_Condition_CHOICES = [
    ('', 'Select product state'),
    ('dry', 'Sec'),
    ('dried pulp', 'Pulpe séchée'),
    ('fresh', 'Frais'),
    ('dry grain', 'Grain sec'),
    ('dry powder', 'Sec / Poudre'),
    ('powder', 'Poudre'),
    ('paste', 'Pâte'),
    ('solid fat', 'Graisse solide'),
    ('processed compressed', 'Transformé / Compressé'),
    ('jam', 'Confiture'),
    ('liquid', 'Liquide'),
    ('dried pod', 'Gousse sèche'),
    ('dried leaves', 'Feuilles séchées'),
    ('frozen', 'Congelé'),
    ('bulk dry', 'Sec (vrac)'),
    ('fresh leaves', 'Feuilles fraîches'),
    ('grilled', 'Grillé'),
    ('processed grain', 'Grain transformé'),
    ('grilled processed', 'Grillé / Transformé'),
]


class ProductForm(forms.ModelForm):
    packaging_condition = forms.ChoiceField(
        choices=[(key, key) for key in PACKAGING_CONDITIONS.keys()],
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'required': True,
            'aria-label': 'Packaging Condition',
        })
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=True,
        label="Category",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'required': True,
            'aria-label': 'Category',
        })
        )
    product_condition = forms.ChoiceField(
        choices=Product_Condition_CHOICES,
        required=True,
        label="Product Condition",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'required': True,
            'aria-label': 'Product Condition',
        })
    )

    class Meta:
        model = Product
        exclude = [
            'warehouse', 'total_value', 'weight_quantity', 'status', 'exit_date',
            'manufacturing_date', 'supplier_code',
            'quality_standards', 'nutritional_info', 'regulatory_codes',
            'product_type', 'lot_number'
        ]
        widgets = {
            'quantity_in_stock': forms.NumberInput(attrs={
                'step': '1',
                'onkeypress': "return (event.charCode != 101 && event.charCode != 69);",
                'oninput': "this.value = this.value.replace(/[eE]/g, '');",
                'aria-describedby': 'quantityHelp',
                'class': 'form-control form-control-lg'
            }),
            'weight_per_bag_kg': forms.NumberInput(attrs={
                'step': '1',
                'onkeypress': "return (event.charCode != 101 && event.charCode != 69);",
                'oninput': "this.value = this.value.replace(/[eE]/g, '');",
                'aria-describedby': 'weightPerBagHelp',
                'class': 'form-control form-control-lg'
            }),
            'weight_quantity_kg': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'readonly': 'readonly',
                'class': 'form-control form-control-lg'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '4',
                'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Enter product description...',
                'aria-label': 'Description'
            }),
            'variety_or_species': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': '',
                'aria-label': 'variety'
            }),
            'origin': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': '',
                'aria-label': 'origin'
            }),

            'supplier_brand': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., Organic Farms',
                'aria-label': 'Supplier Brand'
            }),
            'unit_of_measure': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., kg',
                'aria-label': 'Unit of Measure'
            }),
            'physical_dimensions': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., 20x30x40 cm',
                'aria-label': 'Physical Dimensions'
            }),
            'certifications': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '4',
                'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Enter certifications...',
                'aria-label': 'Certifications'
            }),
            'minimum_threshold': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., 10',
                'aria-label': 'Minimum Threshold'
            }),
            'storage_temperature': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., 10',
                'aria-label': 'Storage Temperature'
            }),
            'humidity_rate': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Recommended Humidity e.g., 10',
                'aria-label': 'Humidity rate'
            }),
            'co2': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Recommended CO2 e.g., 10',
                'aria-label': 'CO2'
            }),
            'o2': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Recommended O2 e.g., 10',
                'aria-label': 'O2'
            }),
            'n2': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Recommended N2 e.g., 10',
                'aria-label': 'N2'
            }),
            'ethylene_management': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Recommended Ethylene Levels e.g., 10',
                'aria-label': 'Ethylene Level'
            }),

            'maximum_threshold': forms.NumberInput(attrs={
                'step': '1',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., 100',
                'aria-label': 'Maximum Threshold'
            }),
            'selling_unit_price': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., 29.99',
                'aria-label': 'Selling Unit Price'
            }),
            'storage_cost': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'e.g., 5.00',
                'aria-label': 'Storage Cost'
            }),
        }

    def __init__(self, *args, warehouse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if warehouse is None and self.instance and self.instance.pk and self.instance.warehouse:
            warehouse = self.instance.warehouse
        if warehouse and warehouse.ownership:
            self.fields['farmer'].queryset = CustomUser.objects.filter(
                is_farmer=True,
                owner=warehouse.ownership
            )
            self.fields['farmer'].required = True
            self.fields['farmer'].widget.attrs.update({
                'class': 'form-select form-select-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'required': True,
                'aria-label': 'Farmer',
            })
        common_attrs = {
            'class': 'form-control form-control-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
        }

        self.fields['sku'].widget.attrs.update({
            **common_attrs,
            # 'readonly': 'readonly',  # Make SKU read-only
            'placeholder': 'Auto-generated',
            'aria-label': 'Stock Keeping Unit',
        })
        self.fields['barcode'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'Auto-generated for Raw, enter for Processed',
            'aria-label': 'Barcode',
        })
        self.fields['product_name'].widget.attrs.update({
            'class': 'form-select form-select-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'required': True,
            'aria-label': 'Product Name',
        })
        self.fields['weight_quantity_kg'] = forms.DecimalField(
            max_digits=100000000000,
            decimal_places=2,
            help_text="Total weight of the product in kilograms (editable for Bulk)",
            widget=forms.NumberInput(attrs={
                **common_attrs,
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 0.50 (in kg)',
                'required': True,
                'aria-label': 'Weight in Kilograms',
            })
        )
        self.fields['weight_per_bag_kg'] = forms.DecimalField(
            max_digits=100000000000,
            decimal_places=2,
            help_text="Total weight of the product in kilograms (editable for Bulk)",
            widget=forms.NumberInput(attrs={
                **common_attrs,
                'step': '0.01',
                'min': '0',
                'placeholder': '',
                'required': True,
                'aria-label': 'Per Bag Quantity',
            })
        )
        self.fields['quantity_in_stock'].widget.attrs.update({
            **common_attrs,
            'min': '0',
            'placeholder': 'e.g., 100',
            'required': False,
            'aria-label': 'Quantity in Stock',
        })
        self.fields['unit_price'].widget.attrs.update({
            **common_attrs,
            'step': '0.01',
            'min': '0',
            'placeholder': 'e.g., 19.99',
            'required': True,
            'aria-label': 'Unit Price',
        })
        self.fields['purchase_unit_price'].widget.attrs.update({
            **common_attrs,
            'step': '0.01',
            'min': '0',
            'placeholder': 'e.g., 19.99',
            'required': False,
            'aria-label': 'Unit Price',
        })
        self.fields['storage_cost'].widget.attrs.update({
            **common_attrs,
            'step': '0.01',
            'min': '0',
            'placeholder': 'e.g., 19.99',
            'required': False,
            'aria-label': 'Unit Price',
        })
        self.fields['harvest_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            **common_attrs,
            'placeholder': 'Select harvest date',
            'aria-label': 'Harvest Date',
            'required' : True,
        })
        self.fields['expiration_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            **common_attrs,
            'placeholder': 'Select harvest date',
            'aria-label': 'Expiration Date',

        })
        self.fields['entry_date'].widget = forms.DateInput(attrs={
            'type': 'date',
            **common_attrs,
            'value': timezone.now().date().isoformat(),
            'aria-label': 'Entry Date',
            'required': True,
        })
        self.fields['farmer'].widget.attrs.update({
            'class': 'form-select form-select-lg',
            'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'aria-label': 'Farmer',
        })
        self.fields['notes_comments'].widget.attrs.update({
            'class': 'form-control',
            'rows': '4',
            'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'placeholder': 'Add any additional notes or comments...',
            'aria-label': 'Notes or Comments',
        })
        self.fields['description'].widget.attrs.update({
            **common_attrs,
            'rows': '4',
            'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'placeholder': 'Enter product description...',
            'aria-label': 'Description',
        })
        self.fields['category'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'e.g., Fruits',
            'aria-label': 'Category',
        })
        self.fields['supplier_brand'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'e.g., Organic Farms',
            'aria-label': 'Supplier Brand',
        })
        self.fields['unit_of_measure'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'e.g., kg',
            'aria-label': 'Unit of Measure',
        })
        self.fields['physical_dimensions'].widget.attrs.update({
            **common_attrs,
            'placeholder': 'e.g., 20x30x40 cm',
            'aria-label': 'Physical Dimensions',
        })
        self.fields['certifications'].widget.attrs.update({
            **common_attrs,
            'rows': '4',
            'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
            'placeholder': 'Enter certifications...',
            'aria-label': 'Certifications',
        })
        self.fields['minimum_threshold'].widget.attrs.update({
            **common_attrs,
            'min': '0',
            'placeholder': 'e.g., 10',
            'aria-label': 'Minimum Threshold',
        })
        self.fields['maximum_threshold'].widget.attrs.update({
            **common_attrs,
            'min': '0',
            'placeholder': 'e.g., 100',
            'aria-label': 'Maximum Threshold',
        })


        self.fields['weight_per_bag_kg'].initial = self.instance.weight_per_bag_kg if self.instance and self.instance.pk else None
        self.fields['harvest_date'].required = False
        self.fields['farmer'].required = False
        self.fields['notes_comments'].required = False
        self.fields['description'].required = False
        self.fields['category'].required = False
        self.fields['supplier_brand'].required = False
        self.fields['unit_of_measure'].required = False
        self.fields['physical_dimensions'].required = False
        self.fields['certifications'].required = False
        self.fields['minimum_threshold'].required = False
        self.fields['maximum_threshold'].required = False

    def clean(self):
        cleaned_data = super().clean()
        product_name = cleaned_data.get('product_name')
        packaging_condition = cleaned_data.get('packaging_condition')
        quantity_in_stock = cleaned_data.get('quantity_in_stock')
        weight_quantity_kg = cleaned_data.get('weight_quantity_kg')
        weight_per_bag_kg = cleaned_data.get('weight_per_bag_kg')
        product_type = get_product_metadata().get(product_name, {}).get('product_type', 'Raw')

        # Validate product_type-specific fields
        #if product_type == 'Raw' and not cleaned_data.get('harvest_date'):
        #    raise ValidationError("Harvest date is required for raw products.")
        #if product_type == 'Processed' and cleaned_data.get('harvest_date'):
        #    raise ValidationError("Harvest date should not be set for processed products.")

        if product_name:
            metadata = get_product_metadata()
            product_data = metadata.get(product_name, {})
            if not cleaned_data.get('notes_comments') and product_data.get('notes_comments'):
                cleaned_data['notes_comments'] = product_data['notes_comments']

        if packaging_condition == "Bulk":
            if weight_per_bag_kg is not None:
                cleaned_data['weight_per_bag_kg'] = None
            if quantity_in_stock is not None:
                cleaned_data['quantity_in_stock'] = None
        else:
            if quantity_in_stock is None:
                raise ValidationError("Quantity in stock is required for non-Bulk packaging.")
            expected_package_weight = PACKAGING_CONDITIONS.get(packaging_condition)
            if isinstance(expected_package_weight, (int, float)):
                expected_package_weight_decimal = Decimal(str(expected_package_weight))
                if weight_per_bag_kg is not None and abs(weight_per_bag_kg - expected_package_weight_decimal) > 0.01:
                    raise ValidationError(
                        f"Weight per bag must be {expected_package_weight} kg for {packaging_condition}."
                    )
                cleaned_data['weight_per_bag_kg'] = expected_package_weight_decimal
            elif isinstance(expected_package_weight, list):
                if weight_per_bag_kg is None:
                    raise ValidationError(f"Weight per bag is required for {packaging_condition}.")
                if weight_per_bag_kg not in expected_package_weight:
                    raise ValidationError(
                        f"Weight per bag must be one of {expected_package_weight} kg for {packaging_condition}."
                    )
            else:
                if weight_per_bag_kg is None:
                    raise ValidationError(f"Weight per bag is required for {packaging_condition}.")

            if weight_per_bag_kg is not None and quantity_in_stock is not None:
                calculated_weight_kg = weight_per_bag_kg * quantity_in_stock
                if weight_quantity_kg is not None and abs(weight_quantity_kg - calculated_weight_kg) > 0.01:
                    raise ValidationError(
                        "Total weight (kg) must match weight per bag (kg) × quantity in stock."
                    )
                cleaned_data['weight_quantity_kg'] = calculated_weight_kg

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.supplier_code = None
        instance.variety_or_species = None
        instance.packaging_condition = self.cleaned_data.get('packaging_condition') or None
        instance.weight_per_bag_kg = self.cleaned_data.get('weight_per_bag_kg')

        if self.cleaned_data.get('weight_quantity_kg'):
            instance.weight_quantity = self.cleaned_data['weight_quantity_kg'] * 1000

        if self.cleaned_data.get('unit_price') and self.cleaned_data.get('weight_quantity_kg'):
            instance.total_value = self.cleaned_data['unit_price'] * self.cleaned_data['weight_quantity_kg']
        else:
            instance.total_value = 0

        metadata = get_product_metadata()
        product_data = metadata.get(self.cleaned_data['product_name'], {})
        instance.product_type = product_data.get('product_type', instance.product_type or 'Raw')

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


class ItemRequestForm(forms.ModelForm):
    class Meta:
        model = ItemRequest
        fields = ['warehouse', 'client', 'product_name', 'weight_requested_kg', 'notes']
        widgets = {
            'warehouse': forms.Select(attrs={
                'class': 'form-control form-select-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'required': True,
                'aria-label': 'Warehouse',
            }),
            'client': forms.Select(attrs={
                'class': 'form-control form-select-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'required': True,
                'aria-label': 'Client',
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'required': True,
                'placeholder': 'Enter product name',
                'aria-label': 'Product Name',
            }),
            'weight_requested_kg': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'style': 'border-radius: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'step': '0.01',
                'min': '0',
                'required': True,
                'placeholder': 'Enter weight in kg',
                'aria-label': 'Weight Requested (kg)',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'style': 'border-radius: 8px; resize: vertical; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);',
                'placeholder': 'Additional notes (optional)',
                'aria-label': 'Notes',
            }),
        }

    def __init__(self, *args, user=None, warehouse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Limit warehouse choices to those the user has access to
            self.fields['warehouse'].queryset = Warehouse.objects.filter(users=user)
            self.fields['client'].queryset = CustomUser.objects.filter(id=user.id, is_client=True)
            self.fields['client'].initial = user
        if warehouse:
            self.fields['warehouse'].queryset = Warehouse.objects.filter(id=warehouse.id)
            self.fields['warehouse'].initial = warehouse
            # Optionally limit product_name choices based on warehouse (could use a Select widget with dynamic choices)
            available_products = Product.objects.filter(
                warehouse=warehouse,
                status='In Stock'
            ).values_list('product_name', flat=True).distinct()
            self.fields['product_name'].widget = forms.Select(
                choices=[(name, name) for name in available_products],
                attrs=self.fields['product_name'].widget.attrs
            )

    def clean(self):
        cleaned_data = super().clean()
        warehouse = cleaned_data.get('warehouse')
        client = cleaned_data.get('client')
        product_name = cleaned_data.get('product_name')
        weight_requested_kg = cleaned_data.get('weight_requested_kg')

        if warehouse and client and product_name:
            # Check client access to warehouse
            if client not in warehouse.users.all():
                raise ValidationError("Client does not have access to this warehouse.")

            # Check product availability
            available_products = Product.objects.filter(
                warehouse=warehouse,
                product_name=product_name,
                status='In Stock'
            )
            if not available_products.exists():
                raise ValidationError(f"Product '{product_name}' is not available in this warehouse.")

            total_weight = sum(p.weight_quantity_kg or 0 for p in available_products)
            if weight_requested_kg and weight_requested_kg > total_weight:
                raise ValidationError(f"Requested weight ({weight_requested_kg} kg) exceeds available weight ({total_weight} kg).")

        if weight_requested_kg is None or weight_requested_kg <= 0:
            raise ValidationError("Weight requested must be greater than 0.")

        return cleaned_data

    def save(self, commit=True, max_unit_price=None):
        instance = super().save(commit=False)
        if max_unit_price:
            instance.total_price = instance.calculate_total_price(decimal.Decimal(str(max_unit_price)))
        if commit:
            instance.save()
        return instance

class ProductMetadataForm(forms.Form):
    Product = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter product name',
            'aria-label': 'Product Name',
        })
    )
    Ethylene_Management = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter ethylene management strategy',
            'aria-label': 'Ethylene Management',
        })
    )
    Ideal_Temperature_C = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 20-25',
            'aria-label': 'Ideal Temperature (C)',
        })
    )
    Relative_Humidity = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 50-60 or <50',
            'aria-label': 'Relative Humidity (%)',
        })
    )
    Maximum_Storage_Duration_days = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 720',
            'aria-label': 'Maximum Storage Duration (days)',
        })
    )
    CO2 = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., <1 or -',
            'aria-label': 'CO2 (%)',
        })
    )
    O2 = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., <5 or -',
            'aria-label': 'O2 (%)',
        })
    )
    N2 = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., >95 or -',
            'aria-label': 'N2 (%)',
        })
    )
    Additional_Notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter additional notes',
            'aria-label': 'Additional Notes',
        })
    )
    Product_Type = forms.ChoiceField(
        choices=[('Raw', 'Raw'), ('Processed', 'Processed')],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'aria-label': 'Product Type',
        })
    )

    def clean_Product(self):
        product_name = self.cleaned_data['Product']
        if not product_name:
            raise forms.ValidationError("Product name is required.")
        return product_name

    def clean_Maximum_Storage_Duration_days(self):
        duration = self.cleaned_data.get('Maximum_Storage_Duration_days')
        if duration is not None and duration < 0:
            raise forms.ValidationError("Maximum storage duration cannot be negative.")
        return duration