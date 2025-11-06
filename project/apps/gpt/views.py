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
    
