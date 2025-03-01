from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from .models import Warehouse,Product,Farmer
from django.db.models import Q
from .forms import WarehouseForm, ProductForm
from django.utils import timezone
from django.core.exceptions import PermissionDenied,ValidationError
from apps.authentication.models import CustomUser
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
import json


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
        {"current_user": request.user,
         'is_owner': request.user.groups.filter(name='owner').exists(),
         "form": form}
    )

# Create your views here.
@login_required(login_url="/login/")
def index(request):
    if request.user.is_superuser:
        queryset = Warehouse.objects.all()
        userqueryset = CustomUser.objects.all()
    else:
        queryset = (Warehouse.objects.filter(users=request.user) | Warehouse.objects.filter(ownership=request.user)).distinct()[:4]
    if  request.user.groups.filter(name='owner').exists():
        users = CustomUser.objects.filter(owner=request.user)
        for user in users:
            accessible_warehouses  = list(Warehouse.objects.filter(users=user).values_list('name', flat=True))
            user.acess = accessible_warehouses
        context = {'segment': 'index',
                   'warehouses': queryset,
                   'is_owner': request.user.groups.filter(name='owner').exists(),
                   'users' : users
                   }
    elif  request.user.is_superuser:
        for user in userqueryset:
            if request.user.groups.filter(name='owner').exists():
                accessible_warehouses = list(Warehouse.objects.filter(users=user).values_list('name', flat=True))
                user.acess = accessible_warehouses
        context = {'segment': 'index',
                   'warehouses': queryset,

                   'users': userqueryset
                   }

    else:
        context = {'segment': 'index',
                   'warehouses': queryset,
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


# views.py


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
    """
    Handle the creation of a new warehouse for authenticated users.

    Args:
        request: HTTP request object containing metadata and form data

    Returns:
        HttpResponse: Rendered form page on GET/invalid POST, redirect on success

    Raises:
        PermissionDenied: If user exceeds warehouse creation limit
    """

    def get_warehouse_limit(user):
        """Determine user's warehouse limit based on subscription plan."""
        subscription_limits = {
            'free': 1,
            'basic': 3,
            'pro': 5,
            'premium': 10
        }
        return subscription_limits.get(getattr(user, 'subscription_plan', 'free'), 1)

    # Check warehouse limit
    current_count = request.user.owned_warehouses.count()
    warehouse_limit = get_warehouse_limit(request.user)

    if current_count >= warehouse_limit:
        messages.error(
            request,
            f"You've reached the maximum of {warehouse_limit} warehouses "
            f"for your {getattr(request.user, 'subscription_plan', 'free')} plan."
        )
        raise PermissionDenied

    if request.method == 'POST':
        form = WarehouseForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    warehouse = form.save(commit=False)
                    warehouse.ownership = request.user
                    warehouse.save()
                    form.save_m2m()  # Save ManyToMany relationships
                messages.success(request, f"Warehouse '{warehouse.name}' created successfully!")
                return redirect('warehouse_list')
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, "An unexpected error occurred. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WarehouseForm(user=request.user)

    context = {
        'form': form,
        'form_action': 'Create',
        'warehouse_limit': warehouse_limit,
        'current_count': current_count,
    }
    return render(request, 'managment/create_warehouse.html', context)


def warehouse_list(request):
    """
    Display and manage warehouse list with filtering, editing, and user addition via modals.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Rendered page, form HTML, or JSON response
    """
    # Handle POST requests
    if request.method == 'POST':
        if 'slug' in request.POST:  # Edit warehouse
            warehouse = Warehouse.objects.get(slug=request.POST['slug'])
            if not request.user.is_superuser and warehouse.ownership != request.user and request.user not in warehouse.users.all():
                return JsonResponse({'error': 'You do not have permission to edit this warehouse.'}, status=403)

            form = WarehouseForm(request.POST, instance=warehouse, user=request.user)
            if form.is_valid():
                form.save()
                return JsonResponse({'success': f'Warehouse "{warehouse.name}" updated successfully'})
            else:
                return HttpResponse(
                    render(request, 'managment/warehouse_form_partial.html', {'form': form}).content,
                    content_type='text/html',
                    status=400
                )
        elif 'username' in request.POST:  # Add user
            if request.user.is_superuser or request.user.can_create_user(request.user.owned_users.count()):
                user = CustomUser(
                    username=request.POST['username'],
                    owner=request.user if not request.user.is_superuser else None,
                    subscription_plan='user',  # Default for new users
                    warehouse_limit=0,  # New users can't own warehouses by default
                    user_limit=0  # New users can't own other users by default
                )
                user.set_password(request.POST.get('password', 'default_password'))  # Set a default or require password
                user.save()
                return JsonResponse({'success': f'User "{user.username}" created successfully'})
            else:
                return JsonResponse({'error': 'You have reached your user creation limit.'}, status=403)

    # Handle GET requests
    name_query = request.GET.get('name', '').strip()
    location_query = request.GET.get('location', '').strip()
    owner_query = request.GET.get('owner', '').strip()
    users_query = request.GET.get('users', '').strip()

    if request.user.is_superuser:
        queryset = Warehouse.objects.all()
    else:
        queryset = (Warehouse.objects.filter(users=request.user) |
                    Warehouse.objects.filter(ownership=request.user)).distinct()

    query = Q()
    if name_query:
        query &= Q(name__icontains=name_query)
    if location_query:
        query &= Q(location__icontains=location_query)
    if owner_query:
        query &= Q(ownership__username__icontains=owner_query)
    if users_query:
        query &= Q(users__username__icontains=users_query)
    if query:
        queryset = queryset.filter(query).distinct()

    if not request.user.is_superuser and not queryset.exists():
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Denied: You do not have access to any warehouses."},
            status=403
        )

    # Handle AJAX for edit form
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'slug' in request.GET:
        warehouse = Warehouse.objects.get(slug=request.GET['slug'])
        form = WarehouseForm(instance=warehouse, user=request.user)
        return render(request, 'managment/warehouse_form_partial.html', {'form': form})

    context = {
        'warehouses': queryset,
        'filters': {
            'name': name_query,
            'location': location_query,
            'owner': owner_query,
            'users': users_query,
        },
        'total_count': queryset.count(),
        'user_limit': request.user.user_limit,
        'current_user_count': request.user.owned_users.count() if not request.user.is_superuser else CustomUser.objects.count(),
    }
    return render(request, 'managment/warehouse_list.html', context)

