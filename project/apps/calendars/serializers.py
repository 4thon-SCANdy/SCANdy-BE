from rest_framework import serializers

from .models import *

class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = ['id', 'user', 'name', 'google_calendar_id', 'is_primary']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class ScheduleSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    def get_tags(self, instance):
      tag = instance.tags.all()
      return [t.name for t in tag]

    class Meta:
        model = Schedule
        fields = ['id', 'google_event_id', 'title', "tags",
                  'content', 'start_datetime', 'end_datetime', 
                  'all_day', 'repeat', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def create(self, validated_data):
        return Schedule.objects.create(**validated_data)
    
    def validate(self, data):
        if data['start_datetime'] > data['end_datetime']:
            raise serializers.ValidationError("시작 시간이 종료 시간보다 늦을 수 없습니다.")
        return data