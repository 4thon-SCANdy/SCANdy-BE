import requests
import json
import re
from django.conf import settings

BASE = "https://api.openai.com/v1/chat/completions"

# ocr이 보내주는 데이터에서 슬롯을 채우도록
QUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "일정 제목 (예: 팀 회의, 발표 준비 등)"
        },
        "content": {
            "type": "string",
            "description": "일정의 세부 내용 또는 메모"
        },
        "start_datetime": {
            "type": "string",
            "description": "일정 시작 일시 (ISO 8601 형식, 예: 2025-11-19T15:15:00)"
        },
        "end_datetime": {
            "type": "string",
            "description": "일정 종료 일시 (ISO 8601 형식, 예: 2025-11-19T16:15:00)"
        },
        "all_day": {
            "type": "boolean",
            "description": "종일 일정 여부 (예: true 또는 false)"
        },
        "repeat": {
            "type": "string",
            "enum": ["NONE", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"],
            "description": "반복 주기 (선택: NONE, DAILY, WEEKLY, MONTHLY, YEARLY)"
        },
        "location": {
            "type": "string",
            "description": "일정 장소 (예: 회의실)"
        },
    },
    "required": ["title", "start_datetime", "end_datetime"]
}


# REPEAT_CHOICES = [
#         ('NONE', '반복 없음'),
#         ('DAILY', '매일'),
#         ('WEEKLY', '매주'),
#         ('MONTHLY', '매월'),
#         ('YEARLY', '매년'),
#     ]

# "title": "팀 회의",
# "content": "SCANdy 팀 회의",
# "start_datetime": "2025-11-19T15:15:00",
# "end_datetime": "2025-11-19T16:15:00",
# "all_day": false,
# "repeat": "WEEKLY",
# "location": "동국대 혜화관 3층 회의실",

def _headers():
    return {
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }

def create_schedule(input_text: str, model: str = "gpt-4o-mini"):
  """
  OCR 텍스트를 받아 일정 데이터를 추출하는 함수.
  """
  system_prompt = (
    "너는 OCR 또는 자연어 입력으로부터 추출된 텍스트를 구조화하는 일정 관리 비서야. "
    "사용자가 보낸 문장에서 제목(title), 내용(content), 시작 및 종료 일시(start_datetime, end_datetime), "
    "장소(location), 반복 주기(repeat), 종일 여부(all_day)를 찾아 JSON 형식으로 반환해줘."
    "반복 주기는 반드시 다음 중 하나로만 반환해야 해: "
    "'NONE', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'."
    "모든 날짜와 시간은 ISO 8601 형식(YYYY-MM-DDTHH:MM:SS)으로 작성하고, "
    "사용자가 시간을 명시하지 않은 경우 all_day 값을 true로 설정해."
    "start_datetime은 있는데, end_datetime 값은 추출할 수 없다면 start_datetime으로부터 1시간 뒤로 설정해줘"
    "위 datetime 항목 외에는 추출할 수 없는 값은 절대 만들어내지말고 null을 반환해줘"
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
            {"role": "user", "content": input_text}
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

