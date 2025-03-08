# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import LoginForm, SignUpForm
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from .models import CustomUser
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import Group
from django.contrib import messages
from django.views import View
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class CustomLogoutView(View):
    def get(self, request):
        return self.logout_and_redirect(request)

    def post(self, request):
        return self.logout_and_redirect(request)

    def logout_and_redirect(self, request):
        logout(request)
        return redirect('login')
def login_view(request):
    form = LoginForm(request.POST or None)

    msg = None

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("/")
            else:
                msg = 'Invalid credentials'
        else:
            msg = 'Error validating the form'

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


@login_required
def user_profile(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after changing the password
            return redirect("profile")  # Redirect to the profile page after successful password change
        profile = CustomUser.objects.get_or_create(user=request.user)[0]
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "managment/user_profile.html",
        {"current_user": request.user,
         'is_owner': request.user.groups.filter(name='owner').exists(),
         "form": form}
    )
from django.contrib import messages
@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile_picture = request.FILES['profile_picture']
            request.user.profile_picture = profile_picture
            request.user.save()
            messages.success(request, 'Your profile picture has been updated successfully.')
        else:
            messages.error(request, 'No file was selected.')
    return redirect('user_profile')  # Redirect back to the user profile page

@login_required
def create_user(request):
    # Ensure only superusers or users in the 'owner' group can access this view
    if not request.user.is_superuser:
        if not request.user.groups.filter(name='owner').exists():
            return render(
                request,
                "home/page-403.html",
                {
                    'is_owner': request.user.groups.filter(name='owner').exists(),
                    "message": "Access Denied: You do not have permission to create users."},
                status=403
            )
    msg = None
    success = False

    if request.method == "POST":
        # Pass the current user to the form
        form = CustomUserCreationForm(request.POST, user=request.user)
        if form.is_valid():
            user = form.save()
            # Assign the selected group to the user
            group_name = form.cleaned_data.get("group")
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            msg = f'User "{user.username}" has been created successfully and assigned to the "{group_name}" group.'
            success = True
            # Optionally, redirect to a different page
            # return redirect("admin_dashboard")  # Uncomment and adjust URL as needed
        else:
            msg = 'Form is not valid. Please correct the errors below.'
    else:
        # Pass the current user to the form and restrict group choices based on permissions
        initial_data = {}
        if not request.user.is_superuser:
            initial_data["group"] = "user"  # Default to 'user' if not a superuser
        form = CustomUserCreationForm(user=request.user, initial=initial_data)

    return render(
        request,
        "accounts/create_user.html",
        {"form": form,
         'is_owner': request.user.groups.filter(name='owner').exists(),
         "msg": msg, "success": success}
    )
def register_user(request):
    msg = None
    success = False

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)

            msg = 'User created - please <a href="/login">login</a>.'
            success = True

            # return redirect("/login/")

        else:
            msg = 'Form is not valid'
    else:
        form = SignUpForm()

    return render(request, "accounts/register.html", {"form": form, "msg": msg, "success": success})
@login_required
def user_list(request):
    # Ensure only superusers or users in the 'owner' group can access this view
    if not request.user.is_superuser:
        if not request.user.groups.filter(name='owner').exists():
            return render(
                request,
                "home/page-403.html",
                {
                    'is_owner': request.user.groups.filter(name='owner').exists(),
                    "message": "Access Denied: You do not have any users."
                },
                status=403
            )
        else:
            # Owners see only their managed users
            queryset = CustomUser.objects.filter(owner=request.user)
    else:
        # Superusers see all users
        queryset = CustomUser.objects.all()

    # Handle filtering
    filters = {}
    if request.GET.get('username'):
        queryset = queryset.filter(username__icontains=request.GET['username'])
        filters['username'] = request.GET['username']
    if request.GET.get('email'):
        queryset = queryset.filter(email__icontains=request.GET['email'])
        filters['email'] = request.GET['email']
    if request.GET.get('group'):
        queryset = queryset.filter(groups__name=request.GET['group'])
        filters['group'] = request.GET['group']

    # Pagination
    paginator = Paginator(queryset, 10)  # Show 10 users per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        page_obj = paginator.page(paginator.num_pages)

    # Context for owners dropdown in Add User modal
    if request.user.is_superuser:
        owners = CustomUser.objects.filter(groups__name='owner')
    else:
        owners = CustomUser.objects.filter(id=request.user.id)

    # Get all groups for the filter dropdown
    all_groups = Group.objects.all()

    # Prepare context
    context = {
        'page_obj': page_obj,
        'filters': filters,
        'owners': owners,
        'groups': all_groups,
        'is_owner': request.user.groups.filter(name='owner').exists(),
    }

    # Handle POST requests for adding/deleting users
    if request.method == 'POST':
        if 'add_user' in request.POST:
            username = request.POST.get('username')
            email = request.POST.get('email')
            warehouse_limit = request.POST.get('warehouse_limit') or None
            user_limit = request.POST.get('user_limit') or None
            owner_id = request.POST.get('owner') or None

            try:
                user = CustomUser.objects.create(
                    username=username,
                    email=email,
                    warehouse_limit=warehouse_limit if warehouse_limit else None,
                    user_limit=user_limit if user_limit else None,
                    owner=CustomUser.objects.get(id=owner_id) if owner_id else request.user if not request.user.is_superuser else None
                )
                user.set_unusable_password()
                user.save()
                return render(request, 'accounts/user_list.html', context)
            except Exception as e:
                context['errors'] = {'form': [str(e)]}

        elif 'delete_user' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user_to_delete = CustomUser.objects.get(id=user_id)
                if request.user.is_superuser or user_to_delete.owner == request.user:
                    user_to_delete.delete()
                return render(request, 'accounts/user_list.html', context)
            except CustomUser.DoesNotExist:
                context['errors'] = {'delete': ['User not found']}
            except Exception as e:
                context['errors'] = {'delete': [str(e)]}

    return render(request, 'accounts/user_list.html', context)
@login_required
def edit_user(request):
    pass