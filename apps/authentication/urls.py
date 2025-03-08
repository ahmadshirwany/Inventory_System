# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path
from .views import login_view, register_user,create_user,user_list,edit_user,user_profile,update_profile_picture
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static
from .views import CustomLogoutView
urlpatterns = [
    path('login/', login_view, name="login"),
    path('register/', register_user, name="register"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("create-user/", create_user, name="create_user"),
    path("user-list/", user_list, name="user_list"),
    path("edit-user/<int:user_id>/", edit_user, name="edit_user"),
    path('user-profile/', user_profile, name='user_profile'),
    path('update-profile-picture/', update_profile_picture, name='update_profile_picture'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
