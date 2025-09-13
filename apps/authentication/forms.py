# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import datetime
import uuid
from datetime import timezone
from datetime import date
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomUser, Farmer,Client
import re
from django.db import transaction
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


def validate_password_strength(password, field_name="password1"):
    """Validate password strength with specific requirements."""
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character.")

    if errors:
        raise forms.ValidationError({field_name: errors})

class CustomUserCreationForm(UserCreationForm):
    group = forms.ChoiceField(
        choices=[],
        label="Assign to Group",
        help_text="Select the group to which the user will belong."
    )
    email = forms.EmailField(required=False, help_text="Optional email address for the user.")
    subscription_plan = forms.ChoiceField(
        choices=CustomUser.SUBSCRIPTION_CHOICES,
        label="Subscription Plan",
        help_text="Select the subscription plan for the user.",
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2", "group", "subscription_plan")

    def __init__(self, *args, **kwargs):
        # Pop the 'user' argument from kwargs
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Dynamically set group choices based on user permissions
        if self.request_user and self.request_user.is_authenticated:
            if self.request_user.is_superuser:
                self.fields['group'].choices = [("owner", "Owner"), ("user", "Employee")]
                self.fields['subscription_plan'].choices = CustomUser.SUBSCRIPTION_CHOICES
            else:
                self.fields['group'].choices = [("user", "Employee")]
                del self.fields['subscription_plan']  # Remove for non-superusers
        else:
            self.fields['group'].choices = [("user", "Employee")]
            del self.fields['subscription_plan']  # Remove if not authenticated

    def clean_group(self):
        group = self.cleaned_data['group']
        if group == 'owner' and not self.request_user.is_superuser:
            raise forms.ValidationError("Only superusers can assign the 'owner' group.")
        return group

    def clean_subscription_plan(self):
        plan = self.cleaned_data.get('subscription_plan')
        if plan and not self.request_user.is_superuser:
            raise forms.ValidationError("Only superusers can assign a subscription plan.")
        if self.cleaned_data.get('group') == 'owner' and not plan:
            raise forms.ValidationError("A subscription plan is required for 'owner' group.")
        return plan

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        # Validate passwords
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords do not match.")
            validate_password_strength(password1, "password1")
            try:
                password_validation.validate_password(password1)
            except forms.ValidationError as e:
                raise forms.ValidationError({"password1": e})

        if self.request_user and self.request_user.user_limit is not None:
            current_user_count = CustomUser.objects.filter(owner=self.request_user).count()
            if not self.request_user.can_create_user(current_user_count):
                raise forms.ValidationError("The requesting user has reached their user creation limit.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if not self.request_user.is_superuser:
            user.owner = self.request_user
        user.subscription_plan = self.cleaned_data.get('subscription_plan', 'basic')
        group_name = self.cleaned_data['group']

        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control"
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control"
            }
        ))


class SignUpForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={

