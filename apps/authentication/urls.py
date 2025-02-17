# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path
from .views import login_view, register_user,create_user,user_list,edit_user,update_password
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('login/', login_view, name="login"),
    path('register/', register_user, name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("create-user/", create_user, name="create_user"),
    path("user-list/", user_list, name="user-list"),
    path("edit-user/<int:user_id>/", edit_user, name="edit_user"),
    path('user-profile/', update_password, name='update_password'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
