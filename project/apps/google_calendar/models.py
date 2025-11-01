from django.db import models

from apps.users.models import User

class GoogleCalendar(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='google_calendars',
        db_column='user_id'
    )
    # google_calendar의 실제 id 값.
    google_calendar_str_id = models.CharField(max_length=255, null=False)

    # is_activated 사용자가 활성화 했는지 여부.
    is_activated = models.BooleanField(null=False, default=True)
    
    # is_primary 구글 캘린더가 기본 캘린더인지 여부.
    is_primary = models.BooleanField(null=False, default=False)
    
    