from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
import json,os
from dateutil.relativedelta import relativedelta

class Warehouse(models.Model):
    name = models.CharField(max_length=255, help_text="Name of the warehouse")
    ownership = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # Delete the warehouse if the owner is deleted
        related_name="owned_warehouses",
        help_text="Owner of the warehouse"
    )
    type = models.CharField(
        max_length=100,
        choices=[('General', 'General'), ('Cold Storage', 'Cold Storage'), ('Bonded', 'Bonded'), ('Automated', 'Automated')],
        default='General',
        help_text="Type of warehouse"
    )
    location = models.CharField(max_length=255, help_text="Geographical location of the warehouse")
    total_capacity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total storage capacity in square meters")
    available_space = models.DecimalField(max_digits=10, decimal_places=2, help_text="Available storage space in square meters")
    utilization_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of utilized space (0-100)")
    zone_layout = models.TextField(blank=True, null=True, help_text="Description or diagram of the warehouse zone layout")
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="warehouses",null=True, blank=True, help_text="Users associated with this warehouse")
    slug = models.SlugField(unique=True, blank=True, help_text="Unique slug for the warehouse URL")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.ownership.subscription_plan == 'basic' and self.ownership.owned_warehouses.exclude(
                id=self.id).count() >= 3:
            raise ValueError("Basic plan users can only create up to 3 warehouses.")
        elif self.ownership.subscription_plan == 'pro' and self.ownership.owned_warehouses.exclude(
                id=self.id).count() >= 5:
            raise ValueError("Pro plan users can only create up to 5 warehouses.")
        elif self.ownership.subscription_plan == 'premium' and self.ownership.owned_warehouses.exclude(
                id=self.id).count() >= 10:
            raise ValueError("Premium plan users can only create up to 10 warehouses.")
        if not self.slug:  # Generate a slug only if it doesn't already exist
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

