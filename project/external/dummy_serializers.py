from rest_framework import serializers

# anable to guess serializer 경고 해소용
class DummySerializer(serializers.Serializer):
    image = serializers.ImageField(required=False)
    task_id = serializers.IntegerField(required=False)