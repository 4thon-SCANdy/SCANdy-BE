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
    
def make_google_event_dict(sched: dict):
    start_val = sched.get("start_datetime")
    end_val = sched.get("end_datetime")

    def build_time_field(value):
        if not value:
            return None
        if "T" in value:  # 시간 포함이면 dateTime으로 처리
            return event_dict.append({"dateTime": value, "timeZone": "Asia/Seoul"})
        else:  # 날짜만 있으면 all-day 이벤트로 처리
            return {"date": value}

    event_dict = {
        "summary": sched.get("title", ""),
        "description": sched.get("content", ""),
    }

    start_field = build_time_field(start_val)
    end_field = build_time_field(end_val)

    if start_field:
        event_dict["start"] = start_field
    if end_field:
        event_dict["end"] = end_field

    return event_dict


# schedule을 구글 캘린더 primary에 추가하는 함수.
# DB에 저장되지 않은 구글 데이터도 받을 수 있도록 인자 옵션 수정
def post_or_update_schedule_of_user(user: User, credential, sched: Schedule | dict, google_event_id=None):
    primary_calendar = user.google_calendars.filter(is_primary=True).first()
    service = build("calendar", "v3", credentials=credential)

    if isinstance(sched, dict):
        event_dict = make_google_event_dict(sched)
    else:
        event_dict = schedule_to_google_calendar_event(schedule=sched) # DB에 저장된 경우

    # 인자로 받은 구글 ID가 있으면 사용
    event_id = google_event_id or sched.google_event_id
    calendar_id = (
        getattr(sched, "google_calendar_str_id", None)
        or user.google_calendars.filter(is_primary=True).values_list("google_calendar_str_id", flat=True).first()
    )

    # 이미 구글 이벤트 ID가 있는 경우 update
    if (isinstance(sched, Schedule) and sched.google_calendar and sched.google_event_id) or google_event_id:
        try:
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            print("가져온 일정", event)

            for key, value in event_dict.items():
                event[key] = value

            print("업데이트한 일정", event)

            # 기존 이벤트 업데이트
            event = service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
        except googleapiclient.errors.HttpError as e:
            # 이벤트가 없는 경우 insert
            if e.resp.status == 404:
                event = service.events().insert(
                    calendarId=calendar_id,
                    body=event_dict
                ).execute()
            else:
                raise
    else:
        # 새로 삽입
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_dict
        ).execute()

    # 구글 관련 데이터 저장, schedule 객체일 경우만
    if isinstance(sched, Schedule):
        sched.google_event_id = event.get('id')
        sched.google_calendar = primary_calendar
        sched.save()
    
    return event

# DB에 없는 일정도 삭제하기 위해 event_id, user 인자 추가
def delete_from_schedule(credential, schedule: Schedule | dict = None, google_event_id=None, user: User = None):

    service = build("calendar", "v3", credentials=credential)

    calendar_id = (
        getattr(getattr(schedule, "google_calendar", None), "google_calendar_str_id", None)
        or user.google_calendars.filter(is_primary=True)
        .values_list("google_calendar_str_id", flat=True)
        .first()
        or "primary"
    )

    event_id = getattr(schedule, "google_event_id", None) or google_event_id

    if not calendar_id or not event_id:
        return
    
    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
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

