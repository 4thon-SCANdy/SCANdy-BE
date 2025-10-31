from rest_framework import status
from rest_framework.response import Response
from rest_framework import viewsets

from .models import Schedule, Tag
from .serializers import (ScheduleSerializer, ScheduleCreateSerializer,
                          TagSerializer)

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer

    def create(self, request, *args, **kwargs):
        serializer = ScheduleCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            schedule = serializer.save()
            return Response(ScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    
