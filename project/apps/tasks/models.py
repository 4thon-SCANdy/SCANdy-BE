from django.db import models
from apps.calendars.models import Schedule

def image_upload_path(instance: 'Image', filename: str) -> str:
    return f"tasks/{instance.pk}/{filename}"

class Task(models.Model):
		id = models.AutoField(primary_key=True)
		ocr_result= models.TextField(null=True, blank=True)
		llm_result= models.TextField(null=True, blank=True)
		
class Image(models.Model):
		id = models.AutoField(primary_key=True)
		schedule = models.ForeignKey(
					Schedule, 
					on_delete=models.CASCADE,
					related_name='schedules',
					db_column='calendar_id'
		)
		image_url = models.URLField(max_length=500, null=False)
		task_image = models.ImageField(upload_to=image_upload_path, blank=True, null=True)
    