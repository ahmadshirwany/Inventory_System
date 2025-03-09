# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import datetime
import uuid
from datetime import timezone

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomUser, Farmer


class CustomUserCreationForm(UserCreationForm):
    group = forms.ChoiceField(
        choices=[],
        label="Assign to Group",
        help_text="Select the group to which the user will belong."
    )

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2", "group")

    def __init__(self, *args, **kwargs):
        # Pop the 'user' argument from kwargs
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Dynamically set group choices based on user permissions
        if self.request_user and self.request_user.is_authenticated:
            if self.request_user.is_superuser:
                self.fields['group'].choices = [("owner", "Owner"), ("user", "User"),("customer", "Customer")]
            else:
                self.fields['group'].choices = [("user", "User")]
        else:
            # Default to 'user' if no user is provided or the user is not authenticated
            self.fields['group'].choices = [("user", "User")]

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.request_user:
            user.owner = self.request_user  # Assign the request user as the owner
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))


class SignUpForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email",
                "class": "form-control"
            }
        ))
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password check",
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
    # CustomUser fields
    username = forms.CharField(max_length=150, required=True, help_text="Unique username for the farmer's user account.")
    email = forms.EmailField(required=False, help_text="Email address for the user (optional).")
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

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        # Validate passwords match
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        # Ensure username is unique
        username = cleaned_data.get("username")
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")

        # Use form email if provided, otherwise generate one
        email = cleaned_data.get("email")
        if not email:
            cleaned_data['email'] = f"{username}@example.com"

        return cleaned_data

    def save(self, request, commit=True):
        # Create the CustomUser instance
        user = CustomUser(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            is_farmer=True,
            owner=request.user if request.user.is_authenticated else None  # Set owner as request.user
        )
        user.set_password(self.cleaned_data['password1'])  # Set the password
        if commit:
            user.save()

        # Create the Farmer instance
        farmer = super().save(commit=False)
        farmer.user = user
        farmer.farmer_id = uuid.uuid4()  # Ensure unique farmer_id
        farmer.registration_date = datetime.datetime.now().date()  # Set registration_date to today
        if commit:
            farmer.save()

        return farmer