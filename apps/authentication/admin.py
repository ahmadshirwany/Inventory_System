from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CustomUser, Farmer, Client
from .plan_utils import get_plan_usage_summary
import uuid

# Custom form for Farmer to ensure required fields
class FarmerForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:  # Only for new farmers
            if not cleaned_data.get('name'):
                raise forms.ValidationError("Name is required when creating a new farmer.")
        return cleaned_data

# Custom form for Client to ensure required fields
class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:  # Only for new clients
            if not cleaned_data.get('name'):
                raise forms.ValidationError("Name is required when creating a new client.")
        return cleaned_data

# Inline admin for Farmer within CustomUser
class FarmerInline(admin.StackedInline):
    model = Farmer
    form = FarmerForm
    can_delete = False
    verbose_name = "Farmer Profile"
    verbose_name_plural = "Farmer Profile"
    extra = 0  # Changed from 1 to 0 to avoid forcing empty forms
    fields = (
        'name', 'contact_number', 'email', 'address',
        'farm_name', 'farm_location', 'total_land_area',
        'certifications', 'compliance_standards', 'notes',
        'registration_date'
    )

# Inline admin for Client within CustomUser
class ClientInline(admin.StackedInline):
    model = Client
    form = ClientForm
    can_delete = False
    verbose_name = "Client Profile"
    verbose_name_plural = "Client Profile"
    extra = 0
    fields = (
        'name', 'user_type', 'email', 'phone', 'address',
        'country', 'account_status', 'notes', 'registration_date'
    )

# Custom admin for CustomUser
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'subscription_plan', 'plan_usage_display', 'is_farmer', 'is_client', 'is_staff', 'owner')
    list_filter = ('subscription_plan', 'is_farmer', 'is_client', 'is_staff', 'owner')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Plan & Limits', {
            'fields': ('subscription_plan', 'owner'),
            'description': 'Subscription plan and ownership information'
        }),
        ('Resource Limits', {
            'fields': ('warehouse_limit', 'user_limit', 'client_limit', 'farmer_limit'),
            'description': 'Maximum number of resources this user can create'
        }),
        ('User Types', {'fields': ('is_farmer', 'is_client')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'subscription_plan', 'owner', 'is_farmer', 'is_client'),
        }),
    )
    inlines = [FarmerInline, ClientInline]
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    readonly_fields = ('plan_usage_display',)

    def plan_usage_display(self, obj):
        """Display current plan usage for the user"""
        if obj.is_superuser:
            return format_html('<span style="color: #28a745;">Superuser - No Limits</span>')
        
        usage = get_plan_usage_summary(obj)
        if not usage:
            return "No usage data"
        
        html_parts = []
        for resource_type, data in usage.items():
            color = '#dc3545' if data['remaining'] == 0 else '#ffc107' if data['remaining'] <= 1 else '#28a745'
            html_parts.append(
                f'<span style="color: {color}; margin-right: 10px;">'
                f'{resource_type.title()}: {data["current"]}/{data["limit"]}'
                f'</span>'
            )
        
        return format_html(''.join(html_parts))
    
    plan_usage_display.short_description = 'Plan Usage'
    plan_usage_display.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not change:
            if 'inlines' in form.data:
                if any('FarmerInline' in key for key in form.data.keys()):
                    obj.is_farmer = True
                if any('ClientInline' in key for key in form.data.keys()):
                    obj.is_client = True
        super().save_model(request, obj, form, change)

# Admin for Farmer model (standalone view)
class FarmerAdmin(admin.ModelAdmin):
    form = FarmerForm
    list_display = ('name', 'farm_name', 'farm_location', 'email', 'contact_number', 'user', 'owner_display')
    list_filter = ('registration_date', 'user__owner', 'user__subscription_plan')
    search_fields = ('name', 'farm_name', 'email', 'user__username', 'user__owner__username')
    fieldsets = (
        ('Farmer Information', {'fields': ('name', 'farmer_id')}),
        ('Contact Information', {'fields': ('contact_number', 'email', 'address')}),
        ('Farm Details', {'fields': ('farm_name', 'farm_location', 'total_land_area')}),
        ('Certifications & Compliance', {'fields': ('certifications', 'compliance_standards')}),
        ('Additional Information', {'fields': ('notes', 'registration_date')}),
        ('User Account', {'fields': ('user',)}),
    )
    readonly_fields = ('farmer_id', 'user')

    def owner_display(self, obj):
        """Display the owner of the farmer"""
        if obj.user and obj.user.owner:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:authentication_customuser_change', args=[obj.user.owner.pk]),
                obj.user.owner.username
            )
        return "No owner"
    
    owner_display.short_description = 'Owner'
    owner_display.admin_order_field = 'user__owner__username'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['farmer_id', 'user']
        return ['farmer_id']

    def save_model(self, request, obj, form, change):
        if not change:
            # Check plan limits before creating farmer
            if obj.user and obj.user.owner:
                from .plan_utils import check_plan_limits
                try:
                    current_count = Farmer.objects.filter(user__owner=obj.user.owner).count()
                    check_plan_limits(obj.user.owner, 'farmer', current_count)
                except Exception as e:
                    self.message_user(request, f"Plan limit error: {str(e)}", level='error')
                    return
            
            username = obj.name.lower().replace(' ', '_') + '_' + str(uuid.uuid4())[:8]
            email = obj.email if obj.email else f"{username}@example.com"
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password='defaultpassword123',
                is_farmer=True
            )
            obj.user = user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            form.base_fields.pop('user', None)
        return form

# Admin for Client model (standalone view)
class ClientAdmin(admin.ModelAdmin):
    form = ClientForm
    list_display = ('name', 'user_type', 'email', 'phone', 'account_status', 'user', 'owner_display')
    list_filter = ('user_type', 'account_status', 'registration_date', 'user__owner', 'user__subscription_plan')
    search_fields = ('name', 'email', 'phone', 'user__username', 'user__owner__username')
    fieldsets = (
        ('Client Information', {'fields': ('name', 'client_id')}),
        ('Contact Information', {'fields': ('email', 'phone', 'address', 'country')}),
        ('Client Details', {'fields': ('user_type', 'account_status')}),
        ('Additional Information', {'fields': ('notes', 'registration_date')}),
        ('User Account', {'fields': ('user',)}),
    )
    readonly_fields = ('client_id', 'user')

    def owner_display(self, obj):
        """Display the owner of the client"""
        if obj.user and obj.user.owner:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:authentication_customuser_change', args=[obj.user.owner.pk]),
                obj.user.owner.username
            )
        return "No owner"
    
    owner_display.short_description = 'Owner'
    owner_display.admin_order_field = 'user__owner__username'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['client_id', 'user']
        return ['client_id']

    def save_model(self, request, obj, form, change):
        if not change:
            # Check plan limits before creating client
            if obj.user and obj.user.owner:
                from .plan_utils import check_plan_limits
                try:
                    current_count = Client.objects.filter(user__owner=obj.user.owner).count()
                    check_plan_limits(obj.user.owner, 'client', current_count)
                except Exception as e:
                    self.message_user(request, f"Plan limit error: {str(e)}", level='error')
                    return
            
            username = obj.name.lower().replace(' ', '_') + '_' + str(uuid.uuid4())[:8]
            email = obj.email if obj.email else f"{username}@example.com"
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password='defaultpassword123',
                is_client=True
            )
            obj.user = user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            form.base_fields.pop('user', None)
        return form

# Register the models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Farmer, FarmerAdmin)
admin.site.register(Client, ClientAdmin)  # Added Client registration