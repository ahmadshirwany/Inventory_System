from django.contrib import admin
from .models import Warehouse, Farmer, Product
import datetime



@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    # Fields to display in the list view of the admin interface
    list_display = (
        'name',
        'ownership',
        'type',
        'location',
        'total_capacity',
        'available_space',
        'utilization_rate',
        'slug',
    )

    # Add filters to the right sidebar in the admin interface
    list_filter = (
        'type',
        'ownership',
        'location',
    )

    # Add search functionality to the admin interface
    search_fields = (
        'name',
        'location',
        'ownership__username',  # Assuming ownership is a User model with a username field
        'slug'
    )

    # Specify fields that can be edited directly from the list view
    list_editable = (
        'available_space',
    )

    # Fields to display in the form when editing or creating a warehouse
    fieldsets = (
        ('Warehouse Details', {
            'fields': (
                'name',
                'ownership',
                'type',
                'location',
                'slug'
            ),
        }),
        ('Capacity Information', {
            'fields': (
                'total_capacity',
                'available_space',
                'utilization_rate',
            ),
        }),
        ('Additional Information', {
            'fields': (
                'zone_layout',
                'users',
            ),
        }),
    )

    # Read-only fields that cannot be edited directly
    readonly_fields = (
        'utilization_rate',
        'slug'
    )

    # Override the save_model method to ensure proper handling of the subscription plan limit
    def save_model(self, request, obj, form, change):
        if not change:  # If this is a new warehouse being created
            user = obj.ownership
            subscription_plan = getattr(user, 'subscription_plan', None)

            if subscription_plan == 'basic' and user.owned_warehouses.count() >= 3:
                self.message_user(request, "Basic plan users can only create up to 3 warehouses.", level='error')
                return
            elif subscription_plan == 'pro' and user.owned_warehouses.count() >= 5:
                self.message_user(request, "Pro plan users can only create up to 5 warehouses.", level='error')
                return
            elif subscription_plan == 'premium' and user.owned_warehouses.count() >= 10:
                self.message_user(request, "Premium plan users can only create up to 10 warehouses.", level='error')
                return

        super().save_model(request, obj, form, change)

    # Custom action to update available space for selected warehouses
    def update_available_space(self, request, queryset):
        updated_count = 0
        for warehouse in queryset:
            if warehouse.total_capacity > 0:
                used_space = warehouse.total_capacity - warehouse.available_space
                warehouse.utilization_rate = (used_space / warehouse.total_capacity) * 100
                warehouse.save()
                updated_count += 1
        self.message_user(request, f"Successfully updated available space for {updated_count} warehouses.")

    update_available_space.short_description = "Update Available Space and Utilization Rate"

    # Register the custom action
    actions = [update_available_space]

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = (
        'farmer_id', 'name', 'farm_name', 'farm_location', 'total_land_area'
    )
    list_filter = ('certifications', 'compliance_standards')
    search_fields = ('farmer_id', 'name', 'farm_name', 'farm_location')
    fieldsets = (
        ('Farmer Details', {
            'fields': ('farmer_id', 'name', 'contact_number', 'email', 'address')
        }),
        ('Farm Details', {
            'fields': ('farm_name', 'farm_location', 'total_land_area')
        }),
        ('Certifications & Compliance', {
            'fields': ('certifications', 'compliance_standards')
        }),
        ('Additional Notes', {
            'fields': ('notes',)
        })
    )


