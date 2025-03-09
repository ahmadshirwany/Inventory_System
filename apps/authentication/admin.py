from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import CustomUser, Farmer
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

# Inline admin for Farmer within CustomUser
class FarmerInline(admin.StackedInline):
    model = Farmer
    form = FarmerForm
    can_delete = False
    verbose_name = "Farmer Profile"
    verbose_name_plural = "Farmer Profile"
    extra = 1
    fields = (
        'name', 'contact_number', 'email', 'address',
        'farm_name', 'farm_location', 'total_land_area',
        'certifications', 'compliance_standards', 'notes',
        'registration_date'
    )

# Custom admin for CustomUser
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'subscription_plan', 'is_farmer', 'is_staff')
    list_filter = ('subscription_plan', 'is_farmer', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Custom Fields', {'fields': ('owner', 'subscription_plan', 'warehouse_limit', 'user_limit', 'is_farmer')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'subscription_plan', 'is_farmer'),
        }),
    )
    inlines = [FarmerInline]
    search_fields = ('username', 'email')
    ordering = ('username',)

    def save_model(self, request, obj, form, change):
        if not change and 'inlines' in form.data:
            obj.is_farmer = True
        super().save_model(request, obj, form, change)

# Admin for Farmer model (standalone view)
class FarmerAdmin(admin.ModelAdmin):
    form = FarmerForm
    list_display = ('name', 'farm_name', 'farm_location', 'email', 'contact_number')
    list_filter = ('registration_date',)
    search_fields = ('name', 'farm_name', 'email')
    fieldsets = (
        (None, {'fields': ('name',)}),  # Remove 'user' from fieldsets since we'll create it
        ('Contact Info', {'fields': ('contact_number', 'email', 'address')}),
        ('Farm Details', {'fields': ('farm_name', 'farm_location', 'total_land_area')}),
        ('Additional Info', {'fields': ('certifications', 'compliance_standards', 'notes', 'registration_date')}),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['user']  # Only readonly when editing
        return []

    def save_model(self, request, obj, form, change):
        if not change:  # New farmer
            # Generate username and create CustomUser
            username = obj.name.lower().replace(' ', '_') + '_' + str(uuid.uuid4())[:8]
            email = obj.email if obj.email else f"{username}@example.com"
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password='defaultpassword123',  # Consider improving this
                is_farmer=True
            )
            obj.user = user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        # Exclude 'user' field from form when adding new farmer
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Only for adding new farmers
            form.base_fields.pop('user', None)  # Remove user field from form
        return form

# Register the models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Farmer, FarmerAdmin)