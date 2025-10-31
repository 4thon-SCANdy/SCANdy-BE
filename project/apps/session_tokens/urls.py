from django.urls import path
from . import views

urlpatterns = [
    path('user/register/', views.NonGoogleRegisterView.as_view(), name='register_non_google'),
    path('user/login/', views.NonGoogleLoginView.as_view(), name='login_non_google'),
]

