# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.managment import views
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    # path('user-profile/', views.update_password, name='update_password'),
    path('warehouses-list/', views.warehouse_list, name='warehouse_list'),
    path('create-warehouse/', views.create_warehouse, name='warehouse_create'),
    path('warehouses-list/<slug:slug>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouses-list/<slug:slug>/product', views.warehouse_detail, name='product_detail'),
    path('warehouses-list/<slug:slug>/product/edit', views.warehouse_detail, name='edit_product'),
    path('warehouses-list/edit/<slug:slug>/', views.edit_warehouse, name='edit_warehouse'),
    # re_path(r'^.*$', views.pages, name='pages'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
