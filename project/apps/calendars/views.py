
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from datetime import datetime, timedelta
import unicodedata


from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action

from apps.users.services import JWTAuthentication

# 직접 작성한 class import하기.
from external.time_manager import TimeRange, KST, ensure_datetime, to_naive_kst
from external.google_manager import get_creds_from_google_token

from apps.google_calendar.services import get_schedules_of_user, post_or_update_schedule_of_user, merge_scheds, delete_from_schedule

from .models import Schedule, Tag

from .serializers import (ScheduleSerializer, ScheduleCreateSerializer, ScheduleUpdateSerializer,
                          TagSerializer, TagCreateSerializer, TagUpdateSerializer)
from .services import expand_repeating_schedule

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
    
    @extend_schema(
        summary="일정 목록 조회 (날짜/태그 필터링)",
        parameters=[
            OpenApiParameter(name="start_datetime", description="조회 시작 날짜 (예: 2025-11-01T00:00:00)", required=False),
            OpenApiParameter(name="end_datetime", description="조회 종료 날짜 (예: 2025-11-30T23:59:59)", required=False),
            OpenApiParameter(name="tag", description="태그 ID (예: 3)", required=False),
        ],
        responses={200: ScheduleSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        start_datetime = request.query_params.get('start_datetime', None)
        end_datetime = request.query_params.get('end_datetime', None)
        tag = request.query_params.get('tag', None)

        # 먼저 db query로 모두 필터링이 가능한 tag부터 필터링 한다.
        # 태그 필터링.
        if tag:
            queryset = queryset.filter(tag__id=tag)

        # 만약 날짜 필터링이 없다면 그대로 return한다.
        if not start_datetime or not end_datetime:
            serializer = ScheduleSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # datetime 들을 timezone-naive로 만들기.
        start_datetime = to_naive_kst(ensure_datetime(start_datetime)).isoformat()
        end_datetime = to_naive_kst(ensure_datetime(end_datetime)).isoformat()
        
        # db 1차 날짜 필터링. db에서 범위 1차 필터링(성능을 위해.)
        # until이 없는 경우에는 그냥 집어넣음.
        queryset = queryset.filter(
            start_datetime__lte=end_datetime
        ).filter(Q(until__gte=start_datetime) | Q(until__isnull=True))

        # datetime으로 파싱.
        start_datetime = ensure_datetime(start_datetime)
        end_datetime = ensure_datetime(end_datetime)
           
        serializer = ScheduleSerializer(queryset, many=True)
        
        # 일단 db에 있는 schedule들만 저장.
        db_sched_list: list = serializer.data
        
        # 여기서 구글의 스케줄 리스트를 sched_list에 추가해야 함.
        # user를 받아서 google_sync라면, google calendar에서 가져온다.
        user = self.request.user
        if user.is_google_sync:
            creds = get_creds_from_google_token(self.request)
            print("GOOGLE SYNC:", user.email, user.is_google_sync)
            print("CREDS:", creds)
            google_sched_list = get_schedules_of_user(user, creds, start_datetime, end_datetime)
            # 중복되는 것들은 없애야 한다.
            print("GOOGLE SCHEDULES:", len(google_sched_list))
            db_sched_list = merge_scheds(db_sched_list, google_sched_list)

        # 2차 필터링. expanded 된 것들도 전부 필터링한다.
        filter_range = TimeRange(
            start=start_datetime,
            end=end_datetime,
        )
        # 스케쥴 분리와 동시에 필터링도 수행한다.
        expanded_scheds: list = expand_repeating_schedule(db_sched_list, filter_range)
        
        return Response({"detail": "일정 조회에 성공했습니다.", "data": expanded_scheds}, status=status.HTTP_200_OK)

    #########################################################################################################################################
    # 일정 생성     
    def create(self, request, *args, **kwargs):
        serializer = ScheduleCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            schedule = serializer.save()
            # Serializer에 구글 연동 관련 데이터를 추가해야 함.
            if request.user.is_google_sync:
                creds = get_creds_from_google_token(request)
                post_or_update_schedule_of_user(request.user, creds, schedule)

            return Response({"detail": "일정 등록을 성공했습니다.", "data": ScheduleSerializer(schedule).data}, 
                            status=status.HTTP_201_CREATED)
        return Response({"detail": "일정 등록을 실패했습니다.", "error":serializer.errors}, 
                        status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, *args, **kwargs):
        schedule = self.get_object()
        
        # partial. update를 지원하기 위해 field들을 다 보내지 않아도 valid 통과.
        serializer = ScheduleUpdateSerializer(
            instance=schedule,
            data=request.data,
            partial=True)
        
        if serializer.is_valid():
            schedule = serializer.save()
            if request.user.is_google_sync:
                creds = get_creds_from_google_token(request)
                post_or_update_schedule_of_user(request.user, creds, schedule)
            return Response({"detail": "일정 수정을 성공했습니다.", "data": ScheduleSerializer(schedule).data}, 
                            status=status.HTTP_200_OK)
        return Response({"detail": "일정 수정을 실패했습니다.", "error":serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        try:
            schedule = self.get_object()
            if request.user.is_google_sync:
                # 삭제할때 google calendar의 데이터도 삭제해야 함.
                creds = get_creds_from_google_token(request)
                delete_from_schedule(creds, schedule)
            
            # super().destroy(request, *args, **kwargs)
            schedule.delete()
            return Response(
                {"detail": f"'{schedule.title}' 일정이 삭제되었습니다."},
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {"error": f"삭제 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @extend_schema(
        summary="일정 검색",
        parameters=[OpenApiParameter(name="keyword", description="검색어", required=True)]
    )   
    @action(detail=False, methods=["GET"])
    # title, content, tag 값을 구글, DB에서 검색하여 필터링
    def search(self, request):
        user = request.user
        start = request.query_params.get("start", "").strip()
        end = request.query_params.get("end", "").strip()
        keyword = request.query_params.get("q", "").strip()
        
        if not keyword and start and end:
            return Response(
                {"error": "검색어, start, end가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset()

        now = datetime.now()
        # start, end가 없을 경우: 이번 달 1일 ~ 마지막 날 / 일정 검색 에러 방지
        if start and end:
            start_dt, end_dt = map(datetime.fromisoformat, [start, end])
        else:
            y, m = now.year, now.month
            start_dt = datetime(y, m, 1)
            if m == 12:
                end_dt = datetime(y + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_dt = datetime(y, m + 1, 1) - timedelta(seconds=1)
            print("start", start_dt)
            print("end", end_dt)
        
        # db 검색
        db_results = queryset.filter(
            (Q(title__icontains=keyword)
            | Q(content__icontains=keyword)
            | Q(tag__name__icontains=keyword)
            )
            & Q(start_datetime__lte=end_dt)
            & Q(end_datetime__gte=start_dt)
        ).distinct()

        db_serialized = ScheduleSerializer(db_results, many=True).data

        # 구글 연동시, 구글 검색
        google_results = []
        if user.is_google_sync:
            creds = get_creds_from_google_token(request)
            google_schedules = get_schedules_of_user(user, creds, start_dt, end_dt)
            print("가져온 구글 일정", google_schedules)

            # DB에 이미 존재하는 google_event_id 수집
            existing_event_ids = {
                sched.get("google_event_id")
                for sched in db_serialized
                if sched.get("google_event_id")
            }

            # 구글 일정 필터링 (중복 제거)
            google_results = [
                event for event in google_schedules
                if (
                    keyword.lower() in event.get("title", "").lower()
                    or keyword.lower() in event.get("content", "").lower()
                )
                and event.get("google_event_id") not in existing_event_ids
            ]

        # 병합 및 중복 제거
        merged_results = merge_scheds(db_serialized, google_results)
        
        return Response(
            {
                "detail": f"'{keyword}' 검색 결과입니다.",
                "count": len(merged_results),
                "data": merged_results
            },
            status=status.HTTP_200_OK
        )
    
    ###################################
    @extend_schema(summary="구글 일정 수정")   
    @action(detail=False, methods=["PATCH"],url_path="google_update")
    def update_google_event(self, request):
        # DB에 없는 구글 이벤트 수정
        try:
            if not request.user.is_google_sync:
                return Response({"error": "구글 연동이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

            creds = get_creds_from_google_token(request)
            updated_data = request.data
            google_event_id = (
                request.headers.get("Google-Event-ID") or
                request.data.get("google_event_id")
            )

            # 구글 API 업데이트 함수 호출
            result = post_or_update_schedule_of_user(
                request.user,
                creds,
                updated_data,
                google_event_id=google_event_id,  # 기존 일정 ID 지정
            )

            return Response({
                "detail": "구글 일정이 수정되었습니다.",
                "data": result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"구글 일정 수정 중 오류가 발생했습니다. {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)
        
    @extend_schema(summary="구글 일정 삭제")   
    @action(detail=False, methods=["DELETE"], url_path="google_delete")
    def delete_google_event(self, request):
        # DB에 없는 구글 이벤트 삭제
        try:
            if not request.user.is_google_sync:
                return Response({"error": "구글 연동이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)
            
            google_event_id = (
                request.headers.get("Google-Event-ID") or
                request.data.get("google_event_id")
            )

            creds = get_creds_from_google_token(request)
            delete_from_schedule(creds, google_event_id=google_event_id, user=request.user)

            return Response({"detail": f"구글 일정({google_event_id})이 삭제되었습니다."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"구글 일정 삭제 중 오류가 발생했습니다. {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)


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
    
    

