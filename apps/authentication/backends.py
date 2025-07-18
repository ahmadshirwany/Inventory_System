from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db import models

class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(
                models.Q(username__iexact=username) | models.Q(email__iexact=username)
            )
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            user = UserModel.objects.filter(email__iexact=username).first()
            if user and user.check_password(password):
                return user
        return None