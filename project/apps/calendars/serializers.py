from .models import Schedule, Tag
from rest_framework import serializers

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'

class ScheduleCreateSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Schedule
        exclude = ('id', 'calendar', 'created_at', 'updated_at')
        
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




