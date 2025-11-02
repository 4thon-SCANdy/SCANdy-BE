from django.db import models

from apps.users.models import User

class SessionToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='session')
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

