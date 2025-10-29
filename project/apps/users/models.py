from django.db import models

class User(models.Model):
    id = models.AutoField(primary_key=True)

    email = models.EmailField(unique=True)
    # 구글 아이디 인식 번호.
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_google_sync = models.BooleanField(default=False)
    google_sub = models.CharField(max_length=255, null=True, blank=True)
    google_refresh_token = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.email
    
