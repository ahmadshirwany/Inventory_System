import decimal
import json
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django import template
from django.contrib.auth.decorators import login_required,user_passes_test
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from .models import Warehouse,Product,ItemRequest
from django.db.models import Q, Max
from .forms import WarehouseForm, ProductForm,ItemRequestForm,PACKAGING_CONDITIONS
from django.utils import timezone
from django.core.exceptions import PermissionDenied,ValidationError
from apps.authentication.models import CustomUser
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from .models import get_product_metadata, refresh_product_metadata
from django.db.models import Sum
import os
from django.conf import settings
from .forms import ProductMetadataForm
from decimal import Decimal,ROUND_HALF_UP

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
                   'is_user': request.user.groups.filter(name='user').exists(),
                   'users' : users,
                   'cutomers':cutomers
                   }
    elif  request.user.is_superuser:
        users = CustomUser.objects.filter(groups__name='user')
        for user in users:
                accessible_warehouses = list(Warehouse.objects.filter(users=user).values_list('name', flat=True))
                user.acess = accessible_warehouses
        cutomers = CustomUser.objects.filter( groups__name='customer')
        for cutomer in cutomers:
            accessible_warehouses = list(Warehouse.objects.filter(users=cutomer).values_list('name', flat=True))
            cutomer.acess = accessible_warehouses
        context = {'segment': 'index',
                   'warehouses': queryset,
                   'users': users,
                   'cutomers': cutomers,
                   'is_user': request.user.groups.filter(name='user').exists(),
                   }

    else:
        context = {'segment': 'index',
                   'warehouses': queryset,
                   'is_owner': request.user.groups.filter(name='owner').exists(),
                   'is_user': request.user.groups.filter(name='user').exists(),
                   'is_client': request.user.groups.filter(name='client').exists(),
                   'is_farmer': request.user.groups.filter(name='farmer').exists(),
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
            {"message": "Access Deniedd: You do not have Acess to edit this warehouse.",
             'is_owner': request.user.groups.filter(name='owner').exists(),},
            status=403
        )
    # Check warehouse limit
    current_count = request.user.owned_warehouses.count()
    warehouse_limit = request.user.warehouse_limit

    if warehouse_limit is None or current_count >= warehouse_limit:
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Deniedd: You reached your warehouse creation limit.",
             'is_owner': request.user.groups.filter(name='owner').exists(),},
            status=403
        )

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
        'is_owner': request.user.groups.filter(name='owner').exists(),
    }
    return render(request, 'managment/create_warehouse.html', context)


