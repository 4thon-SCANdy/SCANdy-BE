from rest_framework import serializers

from .models import *

class TaskCreateSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
    )

    def validate_images(self, value):
        if not value:
            raise serializers.ValidationError("이미지가 최소 1개 이상 필요합니다.")
        return value


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "ocr_result", "llm_result"]

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'task_image']