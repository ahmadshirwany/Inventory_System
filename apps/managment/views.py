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
from .forms import WarehouseForm
from django.core.exceptions import PermissionDenied
from apps.authentication.models import CustomUser


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
def warehouse_detail(request, slug):
    # Get the warehouse by slug
    warehouse = get_object_or_404(Warehouse, slug=slug)

    # Get filter parameters from GET request
    sku = request.GET.get('sku', '')
    product_name = request.GET.get('product_name', '')
    product_type = request.GET.get('product_type', '')
    status = request.GET.get('status', '')

    # Filter products for this warehouse
    products = Product.objects.filter(warehouse=warehouse)
    if sku:
        products = products.filter(sku__icontains=sku)
    if product_name:
        products = products.filter(product_name__icontains=product_name)
    if product_type:
        products = products.filter(product_type=product_type)
    if status:
        products = products.filter(status=status)

    # Prepare context
    filters = {
        'sku': sku,
        'product_name': product_name,
        'product_type': product_type,
        'status': status,
    }
    context = {
        'warehouse': warehouse,
        'products': products,
        'filters': filters,
    }
    return render(request, 'managment/products.html', context)

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
    name_query = request.GET.get('name', '').strip()
    location_query = request.GET.get('location', '').strip()
    owner_query = request.GET.get('owner', '').strip()
    users_query = request.GET.get('users', '').strip()
    if request.user.is_superuser:
        queryset = Warehouse.objects.all()
    else:
        queryset = (Warehouse.objects.filter(users=request.user) | Warehouse.objects.filter(ownership=request.user)).distinct()
    query = Q()
    if name_query:
        query &= Q(name__icontains=name_query)
    if location_query:
        query &= Q(location__icontains=location_query)
    if owner_query:
        query &= Q(users__username__icontains=owner_query)
    if query:
        queryset = queryset.filter(query).distinct()
    if not request.user.is_superuser and not queryset.exists():
        return render(
            request,
            "home/page-403.html",
            {"message": "Access Denied: You do not have Acess to any of the warehouses."},
            status=403
        )

    context = {
        'warehouses': queryset,
        'filters': {
            'name': name_query,
            'location': location_query,
            'owner': owner_query,
            'users': users_query,
        }  # Pass the search query back to the template
    }
    return render(request, 'managment/warehouse_list.html', context)