from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Information', {'fields': ('owner', 'subscription_plan', 'warehouse_limit', 'user_limit', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('subscription_plan', 'warehouse_limit', 'user_limit', 'profile_picture')}),
    )
    list_display = ('username', 'email', 'is_staff', 'subscription_plan', 'warehouse_limit', 'user_limit')

admin.site.register(CustomUser, CustomUserAdmin)