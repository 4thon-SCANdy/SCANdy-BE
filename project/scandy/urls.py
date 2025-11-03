"""
URL configuration for scandy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularJSONAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.users.urls')),
    path('calendar/', include('apps.calendars.urls')),
    path('session/', include('apps.session_tokens.urls')),
    path('google_calendar/', include('apps.google_calendar.urls')),
    path('task/', include('apps.tasks.urls')),
    
    path('api/schema/', SpectacularJSONAPIView.as_view(), name='schema-json'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema-json'), name='redoc'),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema-json"), name="swagger-ui"),
]
