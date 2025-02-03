# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.managment import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    # re_path(r'^.*\.*', views.pages, name='pages'),
    path('user-profile/', views.update_password, name='update_password'),
    # Matches any html file
    # re_path(r'^.*\.*', views.pa ges, name='pages'),

]
