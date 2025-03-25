from django.contrib import admin
from .models import Warehouse, Product, ItemRequest, get_product_metadata, refresh_product_metadata
import datetime

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
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
    list_filter = (
        'type',
        'ownership',
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

    def save_model(self, request, obj, form, change):
        if not change:
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
        'status', 'entry_date', 'expiration_date', 'farmer'
    )
    list_filter = (
        'product_type', 'status', 'warehouse', 'farmer',
        ('entry_date', admin.DateFieldListFilter),
        ('expiration_date', admin.DateFieldListFilter),
    )
    search_fields = ('sku', 'barcode', 'product_name', 'lot_number', 'supplier_code')
    ordering = ('-entry_date',)
    readonly_fields = ('lot_number', 'total_value', 'entry_date')
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
        'weight_requested_kg', 'status', 'request_date', 'approval_date', 'completion_date'
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
        'client__username',
        'warehouse__name'
    )
    ordering = ('-request_date',)
    readonly_fields = (
        'request_date',
        'approval_date',
        'completion_date'
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