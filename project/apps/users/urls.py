from django.urls import path
from . import views

urlpatterns = [
    path('google/url/', views.google_auth_url, name='google_auth_url'),
]

