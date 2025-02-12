from django.contrib import admin
from .models import Warehouse, Farmer, Product



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

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'product_name', 'origin', 'lot_number', 'entry_date', 'status', 'quantity_in_stock', 'warehouse', 'farmer'
    )
    list_filter = ('product_type', 'status', 'warehouse', 'farmer')
    search_fields = ('sku', 'product_name', 'lot_number', 'supplier_code')
    date_hierarchy = 'entry_date'
    fieldsets = (
        ('Product Identification', {
            'fields': ('sku', 'product_name', 'origin', 'lot_number', 'harvest_date', 'entry_date', 'exit_date')
        }),
        ('Supplier & Farmer Details', {
            'fields': ('supplier_code', 'farmer')
        }),
        ('Product Specifications', {
            'fields': ('product_type', 'variety_or_species', 'weight_quantity', 'weight_quantity_kg', 'quantity_in_stock')
        }),
        ('Storage Information', {
            'fields': ('warehouse', 'packaging_condition', 'status')
        }),
        ('Environmental Conditions', {
            'fields': ('humidity_rate', 'storage_temperature', 'co2', 'o2', 'n2', 'ethylene_management')
        }),
        ('Financial Information', {
            'fields': ('unit_price', 'total_value')
        }),
        ('Quality & Regulatory Information', {
            'fields': ('quality_standards', 'nutritional_info', 'regulatory_codes')
        }),
        ('Additional Notes', {
            'fields': ('notes_comments',)
        })
    )