from django.contrib import admin
from .models import Product, get_product_metadata, refresh_product_metadata


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = (
        'sku',
        'product_name',
        'product_type',
        'origin',
        'entry_date',
        'expiration_date',
        'quantity_in_stock',
        'status',
        'storage_temperature',
        'humidity_rate',
    )

    # Fields to filter by in the sidebar
    list_filter = (
        'product_type',
        'status',
        'entry_date',
        'expiration_date',
        'warehouse',
    )

    # Fields to search
    search_fields = (
        'sku',
        'product_name',
        'lot_number',
        'supplier_code',
        'origin',
    )

    # Fields to make editable directly in the list view
    list_editable = (
        'quantity_in_stock',
        'status',
    )

    # Default ordering
    ordering = ('-entry_date', 'product_name')

    # Fields to display in the detail view (form)
    fields = (
        ('sku', 'product_name'),
        ('product_type', 'variety_or_species'),
        ('origin', 'supplier_code'),
        ('lot_number', 'warehouse'),
        ('harvest_date', 'manufacturing_date'),
        ('entry_date', 'exit_date', 'expiration_date'),
        ('weight_quantity', 'weight_quantity_kg'),
        ('quantity_in_stock', 'unit_price', 'total_value'),
        ('status', 'packaging_condition'),
        ('storage_temperature', 'humidity_rate'),
        ('co2', 'o2', 'n2'),
        ('ethylene_management', 'quality_standards'),
        ('nutritional_info', 'regulatory_codes'),
        ('notes_comments', 'farmer'),
    )

    # Prepopulate some fields based on metadata
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Only prepopulate for new objects
            metadata = get_product_metadata()
            product_name_field = form.base_fields['product_name']
            if product_name_field.initial in metadata:
                product_data = metadata[product_name_field.initial]
                form.base_fields['storage_temperature'].initial = self._parse_range_average(product_data['storage_temperature'])
                form.base_fields['humidity_rate'].initial = self._parse_humidity(product_data['humidity_rate'])
                form.base_fields['ethylene_management'].initial = product_data['ethylene_management']
                form.base_fields['notes_comments'].initial = f"{product_data['notes_comments']} Shelf life: {product_data['shelf_life_months']} months."
                form.base_fields['product_type'].initial = product_data['product_type']
        return form

    # Helper method to parse temperature range (e.g., "20-25" -> 22.5)
    def _parse_range_average(self, range_str):
        try:
            values = [float(x) for x in range_str.split("-") if x.strip()]
            return sum(values) / len(values) if values else None
        except (ValueError, TypeError):
            return None

    # Helper method to parse humidity (e.g., "<50" -> 50)
    def _parse_humidity(self, humidity_str):
        try:
            cleaned = ''.join(c for c in humidity_str if c.isdigit() or c == '-' or c == '.')
            values = [float(x) for x in cleaned.split("-") if x.strip()]
            return sum(values) / len(values) if values else float(cleaned)
        except (ValueError, TypeError):
            return None

    # Add custom actions
    actions = ['mark_as_expired', 'mark_as_out_of_stock']

    @admin.action(description="Mark selected products as expired")
    def mark_as_expired(self, request, queryset):
        queryset.update(status='Expired', expiration_date=datetime.date.today())
        self.message_user(request, "Selected products have been marked as expired.")

    @admin.action(description="Mark selected products as out of stock")
    def mark_as_out_of_stock(self, request, queryset):
        queryset.update(status='Out of Stock', exit_date=datetime.date.today())
        self.message_user(request, "Selected products have been marked as out of stock.")

    # Customize the list view with conditional formatting
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('warehouse', 'farmer')  # Optimize queries

    # Display storage temperature with units
    def storage_temperature_display(self, obj):
        return f"{obj.storage_temperature} °C" if obj.storage_temperature else "N/A"
    storage_temperature_display.short_description = "Storage Temp."

    # Display humidity rate with units
    def humidity_rate_display(self, obj):
        return f"{obj.humidity_rate} %" if obj.humidity_rate else "N/A"
    humidity_rate_display.short_description = "Humidity"

    # Override list_display to use custom methods if needed
    list_display = (
        'sku',
        'product_name',
        'product_type',
        'origin',
        'entry_date',
        'expiration_date',
        'quantity_in_stock',
        'status',
        'storage_temperature_display',
        'humidity_rate_display',
    )

    # Read-only fields (optional, e.g., for calculated fields)
    readonly_fields = ('total_value',)  # total_value is calculated in save()

    # Customize the admin page title and header
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial['entry_date'] = datetime.date.today()
        return initial