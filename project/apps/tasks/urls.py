from django.urls import path, include

# from django.conf import settings
# from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from rest_framework import routers
from .views import *


app_name = "tasks"



urlpatterns = [
  # path('', include(router.urls)),
  path("process/", TaskLLMView.as_view()),
]
router = routers.SimpleRouter(trailing_slash=False)
router.register(r'', TaskViewSet, basename='task')
urlpatterns += router.urls
