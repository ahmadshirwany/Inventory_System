from django.contrib.auth.models import AbstractUser
from django.db import models

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
    def save(self, *args, **kwargs):
        if not self.owner and not self.is_superuser:
            self.owner = None  # Explicitly set owner to NULL
        if not self.is_superuser:
            self.warehouse_limit =  3
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