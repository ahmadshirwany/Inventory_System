from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Warehouse, Product, ItemRequest, get_product_metadata, refresh_product_metadata
from apps.authentication.plan_utils import check_plan_limits, get_plan_usage_summary
import datetime

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'ownership',
        'ownership_plan',
        'type',
        'location',
        'total_capacity',
        'available_space',
        'utilization_rate',
        'slug',
    )
    list_filter = (
        'type',
        'ownership',
        'ownership__subscription_plan',
        'location',
    )
    search_fields = (
        'name',
        'location',
        'ownership__username',
        'slug'
    )
    list_editable = (
        'available_space',
    )
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
    readonly_fields = (
        'utilization_rate',
        'slug'
    )

    def ownership_plan(self, obj):
        """Display the subscription plan of the warehouse owner"""
        if obj.ownership:
            plan = obj.ownership.subscription_plan
            color = {
                'free': '#dc3545',
                'basic': '#ffc107', 
                'pro': '#17a2b8',
                'premium': '#28a745'
            }.get(plan, '#6c757d')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                plan.title()
            )
        return "No owner"
    
    ownership_plan.short_description = 'Owner Plan'
    ownership_plan.admin_order_field = 'ownership__subscription_plan'

    def save_model(self, request, obj, form, change):
        if not change:
            # Use the new plan limits system
            try:
                current_count = obj.ownership.owned_warehouses.count()
                check_plan_limits(obj.ownership, 'warehouse', current_count)
            except Exception as e:
                self.message_user(request, f"Plan limit error: {str(e)}", level='error')
                return
        super().save_model(request, obj, form, change)

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
    actions = [update_available_space]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'barcode', 'warehouse', 'product_name', 'product_type', 'quantity_in_stock',
        'weight_quantity_kg', 'status', 'entry_date', 'expiration_date', 'farmer', 'unit_price'
    )
    list_filter = (
        'product_type', 'status', 'warehouse', 'farmer', 'category', 'packaging_condition',
        ('entry_date', admin.DateFieldListFilter),
        ('expiration_date', admin.DateFieldListFilter),
        ('harvest_date', admin.DateFieldListFilter),
        ('manufacturing_date', admin.DateFieldListFilter),
    )
    search_fields = ('sku', 'barcode', 'product_name', 'lot_number', 'supplier_code', 'variety_or_species', 'origin')
    ordering = ('-entry_date',)
    readonly_fields = ('lot_number', 'total_value', 'entry_date')
    fieldsets = (
        ('Identification', {
            'fields': ('sku', 'barcode', 'lot_number', 'product_name', 'description')
        }),
        ('Product Details', {
            'fields': ('product_type', 'variety_or_species', 'origin', 'supplier_code', 'category', 'supplier_brand')
        }),
        ('Physical Properties', {
            'fields': ('unit_of_measure', 'physical_dimensions', 'weight_quantity', 'weight_quantity_kg', 'weight_per_bag_kg')
        }),
        ('Dates', {
            'fields': ('harvest_date', 'manufacturing_date', 'entry_date', 'expiration_date', 'exit_date')
        }),
        ('Quantity and Pricing', {
            'fields': ('quantity_in_stock', 'unit_price', 'purchase_unit_price', 'storage_cost', 'total_value')
        }),
        ('Storage Conditions', {
            'fields': (
                'packaging_condition', 'product_condition', 'humidity_rate', 'storage_temperature', 
                'co2', 'o2', 'n2', 'ethylene_management')
        }),
        ('Quality & Compliance', {
            'fields': ('certifications', 'quality_standards', 'regulatory_codes', 'nutritional_info')
        }),
        ('Status and Relationships', {
            'fields': ('status', 'warehouse', 'farmer')
        }),
        ('Thresholds', {
            'fields': ('minimum_threshold', 'maximum_threshold')
        }),
        ('Additional Information', {
            'fields': ('notes_comments',)
        }),
    )
    actions = ['mark_as_expired', 'mark_as_out_of_stock']

    def mark_as_expired(self, request, queryset):
        today = datetime.datetime.now().date()
        updated = queryset.filter(expiration_date__isnull=True).update(
            status='Expired',
            expiration_date=today
        ) + queryset.exclude(expiration_date__isnull=True).update(status='Expired')
        self.message_user(request, f"{updated} products marked as expired.")

    mark_as_expired.short_description = "Mark selected products as expired"

    def mark_as_out_of_stock(self, request, queryset):
        today = datetime.datetime.now().date()
        updated = queryset.update(status='Out of Stock', exit_date=today, quantity_in_stock=0)
        self.message_user(request, f"{updated} products marked as out of stock.")

    mark_as_out_of_stock.short_description = "Mark selected products as out of stock"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('warehouse', 'farmer')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['notes_comments'].widget.attrs['rows'] = 4
        form.base_fields['nutritional_info'].widget.attrs['rows'] = 4
        form.base_fields['quality_standards'].widget.attrs['rows'] = 4
        return form


@admin.register(ItemRequest)
class ItemRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'warehouse', 'client', 'product_name', 'quantity_requested',
        'weight_requested_kg', 'total_price', 'status', 'request_date', 'approval_date', 'completion_date'
    )
    list_filter = (
        'status',
        'warehouse',
        'client',
        ('request_date', admin.DateFieldListFilter),
        ('approval_date', admin.DateFieldListFilter),
        ('completion_date', admin.DateFieldListFilter),
    )
    search_fields = (
        'product_name',
        'client__name',
        'client__email',
        'warehouse__name'
    )
    ordering = ('-request_date',)
    readonly_fields = (
        'request_date',
        'approval_date',
        'completion_date',
        'total_price'
    )
    fieldsets = (
        ('Request Details', {
            'fields': (
                'warehouse',
                'client',
                'product_name',
                'quantity_requested',
                'weight_requested_kg',
                'status'
            )
        }),
        ('Pricing', {
            'fields': ('total_price',)
        }),
        ('Dates', {
            'fields': (
                'request_date',
                'approval_date',
                'completion_date'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
    )
    actions = ['approve_requests', 'reject_requests', 'complete_requests']

    def approve_requests(self, request, queryset):
        updated = queryset.filter(status='PENDING').update(
            status='APPROVED',
            approval_date=datetime.datetime.now()
        )
        self.message_user(request, f"{updated} requests approved.")

    approve_requests.short_description = "Approve selected requests"

    def reject_requests(self, request, queryset):
        updated = queryset.filter(status__in=['PENDING', 'APPROVED']).update(status='REJECTED')
        self.message_user(request, f"{updated} requests rejected.")

    reject_requests.short_description = "Reject selected requests"

    def complete_requests(self, request, queryset):
        updated = 0
        for item_request in queryset.filter(status='APPROVED'):
            item_request.status = 'COMPLETED'
            item_request.completion_date = datetime.datetime.now()
            item_request.save()  # Triggers process_completion() in the model
            updated += 1
        self.message_user(request, f"{updated} requests completed.")

    complete_requests.short_description = "Complete selected requests"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('warehouse', 'client')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['notes'].widget.attrs['rows'] = 4
        return form