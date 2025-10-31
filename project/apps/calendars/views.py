from rest_framework.response import Response
from rest_framework import viewsets, permissions, status

from apps.users.services import JWTAuthentication

from .models import Schedule, Tag
from .serializers import (ScheduleSerializer, ScheduleCreateSerializer,
                          ScheduleUpdateSerializer,TagSerializer)

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

    def create(self, request, *args, **kwargs):
        serializer = ScheduleCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            schedule = serializer.save()
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
        
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    
