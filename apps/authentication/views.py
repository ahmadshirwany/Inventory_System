# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
from django.http import JsonResponse
# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import LoginForm, SignUpForm
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm,FarmerCreationForm
from .models import CustomUser,Farmer
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
        # Check if this is a password update
        if 'update_password' in request.POST:
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                try:
                    user = form.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Your password was successfully updated!")
                    return redirect("user_profile")
                except Exception as e:
                    messages.error(request, f"An error occurred while updating your password: {str(e)}")
            else:
                if 'old_password' in form.errors:
                    messages.error(request, "Please enter your current password correctly.")
                if 'new_password1' in form.errors or 'new_password2' in form.errors:
                    messages.error(request, "Please check your new password entries.")
                if len(form.errors) > 1:
                    messages.error(request, "Please correct the errors below.")

        # Check if this is a profile picture update
        elif 'profile_picture' in request.FILES:
            try:
                profile = CustomUser.objects.get_or_create(user=request.user)[0]
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
                messages.success(request, "Profile picture updated successfully!")
                return redirect("user_profile")
            except Exception as e:
                messages.error(request, f"Error updating profile picture: {str(e)}")

    # For GET requests or when POST fails, show the form
    form = PasswordChangeForm(request.user)

    context = {
        "current_user": request.user,
        'is_owner': request.user.groups.filter(name='owner').exists(),
        "form": form,
    }
    return render(request, "managment/user_profile.html", context)
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

    current_count = request.user.owned_users.count()
    user_limit = request.user.user_limit

    if current_count >= user_limit:
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Deniedd: You reached your user creation limit.",
             'is_owner': request.user.groups.filter(name='owner').exists(), },
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
    if request.method == 'POST':
        if 'add_user' in request.POST:
            form = CustomUserCreationForm(request.POST, user=request.user)
            if form.is_valid():
                form.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        elif 'edit_user' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user = CustomUser.objects.get(id=user_id)
                user.username = request.POST.get('username')
                user.email = request.POST.get('email')
                warehouse_limit = request.POST.get('warehouse_limit')
                user_limit = request.POST.get('user_limit')
                owner_id = request.POST.get('owner')

                user.warehouse_limit = warehouse_limit if warehouse_limit else None
                user.user_limit = user_limit if user_limit else None
                user.owner = CustomUser.objects.get(id=owner_id) if owner_id else None

                user.save()
                return JsonResponse({'success': True})
            except CustomUser.DoesNotExist:
                return JsonResponse({'success': False, 'errors': {'user_id': ['User not found']}}, status=404)
            except Exception as e:
                return JsonResponse({'success': False, 'errors': {'__all__': [str(e)]}}, status=400)

        elif 'delete_user' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user = CustomUser.objects.get(id=user_id)
                user.delete()
                return JsonResponse({'success': True})
            except CustomUser.DoesNotExist:
                return JsonResponse({'success': False, 'errors': {'user_id': ['User not found']}}, status=404)

    # GET request handling
    if request.user.groups.filter(name='owner').exists():
        users = CustomUser.objects.filter(groups__name__in=['user'])
        users = users.filter(owner=request.user)
    else:
        users = CustomUser.objects.all()
    # Filtering
    filters = {}
    if username := request.GET.get('username'):
        users = users.filter(username__icontains=username)
        filters['username'] = username
    if email := request.GET.get('email'):
        users = users.filter(email__icontains=email)
        filters['email'] = email
    if group := request.GET.get('group'):
        users = users.filter(groups__name=group)
        filters['group'] = group

    # Pagination
    paginator = Paginator(users, 10)  # 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filters': filters,
        'groups': Group.objects.all(),
        'owners': CustomUser.objects.all(),
        'is_owner': request.user.groups.filter(name='owner').exists()
        # You might want to filter this
    }
    return render(request, 'accounts/user_list.html', context)
@login_required
def farmer_list(request):
    # Handle POST requests (add/delete)
    is_owner = Farmer.objects.filter(user__owner=request.user).exists()
    can_add_or_edit = request.user.is_superuser or is_owner
    if request.method == 'POST':
        if 'add_farmer' in request.POST:
            if not can_add_or_edit:
                return JsonResponse({'error': 'Permission denied: Only owners or superusers can add farmers'},
                                    status=403)
            form = FarmerCreationForm(request.POST)
            if form.is_valid():
                form.save(request)  # Pass request to set owner
                return redirect('farmer_list')
            else:
                return JsonResponse({'errors': form.errors}, status=400)
        elif 'delete_farmer' in request.POST:
            farmer_id = request.POST.get('farmer_id')
            try:
                farmer = Farmer.objects.get(id=farmer_id)
                if request.user.is_superuser or farmer.user.owner == request.user:
                    farmer.user.delete()  # Delete associated user as well
                    farmer.delete()
                    return redirect('farmer_list')
                else:
                    return JsonResponse({'error': 'Permission denied'}, status=403)
            except Farmer.DoesNotExist:
                return JsonResponse({'error': 'Farmer not found'}, status=404)

    # Handle GET request (display list)
    if request.user.groups.filter(name='owner').exists():
        farmers = Farmer.objects.filter(user__owner=request.user)
    elif request.user.is_superuser:
        farmers = Farmer.objects.all()
    elif request.user.groups.filter(name='user').exists():
        farmers = Farmer.objects.filter(user__owner=request.user.owner)

    # Filtering
    filters = {}
    if 'name' in request.GET:
        filters['name'] = request.GET['name']
        farmers = farmers.filter(name__icontains=filters['name'])
    if 'farm_name' in request.GET:
        filters['farm_name'] = request.GET['farm_name']
        farmers = farmers.filter(farm_name__icontains=filters['farm_name'])
    if 'email' in request.GET:
        filters['email'] = request.GET['email']
        farmers = farmers.filter(email__icontains=filters['email'])

    # Pagination
    paginator = Paginator(farmers, 10)  # 10 farmers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/farmer_list.html', {
        'page_obj': page_obj,
        'filters': filters,
        'form': FarmerCreationForm(),
        'is_owner': is_owner
    })
@login_required
def edit_user(request):
    pass