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
    images = serializers.SerializerMethodField()
    class Meta:
        model = Schedule
        fields = '__all__'

    # 이미지 url 리스트 반환
    def get_images(self, obj):
        request = self.context.get('request')
        urls = []

        for img in obj.images.all():
            if img.task_image:
                # 절대 URL로 변환
                if request is not None:
                    url = request.build_absolute_uri(img.task_image.url)
                else:
                    url = img.task_image.url
                urls.append(url)

        return urls
        

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

    task_id = serializers.IntegerField(required=False, allow_null=True)
    class Meta:
        model = Schedule
        exclude = ('id', 'calendar', 'created_at', 'updated_at')
        extra_kwargs = {
            'until': {'required': False}
        }
        
    def create(self, validated_data):
        user = self.context['request'].user
        tag_data = validated_data.pop("tag", None)
        task_id = validated_data.pop("task_id", None)
        schedule = Schedule.objects.create(
            calendar=user.calendar,
            **validated_data
        )

        self._handle_tag(schedule, tag_data, user.calendar)

        if task_id:
            try:
                task = Task.objects.get(id=task_id)
                task.images.update(schedule=schedule)
            except Task.DoesNotExist:
                print(f"Task {task_id} 가 없어 일정 연결을 하지 않고 넘어갑니다.")
                
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

