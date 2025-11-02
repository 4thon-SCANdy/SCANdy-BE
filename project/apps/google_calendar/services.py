
from googleapiclient.discovery import build

from apps.users.models import User

from .serializers import GoogleCalendarSerializer, GoogleCalendarAPISerializer

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
