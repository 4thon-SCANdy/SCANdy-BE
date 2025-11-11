from django.contrib import admin

from .models import Calendar, Tag, Schedule

# Register your models here.
admin.site.register(Calendar)
admin.site.register(Tag)
admin.site.register(Schedule)
