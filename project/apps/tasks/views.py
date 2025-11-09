from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.users.services import JWTAuthentication
from apps.ocr.views import OcrView

from .services import create_schedule, parse_response, recommend_time, refine_ocr
class TaskLLMView(OcrView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        # 1) 이미지 업로드 ->  ocr 처리 수행
        ocr_response = super().post(request, *args, **kwargs)

        ocr_results = ocr_response.data.get("results", [])
        if not ocr_results:
            return Response(
                {"error": "OCR 결과가 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
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

        # 3) refine_ocr로 일정 문장 추출
        refined_ocr = refine_ocr(all_texts)
        if "error" in refined_ocr:
            return Response(refined_ocr, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not refined_ocr:
            return Response({"error": "OCR에서 일정을 추출할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)


        # 3) 각 텍스트에 대해 일정 생성

        user = request.user
        print("요청 유저:", user)
        print("input text:", refined_ocr)

        results = [] # 여러 문장을 받도록
        for t in refined_ocr:
            # 스케줄 생성 -> OCR 파싱
            created = create_schedule(t)
            parsed = parse_response(created)
            results.append(parsed)

        print("create_schedule 결과:", results)

        # 4) 겹치는 일정 조회 + 추천 시간 반환
        recommends = []
        for r in results:
            recommend = recommend_time(user, r["start_datetime"], r["end_datetime"], request)
            recommends.append(recommend)

        return Response(
            {"ocr_result": refined_ocr, "llm_result": results, "recommendation": recommends},
            status=status.HTTP_200_OK,
        )
