from django.urls import path
from .views import ScheduleLLMView

urlpatterns = [
    path("test/", ScheduleLLMView.as_view()),
]
