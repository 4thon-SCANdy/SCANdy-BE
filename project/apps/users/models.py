from django.db import models

class User(models.Model):
    id = models.AutoField(primary_key=True)

    email = models.EmailField(unique=True)
    # 구글 아이디 인식 번호.
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_google_sync = models.BooleanField(default=False)
    google_sub = models.CharField(max_length=255, null=True, blank=True)
    google_refresh_token = models.CharField(max_length=255, null=True, blank=True)
    
    # 보안용 함수.
    @property
    def is_authenticated(self):
        return True
    
    # id_info에서 정보를 뽑아 user 저장혹은 그냥 리턴.
    @classmethod
    def get_or_create_google_user(cls, id_info, refresh_token=None):
        google_sub = id_info.get("sub")
        email = id_info.get("email")
        user, created = cls.objects.get_or_create(
            google_sub=google_sub,
            defaults={
                "email": email,
                "is_google_sync": True,
                "google_refresh_token": refresh_token
            }
        )
        if not created and refresh_token:
            user.google_refresh_token = refresh_token
            user.save()
        return user
    
    # save를 오버라이딩 해서 calendar 만들지 결정.
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        # 만약 user가 새로 생성되는 거라면 calendar도 생성.
        if is_new:
            from apps.calendars.models import Calendar
            Calendar.objects.create(user=self)


    def __str__(self):
        return self.email
    
