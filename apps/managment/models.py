import decimal

from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
import json,os
from dateutil.relativedelta import relativedelta
import uuid
from django.utils import timezone
from apps.authentication.models import CustomUser
from django.db.models import Max

class Warehouse(models.Model):
    WAREHOUSE_TYPES = [
        ('general', 'Entrepôt général 📦'),
        ('cold_storage', 'Chambre froide / Réfrigéré ❄️'),
        ('dry_storage', 'Stockage sec 🌾'),
        ('climate_controlled', 'Stockage à climat contrôlé 🌿'),
        ('bulk_storage', 'Silo / Stockage en vrac 🏗'),
        ('freezer', 'Chambre de congélation 🧊'),
        ('processing_packaging', 'Zone de transformation & emballage 🏭'),
        ('chemical_storage', 'Entrepôt pour produits chimiques ⚠️'),
        ('bonded', 'Entrepôt sous douane 🛃'),
        ('seasonal', 'Stockage saisonnier / temporaire ⛺'),
    ]
    WAREHOUSE_TYPES = sorted(WAREHOUSE_TYPES, key=lambda x: x[0])
    name = models.CharField(max_length=255, help_text="Name of the warehouse")
    ownership = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_warehouses",
        help_text="Owner of the warehouse"
    )
    type = models.CharField(
        max_length=50,
        choices=WAREHOUSE_TYPES,
        default='general',
        help_text="Type of warehouse"
    )
    location = models.CharField(max_length=255, help_text="Geographical location of the warehouse")
    total_capacity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total storage capacity in square meters")
    available_space = models.DecimalField(max_digits=10, decimal_places=2, help_text="Available storage space in square meters")
    utilization_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of utilized space (0-100)")
    zone_layout = models.TextField(blank=True, null=True, help_text="Description or diagram of the warehouse zone layout")
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="warehouses",
        blank=True,
        help_text="Users associated with this warehouse"
    )
    slug = models.SlugField(unique=True, blank=True, help_text="Unique slug for the warehouse URL")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Check warehouse limits using the new plan limits system
        current_warehouse_count = self.ownership.owned_warehouses.exclude(id=self.id).count()
        if not self.ownership.can_create_warehouse(current_warehouse_count):
            raise ValidationError(
                f"Plan limit exceeded. You can only create {self.ownership.warehouse_limit} warehouses with your {self.ownership.subscription_plan} plan."
            )

        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            num = 1
            while Warehouse.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{num}"
                num += 1
            self.slug = unique_slug

        if self.total_capacity < self.available_space:
            raise ValidationError("Total capacity cannot be less than available space.")

        if self.total_capacity > 0:
            used_space = self.total_capacity - self.available_space
            self.utilization_rate = (used_space / self.total_capacity) * 100

        super(Warehouse, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
@receiver(pre_save, sender=Warehouse)
def assign_owner(sender, instance, **kwargs):
    if not instance.ownership:  # If no owner is assigned
        if hasattr(instance, 'creator') and instance.creator:
            instance.ownership = instance.creator

# class Farmer(models.Model):
#     farmer_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Unique ID assigned to the farmer")
#     name = models.CharField(max_length=255, help_text="Full name of the farmer")
#     contact_number = models.CharField(max_length=20, blank=True, null=True, help_text="Primary contact number of the farmer")
#     email = models.EmailField(max_length=255, blank=True, null=True, unique=True, help_text="Email address of the farmer")
#     address = models.TextField(help_text="Physical address of the farmer")
#     farm_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the farm")
#     farm_location = models.CharField(max_length=255, help_text="Geographical location of the farm")
#     total_land_area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Total area of the farm in hectares")
#     certifications = models.TextField(blank=True, null=True, help_text="List of certifications held by the farmer")
#     compliance_standards = models.TextField(blank=True, null=True, help_text="Compliance standards followed by the farmer")
#     notes = models.TextField(blank=True, null=True, help_text="Additional notes or comments about the farmer")
#     registration_date = models.DateField(null=True, blank=True, help_text="Date of Registration")
#     owner = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="farmer_owner",
#         help_text="Owner of the farmer"
#     )
#
#     def __str__(self):
#         return f"{self.name} ({self.farm_name or 'No Farm Name'})"
#
#     def clean(self):
#         if self.total_land_area and self.total_land_area < 0:
#             raise ValidationError("Total land area cannot be negative.")
#
#     class Meta:
#         verbose_name = "Farmer"
#         verbose_name_plural = "Farmers"
#         indexes = [models.Index(fields=['farmer_id', 'name'])]


JSON_FILE_PATH = os.path.join(settings.BASE_DIR.parent, 'apps', 'managment', 'products.json')

# Global variable to store metadata
_product_metadata_cache = None


def load_product_metadata():
    """Load and parse the product metadata from the JSON file without modifying values."""
    global _product_metadata_cache
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)

        # Parse the JSON into a usable dictionary
        metadata = {}
        for item in data:
            product_name = item["Product"]
            metadata[product_name] = {
                "storage_temperature": item['Ideal Temperature (C)'],
                "humidity_rate": item['Relative Humidity (%)'],  # Assuming months in JSON
                "CO2 (%)": item["CO2 (%)"],
                "O2 (%)": item["O2 (%)"],
                "n2": item['N2 (%)'],
                "ethylene_management": item["Ethylene Management"],
                "notes_comments": item["Additional Notes"],
                "product_type": item["Product Type"],
                "Maximum Storage Duration (days)": item["Maximum Storage Duration (days)"],
                "Additional Notes": item["Additional Notes"]
            }
        _product_metadata_cache = metadata
        return metadata
    except FileNotFoundError:
        print(f"Warning: JSON file not found at {JSON_FILE_PATH}. Using empty metadata.")
        _product_metadata_cache = {}
        return {}
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in {JSON_FILE_PATH}")


