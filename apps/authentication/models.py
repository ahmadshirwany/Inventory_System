import uuid
from django.contrib.auth.models import AbstractUser,Group
from django.db import models
import os
from core import settings
from django.core.exceptions import ValidationError


def user_profile_picture_path(instance, filename):
    # Get the user's ID and create a folder for their profile pictures
    user_id = instance.id
    if not user_id:
        # If the user ID is not yet available (e.g., during object creation),
        # you can use a placeholder or handle it differently.
        user_id = "temp"

    # Get the original file extension
    _, ext = os.path.splitext(filename)

    # Generate a unique filename using the user ID and the original file extension
    unique_filename = f"profile_{user_id}{ext}"

    # Return the final upload path
    return os.path.join('profile_pictures', str(user_id), unique_filename)


class CustomUser(AbstractUser):
    owner = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,  # If the owner is deleted, set this field to NULL
        related_name='owned_users'
    )
    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic Plan'),
        ('pro', 'Pro Plan'),
        ('premium', 'Premium Plan'),
        ('user', 'User Plan'),
    ]
    subscription_plan = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES, default='basic')
    warehouse_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The maximum number of warehouses this user can create. NULL means no warehouses allowed."
    )
    user_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The maximum number of Users this user can create. NULL means no Users allowed."
    )
    client_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The maximum number of Clients this user can create. NULL means no Clients allowed."
    )
    farmer_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The maximum number of Farmers this user can create. NULL means no Farmers allowed."
    )
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True,
        default='profile_pictures/blank-profile-picture.png',  # Default image
        help_text="Upload a profile picture for the user."
    )
    is_farmer = models.BooleanField(default=False, help_text="Designates whether this user is a farmer")
    is_client = models.BooleanField(default=False, help_text="Designates whether this user is a client")

    PLAN_LIMITS = {
        'free' : {'warehouse_limit': 1, 'user_limit': 1, 'client_limit': 1, 'farmer_limit': 1},
        'basic': {'warehouse_limit': 2, 'user_limit': 10, 'client_limit': 10, 'farmer_limit': 10},
        'pro': {'warehouse_limit': 5, 'user_limit': 50, 'client_limit': 50, 'farmer_limit': 50},
        'premium': {'warehouse_limit': 10, 'user_limit': 1000, 'client_limit': 1000, 'farmer_limit': 1000},
    }

    def save(self, *args, **kwargs):
        self.clean()
        if not self.owner and not self.is_superuser:
            self.owner = None  # Explicitly set owner to NULL
        if not self.profile_picture:
            # Assign the default image path
            self.profile_picture = 'profile_pictures/blank-profile-picture.png'
        
        # Only set limits for owners (users without an owner), not for owned users
        if not self.owner:
            limits = self.PLAN_LIMITS.get(self.subscription_plan, self.PLAN_LIMITS['basic'])
            self.warehouse_limit = limits['warehouse_limit']
            self.user_limit = limits['user_limit']
            self.client_limit = limits['client_limit']
            self.farmer_limit = limits['farmer_limit']
        else:
            # For owned users, set subscription_plan to 'user' and clear limits
            self.subscription_plan = 'user'
            self.warehouse_limit = 0
            self.user_limit = 0
            self.client_limit = 0
            self.farmer_limit = 0
            
        super().save(*args, **kwargs)
        
        # Handle farmer group
        if self.is_farmer:
            farmer_group, _ = Group.objects.get_or_create(name='farmer')
            self.groups.clear()
            self.groups.add(farmer_group)

        # Handle client group
        if self.is_client:
            client_group, _ = Group.objects.get_or_create(name='client')
            self.groups.clear()
            self.groups.add(client_group)

        # Handle 'user' group (for regular users)
        if not self.is_farmer and not self.is_client and self.owner:
            user_group, _ = Group.objects.get_or_create(name='user')
            self.groups.clear()
            self.groups.add(user_group)

    def clean(self):
        if self.is_farmer and self.is_client:
            raise ValidationError("A user cannot be both farmer and client simultaneously")

    def get_effective_owner(self):
        """Get the effective owner for plan limit checking"""
        return self.owner if self.owner else self

    def can_create_warehouse(self, current_warehouse_count):
        effective_owner = self.get_effective_owner()
        if effective_owner.warehouse_limit is None:
            return False
        return current_warehouse_count < effective_owner.warehouse_limit

    def can_create_user(self, current_user_count):
        effective_owner = self.get_effective_owner()
        if effective_owner.user_limit is None:
            return False
        return current_user_count < effective_owner.user_limit

    def can_create_client(self):
        effective_owner = self.get_effective_owner()
        current_client_count = Client.objects.filter(user__owner=effective_owner).count()
        if effective_owner.client_limit is None:
            return False
        return current_client_count < effective_owner.client_limit

    def can_create_farmer(self):
        effective_owner = self.get_effective_owner()
        current_farmer_count = Farmer.objects.filter(user__owner=effective_owner).count()
        if effective_owner.farmer_limit is None:
            return False
        return current_farmer_count < effective_owner.farmer_limit

    def __str__(self):
        return self.username

