from rest_framework import viewsets, permissions

from drf_spectacular.utils import extend_schema_view, extend_schema

from apps.users.services import JWTAuthentication

from external.custom_swagger import TOKEN_HEADER

from .models import GoogleCalendar
from .serializers import GoogleCalendarSerializer, GoogleCalendarUpdateSerializer

# 유저가 마음대로 google_calendar를 삭제할 수는 없게 해야 한다.

# 그래서 get, update만 허용한 viewset을 제작.
@extend_schema_view(
    list=extend_schema(
        parameters=[
            TOKEN_HEADER,
        ],
    ),
    retrieve=extend_schema(
        parameters=[
            TOKEN_HEADER,
        ],
    ),
    partial_update=extend_schema(
        parameters=[
            TOKEN_HEADER,
        ],
    )
)
class GoogleCalendarViewSet(viewsets.ModelViewSet):
    # user authentication class.
    authentication_classes = [JWTAuthentication]
    serializer_class = GoogleCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]

    # get, patch만 허용함.
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        # 구글 인증을 하고, 구글 캘린더를 update 해야 함.
        # 이것도 수정 필요.
        user = self.request.user
        return GoogleCalendar.objects.filter(
            user=user
        )

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return GoogleCalendarUpdateSerializer
        return super().get_serializer_class()