def get_product_metadata():
    """Get the cached metadata, loading it if not already loaded."""
    global _product_metadata_cache
    if _product_metadata_cache is None:
        _product_metadata_cache = load_product_metadata()
    return _product_metadata_cache


def refresh_product_metadata():
    """Force reload of the JSON file."""
    global _product_metadata_cache
    _product_metadata_cache = load_product_metadata()


# Generate PRODUCT_CHOICES dynamically with a fallback
JSON_FILE_PATH = os.path.join(settings.BASE_DIR.parent, 'apps', 'managment', 'products.json')
_product_metadata_cache = None

def load_product_metadata():
    """Load and parse the product metadata from the JSON file without modifying values."""
    global _product_metadata_cache
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        metadata = {}
        for item in data:
            product_name = item["Product"]
            metadata[product_name] = {
                "storage_temperature": item['Ideal Temperature (C)'],
                "humidity_rate": item['Relative Humidity (%)'],
                "CO2 (%)": item["CO2 (%)"],
                "O2 (%)": item["O2 (%)"],
                "n2": item['N2 (%)'],
                "ethylene_management": item["Ethylene Management"],
                "notes_comments": item["Additional Notes"],
                "product_type": item["Product Type"],
                "Maximum Storage Duration (days)": item["Maximum Storage Duration (days)"],
                "Additional Notes": item["Additional Notes"]
            }
        _product_metadata_cache = metadata
        return metadata
    except FileNotFoundError:
        print(f"Warning: JSON file not found at {JSON_FILE_PATH}. Using empty metadata.")
        _product_metadata_cache = {}
        return {}
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in {JSON_FILE_PATH}")

def get_product_metadata():
    """Get the cached metadata, loading it if not already loaded."""
    global _product_metadata_cache
    if _product_metadata_cache is None:
        _product_metadata_cache = load_product_metadata()
    return _product_metadata_cache

def refresh_product_metadata():
    """Force reload of the JSON file."""
    global _product_metadata_cache
    _product_metadata_cache = load_product_metadata()
def generate_lot_number():
    """Generate a unique lot number based on date and UUID."""
    date_prefix = timezone.now().strftime('%Y%m%d')  # e.g., 20250305
    unique_suffix = uuid.uuid4().hex[:6].upper()     # 6-character unique hex
    return f"LOT-{date_prefix}-{unique_suffix}"
def get_product_choices():
    """Dynamically generate product choices from metadata."""
    return [(name, name) for name in sorted(get_product_metadata().keys())]
