from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import create_schedule, parse_response
class ScheduleLLMView(APIView):

    def post(self, request):
        text = request.data.get("text") #ocr return 값이 들어갈 예정
        if not text:
            return Response({"error": "text 필드가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        data = create_schedule(input_text=text)
        print("create_schedule 결과:", data)

        result = parse_response(data)
        return Response(result, status=status.HTTP_200_OK)
