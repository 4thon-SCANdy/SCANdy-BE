import requests

def create_google_event(access_token, calendar_id, schedule):
    # 구글 캘린더 일정 등록

    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    event = {
        "summary": schedule.title,
        "description": schedule.content or "",
        "start": {"dateTime": schedule.start_datetime.isoformat(), "timeZone": "Asia/Seoul"},
        "end": {"dateTime": schedule.end_datetime.isoformat(), "timeZone": "Asia/Seoul"},
        "location": schedule.locate,
        # 반복 옵션 추가
    }

    response = requests.post(url, headers=headers, json=event)

    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Google Calendar API error: {response.text}")