PRODUCT_CHOICES = [(name, name) for name in get_product_metadata().keys()]

class Product(models.Model):
    sku = models.CharField(max_length=50, help_text="Stock Keeping Unit", db_index=True)
    barcode = models.CharField(max_length=50, help_text="Unique barcode identifier", db_index=True)
    product_name = models.CharField(
        max_length=255,
        choices=get_product_choices,
        help_text="Name of the product",
        db_index=True
    )
    description = models.TextField(blank=True, null=True, help_text="Description of the product")
    category = models.CharField(max_length=255, blank=True, null=True, help_text="Category of the product")
    supplier_brand = models.CharField(max_length=255, blank=True, null=True, help_text="Brand provided by the supplier")
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True, help_text="Unit of measure for the product (e.g., kg, liters)")
    physical_dimensions = models.CharField(max_length=255, blank=True, null=True, help_text="Physical dimensions of the product (e.g., LxWxH in cm)")
    certifications = models.TextField(blank=True, null=True, help_text="Certifications or compliance standards of the product")
    minimum_threshold = models.PositiveIntegerField(blank=True, null=True, help_text="Minimum stock threshold for reordering")
    maximum_threshold = models.PositiveIntegerField(blank=True, null=True, help_text="Maximum stock threshold for storage")
    origin = models.CharField(max_length=255, null=True, blank=True, help_text="Country or region of origin")
    lot_number = models.CharField(
        max_length=100,
        unique=True,
        default=generate_lot_number,
        editable=False,
        help_text="Auto-generated unique lot number for batch identification"
    )
    harvest_date = models.DateField(null=True, blank=True, help_text="Date of harvest")
    entry_date = models.DateField(default=now, help_text="Date when the product entered the warehouse", db_index=True)
    manufacturing_date = models.DateField(null=True, blank=True, help_text="Date of manufacturing")
    expiration_date = models.DateField(null=True, blank=True, help_text="Date when the product expires", db_index=True)
    exit_date = models.DateField(null=True, blank=True, help_text="Date when the product exits the warehouse")
    supplier_code = models.CharField(max_length=100, null=True, blank=True, help_text="Code assigned to the supplier")
    product_type = models.CharField(
        max_length=100,
        choices=[('Raw', 'Raw'), ('Processed', 'Processed')],
        default='RAW',
        help_text="Type of product"
    )
    variety_or_species = models.CharField(max_length=255, null=True, blank=True,
                                          help_text="Variety or species of the product")
    packaging_condition = models.CharField(max_length=255, null=True, blank=True,
                                           help_text="Condition of the packaging")
    product_condition = models.CharField(max_length=255, null=True, blank=True,help_text="Condition of the product")
    weight_quantity = models.DecimalField(max_digits=1000000000, decimal_places=2,
                                          help_text="Weight or quantity of the product (in default units)")
    weight_quantity_kg = models.DecimalField(max_digits=100000000000, decimal_places=2, null=True, blank=True,
                                             help_text="Weight of the product in kilograms")
    weight_per_bag_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight per bag or container in kilograms"
    )
    quantity_in_stock = models.PositiveIntegerField(help_text="Quantity available in stock",null=True, blank=True,)
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="products",
        help_text="Warehouse where the product is stored"
    )
    status = models.CharField(
        max_length=100,
        choices=[('In Stock', 'In Stock'), ('Out of Stock', 'Out of Stock'), ('Expired', 'Expired')],
        default='In Stock',
        help_text="Current status of the product"
    )
    quality_standards = models.TextField(blank=True, null=True, help_text="Quality standards met by the product")
    humidity_rate = models.CharField(max_length=10, null=True, blank=True,
                                     help_text="Humidity rate in percentage (e.g., '50.25')")
    storage_temperature = models.CharField(max_length=10, null=True, blank=True,
                                           help_text="Storage temperature in degrees Celsius (e.g., '-2.50')")
    co2 = models.CharField(max_length=10, null=True, blank=True,
                           help_text="CO₂ concentration in percentage (e.g., '5.00')")
    o2 = models.CharField(max_length=10, null=True, blank=True,
                          help_text="O₂ concentration in percentage (e.g., '21.00')")
    n2 = models.CharField(max_length=10, null=True, blank=True,
                          help_text="N₂ concentration in percentage (e.g., '78.00')")
    ethylene_management = models.CharField(max_length=255, blank=True, null=True,
                                           help_text="Ethylene management strategy")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit of the product")
    purchase_unit_price =  models.DecimalField(blank=True,null=True,max_digits=10, decimal_places=2, help_text="Purchase Price per unit of the product")
    storage_cost =  models.DecimalField(blank=True,null=True,max_digits=10, decimal_places=2, help_text="Storage Cost per unit of the product")
    total_value = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total value of the product in stock")
    nutritional_info = models.TextField(blank=True, null=True, help_text="Nutritional information about the product")
    regulatory_codes = models.CharField(max_length=255, blank=True, null=True,
                                        help_text="Regulatory codes applicable to the product")
    notes_comments = models.TextField(blank=True, null=True, help_text="Additional notes or comments about the product")
    farmer = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Farmer who supplied the product",
        limit_choices_to={'is_farmer': True}
    )

    def populate_from_metadata(self):
        """Populate fields from product metadata if not already set."""
        metadata = get_product_metadata()
        if self.product_name not in metadata:
            return

        product_data = metadata[self.product_name]

        # Set product_type early if not provided
        self.product_type = product_data.get("product_type", self.product_type)

        # Adjust dates based on product_type
        if self.product_type == 'Raw' and self.manufacturing_date:
            self.harvest_date = self.manufacturing_date
            self.manufacturing_date = None
        elif self.product_type == 'Processed' and self.harvest_date:
            self.manufacturing_date = self.harvest_date
            self.harvest_date = None

        # Populate other fields
        if self.storage_temperature is None:
            temp_str = product_data.get("storage_temperature", "")
            try:
                temp_values = [float(x) for x in temp_str.split("-") if x.strip()]
                self.storage_temperature = sum(temp_values) / len(temp_values) if temp_values else None
            except (ValueError, TypeError):
                self.storage_temperature = None

        if self.humidity_rate is None:
            humidity_str = product_data.get("humidity_rate", "")
            try:
                humidity_cleaned = ''.join(c for c in humidity_str if c.isdigit() or c == '-' or c == '.')
                humidity_values = [float(x) for x in humidity_cleaned.split("-") if x.strip()]
                self.humidity_rate = sum(humidity_values) / len(humidity_values) if humidity_values else None
            except (ValueError, TypeError):
                self.humidity_rate = None

        if self.co2 is None and product_data.get('CO2 (%)'):
            try:
                self.co2 = float(product_data['CO2 (%)'].replace('<', '').replace('>', '').strip())
            except (ValueError, TypeError):
                self.co2 = None

        if self.o2 is None and product_data.get('O2 (%)'):
            try:
                self.o2 = float(product_data['O2 (%)'].replace('<', '').replace('>', '').strip())
            except (ValueError, TypeError):
                self.o2 = None

        if self.n2 is None and product_data.get('n2') and product_data["n2"] != "Balance":
            try:
                self.n2 = float(product_data["n2"].replace('<', '').replace('>', '').strip())
            except (ValueError, TypeError):
                self.n2 = None

        if not self.ethylene_management:
            self.ethylene_management = product_data.get("ethylene_management")

        if not self.notes_comments:
            self.notes_comments = product_data.get('notes_comments', '')

        if not self.expiration_date and "Maximum Storage Duration (days)" in product_data:
            try:
                max_shelf_life = int(product_data["Maximum Storage Duration (days)"])
                for date_attr in [self.manufacturing_date, self.harvest_date]:
                    if date_attr:
                        self.expiration_date = date_attr + relativedelta(days=max_shelf_life)
                        break  # Stop after setting expiration_date once
            except (ValueError, TypeError):
                pass

    def clean(self):
        super().clean()
        self.populate_from_metadata()
        today = timezone.now().date()
        if self.minimum_threshold is not None and self.maximum_threshold is not None:
            if self.minimum_threshold > self.maximum_threshold:
                raise ValidationError("Minimum threshold cannot exceed maximum threshold.")
        if self.expiration_date and self.expiration_date < today and self.status != 'Expired':
            raise ValidationError("Expiration date cannot be in the past unless status is 'Expired'.")
        # Validate farmer
        if self.farmer and not self.farmer.is_farmer:
            raise ValidationError("Selected user must be a farmer (is_farmer must be True).")

        # Validate uniqueness
        if self.warehouse is not None:
            if Product.objects.exclude(pk=self.pk).filter(sku=self.sku, warehouse=self.warehouse).exists():
                raise ValidationError(f"SKU {self.sku} already exists in warehouse {self.warehouse}.")
            if Product.objects.exclude(pk=self.pk).filter(barcode=self.barcode, warehouse=self.warehouse).exists():
                raise ValidationError(f"Barcode {self.barcode} already exists in warehouse {self.warehouse}.")
                # Ensure weight_quantity_kg is set and calculate weight_quantity
        if self.weight_quantity_kg is not None:
            if self.weight_quantity_kg < 0:
                raise ValidationError("Weight quantity in kg cannot be negative.")
        # Validate weight_per_bag_kg
        if self.weight_per_bag_kg is not None:
            if self.weight_per_bag_kg < 0:
                raise ValidationError("Weight per bag in kg cannot be negative.")
            if self.quantity_in_stock is not None and self.packaging_condition != 'Bulk':
                calculated_weight_kg = self.weight_per_bag_kg * self.quantity_in_stock
                if self.weight_quantity_kg is not None and abs(
                        self.weight_quantity_kg - calculated_weight_kg) > 0.01:
                    self.weight_quantity_kg = calculated_weight_kg
        elif self.packaging_condition != 'Bulk' and self.quantity_in_stock is not None:
            raise ValidationError("Weight per bag in kg is required for non-Bulk packaging with quantity in stock.")
            # Convert kg to grams (assuming default unit is grams)
            self.weight_quantity = self.weight_quantity_kg * 1000
        elif self.weight_quantity is not None:
            # If weight_quantity_kg is not provided but weight_quantity is, calculate backwards
            self.weight_quantity_kg = self.weight_quantity / 1000
        # Validate product type
        if self.product_type == 'Raw':
            if not self.harvest_date:
                raise ValidationError("Harvest date is required for raw products.")
            if self.manufacturing_date:
                raise ValidationError("Manufacturing date should not be set for raw products.")
        elif self.product_type == 'Processed':
            if not self.manufacturing_date:
                raise ValidationError("Manufacturing date is required for processed products.")
            if self.harvest_date:
                raise ValidationError("Harvest date should not be set for processed products.")
        # Product type logic (if applicable)
        if self.product_type == 'Raw' and not self.harvest_date:
            raise ValidationError("Harvest date is required for raw products.")
        if self.product_type == 'Processed' and not self.manufacturing_date:
            raise ValidationError("Manufacturing date is required for processed products.")
        if self.product_type == 'Raw' and self.manufacturing_date:
            raise ValidationError("Manufacturing date should not be set for raw products.")
        if self.product_type == 'Processed' and self.harvest_date:
            raise ValidationError("Harvest date should not be set for processed products.")

        # Existing validation logic
        if self.harvest_date and self.entry_date:
            today = timezone.now().date()
            if self.harvest_date > today:
                raise ValidationError("Harvest date cannot be in the future.")
            if self.harvest_date > self.entry_date:
                raise ValidationError("Harvest date cannot be later than entry date.")
        if self.manufacturing_date and self.entry_date:
            if self.manufacturing_date > self.entry_date:
                raise ValidationError("Manufacturing date cannot be later than entry date.")
        if self.entry_date and self.exit_date:
            if self.entry_date > self.exit_date:
                raise ValidationError("Entry date cannot be later than exit date.")
        if self.harvest_date and self.exit_date:
            if self.harvest_date > self.exit_date:
                raise ValidationError("Harvest date cannot be later than exit date.")
        if self.manufacturing_date and self.exit_date:
            if self.manufacturing_date > self.exit_date:
                raise ValidationError("Manufacturing date cannot be later than exit date.")
        if self.expiration_date and self.entry_date:
            if self.expiration_date <= self.entry_date:  # Fixed: Expiration should be after entry
                raise ValidationError("Expiration date must be after entry date.")
        if self.expiration_date and self.manufacturing_date:
            if self.expiration_date <= self.manufacturing_date:
                raise ValidationError("Expiration date must be after manufacturing date.")
        if self.expiration_date and self.harvest_date:
            if self.expiration_date <= self.harvest_date:
                raise ValidationError("Expiration date must be after harvest date.")
        if self.manufacturing_date and self.harvest_date:
            if self.manufacturing_date <= self.harvest_date:
                raise ValidationError("Manufacturing date must be after harvest date.")

        # Non-negative constraints
        if self.quantity_in_stock:
            if self.quantity_in_stock < 0:
                raise ValidationError("Quantity in stock cannot be negative.")
        if self.weight_quantity_kg is not None and self.weight_quantity_kg < 0:
            raise ValidationError("Weight quantity in kg cannot be negative.")
        if self.unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")
        if self.total_value is not None and self.total_value < 0:  # Add if calculated
            raise ValidationError("Total value cannot be negative.")

        if self.purchase_unit_price is not None and self.purchase_unit_price < 0:
            raise ValidationError("Purchase unit price cannot be negative.")
        if self.purchase_unit_price is not None and self.unit_price is not None:
            if self.purchase_unit_price > self.unit_price:
                raise ValidationError("Purchase unit price cannot exceed selling unit price.")

        if self.storage_cost is not None and self.storage_cost < 0:
            raise ValidationError("Storage cost cannot be negative.")

        # Status consistency
        if self.quantity_in_stock:
            if self.quantity_in_stock == 0 and self.status not in ['Out of Stock', 'Expired']:
                raise ValidationError("Status must be 'Out of Stock' or 'Expired' when quantity in stock is 0.")
            if self.quantity_in_stock > 0 and self.status == 'Out of Stock':
                raise ValidationError("Status cannot be 'Out of Stock' when quantity in stock is greater than 0.")
        if self.status == 'Out of Stock' and not self.exit_date:
            raise ValidationError("Exit date must be set when status is 'Out of Stock'.")
        if self.status == 'Expired' and not self.expiration_date:
            raise ValidationError("Expiration date must be set when status is 'Expired'.")
        if self.expiration_date and self.expiration_date <= timezone.now().date() and self.status != 'Expired':
            raise ValidationError("Status must be 'Expired' if expiration date is past or present.")

    def generate_sku(self):
        """Generate a unique SKU based on warehouse ID and sequential number."""
        if not self.warehouse:
            raise ValidationError("Warehouse must be set to generate SKU.")
        max_seq =Product.objects.filter(warehouse=self.warehouse).select_for_update().aggregate(Max('sku'))['sku__max']
        seq = 1
        if max_seq and '-' in max_seq:
            try:
                seq = int(max_seq.split('-')[-1]) + 1
            except ValueError:
                seq = 1
        return f"WH-{self.warehouse.id}-{seq:06d}"

    def generate_barcode(self):
        """Generate a unique 12-digit barcode."""
        max_retries = 10
        for _ in range(max_retries):
            barcode = str(uuid.uuid4().int)[:12].zfill(12)
            if not Product.objects.filter(barcode=barcode).exists():
                return barcode
        raise ValidationError("Unable to generate a unique barcode after multiple attempts.")

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        if not self.barcode and self.product_type == 'Raw':
            self.barcode = self.generate_barcode()
        if self.weight_per_bag_kg is not None and self.quantity_in_stock is not None and self.packaging_condition != 'Bulk':
            self.weight_quantity_kg = self.weight_per_bag_kg * self.quantity_in_stock

        if self.weight_quantity_kg is not None:
            self.weight_quantity = self.weight_quantity_kg * 1000

        if self.unit_price and self.weight_quantity_kg:
            if self.weight_quantity_kg <= 0:
                raise ValidationError("Weight quantity in kg must be positive for total value calculation.")
            self.total_value = self.unit_price * self.weight_quantity_kg
        else:
            self.total_value = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} ({self.sku})"

    def mark_as_exited(self):
        self.exit_date = now().date()
        self.status = 'Out of Stock'
        self.save()

    def is_in_warehouse(self):
        return self.exit_date is None and self.status == 'In Stock'

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-entry_date']
        constraints = [
            models.UniqueConstraint(fields=['sku', 'warehouse'], name='unique_sku_per_warehouse'),
            models.UniqueConstraint(fields=['barcode', 'warehouse'], name='unique_barcode_per_warehouse'),
        ]
