from apps.tasks.models import Task
from .models import Schedule, Tag
from apps.tasks.seriallizers import ImageSerializer
from rest_framework import serializers

from django.utils.dateparse import parse_datetime

from external.time_manager import KST

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        exclude = ('calendar',)

class TagCreateSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Tag
        exclude = ('id', 'calendar')
        
    def create(self, validated_data):
        user = self.context['request'].user
        tag = Tag.objects.create(
            calendar=user.calendar,
            **validated_data
        )
        return tag
    
class TagUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        exclude = ('id', 'calendar')

    def update(self, instance, validated_data):        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

class ScheduleSerializer(serializers.ModelSerializer):
    tag = TagSerializer(required=False)
    class Meta:
        model = Schedule
        fields = '__all__'
        
    # 공통 태그 처리 로직
    def _handle_tag(self, schedule, tag_data, calendar):
        if not tag_data:
            return
        tag_obj, _ = Tag.objects.get_or_create(
            calendar=calendar,
            name=tag_data.get("name"),
            defaults={"color": tag_data.get("color", 0)},
        )
        schedule.tag = tag_obj
        schedule.save()
        

class ScheduleCreateSerializer(ScheduleSerializer): 
    class Meta:
        model = Schedule
        exclude = ('id', 'calendar', 'created_at', 'updated_at')
        extra_kwargs = {
            'until': {'required': False}
        }
        
    def create(self, validated_data):
        user = self.context['request'].user
        tag_data = validated_data.pop("tag", None)
        schedule = Schedule.objects.create(
            calendar=user.calendar,
            **validated_data
        )

        task_id = self.initial_data.get("task_id")
        task_obj = None
        if task_id:
            try:
                task_obj = Task.objects.get(id=task_id)
            except Task.DoesNotExist:
                pass  # task_id가 유효하지 않으면 무시

        if task_obj:
            schedule.task = task_obj
            schedule.save(update_fields=["task"])
        
        self._handle_tag(schedule, tag_data, user.calendar)
    
        return schedule
    
class ScheduleUpdateSerializer(ScheduleSerializer):
    class Meta:
        model = Schedule
        exclude = ('id', 'calendar', 'created_at', 'updated_at')

    def update(self, instance, validated_data):  
        tag_data = validated_data.pop("tag", None)      
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        self._handle_tag(instance, tag_data, instance.calendar)
        instance.save()
        return instance

