from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Calendar, Schedule
from .serializers import CalendarSerializer, ScheduleSerializer

@extend_schema(tags=["📅캘린더"], summary="캘린더 생성, 조회")
class CalendarViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Calendar.objects.all().order_by("-id")
    serializer_class = CalendarSerializer

    def list(self, request, *args, **kwargs):
        calendars = self.queryset.filter(user=request.user)
        serializer = self.get_serializer(calendars, many=True)
        return Response({
            "message": "캘린더 목록 조회에 성공했습니다.",
            "total_count": calendars.count(),
            "result": serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response({
            "message": "캘린더가 생성되었습니다.",
            "result": serializer.data
        }, status=status.HTTP_201_CREATED)

@extend_schema(tags=["🗓️일정"], summary="일정 등록/수정/조회/삭제",)
class ScheduleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Schedule.objects.all().order_by("-start_datetime")
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        return self.queryset.filter(calendar__user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        calendar_id = request.data.get('calendar')

        # calendar 유효성 검증
        try:
            calendar = Calendar.objects.get(id=calendar_id, user=user)
        except Calendar.DoesNotExist:
            return Response(
                {"error": "해당 캘린더를 찾을 수 없거나 권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(calendar=calendar)
        return Response({
            "message": "일정이 성공적으로 등록되었습니다.",
            "result": serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response({
            "message": "일정이 수정되었습니다.",
            "result": ScheduleSerializer(updated).data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            "message": "일정이 삭제되었습니다.",
            "schedule_id": kwargs.get('pk')
        }, status=status.HTTP_200_OK)
