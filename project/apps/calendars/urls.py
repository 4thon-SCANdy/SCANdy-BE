from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

app_name = "calendars"

router = DefaultRouter(trailing_slash=False)
router.register('', CalendarViewSet, basename='calendar')
router.register('event', ScheduleViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
]