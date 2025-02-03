from django.contrib import admin
from .models import Warehouse, Product

class ProductInline(admin.TabularInline):
    model = Product
    extra = 1

class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location')
    filter_horizontal = ('users',)
    inlines = [ProductInline]

    def get_queryset(self, request):
        """Limit warehouse visibility based on the user's assigned warehouses."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Allow superusers to see all warehouses
        return qs.filter(users=request.user)

class ProductAdmin(admin.ModelAdmin):
    readonly_fields = ['date_added']
    list_display = ('name', 'sku', 'product_type', 'quantity_in_stock', 'price', 'warehouse')
    list_filter = ('product_type', 'warehouse', 'manufacturer_name')
    search_fields = ('name', 'sku', 'barcode', 'manufacturer_name')
    ordering = ['warehouse', 'name']
    fieldsets = (
        (None, {
            'fields': ('name', 'sku', 'barcode', 'product_type', 'description')
        }),
        ('Stock Details', {
            'fields': ('quantity_in_stock', 'price', 'unit_of_measure', 'expiry_date', 'warehouse'),
        }),
        ('Manufacturer and Supplier', {
            'fields': ('manufacturer_name', 'supplier_details'),
        }),
        ('Additional Information', {
            'fields': ('date_added',),
        }),
    )

    def get_queryset(self, request):
        """Limit product visibility based on the user's assigned warehouses."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superusers can see all products
        return qs.filter(warehouse__in=request.user.warehouses.all())

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "warehouse" and not request.user.is_superuser:
            kwargs["queryset"] = Warehouse.objects.filter(users=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Warehouse, WarehouseAdmin)
admin.site.register(Product, ProductAdmin)
