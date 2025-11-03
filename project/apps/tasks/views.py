from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.db import transaction

from .models import Task, Image
from apps.calendars.models import Schedule
from .seriallizers import TaskCreateSerializer, TaskSerializer
from .services import process_task_from_image


# 첨부된 이미지로 일정 해석
class TaskViewSet(viewsets.ViewSet):
    # 이미지 -> ocr, llm 일정 해석
    @action(detail=False, methods=["post"])
    def image_upload(self, request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        images = serializer.validated_data.get("images")

        with transaction.atomic():
            task = process_task_from_image(images)

        return Response({
            "task_id": task.id,
            "ocr_result": task.ocr_result,
            "llm_result": task.llm_result
        }, status=status.HTTP_201_CREATED)