                "class": "form-control"
            }
        ))
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={

                "class": "form-control"
            }
        ))
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={

                "class": "form-control"
            }
        ))
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={

                "class": "form-control"
            }
        ))

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'  # Restrict to image files
            })
        }

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Add file size validation (e.g., max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large (max 5MB)")
            # Add content type validation
            if not picture.content_type.startswith('image/'):
                raise forms.ValidationError("File must be an image")
        return picture

class FarmerCreationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, help_text="Unique username for the farmer's user account.")
    user_email = forms.EmailField(required=True, help_text="Email address for the user account.")
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        help_text="Enter a password for the farmer's user account."
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        help_text="Confirm the password."
    )
    contact_number = forms.CharField(max_length=20, required=True, help_text="Primary contact number of the farmer.")

    class Meta:
        model = Farmer
        fields = (
            'name', 'contact_number', 'email', 'address',
            'farm_name', 'farm_location', 'total_land_area',
            'certifications', 'compliance_standards', 'notes',
        )
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'certifications': forms.Textarea(attrs={'rows': 3}),
            'compliance_standards': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        # Basic phone number validation (e.g., +1234567890 or 123-456-7890)
        phone_pattern = r'^\+?1?\d{9,15}$|^(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})$'
        if not re.match(phone_pattern, contact_number):
            raise forms.ValidationError("Enter a valid phone number (e.g., +1234567890 or 123-456-7890).")
        return contact_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        username = cleaned_data.get("username")
        user_email = cleaned_data.get("user_email")
        farmer_email = cleaned_data.get("email")

        # Validate passwords
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords do not match.")
            validate_password_strength(password1)
            try:
                password_validation.validate_password(password1)
            except forms.ValidationError as e:
                raise forms.ValidationError({"password1": e})
        getUser = get_user_model()
        # Ensure username is unique
        if getUser.objects.filter(username=username).exists():
            raise forms.ValidationError({"username": "This username is already taken."})

        # Ensure user_email is unique
        if getUser.objects.filter(email=user_email).exists():
            raise forms.ValidationError({"user_email": "This email is already taken."})

        # Ensure farmer_email is unique if provided
        if farmer_email and Farmer.objects.filter(email=farmer_email).exists():
            raise forms.ValidationError({"email": "This farmer email is already taken."})

        return cleaned_data

    @transaction.atomic
    def save(self, request, commit=True):
        # Create CustomUser instance
        if request.user.is_authenticated and request.user.groups.filter(name='owner').exists():
            if not request.user.can_create_farmer():
                raise forms.ValidationError("You have reached your Farmer creation limit.")
            current_user_owner = request.user
        else:
            if not request.user.owner.can_create_farmer():
                raise forms.ValidationError("You have reached your Farmer creation limit.")
            current_user_owner = request.user.owner if request.user.is_authenticated else None
        user = CustomUser(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['user_email'],
            is_farmer=True,
            owner=current_user_owner
        )
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()

        # Create Farmer instance
        farmer = super().save(commit=False)
        farmer.user = user
        farmer.email = self.cleaned_data['user_email']
        farmer.registration_date = date.today()
        if commit:
            farmer.save()

        return farmer

class ClientCreationForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        help_text="Unique username for the client's user account.",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        help_text="Email address for the user account.",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Enter a password for the client's user account."
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Confirm the password."
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        help_text="Primary phone number of the client.",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Client
        fields = (
            'name', 'user_type', 'email', 'phone', 'address',
            'country', 'account_status', 'notes'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-control form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'account_status': forms.Select(attrs={'class': 'form-control form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        phone_pattern = r'^\+?1?\d{9,15}$|^(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})$'
        if not re.match(phone_pattern, phone):
            raise forms.ValidationError("Enter a valid phone number (e.g., +1234567890 or 123-456-7890).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")

        # Validate passwords match
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        validate_password_strength(password1)
        try:
            password_validation.validate_password(password1)
        except forms.ValidationError as e:
            raise forms.ValidationError({"password1": e})

        # Ensure username is unique
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError({"username": "This username is already taken."})

        # Ensure email is unique
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError({"email": "This email is already taken."})

        return cleaned_data

    @transaction.atomic
    def save(self, request, commit=True):
        if request.user.is_authenticated and request.user.groups.filter(name='owner').exists():
            if not request.user.can_create_client():
                raise forms.ValidationError("You have reached your client creation limit.")
            current_user_owner = request.user
        else:
            if not request.user.owner.can_create_client():
                raise forms.ValidationError("You have reached your client creation limit.")
            current_user_owner = request.user.owner if request.user.is_authenticated else None
        user = CustomUser(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            is_client=True,
            owner=request.user if request.user.is_authenticated and not request.user.is_superuser else None
        )
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()

        client = super().save(commit=False)
        client.user = user
        client.client_id = uuid.uuid4()
        client.registration_date = date.today()
        if commit:
            client.save()
        return client