# Farmer Model
class Farmer(models.Model):
    farmer_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Unique ID assigned to the farmer")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_profile',
        help_text="Associated user account"
    )
    name = models.CharField(max_length=255, help_text="Full name of the farmer")
    contact_number = models.CharField(max_length=20, blank=True, null=True, help_text="Primary contact number of the farmer")
    email = models.EmailField(max_length=255, blank=True, null=True, unique=True, help_text="Email address of the farmer")
    address = models.TextField(help_text="Physical address of the farmer")
    farm_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the farm")
    farm_location = models.CharField(max_length=255, help_text="Geographical location of the farm")
    total_land_area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Total area of the farm in hectares")
    certifications = models.TextField(blank=True, null=True, help_text="List of certifications held by the farmer")
    compliance_standards = models.TextField(blank=True, null=True, help_text="Compliance standards followed by the farmer")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes or comments about the farmer")
    registration_date = models.DateField(null=True, blank=True, help_text="Date of Registration")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Farmer'
        verbose_name_plural = 'Farmers'

class Client(models.Model):
    # Fields from the SQL table with translations
    id_client = models.AutoField(primary_key=True, help_text="Unique auto-incremented ID for the client")
    name = models.CharField(max_length=255, null=False, blank=False, help_text="User/company name")  # 'nom' -> 'name'
    USER_TYPE_CHOICES = [
        ('Producteur', 'Producer'),
        ('Transformateur', 'Processor'),
        ('Acheteur Local', 'Local Buyer'),
        ('Acheteur Régional', 'Regional Buyer'),
        ('Acheteur International', 'International Buyer'),
    ]
    user_type = models.CharField(  # 'type_utilisateur' -> 'user_type'
        max_length=22,
        choices=USER_TYPE_CHOICES,
        null=False,
        blank=False,
        help_text="User role in ecosystem"
    )
    email = models.EmailField(max_length=255, unique=True, null=False, blank=False, help_text="Contact email")
    phone = models.CharField(max_length=20, null=False, blank=False, help_text="Direct contact number")  # 'telephone' -> 'phone'
    address = models.TextField(null=True, blank=True, help_text="Physical address/geolocation")  # 'adresse' -> 'address'
    country = models.CharField(max_length=100, default='Senegal', help_text="Origin country for international buyers")  # 'pays' -> 'country', 'Sénégal' -> 'Senegal'
    ACCOUNT_STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Suspended', 'Suspended'),
    ]
    account_status = models.CharField(  # 'statut_compte' -> 'account_status'
        max_length=10,
        choices=ACCOUNT_STATUS_CHOICES,
        default='Active',  # 'Actif' -> 'Active'
        help_text="Account status"
    )

    # Essential fields from Farmer model (already in English, kept as is)
    client_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Unique UUID for the client")
    user = models.OneToOneField(
        settings.   AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_profile',
        help_text="Associated user account"
    )
    notes = models.TextField(blank=True, null=True, help_text="Additional notes or comments about the client")
    registration_date = models.DateField(null=True, blank=True, help_text="Date of Registration")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        indexes = [
            models.Index(fields=['user_type']),  # 'type_utilisateur' -> 'user_type'
            models.Index(fields=['account_status']),  # 'statut_compte' -> 'account_status'
        ]
        db_table = 'client'
        db_table_comment = 'Central registry for all platform actors'

    # def clean(self):
    #     super().clean()
    #     if self.user and self.user.owner:
    #         # Check if the owner can create more clients
    #         current_client_count = Client.objects.filter(user__owner=self.user.owner).count()
    #         if not self.user.owner.can_create_client(current_client_count):
    #             raise ValidationError(
    #                 f"Plan limit exceeded. Owner can only create {self.user.owner.client_limit} clients."
    #             )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # Ensure the associated user is marked as a client and assigned to the 'client' group
        if self.user:
            client_group, _ = Group.objects.get_or_create(name='client')
            self.user.groups.clear()
            self.user.groups.add(client_group)
            self.user.save()