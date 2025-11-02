from .models import Schedule, Tag
from rest_framework import serializers

from django.utils.dateparse import parse_datetime

from external.time_manager import KST

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'

    # timezone을 바꿈.
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        for field in ['start_datetime', 'end_datetime', 'until']:
            if ret.get(field):
                dt = parse_datetime(ret[field])
                if dt is not None:
                    ret[field] = dt.replace(tzinfo=KST)
        return ret  

class ScheduleCreateSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Schedule
        exclude = ('id', 'calendar', 'created_at', 'updated_at')
        extra_kwargs = {
            'until': {'required': False}
        }
        
    def create(self, validated_data):
        user = self.context['request'].user
        schedule = Schedule.objects.create(
            calendar=user.calendar,
            **validated_data
        )
        return schedule
    
class ScheduleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        exclude = ('id', 'calendar', 'created_at', 'updated_at')

    def update(self, instance, validated_data):        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

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
        exclude = ('id', 'calendar',)

    def update(self, instance, validated_data):        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    