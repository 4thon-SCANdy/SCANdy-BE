import requests
import json
import re
from django.conf import settings

BASE = "https://api.openai.com/v1/chat/completions"

# ocr이 보내주는 데이터에서 슬롯을 채우도록
QUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "일정 제목"},
        "date": {"type": "string", "description": "YYYY-MM-DD 형식 날짜"},
        "time": {"type": "string", "description": "HH:MM 형식 시간"},
        "location": {"type": "string", "description": "장소"},
        "tag": {"type": "string", "description": "태그"},
    },
    "required": ["title", "date"],
}

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
      "너는 OCR로부터 추출된 텍스트를 바탕으로 일정을 구조화하는 비서야. "
      "사용자가 보낸 텍스트에서 날짜, 시간, 장소, 제목, 태그 등을 JSON으로 추출해줘."
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
