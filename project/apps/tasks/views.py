from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.users.services import JWTAuthentication
from apps.ocr.views import OcrView
from apps.tasks.models import Task
from external.dummy_serializers import DummySerializer

from .services import create_schedule, parse_response, recommend_time, refine_ocr

import time, json

class TaskLLMView(OcrView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DummySerializer

    def post(self, request, *args, **kwargs): 

        # 1) 이미지 업로드 ->  ocr 처리 수행
        ocr_response = super().post(request, *args, **kwargs)
        
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
            start = r.get("start_datetime")
            end = r.get("end_datetime")

            if not start or not end:
                print("recommend_time skip: datetime 누락", r)
                continue  # None 값이면 생략
            recommend = recommend_time(user, start, end, request)
            recommends.append(recommend)

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
