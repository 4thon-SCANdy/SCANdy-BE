from django.contrib import admin

from .models import Task, Image

# Register your models here.
admin.site.register(Task)
admin.site.register(Image)
