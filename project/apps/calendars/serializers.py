from .models import Schedule, Tag
from rest_framework import serializers

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'

class ScheduleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        exclude = ('id', 'created_at', 'updated_at')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'




