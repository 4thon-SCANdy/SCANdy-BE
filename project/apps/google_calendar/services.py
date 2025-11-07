import datetime

import googleapiclient
from googleapiclient.discovery import build

from apps.users.models import User
from apps.calendars.models import Schedule

from .models import GoogleCalendar
from .serializers import (GoogleCalendarSerializer, GoogleCalendarAPISerializer,
                          GoogleCalendarEventToScheduleSerializer)

from external.time_manager import KST, datetime_to_zulu, ensure_datetime


# user를 받아서 (is_google_sync 검사.) google_calendar db를 업데이트 하거나 create한다.
def update_google_calendar(user: User, credential):
    if not user.is_google_sync:
        return
    
    service = build("calendar", "v3", credentials=credential)

    # 사용자의 calendar모든 리스트.
    calendars = []
    
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        calendars.extend(calendar_list.get('items', []))
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    
    # calendar를 serializer로 변환, DB에 저장/업데이트.
    google_api_ser = GoogleCalendarAPISerializer(data=calendars, many=True)
    google_api_ser.is_valid(raise_exception=True)
    normalized_data = google_api_ser.validated_data

    # error 방지를 위해 분리해서 처리.
    for norm in normalized_data:
        model_ser = GoogleCalendarSerializer(
            data=norm,
            many=False,
            context={'user': user}
        )
        model_ser.is_valid(raise_exception=True)
        model_ser.save(user=user)

def get_schedules_of_user(user: User, credential, start_datetime: datetime.datetime, end_datetime: datetime.datetime):
    service = build("calendar", "v3", credentials=credential)

    google_calendars = user.google_calendars.all()

    # 한국 시간(utc+9 반영) 변경해서 처리.
    time_min = start_datetime.astimezone(KST).isoformat()
    time_max = end_datetime.astimezone(KST).isoformat()

    # 여러 캘린더에서 이벤트 가져오기
    events_result = []
    for calendar in google_calendars:
        result = (
            service.events()
            .list(
                calendarId=calendar.google_calendar_str_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=False,
            )
            .execute()
        )
        events = result.get('items', [])
        # event마다 serialize를 진행한다.
        for event in events:
            serializer = GoogleCalendarEventToScheduleSerializer(
                data=event,
                context={'google_calendar_id': calendar.id}
            )
            if serializer.is_valid():
                internal_data = serializer.validated_data
                events_result.append(internal_data)
            else:
                print("Invalid event:", serializer.errors)
        
    return events_result


# schedule을 google calendar event 형식으로 만듬.
def schedule_to_google_calendar_event(schedule: Schedule) -> dict:
    return {
        'summary': schedule.title,
        'description': schedule.content,
        'start': {'dateTime': schedule.start_datetime.isoformat(), 'timeZone': 'Asia/Seoul'},
        'end': {'dateTime': schedule.end_datetime.isoformat(), 'timeZone': 'Asia/Seoul'},
        **({'recurrence': [f"RRULE:FREQ={schedule.repeat};UNTIL={datetime_to_zulu(schedule.until)}"]}
            if schedule.repeat != "NONE" and schedule.until else {})
    }
    

# schedule을 구글 캘린더 primary에 추가하는 함수.
def post_or_update_schedule_of_user(user: User, credential, sched: Schedule):
    primary_calendar = user.google_calendars.filter(is_primary=True).first()
    service = build("calendar", "v3", credentials=credential)
    event_dict = schedule_to_google_calendar_event(schedule=sched)

    # 이미 구글 이벤트 ID가 있는 경우 update
    if sched.google_calendar and sched.google_event_id:
        try:
            event = service.events().get(
                calendarId=sched.google_calendar.google_calendar_str_id,
                eventId=sched.google_event_id
            ).execute()

            # 기존 이벤트 업데이트
            event = service.events().update(
                calendarId=sched.google_calendar.google_calendar_str_id,
                eventId=sched.google_event_id,
                body=event_dict
            ).execute()
        except googleapiclient.errors.HttpError as e:
            # 이벤트가 없는 경우 insert
            if e.resp.status == 404:
                event = service.events().insert(
                    calendarId=primary_calendar.google_calendar_str_id,
                    body=event_dict
                ).execute()
            else:
                raise
    else:
        # 새로 삽입
        event = service.events().insert(
            calendarId=primary_calendar.google_calendar_str_id,
            body=event_dict
        ).execute()

    # 구글 관련 데이터 저장
    sched.google_event_id = event.get('id')
    sched.google_calendar = primary_calendar
    sched.save()

def delete_from_schedule(credential, schedule: Schedule):
    if not schedule.google_calendar or not schedule.google_event_id:
        return

    service = build("calendar", "v3", credentials=credential)

    try:
        service.events().delete(
            calendarId=schedule.google_calendar.google_calendar_str_id,
            eventId=schedule.google_event_id
        ).execute()
    except googleapiclient.errors.HttpError as e:
        if e.resp.status != 404:
            raise

# 두개의 list를 합쳐 하나의 list로 만든다.
def merge_scheds(sched_list: list, google_sched_list: list):
    sched_list = sched_list or []

    existing_ids = {
        GoogleCalendar.objects.get(id=sched.get('google_calendar_id')).id
        for sched in sched_list
        if sched.get('google_calendar_id')
    }
    new_sched_list = sched_list.copy()

    for g_s in google_sched_list:
        if g_s.get('google_calendar_id') in existing_ids:
            continue
        else:
            new_sched_list.append(g_s)

    return new_sched_list

