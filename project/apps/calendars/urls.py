from django.urls import path

from rest_framework import routers


from .views import ScheduleViewSet, TagViewSet

urlpatterns = [
    
]

router = routers.SimpleRouter(trailing_slash=False)
router.register(r'events', ScheduleViewSet, basename='events')
router.register(r'tag', TagViewSet, basename='tag')
urlpatterns += router.urls
