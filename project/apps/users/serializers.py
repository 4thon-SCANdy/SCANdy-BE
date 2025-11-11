from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "is_google_sync", "google_sub", "google_refresh_token"]
        extra_kwargs = {'google_refresh_token': {'write_only': True}}

class GoogleLoginSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField()

