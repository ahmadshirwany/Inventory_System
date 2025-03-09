from .models import Warehouse
import datetime
from django.contrib import admin
from .models import Product, get_product_metadata, refresh_product_metadata


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


class ProductAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = (
        'sku', 'barcode', 'product_name', 'product_type', 'quantity_in_stock',
        'status', 'entry_date', 'expiration_date', 'warehouse', 'farmer'
    )

    # Fields to filter by in the sidebar
    list_filter = (
        'product_type', 'status', 'warehouse', 'farmer',
        ('entry_date', admin.DateFieldListFilter),
        ('expiration_date', admin.DateFieldListFilter),
    )

    # Fields to search
    search_fields = ('sku', 'barcode', 'product_name', 'lot_number', 'supplier_code')

    # Default ordering
    ordering = ('-entry_date',)

    # Fields to make read-only (e.g., auto-generated or calculated fields)
    readonly_fields = ('lot_number', 'total_value', 'entry_date')

    # Fieldsets to organize the edit form
    fieldsets = (
        ('Identification', {
            'fields': ('sku', 'barcode', 'lot_number', 'product_name')
        }),
        ('Product Details', {
            'fields': ('product_type', 'variety_or_species', 'origin', 'supplier_code')
        }),
        ('Dates', {
            'fields': ('harvest_date', 'manufacturing_date', 'entry_date', 'expiration_date', 'exit_date')
        }),
        ('Quantity and Value', {
            'fields': ('weight_quantity', 'weight_quantity_kg', 'quantity_in_stock', 'unit_price', 'total_value')
        }),
        ('Storage Conditions', {
            'fields': (
            'packaging_condition', 'humidity_rate', 'storage_temperature', 'co2', 'o2', 'n2', 'ethylene_management')
        }),
        ('Status and Relationships', {
            'fields': ('status', 'warehouse', 'farmer')
        }),
        ('Additional Information', {
            'fields': ('quality_standards', 'nutritional_info', 'regulatory_codes', 'notes_comments')
        }),
    )

    # Prepopulate fields (if slug or similar is needed, though not applicable here)
    # prepopulated_fields = {}

    # Actions for bulk operations
    actions = ['mark_as_expired', 'mark_as_out_of_stock']

    def mark_as_expired(self, request, queryset):
        """Mark selected products as expired and set expiration date to today if not set."""
        today = timezone.now().date()
        updated = queryset.filter(expiration_date__isnull=True).update(
            status='Expired',
            expiration_date=today
        ) + queryset.exclude(expiration_date__isnull=True).update(status='Expired')
        self.message_user(request, f"{updated} products marked as expired.")

    mark_as_expired.short_description = "Mark selected products as expired"

    def mark_as_out_of_stock(self, request, queryset):
        """Mark selected products as out of stock and set exit date to today."""
        today = timezone.now().date()
        updated = queryset.update(status='Out of Stock', exit_date=today, quantity_in_stock=0)
        self.message_user(request, f"{updated} products marked as out of stock.")

    mark_as_out_of_stock.short_description = "Mark selected products as out of stock"

    # Customize the queryset to improve performance or add logic
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('warehouse', 'farmer')  # Optimize queries for foreign keys

    # Optionally, customize form field display (e.g., for large text fields)
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['notes_comments'].widget.attrs['rows'] = 4
        form.base_fields['nutritional_info'].widget.attrs['rows'] = 4
        form.base_fields['quality_standards'].widget.attrs['rows'] = 4
        return form


# Register the model with the admin site
admin.site.register(Product, ProductAdmin)