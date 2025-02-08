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
    # re_path(r'^.*$', views.pages, name='pages'),


]
