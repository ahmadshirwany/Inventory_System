from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from .models import Warehouse,Product
from django.db.models import Q
from .forms import WarehouseForm, ProductForm
from django.utils import timezone
from django.core.exceptions import PermissionDenied,ValidationError
from apps.authentication.models import CustomUser
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from .models import get_product_metadata

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
        users = CustomUser.objects.filter(owner=request.user,groups__name='user')
        for user in users:
            accessible_warehouses  = list(Warehouse.objects.filter(users=user).values_list('name', flat=True))
            user.acess = accessible_warehouses
        cutomers = CustomUser.objects.filter(owner=request.user,groups__name='customer')
        for cutomer in cutomers:
            accessible_warehouses = list(Warehouse.objects.filter(users=cutomer).values_list('name', flat=True))
            cutomer.acess = accessible_warehouses
        context = {'segment': 'index',
                   'warehouses': queryset,
                   'is_owner': request.user.groups.filter(name='owner').exists(),
                   'users' : users,
                   'cutomers':cutomers
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

    def get_warehouse_limit(user):
        """Determine user's warehouse limit based on subscription plan."""
        subscription_limits = {
            'free': 1,
            'basic': 3,
            'pro': 5,
            'premium': 10
        }
        return subscription_limits.get(getattr(user, 'subscription_plan', 'free'), 1)
    if not request.user.is_superuser and not request.user.groups.filter(name='owner').exists():
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Deniedd: You do not have Acess to edit this warehouse."},
            status=403
        )
    # Check warehouse limit
    current_count = request.user.owned_warehouses.count()
    warehouse_limit = request.user.warehouse_limit

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
        'is_owner': request.user.groups.filter(name='owner').exists(),
        'total_count': queryset.count(),
        'user_limit': request.user.user_limit,
        'current_user_count': request.user.owned_users.count() if not request.user.is_superuser else CustomUser.objects.count(),
    }
    return render(request, 'managment/warehouse_list.html', context)


def get_product_metadata_view(request):
    product_name = request.GET.get('product_name')
    if not product_name:
        return JsonResponse({'error': 'Product name is required'}, status=400)

    metadata = get_product_metadata()
    if product_name in metadata:
        return JsonResponse(metadata[product_name])
    return JsonResponse({'error': 'Product not found'}, status=404)

@login_required
def warehouse_detail(request, slug):
    # Authorization check
    if not request.user.is_superuser:
        warehouse = get_object_or_404(Warehouse, slug=slug)
        if request.user != warehouse.ownership and request.user not in warehouse.users.all():
            return render(
                request,
                "home/page-403.html",
                {
                    'is_owner': request.user.groups.filter(name='owner').exists(),
                    "message": "Access Denied: You do not have permission to access this warehouse."
                },
                status=403
            )
    else:
        warehouse = get_object_or_404(Warehouse, slug=slug)

    products = Product.objects.filter(warehouse=warehouse)
    filters = {
        'sku': request.GET.get('sku', ''),
        'barcode': request.GET.get('barcode', ''),
        'product_name': request.GET.get('product_name', ''),
        'product_type': request.GET.get('product_type', ''),
        'status': request.GET.get('status', ''),
    }

    # Apply filters
    if filters['sku']:
        products = products.filter(sku__icontains=filters['sku'])
    if filters['barcode']:
        products = products.filter(barcode__icontains=filters['barcode'])
    if filters['product_name']:
        products = products.filter(product_name__icontains=filters['product_name'])
    if filters['product_type']:
        products = products.filter(product_type=filters['product_type'])
    if filters['status']:
        products = products.filter(status=filters['status'])

    # Pagination
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form = ProductForm(request.POST)

        if 'add_product' in request.POST:
            if form.is_valid():
                product = form.save(commit=False)
                product.warehouse = warehouse
                try:
                    product.full_clean()
                    product.save()
                    return JsonResponse({'success': True, 'message': 'Product added successfully'}, status=201)
                except ValidationError as e:
                    return JsonResponse({'success': False, 'errors': e.message_dict}, status=400)
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        elif 'edit_product' in request.POST:
            sku = request.POST.get('sku')
            product = get_object_or_404(Product, sku=sku, warehouse=warehouse)
            form = ProductForm(request.POST, instance=product)
            if form.is_valid():
                try:
                    updated_product = form.save(commit=False)
                    updated_product.full_clean()
                    updated_product.save()
                    return JsonResponse({'success': True, 'message': 'Product updated successfully'}, status=200)
                except ValidationError as e:
                    return JsonResponse({'success': False, 'errors': e.message_dict}, status=400)
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)



        elif 'take_out_product' in request.POST:

            sku = request.POST.get('sku')

            product = get_object_or_404(Product, sku=sku, warehouse=warehouse)

            # Get take-out values

            quantity_to_take = request.POST.get('quantity_to_take', '')

            weight_kg_to_take = request.POST.get('weight_kg_to_take', '')

            # Convert to float/int, handling empty strings

            quantity_to_take = int(quantity_to_take) if quantity_to_take else 0

            weight_kg_to_take = float(weight_kg_to_take) if weight_kg_to_take else 0.0

            # At least one value must be provided

            if quantity_to_take <= 0 and weight_kg_to_take <= 0:
                return JsonResponse({

                    'success': False,

                    'errors': {'__all__': ['Please specify at least one of Quantity or Weight (kg) to take out.']}

                }, status=400)

            # Validate quantity

            if quantity_to_take > product.quantity_in_stock:
                return JsonResponse({

                    'success': False,

                    'errors': {'quantity_to_take': [f'Cannot take out more than {product.quantity_in_stock} units']}

                }, status=400)

            # Validate weight

            if weight_kg_to_take > (product.weight_quantity_kg or 0):
                return JsonResponse({

                    'success': False,

                    'errors': {'weight_kg_to_take': [f'Cannot take out more than {product.weight_quantity_kg} kg']}

                }, status=400)

            # Calculate weight per unit if both fields exist

            weight_per_unit = None

            if product.quantity_in_stock > 0 and product.weight_quantity_kg:
                weight_per_unit = product.weight_quantity_kg / product.quantity_in_stock

            # Update quantity and weight

            if quantity_to_take > 0:

                product.quantity_in_stock -= quantity_to_take

                if weight_per_unit and product.weight_quantity_kg:
                    proportional_weight = quantity_to_take * weight_per_unit

                    product.weight_quantity_kg -= min(proportional_weight, product.weight_quantity_kg)

            if weight_kg_to_take > 0:

                product.weight_quantity_kg = (product.weight_quantity_kg or 0) - weight_kg_to_take

                if weight_per_unit and product.quantity_in_stock > 0:
                    proportional_quantity = int(weight_kg_to_take / weight_per_unit)

                    product.quantity_in_stock -= min(proportional_quantity, product.quantity_in_stock)

            # Ensure non-negative values

            product.quantity_in_stock = max(0, product.quantity_in_stock)

            product.weight_quantity_kg = max(0, product.weight_quantity_kg)

            # Update status and total value

            if product.quantity_in_stock == 0 or product.weight_quantity_kg == 0:
                product.status = 'Out of Stock'

                product.exit_date = timezone.now().date()

            product.total_value = product.unit_price * product.quantity_in_stock

            product.save()

            return JsonResponse({'success': True, 'message': 'Product taken out successfully'}, status=200)
    # For GET requests, render the products page
    return render(request, 'managment/products.html', {
        'warehouse': warehouse,
        'page_obj': page_obj,
        'form': ProductForm(warehouse=warehouse),  # Pass an empty form for the modal
        'filters': filters,
        'is_owner': request.user.groups.filter(name='owner').exists(),
    })