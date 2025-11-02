import datetime

from django.utils.dateparse import parse_datetime

from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action


from apps.users.services import JWTAuthentication

# 직접 작성한 class import하기.
from external.time_manager import TimeRange

from .models import Schedule, Tag
from .serializers import (ScheduleSerializer, ScheduleCreateSerializer, ScheduleUpdateSerializer,
                          TagSerializer, TagCreateSerializer, TagUpdateSerializer)
from .services import expand_repeating_schedule
from .google_calendar import create_google_event

class ScheduleViewSet(viewsets.ModelViewSet):
    # user authentication class.
    authentication_classes = [JWTAuthentication]
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Schedule.objects.filter(
            # authentication을 마치게 되면 request.user에 user object가 들어있다. (정확히는 user_id)
            calendar=self.request.user.calendar
        )
    # list의 경우 파라미터에 start_datetime, end_datetime이 있다면 그걸로 필터링 해야 한다.
    # 또한 태그 필터링도 지원하여야 한다. tag로 파라미터를 받는다.
    # 없는 경우 그냥 get_queryset을 받는다. (user의 모든 일정)
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        start_datetime = request.query_params.get('start_datetime', None)
        end_datetime = request.query_params.get('end_datetime', None)
        tag = request.query_params.get('tag', None)
        
        # 먼저 db query로 모두 필터링이 가능한 tag부터 필터링 한다.
        # 태그 필터링.
        if tag:
            queryset = queryset.filter(tag__id=tag)
        
        # db 1차 날짜 필터링. db에서 범위 1차 필터링(성능을 위해.)
        if start_datetime and end_datetime:
            queryset = queryset.filter(
                start_datetime__lte=end_datetime,
                until__gte=start_datetime
            )
           
        serializer = ScheduleSerializer(queryset, many=True)
        
        # 일단 db에 있는 schedule들만 저장.
        db_sched_list: list = serializer.data
        
        # 여기서 구글의 스케줄 리스트를 sched_list에 추가해야 함.
        
        # 스케쥴을 repeat에 따라 분리한다.
        expanded_scheds: list = expand_repeating_schedule(db_sched_list)
        
        # 2차 필터링. expanded 된 것들도 전부 필터링한다.
        if start_datetime and end_datetime:
             # range를 설정: 프론트에서 입력한 start_datetime, end_datetime.
            filter_range = TimeRange(
                start=parse_datetime(start_datetime),
                end=parse_datetime(end_datetime)
            )
            expanded_scheds = [
                sched for sched in expanded_scheds if filter_range.overlaps(TimeRange(parse_datetime(sched['start_datetime']), parse_datetime(sched['end_datetime'])))]
        
        
        return Response(expanded_scheds, status=status.HTTP_200_OK)
        
    def create(self, request, *args, **kwargs):
        serializer = ScheduleCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            schedule = serializer.save()
            # Serializer에 구글 연동 관련 데이터를 추가해야 함.

            user = request.user
            access_token = request.session.get("google_access_token", None)

            # 유저가 구글 연동 중이고, 엑세스 토큰이 있다면
            if getattr(user, "is_google_sync", True) and access_token:
                try:
                    event = create_google_event(
                        access_token=access_token,
                        calendar_id="primary",
                        schedule=schedule
                    )
        
                    # 구글 이벤트 id 저장
                    schedule.google_event_id = event.get("id")
                    schedule.save()
                except Exception as e:
                    print(f"구글 일정 등록 실패: {e}")

            return Response(ScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        

    
    def update(self, request, *args, **kwargs):
        schedule = self.get_object()
        
        # partial. update를 지원하기 위해 field들을 다 보내지 않아도 valid 통과.
        serializer = ScheduleUpdateSerializer(
            instance=schedule,
            data=request.data,
            partial=True)
        
        if serializer.is_valid():
            schedule = serializer.save()
            return Response(ScheduleSerializer(schedule).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=["GET"])
    # 태그명을 받아, 태그명에 해당하는 일정만 보여주기
    def filter(self, request):
        tag_name = request.query_params.get("tag")
        
        if not tag_name:
            return Response(
                {"error": "tag가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Tag 모델의 name 기준으로 필터링
        tag_schedules = Schedule.objects.filter(tags__name=tag_name)

        serializer = self.get_serializer(tag_schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
class TagViewSet(viewsets.ModelViewSet):
    # user authentication class.
    authentication_classes = [JWTAuthentication]
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    serializer_class = TagSerializer
    
    def get_queryset(self):
        return Tag.objects.filter(
            calendar=self.request.user.calendar
        )
    
    def create(self, request, *args, **kwargs):
        serializer = TagCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            tag = serializer.save()
            return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        tag = self.get_object()
        
        # partial. update를 지원하기 위해 field들을 다 보내지 않아도 valid 통과.
        serializer = TagUpdateSerializer(
            instance=tag,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            tag = serializer.save()
            return Response(TagSerializer(tag).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    

