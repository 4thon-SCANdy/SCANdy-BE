from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

import traceback

from apps.users.services import JWTAuthentication
from apps.ocr.views import OcrView

from .models import Task
from .seriallizers import TaskSerializer, TaskCreateSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .services import create_schedule, parse_response, recommend_time, refine_ocr

from external.dummy_serializers import DummySerializer
from external.custom_swagger import TOKEN_HEADER
from external.time_manager import ensure_datetime

import time, json

class TaskLLMView(OcrView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TaskCreateSerializer,
        parameters=[TOKEN_HEADER],
    )
    def post(self, request, *args, **kwargs): 

        # 1) 이미지 업로드 ->  ocr 처리 수행
        try:
            ocr_response = super().post(request, *args, **kwargs)

            if not hasattr(ocr_response, "data"):
                return Response(
                    {"error": "OCR 응답이 비정상입니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            
            ocr_results = ocr_response.data.get("results", [])
            task_id = ocr_response.data.get("task_id")
            if not ocr_results:
                return Response(
                    {"error": "OCR 결과가 없습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            print("ocr_results:", ocr_results)

            
            # 2) ocr 결과 전처리
            all_texts = []
            for item in ocr_results:
                if "texts" in item and isinstance(item["texts"], list):
                    all_texts.extend(item["texts"])

            if not all_texts:
                return Response(
                    {"error": "OCR에서 텍스트를 찾을 수 없습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            print("ocr_all texts:", all_texts)

            # 3) refine_ocr로 일정 문장 추출
            refined_ocr = refine_ocr(all_texts)

            if "error" in refined_ocr:
                return Response(refined_ocr, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not refined_ocr:
                return Response({"error": "OCR에서 일정을 추출할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 3) 각 텍스트에 대해 일정 생성
            user = request.user
            print("refined_ocr 결과:", refined_ocr)

            if isinstance(refined_ocr, list):
                refined_ocr = [r for r in refined_ocr if r.strip()]
            else:
                refined_ocr = [refined_ocr]

            results = [] # 여러 문장을 받도록
            for t in refined_ocr:
                # 스케줄 생성 -> OCR 파싱
                created = create_schedule(t)
                if isinstance(created, dict) and "error" in created:
                    print("create_schedule 실패:", created)
                    continue
                print("일정 생성", created)
                parsed = parse_response(created)

                if not parsed:
                    continue    
                results.extend(parsed)

            print("create_schedule 결과:", results)

            # 4) 겹치는 일정 조회 + 추천 시간 반환
            recommends = []
            for r in results:
                start = ensure_datetime(r.get("start_datetime"))
                end = ensure_datetime(r.get("end_datetime"))
                print("🔹 recommend_time 입력:", start, end) 

                if not start or not end:
                    print("recommend_time skip: datetime 누락", r)
                    continue  # None 값이면 생략
                recommend = recommend_time(user, start, end, request)
                if recommend and "recommendation" in recommend:
                    recommends.extend(recommend["recommendation"])
                    
            # response list용으로 변환
            parsed_ocr = refined_ocr
            if isinstance(refined_ocr, list) and len(refined_ocr) == 1 and isinstance(refined_ocr[0], str):
                try:
                    parsed_ocr = json.loads(refined_ocr[0])
                    print("Response용 OCR 파싱 성공:", parsed_ocr)
                except json.JSONDecodeError:
                    print("Response용 OCR 파싱 실패, 원본 유지")

            # 5) task 모델 업데이트
            if task_id:
                try:
                    task = Task.objects.get(id=task_id)
                    task.ocr_result = "\n".join(all_texts)
                    task.llm_result = json.dumps(results, ensure_ascii=False)
                    task.save(update_fields=["ocr_result", "llm_result"])
                except Task.DoesNotExist:
                    print(f"Task {task_id}가 없어 저장에 실패했습니다.")


            return Response(
                {"task_id": task_id, "ocr_result": parsed_ocr, "llm_result": results, "recommendation": recommends},
                status=status.HTTP_200_OK,
            )
        
        except Exception as e:
            print("🔥 TaskLLM Internal Error:", e)
            traceback.print_exc()
            return Response(
                {"detail": str(e), "traceback": traceback.format_exc().splitlines()},
                status=500
            )

# /task/task_id → image 링크 , llm, ocr 분석결과
class TaskViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    serializer_class = TaskSerializer
    queryset = Task.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # list는 여러 개 보여주는 부분
        return Response(
            {"detail": "Task 조회에 성공했습니다."},
            status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()  # Task instance 하나 가져오기

        serializer = self.get_serializer(task)

        ocr_result = getattr(task, "ocr_result", None)
        llm_result = json.loads(getattr(task, "llm_result", None))

        # 개행 제거
        if isinstance(ocr_result, str):
            ocr_result = ocr_result.replace("\n", " ")
        if isinstance(llm_result, str):
            llm_result = llm_result.replace("\n", " ")

        data = [{
            "ocr_result": ocr_result,
            "llm_result": llm_result
        }]

        
        image_urls = []
        for image_obj in task.images.all():
            if image_obj.image:
                abs_url = request.build_absolute_uri(image_obj.image.url)
                image_urls.append(abs_url)

        data.append({"image_urls":image_urls})

        return Response({
            "detail": f"Task {task.id} 조회를 성공했습니다",
            "data": data
        }, status=status.HTTP_200_OK)