class Farmer(models.Model):
    farmer_id = models.CharField(max_length=100, unique=True, help_text="Unique ID assigned to the farmer")
    name = models.CharField(max_length=255, help_text="Full name of the farmer")
    contact_number = models.CharField(max_length=20, blank=True, null=True, help_text="Primary contact number of the farmer")
    email = models.EmailField(max_length=255, blank=True, null=True, help_text="Email address of the farmer")
    address = models.TextField(help_text="Physical address of the farmer")
    farm_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the farm")
    farm_location = models.CharField(max_length=255, help_text="Geographical location of the farm")
    total_land_area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Total area of the farm in hectares")
    certifications = models.TextField(blank=True, null=True, help_text="List of certifications held by the farmer")
    compliance_standards = models.TextField(blank=True, null=True, help_text="Compliance standards followed by the farmer")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes or comments about the farmer")
    registration_date = models.DateField(null=True, blank=True, help_text="Date of Registration")
    def __str__(self):
        return f"{self.name} ({self.farm_name})"

    class Meta:
        verbose_name = "Farmer"
        verbose_name_plural = "Farmers"


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
PRODUCT_CHOICES = [(name, name) for name in get_product_metadata().keys()]

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit", db_index=True)
    product_name = models.CharField(
        max_length=255,
        choices=PRODUCT_CHOICES,
        help_text="Name of the product",
        db_index=True
    )
    origin = models.CharField(max_length=255, help_text="Country or region of origin")
    lot_number = models.CharField(max_length=100, help_text="Lot number for batch identification")
    harvest_date = models.DateField(null=True, blank=True, help_text="Date of harvest")
    entry_date = models.DateField(default=now, help_text="Date when the product entered the warehouse", db_index=True)
    manufacturing_date = models.DateField(null=True, blank=True, help_text="Date of manufacturing")
    expiration_date = models.DateField(null=True, blank=True, help_text="Date when the product expires", db_index=True)
    exit_date = models.DateField(null=True, blank=True, help_text="Date when the product exits the warehouse")
    supplier_code = models.CharField(max_length=100, help_text="Code assigned to the supplier")
    product_type = models.CharField(
        max_length=100,
        choices=[('Raw', 'Raw'), ('Processed', 'Processed')],
        default='Raw',
        help_text="Type of product"
    )
    variety_or_species = models.CharField(max_length=255, help_text="Variety or species of the product")
    weight_quantity = models.DecimalField(max_digits=10, decimal_places=2,
                                          help_text="Weight or quantity of the product (in default units)")
    weight_quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                             help_text="Weight of the product in kilograms")
    quantity_in_stock = models.PositiveIntegerField(help_text="Quantity available in stock")
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Warehouse where the product is stored"
    )
    packaging_condition = models.CharField(max_length=255, help_text="Condition of the packaging")
    status = models.CharField(
        max_length=100,
        choices=[('In Stock', 'In Stock'), ('Out of Stock', 'Out of Stock'), ('Expired', 'Expired')],
        default='In Stock',
        help_text="Current status of the product"
    )
    quality_standards = models.TextField(blank=True, null=True, help_text="Quality standards met by the product")
    humidity_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                        help_text="Humidity rate in percentage")
    storage_temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                              help_text="Storage temperature in degrees Celsius")
    co2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                              help_text="CO₂ concentration in percentage")
    o2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                             help_text="O₂ concentration in percentage")
    n2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                             help_text="N₂ concentration in percentage")
    ethylene_management = models.CharField(max_length=255, blank=True, null=True,
                                           help_text="Ethylene management strategy")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit of the product")
    total_value = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total value of the product in stock")
    nutritional_info = models.TextField(blank=True, null=True, help_text="Nutritional information about the product")
    regulatory_codes = models.CharField(max_length=255, blank=True, null=True,
                                        help_text="Regulatory codes applicable to the product")
    notes_comments = models.TextField(blank=True, null=True, help_text="Additional notes or comments about the product")
    farmer = models.ForeignKey(
        'Farmer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Farmer who supplied the product"
    )

    def clean(self):
        super().clean()
        if self.harvest_date and self.manufacturing_date and self.harvest_date > self.manufacturing_date:
            raise ValidationError("Harvest date cannot be later than manufacturing date.")
        if self.entry_date and self.exit_date and self.entry_date > self.exit_date:
            raise ValidationError("Entry date cannot be later than exit date.")
        if self.expiration_date and self.manufacturing_date and self.expiration_date <= self.manufacturing_date:
            raise ValidationError("Expiration date must be after manufacturing date.")

    def save(self, *args, **kwargs):
        # Get the latest metadata
        metadata = get_product_metadata()

        if self.product_name in metadata:
            product_data = metadata[self.product_name]

            # Auto-populate fields if not set, handling ranges and special characters
            if self.storage_temperature is None:
                temp_str = product_data["storage_temperature"]
                temp_values = [float(x) for x in temp_str.split("-") if x.strip()]
                self.storage_temperature = sum(temp_values) / len(temp_values) if temp_values else None

            if self.humidity_rate is None:
                humidity_str = product_data["humidity_rate"]
                # Handle "<" or ">" by taking the numeric part
                humidity_cleaned = ''.join(c for c in humidity_str if c.isdigit() or c == '-' or c == '.')
                humidity_values = [float(x) for x in humidity_cleaned.split("-") if x.strip()]
                self.humidity_rate = sum(humidity_values) / len(humidity_values) if humidity_values else float(humidity_cleaned)

            if self.co2 is None and product_data["co2"] is not None:
                co2_str = product_data["co2"]
                self.co2 = float(co2_str.replace("<", "").replace(">", "").strip())

            if self.o2 is None and product_data["o2"] is not None:
                o2_str = product_data["o2"]
                self.o2 = float(o2_str.replace("<", "").replace(">", "").strip())

            if self.n2 is None and product_data["n2"] is not None and product_data["n2"] != "Balance":
                n2_str = product_data["n2"]
                self.n2 = float(n2_str.replace("<", "").replace(">", "").strip())

            if not self.ethylene_management:
                self.ethylene_management = product_data["ethylene_management"]

            if not self.notes_comments:
                shelf_life_str = product_data["shelf_life_months"]
                self.notes_comments = f"{product_data['notes_comments']} Shelf life: {shelf_life_str} months."

            if not self.product_type:
                self.product_type = product_data["product_type"]

            # Calculate expiration_date based on shelf life if manufacturing_date is set
            if self.manufacturing_date and not self.expiration_date:
                shelf_life_str = product_data["shelf_life_months"]
                max_shelf_life = int(shelf_life_str.split("-")[-1].replace("+", "").strip())
                self.expiration_date = self.manufacturing_date + relativedelta(months=max_shelf_life)

        # Existing save logic
        if self.unit_price and self.quantity_in_stock:
            self.total_value = self.unit_price * self.quantity_in_stock
        if self.weight_quantity_kg is None and self.weight_quantity:
            self.weight_quantity_kg = self.weight_quantity / 1000

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