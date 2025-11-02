from django.db import transaction, IntegrityError

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
        data = self.validated_data

        google_calendar_str_id = data.get('google_calendar_str_id')

        defaults = {
            'summary': data.get('summary', ''),
            'is_primary': data.get('is_primary', False),
            'is_activated': data.get('is_activated', True),
        }
        
        # user와 google_Calendar_str_id가 이미 있으면 update, 아니면 create한다.
        with transaction.atomic():
            obj, created = GoogleCalendar.objects.update_or_create(
                user=user,
                google_calendar_str_id=google_calendar_str_id,
                defaults=defaults
            )

        self.instance = obj
        return obj
    
# update만 가능한 serializer
class GoogleCalendarUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleCalendar
        fields = ['id', 'is_activated']
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        # is_activated만 수정할 수 있다.
        is_activated = validated_data.get('is_activated', instance.is_activated)

        with transaction.atomic():
            instance.is_activated = is_activated
            instance.save(update_fields=['is_activated'])

        return instance

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
