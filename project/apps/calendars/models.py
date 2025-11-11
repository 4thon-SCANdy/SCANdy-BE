from django.db import models

from apps.users.models import User
from apps.google_calendar.models import GoogleCalendar
from apps.tasks.models import Task

from external.time_manager import KST

class Calendar(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='calendar',
        db_column='user_id'
    )

class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    calendar = models.ForeignKey(
        Calendar, 
        on_delete=models.CASCADE,
        related_name='tags',
        db_column='calendar_id'
    )
    name = models.CharField(max_length=50, null=False)
    color = models.IntegerField(null=False, default=0)

    def __str__(self):
        return self.name

class Schedule(models.Model):

    REPEAT_CHOICES = [
        ('NONE', '반복 없음'),
        ('DAILY', '매일'),
        ('WEEKLY', '매주'),
        ('MONTHLY', '매월'),
        ('YEARLY', '매년'),
    ]

    id = models.AutoField(primary_key=True)
    calendar = models.ForeignKey(
        Calendar,
        on_delete=models.CASCADE,
        related_name='schedules',
        db_column='calendar_id'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='schedules',
        db_column='tag_id'
    )
    google_calendar = models.ForeignKey(
        GoogleCalendar,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='google_calendars',
        db_column='google_calendar_id',
        default=None,
    )
    task = models.ForeignKey(
		Task,
		on_delete=models.CASCADE,
		related_name='schedules',
        db_column='task_id',
        null=True,
        blank=True,
	)
    google_event_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=200, null=False)
    content = models.TextField(null=True, blank=True)
    start_datetime = models.DateTimeField(null=True)
    end_datetime = models.DateTimeField(null=True)

    until = models.DateTimeField(null=True)

    all_day = models.BooleanField(null=False, default=False)
    repeat = models.CharField(max_length=10, choices=REPEAT_CHOICES, null=False, blank=False, default="NONE")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    locate = models.TextField(null=True, blank=True)

    # 만약 all day라면 시간 데이터를 전부 없앤다.
    def save(self, *args, **kwargs):
        if self.all_day:
            if self.start_datetime:
                self.start_datetime = self.start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            if self.end_datetime:
                self.end_datetime = self.end_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        super().save(*args, **kwargs)
