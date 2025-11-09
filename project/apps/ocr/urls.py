from django.urls import path
from .views import OcrView

app_name = "ocr"

urlpatterns = [
    path('', OcrView.as_view(), name='ocr'),
]

# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)