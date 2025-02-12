from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'owner')
    fieldsets = (
        *UserAdmin.fieldsets,  # Include all default fields from UserAdmin
        (
            'Ownership Information',  # New section for the owner field
            {
                'fields': ('owner','user_limit')
            }
        )
    )

admin.site.register(CustomUser, CustomUserAdmin)