from django.db import models

class Users(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False)
    google_sync = models.BooleanField(default=False)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.name