from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from .models import Warehouse
from django.db.models import Q
from .forms import WarehouseForm
from django.core.exceptions import PermissionDenied


@login_required
def update_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after changing the password
            return redirect("profile")  # Redirect to the profile page after successful password change
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "managment/user_profile.html",
        {"current_user": request.user, "form": form}
    )

# Create your views here.
@login_required(login_url="/login/")
def index(request):
    context = {'segment': 'index',
               'is_owner': request.user.groups.filter(name='owner').exists()
               }

    html_template = loader.get_template('managment/index.html')
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split('/')[-1]
        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('managment/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

#
# @login_required  # Ensure the user is authenticated
# def warehouse_list(request):
#     if request.user.is_superuser:
#         # Superusers can see all warehouses
#         warehouses = Warehouse.objects.all()
#     else:
#         # Regular users can only see warehouses they are associated with
#         warehouses = Warehouse.objects.filter(users=request.user)
#     # If no warehouses are found for a regular user, raise a 403 Forbidden error
#     if not request.user.is_superuser and not warehouses.exists():
#         return render(
#             request,
#             "home/page-403.html",
#             {"message": "Access Denied: You do not have Acess to any of the warehouses."},
#             status=403
#         )
#     context = {
#         'warehouses': warehouses
#     }
#     return render(request, 'managment/warehouse_list.html', context)

# views.py
@login_required
def warehouse_detail(request, slug):
    context = {}
    html_template = loader.get_template('home/page-404.html')
    return HttpResponse(html_template.render(context, request))

@login_required
def edit_warehouse(request, slug):
    warehouse = get_object_or_404(Warehouse, slug=slug)
    if not request.user.is_superuser and warehouse.ownership != request.user:
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Denied: You do not have Acess to edit this warehouse."},
            status=403
        )
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('warehouse_list')  # Redirect to the warehouse list page
    else:
        form = WarehouseForm(instance=warehouse, user=request.user)
    context = {'form': form, 'warehouse': warehouse}
    return render(request, 'managment/edit_warehouse.html', context)

@login_required
def create_warehouse(request):
    def is_within_limit(user):
        subscription_plan = getattr(user, 'subscription_plan', 'free')  # Default to 'free' if not set

        return user.owned_warehouses.count() < user.warehouse_limit

    if not is_within_limit(request.user):
        raise PermissionDenied("You have reached the maximum number of warehouses allowed by your subscription plan.")

    if request.method == 'POST':
        form = WarehouseForm(request.POST, user=request.user)
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse.ownership = request.user  # Set the ownership to the current user
            warehouse.save()
            form.save_m2m()  # Save ManyToMany relationships (e.g., users)
            return redirect('warehouse_list')  # Redirect to the warehouse list page
    else:
        form = WarehouseForm(user=request.user)

    context = {'form': form}
    return render(request, 'managment/create_warehouse.html', context)

@login_required  # Ensure the user is authenticated
def warehouse_list(request):
    search_query = request.GET.get('search', '').strip()
    if request.user.is_superuser:
        # Superusers can see all warehouses
        queryset = Warehouse.objects.all()
    else:
        # Regular users can only see warehouses they are associated with
        queryset = Warehouse.objects.filter(users=request.user) | Warehouse.objects.filter(ownership=request.user)
    # Apply search filtering
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |  # Search by name
            Q(location__icontains=search_query)  # Search by location
        )

    # If no warehouses are found for a regular user, raise a 403 Forbidden error
    if not request.user.is_superuser and not queryset.exists():
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Denied: You do not have Acess to any of the warehouses."},
            status=403
        )

    context = {
        'warehouses': queryset,
        'search_query': search_query,  # Pass the search query back to the template
    }
    return render(request, 'managment/warehouse_list.html', context)