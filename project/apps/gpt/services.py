import json, re, requests
from django.conf import settings
from datetime import datetime, timedelta
from apps.calendars.models import Schedule
from external.time_manager import ensure_datetime
from django.db.models import Q

BASE = "https://api.openai.com/v1/chat/completions"

# ocr이 보내주는 데이터에서 슬롯을 채우도록
QUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "일정 제목 (예: 팀 회의, 발표 준비 등)",
        },
        "content": {"type": "string", "description": "일정의 세부 내용 또는 메모"},
        "start_datetime": {
            "type": "string",
            "description": "일정 시작 일시 (ISO 8601 형식, 예: 2025-11-19T15:15:00)",
        },
        "end_datetime": {
            "type": "string",
            "description": "일정 종료 일시 (ISO 8601 형식, 예: 2025-11-19T16:15:00)",
        },
        "all_day": {
            "type": "boolean",
            "description": "종일 일정 여부 (예: true 또는 false)",
        },
        "repeat": {
            "type": "string",
            "enum": ["NONE", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"],
            "description": "반복 주기 (선택: NONE, DAILY, WEEKLY, MONTHLY, YEARLY)",
        },
        "location": {"type": "string", "description": "일정 장소 (예: 회의실)"},
    },
    "required": ["title", "start_datetime", "end_datetime"],
}


def _headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }


def create_schedule(input_text: str, model: str = "gpt-4o-mini"):
    today = datetime.now()
    today_str = today.strftime("%Y년 %m월 %d일")

    system_prompt = (
        f"오늘은 {today_str}이야."
        "너는 OCR 또는 자연어 입력으로부터 추출된 텍스트를 구조화하는 일정 관리 비서야. "
        "사용자가 보낸 문장에서 제목(title), 내용(content), 시작 및 종료 일시(start_datetime, end_datetime), "
        "장소(location), 반복 주기(repeat), 종일 여부(all_day)를 찾아 JSON 형식으로 반환해줘."
        "반복 주기는 반드시 다음 중 하나로만 반환해야 해: "
        "'NONE', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'."
        "모든 날짜와 시간은 ISO 8601 형식(YYYY-MM-DDTHH:MM:SS)으로 작성하고, "
        "사용자가 연도를 명시하지 않았다면 오늘 날짜를 기준으로 같은 연도로 설정해."
        "사용자가 시간을 명시하지 않은 경우 all_day 값을 true로 설정해."
        "end_datetime이 없다면 start_datetime보다 1시간 뒤로 설정해."
        "추출할 수 없는 값은 절대 만들어내지말고 null을 반환해줘"
        "출력은 반드시 JSON만 반환해야 하며, 예시는 다음과 같아:"
        "{"
        '  "title": "팀 회의",'
        '  "content": "SCANdy 팀 회의",'
        '  "start_datetime": "2025-11-19T15:15:00",'
        '  "end_datetime": "2025-11-19T16:15:00",'
        '  "all_day": false,'
        '  "repeat": "WEEKLY",'
        '  "location": "동국대 혜화관 3층 회의실"'
        "}"
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ],
    }

    try:
        r = requests.post(BASE, headers=_headers(), json=body, timeout=(5, 20))
        print("헤더:", r.request.headers)
        r.raise_for_status()
        data = r.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def parse_response(data):
    try:
        content = data["choices"][0]["message"]["content"]
        # json 코드블록 제거
        content = re.sub(r"```json|```", "", content).strip()
        schedule = json.loads(content)
        return schedule
    except Exception as e:
        print("JSON 파싱 실패:", e)
        return None


# 추출한 날짜와 시간을 캘린더에서 검색하여, 이미 일정이 있다면 1시간 뒤로 추천해주는 로직
def recommend_time(user, start_str, end_str):
    start_dt = ensure_datetime(start_str)
    end_dt = ensure_datetime(end_str)

    overlapping = Schedule.objects.filter(
        calendar=user.calendar,
        start_datetime__lt=end_dt,
        end_datetime__gt=start_dt,
    )

    if overlapping.exists():
        start_dt += timedelta(hours=1)
        end_dt += timedelta(hours=1)
        return {
            "detail": "겹치는 일정이 있어 1시간 뒤로 추천합니다.",
            "recommended_start": start_dt.isoformat(),
            "recommended_end": end_dt.isoformat(),
        }
    else:
        return {
            "detail": "겹치는 일정이 없습니다.",
            "recommended_start": start_dt.isoformat(),
            "recommended_end": end_dt.isoformat(),
        }
