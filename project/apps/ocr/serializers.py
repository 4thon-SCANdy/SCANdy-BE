import base64
import uuid
import time
import math
import requests
import concurrent.futures
from rest_framework import serializers
from django.conf import settings

from apps.tasks.models import Image, Task
from apps.calendars.models import Schedule
from django.db import transaction

# MIME → 확장자 매핑
MIME_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    # 필요시 webp 열기 (엔진에 따라 실패할 수 있음)
    # "image/webp": "webp",
}

MAX_FILES = 5
MAX_FILE_MB = 50

# 동시 호출 개수와 재시도 설정
MAX_WORKERS = 4            # 3~5 권장
MAX_RETRIES = 2            # 429/5xx 등에 대해 재시도
BASE_BACKOFF_SEC = 0.6     # 0.6 → 1.2 → ...

def _ext_from_file(f):
    ctype = getattr(f, "content_type", "") or ""
    if ctype in MIME_EXT:
        return MIME_EXT[ctype]
    # content_type이 비어도 확장자로 보조 판정
    name = getattr(f, "name", "") or ""
    ext = (name.split(".")[-1] or "").lower()
    return ext if ext in set(MIME_EXT.values()) else "jpg"

def _b64_from_file(f):
    f.seek(0)
    # 순수 base64 문자열 (개행 제거)
    return base64.b64encode(f.read()).decode("utf-8").replace("\n", "").replace("\r", "")

def _clova_payload_one(name, fmt, b64):
    return {
        "version": "V2",  # ★ Custom OCR는 V2
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "images": [{"name": name, "format": fmt, "data": b64}],  # ★ 항상 1장
    }

def _clova_headers(secret):
    return {
        "Content-Type": "application/json",
        "X-OCR-SECRET": secret,
    }

def _post_with_retries(url, json, headers):
    # 간단한 지수 백오프 재시도
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=json, headers=headers, timeout=30)
            # 429 or 5xx면 재시도 고려
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(BASE_BACKOFF_SEC * (2 ** attempt))
                continue
            return resp
        except requests.RequestException as e:
            # 네트워크 오류 재시도
            if attempt < MAX_RETRIES:
                time.sleep(BASE_BACKOFF_SEC * (2 ** attempt))
                continue
            # 마지막 시도 실패 시 그대로 raise
            raise e

class OcrImageSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        max_length=MAX_FILES,
        allow_empty=False,
    )

    def validate_images(self, files):
        if len(files) > MAX_FILES:
            raise serializers.ValidationError(f"이미지는 최대 {MAX_FILES}개까지 업로드 가능합니다.")
        for f in files:
            if hasattr(f, "size") and f.size > MAX_FILE_MB * 1024 * 1024:
                raise serializers.ValidationError(f"{getattr(f, 'name', 'file')}: 파일 크기는 최대 {MAX_FILE_MB}MB 입니다.")
            ctype = getattr(f, "content_type", "") or ""
            if ctype not in MIME_EXT:
                # 확장자로 보조 판정
                name = getattr(f, "name", "") or ""
                ext = (name.split(".")[-1] or "").lower()
                if ext not in set(MIME_EXT.values()):
                    raise serializers.ValidationError(f"{name or 'file'}: 지원하지 않는 이미지 형식입니다.")
        return files

    def create(self, validated_data):
        files = validated_data["images"]
        user = self.context["request"].user

        api_url = getattr(settings, "CLOVA_OCR_URL", None)
        secret  = getattr(settings, "CLOVA_OCR_SECRET", None)
        if not api_url or not secret:
            raise serializers.ValidationError("서버 설정 오류: CLOVA_OCR_URL / CLOVA_OCR_SECRET 을 확인하세요.")

        headers = _clova_headers(secret)

        # 하나의 Task를 만들어서 이미지들을 묶어줌 (optional)
        with transaction.atomic():
            task = Task.objects.create()

            items = []
            for idx, f in enumerate (files):
                # 1) 이미지 저장 (유저, Task 연결)
                img_instance = Image.objects.create(
                    task=task,
                    task_image=f,
                )

                # 2) 파일 형태에 따른 전처리
                # 파일 → (index, name, fmt, b64) 전처리 (I/O는 메인 스레드에서)
                name = getattr(f, "name", f"image_{idx+1}.jpg")
                fmt  = _ext_from_file(f)
                b64  = _b64_from_file(f)
                items.append((idx, name, fmt, b64))

        results = [None] * len(items)

        def work(item):
            idx, name, fmt, b64 = item
            payload = _clova_payload_one(name, fmt, b64)
            try:
                resp = _post_with_retries(api_url, json=payload, headers=headers)
                if resp.status_code >= 400:
                    # CLOVA가 상세 원인을 문자열로 내려줌
                    return idx, {
                        "file": name,
                        "status": resp.status_code,
                        "error": resp.text,
                    }
                data = resp.json()
                texts = [
                    (field.get("inferText") or "")
                    for img in data.get("images", []) or []
                    for field in img.get("fields", []) or []
                ]
                texts = [t for t in texts if t]

                return idx, {
                    "file": name,
                    "texts": texts,                      # ★ TaskLLMView가 기대하는 키
                    "full_text": " ".join(texts),        # (선택) 한 줄로 합친 텍스트 - 디버그/로그용
                    # "raw": data,                       # (선택) 필요시 주석 해제
                }
            except requests.RequestException as e:
                return idx, {
                    "file": name,
                    "status": 0,
                    "error": str(e),
                }

        # 병렬 전송 (동시성 제한)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            for idx, res in ex.map(work, items):
                results[idx] = res

        return {"task_id": task.id, "results": results}
