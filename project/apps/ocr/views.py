# django
from .serializers import OcrImageSerializer
from external.dummy_serializers import DummySerializer

# rest_framework
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status


class OcrView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DummySerializer


    def post(self, request):
        # 1) 파일 수집 (images 키 기준)
        files = request.FILES.getlist("images")
        # 혹시 클라이언트가 images[] 형태로 보낼 수도 있어 보조 안전장치
        if not files and "images[]" in request.FILES:
            files = request.FILES.getlist("images[]")

        if not files:
            return Response(
                {"detail": "images 파일을 최소 1개 업로드하세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) 직렬화/검증
        serializer = OcrImageSerializer(data={"images": files}, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # 3) 처리 (serializer.create 내부에서 CLOVA 병렬 호출)
        result = serializer.save()

        # result 구조: {"results": [ {file, texts|error, ...}, ... ]}
        return Response(result, status=status.HTTP_200_OK)
