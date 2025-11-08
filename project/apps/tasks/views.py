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
        texts = request.data.get("text") #ocr return 값이 들어갈 예정
        if not texts:
            return Response({"error": "text 필드가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        print("요청 유저:", user)
        print("input text:", texts)

        results = [] # 여러 문장을 받도록
        for t in texts:
            # 스케줄 생성 -> OCR 파싱
            created = create_schedule(t)
            parsed = parse_response(created)
            results.append(parsed)

        print("create_schedule 결과:", results)

        # 겹치는 일정 조회
        recommends = []
        for r in results:
            recommend = recommend_time(user, r["start_datetime"], r["end_datetime"])
            recommends.append(recommend)

        return Response(
            {"llm_result": results, "recommendation": recommends},
            status=status.HTTP_200_OK,
        )
    
