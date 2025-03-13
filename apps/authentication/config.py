# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    name = 'apps.authentication'  # Full app name including 'apps' module
    label = 'authentication'      # Unique label (can stay as is)

    def ready(self):
        from . import signals     # Imports signals.py from the same directory