@login_required
def warehouse_detail(request, slug):
    warehouse = get_object_or_404(Warehouse, slug=slug)
    if request.user != warehouse.ownership and request.user not in warehouse.users.all() and not request.user.is_superuser:
        return render(request, '403.html', status=403)

    # Handle product listing
    sku = request.GET.get('sku', '')
    product_name_filter = request.GET.get('product_name', '')
    product_type = request.GET.get('product_type', '')
    status = request.GET.get('status', '')

    products = Product.objects.filter(warehouse=warehouse)
    if sku:
        products = products.filter(sku__icontains=sku)
    if product_name_filter:
        products = products.filter(product_name__icontains=product_name_filter)
    if product_type:
        products = products.filter(product_type=product_type)
    if status:
        products = products.filter(status=status)

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    filters = {
        'sku': sku,
        'product_name': product_name_filter,
        'product_type': product_type,
        'status': status,
    }

    # Handle add product form
    if request.method == 'POST' and 'add_product' in request.POST:
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.warehouse = warehouse
            product.save()
            return JsonResponse({'success': True})
        else:
            # Return errors as JSON
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            return JsonResponse({'errors': errors}, status=400)
    else:
        form = ProductForm(initial={'entry_date': timezone.now().date()})

    farmers = Farmer.objects.all()
    context = {
        'warehouse': warehouse,
        'page_obj': page_obj,
        'filters': filters,
        'form': form,
        'farmers': farmers,
        'today': timezone.now().date(),
    }
    return render(request, 'managment/products.html', context)