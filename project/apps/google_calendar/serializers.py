from django.db import transaction

from rest_framework import serializers
from .models import GoogleCalendar

class GoogleCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleCalendar
        fields = [
            'id',
            'google_calendar_str_id',
            'summary',
            'is_activated',
            'is_primary',
        ]
        read_only_fields = ['id']
    def save(self, **kwargs):
        user = kwargs.pop('user', None) or self.context.get('user')
        if user is None:
            raise serializers.ValidationError("User must be provided to save GoogleCalendar.")

        if not hasattr(self, 'validated_data'):
            raise serializers.ValidationError("Call is_valid() before save()")

        data = self.validated_data

        google_calendar_str_id = data.get('google_calendar_str_id')
        if not google_calendar_str_id:
            raise serializers.ValidationError("google_calendar_str_id is required.")

        defaults = {
            'summary': data.get('summary', ''),
            'is_primary': data.get('is_primary', False),
            'is_activated': data.get('is_activated', True),
        }

        with transaction.atomic():
            obj, created = GoogleCalendar.objects.update_or_create(
                user=user,
                google_calendar_str_id=google_calendar_str_id,
                defaults=defaults
            )

        self.instance = obj
        return obj

'''
예시 Calendar 하나의 오브젝트 Json
{
    "id": "sanyoentertain@gmail.com",
    "summary": "sanyoentertain@gmail.com",
    "timeZone": "Asia/Seoul",
    "accessRole": "owner",
    "primary": true,
    "colorId": "14",
    "backgroundColor": "#9fe1e7",
}
'''
class GoogleCalendarAPISerializer(serializers.Serializer):
    id = serializers.CharField(required=True)
    summary = serializers.CharField(required=True)
    primary = serializers.BooleanField(required=False, default=False)

    def to_internal_value(self, data):
        raw = super().to_internal_value(data)
        normalized = {
            'google_calendar_str_id': raw['id'],
            'summary': raw['summary'],
            'is_primary': bool(raw.get('primary', False)),
        }
        return normalized
