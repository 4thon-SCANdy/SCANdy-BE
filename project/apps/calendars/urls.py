from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import ScheduleViewSet, TagViewSet

urlpatterns = [
    
]

router = DefaultRouter()
router.register(r'schedule', ScheduleViewSet, basename='schedule')
router.register(r'tag', TagViewSet, basename='tag')
urlpatterns += router.urls