class ProductLog(models.Model):
    # Foreign key to the Product model
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="The product this log entry pertains to"
    )

    # User who performed the action (assuming Django's default User model)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user who performed the action"
    )

    # Action type choices
    ACTION_CHOICES = [
        ('ADD', 'Product Added'),
        ('UPDATE', 'Product Updated'),
        ('REMOVE', 'Product Removed'),
        ('STOCK_OUT', 'Stock Taken Out'),
    ]
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="The type of action performed on the product"
    )

    # Timestamp of the action
    timestamp = models.DateTimeField(
        default=now,
        help_text="The date and time when the action occurred",
        db_index=True
    )

    # Quantity changes (for stock updates or removals)
    quantity_changed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The quantity added or removed (positive for add, negative for remove)"
    )

    # Previous and new stock quantities (optional, for reference)
    previous_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Quantity in stock before the action"
    )
    new_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Quantity in stock after the action"
    )

    # Notes or additional details about the action
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional details about the action"
    )

    def __str__(self):
        return f"{self.action} on {self.product} by {self.user} at {self.timestamp}"

    class Meta:
        verbose_name = "Product Log"
        verbose_name_plural = "Product Logs"
        ordering = ['-timestamp']
class ItemRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        related_name='item_requests',
        help_text="Warehouse where the items are stored"
    )
    client = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.CASCADE,
        related_name='item_requests',
        limit_choices_to={'is_client': True},
        help_text="Client making the request"
    )
    product_name = models.CharField(
        max_length=255,
        help_text="Name of the requested product",
        db_index=True
    )
    quantity_requested = models.PositiveIntegerField(
        help_text="Number of units requested",
        null=True,
        blank=True
    )
    weight_requested_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Weight requested in kilograms",
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current status of the request"
    )
    request_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when request was made"
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when request was approved"
    )
    completion_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when request was completed"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the request"
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total price of the requested items based on max unit price"
    )

    def calculate_total_price(self, max_unit_price):
        """Calculate total price based on requested quantity or weight."""
        if self.quantity_requested and max_unit_price:
            return self.quantity_requested * max_unit_price
        elif self.weight_requested_kg and max_unit_price:
            return self.weight_requested_kg * max_unit_price
        return None
    def clean(self):
        if self.client not in self.warehouse.users.all():
            raise ValidationError("Client does not have access to this warehouse")
        if not self.quantity_requested and not self.weight_requested_kg:
            raise ValidationError("Must specify either quantity or weight requested")
        available_products = Product.objects.filter(
            warehouse=self.warehouse,
            product_name=self.product_name,
            status='In Stock'
        )
        if not available_products.exists():
            raise ValidationError(f"Product '{self.product_name}' is not available in this warehouse")
        total_quantity = sum(p.quantity_in_stock or 0 for p in available_products)
        total_weight = sum(p.weight_quantity_kg or 0 for p in available_products)
        if self.quantity_requested and self.quantity_requested > total_quantity:
            raise ValidationError(f"Requested quantity ({self.quantity_requested}) exceeds available stock ({total_quantity})")
        if self.weight_requested_kg and self.weight_requested_kg > total_weight:
            raise ValidationError(f"Requested weight ({self.weight_requested_kg} kg) exceeds available weight ({total_weight} kg)")

    def save(self, *args, **kwargs):
        if self.status == 'APPROVED' and not self.approval_date:
            self.approval_date = timezone.now()
        elif self.status == 'COMPLETED' and not self.completion_date:
            self.completion_date = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Request {self.id} - {self.product_name} by {self.client}"

    class Meta:
        verbose_name = "Item Request"
        verbose_name_plural = "Item Requests"
        ordering = ['-request_date']