from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import GoogleCalendarViewSet

urlpatterns = [
    
]

router = DefaultRouter()
router.register(r'', GoogleCalendarViewSet, basename='google_calendar')
urlpatterns += router.urls
