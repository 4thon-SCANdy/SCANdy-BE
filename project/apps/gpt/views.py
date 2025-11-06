from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .services import create_schedule, parse_response

from apps.users.services import JWTAuthentication


class ScheduleLLMView(APIView):
    
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        text = request.data.get("text")
        if not text:
            return Response({"error": "text 필드가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        data = create_schedule(input_text=text)
        print("✅ [DEBUG] create_schedule 결과:", data)

        result = parse_response(data)
        return Response(result, status=status.HTTP_200_OK)
