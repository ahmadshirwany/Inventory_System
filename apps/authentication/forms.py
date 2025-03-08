# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomUser

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
                self.fields['group'].choices = [("user", "User"),("customer", "Customer")]
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