def warehouse_list(request):
    if request.method == 'POST':
        if 'slug' in request.POST:  # Edit warehouse
            warehouse = Warehouse.objects.get(slug=request.POST['slug'])
            if not request.user.is_superuser and warehouse.ownership != request.user and request.user not in warehouse.users.all():
                return JsonResponse({'error': 'You do not have permission to edit this warehouse.'}, status=403)

            form = WarehouseForm(request.POST, instance=warehouse, user=request.user)
            if form.is_valid():
                warehouse = form.save(commit=False)
                warehouse.save()

                # Explicitly save ManyToMany relationships
                form.save_m2m()
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
    warehouses = queryset
    for warehouse in warehouses:
        warehouse.filtered_users = warehouse.users.filter(groups__name='user')
        warehouse.filtered_clients = warehouse.users.filter(groups__name='client')
        warehouse.filtered_farmers = warehouse.users.filter(groups__name='customer')
    context = {
        'warehouses': warehouses,
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
        'is_client': request.user.groups.filter(name='client').exists(),
        'is_user': request.user.groups.filter(name='user').exists(),
        'is_farmer': request.user.groups.filter(name='farmer').exists(),
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
    if not request.user.is_superuser:
        warehouse = get_object_or_404(Warehouse, slug=slug)
        if not hasattr(warehouse, 'ownership') or warehouse.ownership is None or \
                (request.user != warehouse.ownership and request.user not in warehouse.users.all()):
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

    products = Product.objects.filter(warehouse=warehouse).select_related('farmer').prefetch_related('warehouse')
    filters = {
        'sku': request.GET.get('sku', ''),
        'barcode': request.GET.get('barcode', ''),
        'product_name': request.GET.get('product_name', ''),
        'product_type': request.GET.get('product_type', ''),
        'status': request.GET.get('status', ''),
    }

    valid_product_types = [choice[0] for choice in Product._meta.get_field('product_type').choices]
    valid_statuses = [choice[0] for choice in Product._meta.get_field('status').choices]
    if filters['product_type'] and filters['product_type'] not in valid_product_types:
        filters['product_type'] = ''
    if filters['status'] and filters['status'] not in valid_statuses:
        filters['status'] = ''

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

    sort_by = request.GET.get('sort_by', 'entry_date')
    valid_sort_fields = ['sku', 'product_name', 'entry_date', 'status', '-entry_date']
    if sort_by in valid_sort_fields:
        products = products.order_by(sort_by)
    else:
        products = products.order_by('entry_date')

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form = ProductForm(request.POST, warehouse=warehouse)
        if 'add_product' in request.POST:
            if form.is_valid():
                product = form.save(commit=False)
                product.warehouse = warehouse
                try:
                    product.full_clean()
                    product.save()
                    return JsonResponse({'success': True, 'message': 'Product added successfully'}, status=201)
                except ValidationError as e:
                    return JsonResponse({'success': False, 'errors': dict(e)}, status=400)
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        elif 'delete_product' in request.POST:
            sku = request.POST.get('sku')
            if not sku:
                return JsonResponse({'success': False, 'errors': {'sku': ['SKU is required']}}, status=400)
            try:
                product = get_object_or_404(Product, sku=sku, warehouse=warehouse)
                if request.user.is_superuser or request.user == warehouse.ownership:
                    product.delete()
                    return JsonResponse({'success': True, 'message': 'Product deleted successfully'}, status=200)
                else:
                    return JsonResponse(
                        {'success': False, 'errors': {'permission': ['You do not have permission to delete this product']}},
                        status=403
                    )
            except Exception as e:
                return JsonResponse({'success': False, 'errors': {'server': [str(e)]}}, status=400)

        elif 'take_out_product' in request.POST:
            sku = request.POST.get('sku')
            product = get_object_or_404(Product, sku=sku, warehouse=warehouse)

            quantity_to_take = request.POST.get('quantity_to_take', '')
            weight_kg_to_take = request.POST.get('weight_kg_to_take', '')

            quantity_to_take = int(quantity_to_take) if quantity_to_take else 0
            weight_kg_to_take = decimal.Decimal(weight_kg_to_take) if weight_kg_to_take else decimal.Decimal('0.0')

            if quantity_to_take <= 0 and weight_kg_to_take <= 0:
                return JsonResponse({
                    'success': False,
                    'errors': {'__all__': ['Please specify at least one of Quantity or Weight (kg) to take out.']}
                }, status=400)

            if quantity_to_take > 0 and product.quantity_in_stock is not None:
                if quantity_to_take > product.quantity_in_stock:
                    return JsonResponse({
                        'success': False,
                        'errors': {'quantity_to_take': [f'Cannot take out more than {product.quantity_in_stock} units']}
                    }, status=400)

            if weight_kg_to_take > (product.weight_quantity_kg or 0):
                return JsonResponse({
                    'success': False,
                    'errors': {'weight_kg_to_take': [f'Cannot take out more than {product.weight_quantity_kg} kg']}
                }, status=400)

            weight_per_unit = None
            if product.quantity_in_stock is not None and product.quantity_in_stock > 0 and product.weight_quantity_kg:
                weight_per_unit = float(product.weight_quantity_kg) / product.quantity_in_stock

            if product.packaging_condition == 'Bulk' and product.quantity_in_stock is None:
                if weight_kg_to_take > 0:
                    product.weight_quantity_kg = (product.weight_quantity_kg or decimal.Decimal(
                        '0')) - weight_kg_to_take

            else:
                if quantity_to_take > 0:
                    product.quantity_in_stock -= quantity_to_take
                    if weight_per_unit and product.weight_quantity_kg:
                        proportional_weight = decimal.Decimal(str(quantity_to_take * weight_per_unit))

                        product.weight_quantity_kg -= min(proportional_weight, product.weight_quantity_kg)
                if weight_kg_to_take > 0:
                    product.weight_quantity_kg = (product.weight_quantity_kg or decimal.Decimal(
                        '0')) - weight_kg_to_take

                    if weight_per_unit and product.quantity_in_stock is not None and product.quantity_in_stock > 0:
                        proportional_quantity = int(weight_kg_to_take / Decimal(weight_per_unit))
                        product.quantity_in_stock -= min(proportional_quantity, product.quantity_in_stock)

            # Ensure non-negative values

            if product.quantity_in_stock is not None:
                product.quantity_in_stock = max(0, product.quantity_in_stock)

            product.weight_quantity_kg = max(0, product.weight_quantity_kg)

            # Update status if out of stock

            if (
                    product.quantity_in_stock == 0 or product.quantity_in_stock is None) and product.weight_quantity_kg == 0:
                product.status = 'Out of Stock'
                product.exit_date = timezone.now().date()

            product.weight_quantity = product.weight_quantity_kg * 1000
            product.total_value = (product.unit_price * product.weight_quantity_kg).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if product.weight_quantity_kg else 0

            try:
                product.full_clean()
                product.save()
                return JsonResponse({'success': True, 'message': 'Product taken out successfully'}, status=200)
            except ValidationError as e:
                return JsonResponse({'success': False, 'errors': dict(e)}, status=400)

    metadata = get_product_metadata()
    context = {
        'warehouse': warehouse,
        'page_obj': page_obj,
        'form': ProductForm(warehouse=warehouse),
        'filters': filters,
        'is_owner': request.user.groups.filter(name='owner').exists(),
        'is_user': request.user.groups.filter(name='user').exists(),
        'product_metadata': json.dumps(metadata),
        'packaging_conditions': json.dumps(PACKAGING_CONDITIONS),
        'is_farmer': request.user.groups.filter(name='farmer').exists(),
        # 'filter_query': urlencode(filters)
    }
    return render(request, 'managment/products.html', context)

import uuid
@login_required
def generate_barcode(request, slug):
    warehouse = get_object_or_404(Warehouse, slug=slug)
    while True:
        barcode = str(uuid.uuid4().int)[:12]
        if not Product.objects.filter(barcode=barcode).exists():
            return JsonResponse({'barcode': barcode})
    return JsonResponse({'error': 'Unable to generate unique barcode'}, status=500)

@login_required
def generate_sku(request, slug):
    warehouse = get_object_or_404(Warehouse, slug=slug)
    try:
        max_seq = Product.objects.filter(warehouse=warehouse).aggregate(Max('sku'))['sku__max']
        seq = 1
        if max_seq and '-' in max_seq:
            try:
                seq = int(max_seq.split('-')[-1]) + 1
            except ValueError:
                seq = 1
        sku = f"WH-{warehouse.id}-{seq:06d}"
        return JsonResponse({'sku': sku})
    except Exception as e:
        return JsonResponse({'error': f'Unable to generate unique SKU: {str(e)}'}, status=500)

@login_required
def warehouse_detail_customer(request, slug):
    if not request.user.groups.filter(name='client').exists():
        return render(request, "home/page-403.html", {"message": "Access Denied: This page is for customers only."}, status=403)

    warehouse = get_object_or_404(Warehouse, slug=slug)
    if request.user not in warehouse.users.all():
        return render(request, "home/page-403.html", {"message": "Access Denied: You do not have permission to view this warehouse."}, status=403)

    products = Product.objects.filter(warehouse=warehouse, status='In Stock')
    filters = {
        'product_name': request.GET.get('product_name', ''),
        'product_type': request.GET.get('product_type', ''),
    }

    if filters['product_name']:
        products = products.filter(product_name__icontains=filters['product_name'])
    if filters['product_type']:
        products = products.filter(product_type=filters['product_type'])

    aggregated_products = products.values('product_name', 'product_type').annotate(
        total_weight_kg=Sum('weight_quantity_kg'),
        max_unit_price=Max('unit_price'),
        total_quantity=Sum('quantity_in_stock')
    ).order_by('product_name')

    aggregated_products_list = [
        {
            'product_name': item['product_name'],
            'product_type': item['product_type'],
            'total_weight_kg': float(item['total_weight_kg']) if item['total_weight_kg'] else 0,
            'max_unit_price': float(item['max_unit_price']) if item['max_unit_price'] else 0,
            'total_quantity': item['total_quantity'] or 0
        }
        for item in aggregated_products
    ]

    paginator = Paginator(aggregated_products_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form = ItemRequestForm(request.POST, user=request.user, warehouse=warehouse)
        if form.is_valid():
            try:
                product_name = form.cleaned_data['product_name']
                max_unit_price = next(
                    (p['max_unit_price'] for p in aggregated_products_list if p['product_name'] == product_name),
                    None
                )
                item_request = form.save(commit=False, max_unit_price=max_unit_price)
                item_request.full_clean()  # Additional model-level validation
                item_request.save()
                return JsonResponse({
                    'success': True,
                    'total_price': str(item_request.total_price) if item_request.total_price else 'N/A'
                })
            except ValidationError as e:
                return JsonResponse({'success': False, 'errors': e.message_dict}, status=400)
            except Exception as e:
                return JsonResponse({'success': False, 'errors': {'general': [str(e)]}}, status=500)
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    form = ItemRequestForm(user=request.user, warehouse=warehouse)
    context = {
        'warehouse': warehouse,
        'page_obj': page_obj,
        'filters': filters,
        'is_customer': True,
        'form': form,
        'is_client': request.user.groups.filter(name='client').exists(),
    }
    return render(request, 'managment/customer_products.html', context)
@login_required
def owner_requests(request):
    if not request.user.is_authenticated:
        return render(request, "home/page-403.html", {"message": "Access Denied: You must be logged in."}, status=403)
    if  request.user.groups.filter(name='client').exists():
        return render(request, "home/page-403.html", {"message": "Access Denied: This page is not for customers."},
                      status=403)
    # Determine accessible warehouses based on user role
    if request.user.groups.filter(name='owner').exists()  or request.user.is_superuser:  # Top-level owner or superuser
        # Owner sees all warehouses they directly own plus those owned by their users
        accessible_warehouses = Warehouse.objects.filter(
            Q(ownership=request.user) | Q(ownership__owner=request.user)
        )
        is_owner = True
    else:  # Regular user
        # User only sees warehouses they have direct access to
        accessible_warehouses = Warehouse.objects.filter(users=request.user)
        is_owner = False

    # Check if user has access to any warehouses
    if not accessible_warehouses.exists() and not request.user.is_superuser:
        return render(request, "home/page-403.html",
                      {"message": "Access Denied: You do not have access to any warehouses."}, status=403)

    # Fetch all requests for accessible warehouses
    item_requests = ItemRequest.objects.filter(
        warehouse__in=accessible_warehouses
    ).order_by('-request_date')

    # Pagination
    paginator = Paginator(item_requests, 10)  # 10 requests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Handle POST requests for processing
    if request.method == 'POST' and 'action' in request.POST:
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        try:
            # Ensure user has permission for this specific request
            item_request = ItemRequest.objects.get(
                id=request_id,
                warehouse__in=accessible_warehouses
            )

            if action == 'approve' and item_request.status == 'PENDING':
                item_request.status = 'APPROVED'
                item_request.approval_date = timezone.now()
            elif action == 'reject' and item_request.status in ['PENDING', 'APPROVED']:
                item_request.status = 'REJECTED'
            elif action == 'complete' and item_request.status == 'APPROVED':
                # Subtract stock from products with nearest expiration date
                remaining_weight = item_request.weight_requested_kg
                products = Product.objects.filter(
                    warehouse=item_request.warehouse,
                    product_name=item_request.product_name,
                    status="In Stock",
                ).order_by("expiration_date", "entry_date")  # Prioritize expiration_date, then entry_date

                if not products.exists():
                    raise ValidationError(f"No stock available for {item_request.product_name}.")

                total_available = sum(p.weight_quantity_kg or 0 for p in products)
                if remaining_weight > total_available:
                    raise ValidationError(
                        f"Requested {remaining_weight} kg exceeds available {total_available} kg."
                    )

                for product in products:
                    if remaining_weight <= 0:
                        break

                    available_weight = product.weight_quantity_kg or 0
                    weight_to_take = min(remaining_weight, available_weight)
                    if weight_to_take <= 0:
                        continue

                    # Update product stock
                    previous_weight = product.weight_quantity_kg
                    previous_quantity = product.quantity_in_stock or 0
                    product.weight_quantity_kg -= weight_to_take

                    # Adjust quantity_in_stock if applicable (non-Bulk packaging)
                    if product.packaging_condition != "Bulk" and product.quantity_in_stock and product.weight_per_bag_kg:
                        weight_per_unit = product.weight_per_bag_kg
                        quantity_to_take = int(weight_to_take / weight_per_unit)
                        product.quantity_in_stock -= min(quantity_to_take, product.quantity_in_stock)
                    else:
                        quantity_to_take = 0

                    product.weight_quantity = product.weight_quantity_kg * 1000  # Convert kg to g
                    product.quantity_in_stock = max(0, product.quantity_in_stock or 0)
                    product.weight_quantity_kg = max(0, product.weight_quantity_kg)

                    # Update status and exit date if out of stock
                    if product.quantity_in_stock == 0 or product.weight_quantity_kg == 0:
                        product.status = "Out of Stock"
                        product.exit_date = timezone.now().date()

                    # Update total_value based on weight
                    product.total_value = product.unit_price * product.weight_quantity_kg

                    product.save()

                    # Log the stock change
                    # ProductLog.objects.create(
                    #     product=product,
                    #     user=request.user,
                    #     action="REMOVE",
                    #     quantity_change=-quantity_to_take,
                    #     weight_change_kg=-weight_to_take,
                    #     notes=f"Stock removed for ItemRequest {item_request.id} (Completed)"
                    # )

                    remaining_weight -= weight_to_take

                if remaining_weight > 0:
                    raise ValidationError("Insufficient stock to fulfill request.")

                item_request.status = "COMPLETED"
                item_request.completion_date = timezone.now()
                item_request.status = 'COMPLETED'
                item_request.completion_date = timezone.now()
            item_request.save()
            return JsonResponse({'success': True, 'status': item_request.status})
        except ItemRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Request not found or not accessible'}, status=404)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    context = {
        'page_obj': page_obj,
        'is_owner': is_owner,
        'is_user': request.user.groups.filter(name='user').exists(),
        'is_client': request.user.groups.filter(name='client').exists(),
    }
    return render(request, 'managment/owner_requests.html', context)

@login_required
def customer_requests(request):
    if not request.user.groups.filter(name='client').exists():
        return render(request, "home/page-403.html", {"message": "Access Denied: This page is for customers only."}, status=403)

    # Fetch customer's requests
    customer_requests = ItemRequest.objects.filter(client=request.user).order_by('-request_date')
    paginator = Paginator(customer_requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'is_customer': True,
        'is_client': request.user.groups.filter(name='client').exists(),
    }
    return render(request, 'managment/customer_requests.html', context)


def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser, login_url='home')
def manage_product_metadata(request):
    JSON_FILE_PATH = os.path.join(settings.BASE_DIR.parent, 'apps', 'managment', 'products.json')

    # Load current metadata
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            products = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        products = []

    if request.method == 'POST':
        # Handle form submission
        if 'add_product' in request.POST:
            form = ProductMetadataForm(request.POST)
            if form.is_valid():
                new_product = form.cleaned_data
                # Map form field names to JSON keys
                json_product = {
                    'Product': new_product['Product'],
                    'Ethylene Management': new_product['Ethylene_Management'],
                    'Ideal Temperature (C)': new_product['Ideal_Temperature_C'],
                    'Relative Humidity (%)': new_product['Relative_Humidity'],
                    'Maximum Storage Duration (days)': new_product['Maximum_Storage_Duration_days'],
                    'CO2 (%)': new_product['CO2'],
                    'O2 (%)': new_product['O2'],
                    'N2 (%)': new_product['N2'],
                    'Additional Notes': new_product['Additional_Notes'],
                    'Product Type': new_product['Product_Type']
                }
                products.append(json_product)
                try:
                    with open(JSON_FILE_PATH, 'w') as f:
                        json.dump(products, f, indent=2)
                    refresh_product_metadata()  # Refresh cache
                    messages.success(request, "Product added successfully.")
                    return redirect('manage_product_metadata')
                except Exception as e:
                    messages.error(request, f"Error saving product: {str(e)}")
            else:
                messages.error(request, "Invalid form data. Please check the fields.")
        elif 'edit_product' in request.POST:
            index = int(request.POST.get('index'))
            form = ProductMetadataForm(request.POST)
            if form.is_valid():
                json_product = {
                    'Product': form.cleaned_data['Product'],
                    'Ethylene Management': form.cleaned_data['Ethylene_Management'],
                    'Ideal Temperature (C)': form.cleaned_data['Ideal_Temperature_C'],
                    'Relative Humidity (%)': form.cleaned_data['Relative_Humidity'],
                    'Maximum Storage Duration (days)': form.cleaned_data['Maximum_Storage_Duration_days'],
                    'CO2 (%)': form.cleaned_data['CO2'],
                    'O2 (%)': form.cleaned_data['O2'],
                    'N2 (%)': form.cleaned_data['N2'],
                    'Additional Notes': form.cleaned_data['Additional_Notes'],
                    'Product Type': form.cleaned_data['Product_Type']
                }
                products[index] = json_product
                try:
                    with open(JSON_FILE_PATH, 'w') as f:
                        json.dump(products, f, indent=2)
                    refresh_product_metadata()  # Refresh cache
                    messages.success(request, "Product updated successfully.")
                    return redirect('manage_product_metadata')
                except Exception as e:
                    messages.error(request, f"Error saving product: {str(e)}")
            else:
                messages.error(request, "Invalid form data. Please check the fields.")
        elif 'delete_product' in request.POST:
            index = int(request.POST.get('index'))
            try:
                products.pop(index)
                with open(JSON_FILE_PATH, 'w') as f:
                    json.dump(products, f, indent=2)
                refresh_product_metadata()  # Refresh cache
                messages.success(request, "Product deleted successfully.")
                return redirect('manage_product_metadata')
            except Exception as e:
                messages.error(request, f"Error deleting product: {str(e)}")

    # Prepare forms for existing products with proper field mapping
    product_forms = []
    for i, product in enumerate(products):
        initial_data = {
            'Product': product.get('Product'),
            'Ethylene_Management': product.get('Ethylene Management'),
            'Ideal_Temperature_C': product.get('Ideal Temperature (C)'),
            'Relative_Humidity': product.get('Relative Humidity (%)'),
            'Maximum_Storage_Duration_days': product.get('Maximum Storage Duration (days)'),
            'CO2': product.get('CO2 (%)'),
            'O2': product.get('O2 (%)'),
            'N2': product.get('N2 (%)'),
            'Additional_Notes': product.get('Additional Notes'),
            'Product_Type': product.get('Product Type')
        }
        product_forms.append((i, ProductMetadataForm(initial=initial_data)))

    add_form = ProductMetadataForm()

    return render(request, 'managment/manage_product_metadata.html', {
        'product_forms': product_forms,
        'add_form': add_form,
    })