from django.urls import path
from . import views

urlpatterns = [
    path('google/url/', views.google_auth_url, name='google_auth_url'),
    path('google/oauth_callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path('user/get_user_from_token/', views.UserFromTokenView.as_view(), name='user_from_token'),
]

