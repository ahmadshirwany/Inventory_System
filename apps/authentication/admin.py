from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import CustomUser, Farmer, Client
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
    list_display = ('username', 'email', 'subscription_plan', 'is_farmer', 'is_client', 'is_staff')
    list_filter = ('subscription_plan', 'is_farmer', 'is_client', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Custom Fields', {'fields': ('owner', 'subscription_plan', 'warehouse_limit', 'user_limit', 'is_farmer', 'is_client')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'subscription_plan', 'is_farmer', 'is_client'),
        }),
    )
    inlines = [FarmerInline, ClientInline]  # Added ClientInline
    search_fields = ('username', 'email')
    ordering = ('username',)

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
    list_display = ('name', 'farm_name', 'farm_location', 'email', 'contact_number')
    list_filter = ('registration_date',)
    search_fields = ('name', 'farm_name', 'email')
    fieldsets = (
        (None, {'fields': ('name',)}),
        ('Contact Info', {'fields': ('contact_number', 'email', 'address')}),
        ('Farm Details', {'fields': ('farm_name', 'farm_location', 'total_land_area')}),
        ('Additional Info', {'fields': ('certifications', 'compliance_standards', 'notes', 'registration_date')}),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['user']
        return []

    def save_model(self, request, obj, form, change):
        if not change:
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
    list_display = ('name', 'user_type', 'email', 'phone', 'account_status')
    list_filter = ('user_type', 'account_status', 'registration_date')
    search_fields = ('name', 'email', 'phone')
    fieldsets = (
        (None, {'fields': ('name',)}),
        ('Contact Info', {'fields': ('email', 'phone', 'address', 'country')}),
        ('Client Details', {'fields': ('user_type', 'account_status')}),
        ('Additional Info', {'fields': ('notes', 'registration_date')}),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['user', 'client_id']
        return ['client_id']

    def save_model(self, request, obj, form, change):
        if not change:
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