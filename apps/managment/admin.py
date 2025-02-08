from django.contrib import admin
from .models import Warehouse, Farmer, Product

# Register your models here.

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'ownership', 'type', 'location', 'total_capacity', 'available_space', 'utilization_rate'
    )
    list_filter = ('ownership', 'type')
    search_fields = ('name', 'location')
    filter_horizontal = ('users',)
    fieldsets = (
        ('Warehouse Information', {
            'fields': ('name', 'ownership', 'type', 'location', 'total_capacity', 'available_space', 'utilization_rate')
        }),
        ('Zone Layout', {
            'fields': ('zone_layout',)
        }),
        ('Users', {
            'fields': ('users',)
        })
    )

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