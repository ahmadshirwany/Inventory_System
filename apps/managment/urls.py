# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.managment import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    path('user-profile/', views.update_password, name='update_password'),
    path('warehouses-list/', views.warehouse_list, name='warehouse_list'),
    path('create-warehouse/', views.create_warehouse, name='create_warehouse'),
    path('warehouses-list/<slug:slug>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouses-list/edit/<slug:slug>/', views.edit_warehouse, name='edit_warehouse'),
    # re_path(r'^.*$', views.pages, name='pages'),


]
