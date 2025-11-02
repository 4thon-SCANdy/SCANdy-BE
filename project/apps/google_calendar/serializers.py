from django.db import transaction, IntegrityError
import dateutil.parser
from rest_framework import serializers

from .models import GoogleCalendar

from apps.calendars.models import Schedule


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
    
# google calendar event에 나온 json을 event의 json 형태로 변환하는 Serializer
class GoogleCalendarEventToScheduleSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        # context에서 google_calendar_id 가져오기
        google_calendar_id = self.context.get('google_calendar_id')
        if google_calendar_id is None:
            raise serializers.ValidationError("google_calendar_id is required in context.")

        # start_datetime, end_datetime 처리
        start_raw = data['start'].get('dateTime') or data['start'].get('date')
        end_raw = data['end'].get('dateTime') or data['end'].get('date')
        start_dt = dateutil.parser.isoparse(start_raw)
        end_dt = dateutil.parser.isoparse(end_raw)

        # recurrence에서 repeat, until 처리
        recurrence = data.get('recurrence', [])
        repeat = 'NONE'
        until = None
        if recurrence:
            rule = recurrence[0]  # 예: "RRULE:FREQ=WEEKLY;WKST=SU;UNTIL=20260216T145959Z;BYDAY=TU"
            parts = rule.replace('RRULE:', '').split(';')
            rule_dict = {p.split('=')[0]: p.split('=')[1] for p in parts if '=' in p}
            repeat = rule_dict.get('FREQ', 'NONE')
            until_str = rule_dict.get('UNTIL')
            if until_str:
                until = dateutil.parser.isoparse(until_str)
                
        # color 매핑.
        colorId = data.get('colorId')
        # int 타입이면 변환.
        if colorId and isinstance(colorId, str):
            if colorId.isdigit():
                colorId = int(colorId)
        else:
            colorId = None

        internal = {
            'id': None,
            'google_calendar_id': google_calendar_id,
            'google_event_id': data['id'],
            'title': data.get('summary', ''),
            'content': data.get('description', ''),
            'start_datetime': start_dt.isoformat(),
            'end_datetime': end_dt.isoformat(),
            'repeat': repeat,
            'until': until.isoformat() if until else None,
            'colorId': colorId if colorId else 0,
        }
        return internal
    
