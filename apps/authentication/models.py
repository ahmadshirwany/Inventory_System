from django.contrib.auth.models import AbstractUser
from django.db import models
import os

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
        'self',  # Self-referential relationship
        null=True,
        blank=True,
        on_delete=models.CASCADE,  # If the owner is deleted, set this field to NULL
        related_name='owned_users'
    )
    SUBSCRIPTION_CHOICES = [
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
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True,
        default='profile_pictures/blank-profile-picture.png',  # Default image
        help_text="Upload a profile picture for the user."
    )
    def save(self, *args, **kwargs):
        if not self.owner and not self.is_superuser:
            self.owner = None  # Explicitly set owner to NULL
        if not self.is_superuser:
            self.warehouse_limit =  3
        if not self.profile_picture:
            # Assign the default image path
            self.profile_picture = 'profile_pictures/blank-profile-picture.png'
        super().save(*args, **kwargs)

    def can_create_warehouse(self, current_warehouse_count):
        if self.warehouse_limit is None:
            return False
        return current_warehouse_count < self.warehouse_limit

    def can_create_user(self, current_user_count):
        if self.user_limit is None:
            return False
        return current_user_count < self.user_limit

    def __str__(self):
        return self.username