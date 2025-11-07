# from rest_framework import viewsets
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.decorators import action
# from django.db import transaction

# from .models import Task, Image
# from apps.calendars.models import Schedule
# from .seriallizers import TaskCreateSerializer, TaskSerializer
# from .services import process_task_from_image


# # 첨부된 이미지로 일정 해석
# class TaskViewSet(viewsets.ViewSet):
#     # 이미지 -> ocr, llm 일정 해석
#     @action(detail=False, methods=["post"])
#     def image_upload(self, request):
#         serializer = TaskCreateSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         images = serializer.validated_data.get("images")

#         with transaction.atomic():
#             task = process_task_from_image(images)

#         return Response({
#             "task_id": task.id,
#             "ocr_result": task.ocr_result,
#             "llm_result": task.llm_result
#         }, status=status.HTTP_201_CREATED)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.users.services import JWTAuthentication
from .services import create_schedule, parse_response, recommend_time
class ScheduleLLMView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get("text") #ocr return 값이 들어갈 예정
        if not text:
            return Response({"error": "text 필드가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        print("요청 유저:", user)

        data = create_schedule(input_text=text)
        print("create_schedule 결과:", data)

        result = parse_response(data)

        recommend = recommend_time(user, result["start_datetime"], result["end_datetime"])

        return Response(
            {"llm_result": result, "recommendation": recommend},
            status=status.HTTP_200_OK,
        )
    
