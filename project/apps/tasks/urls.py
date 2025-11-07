from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from .views import *


app_name = "tasks"

# router = DefaultRouter(trailing_slash=False)
# router.register('', TaskViewSet, basename='task')

urlpatterns = [
  # path('', include(router.urls)),
  path("process/", ScheduleLLMView.as_view()),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

