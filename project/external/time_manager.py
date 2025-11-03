import datetime
from datetime import timezone, timedelta
from django.utils.dateparse import parse_datetime

# 한국 timezone 설정.
KST = timezone(timedelta(hours=9))

# 시간 범위를 나타내는 클래스.
class TimeRange:
    start: datetime.datetime
    end: datetime.datetime
    def __init__(self, start: datetime.datetime, end: datetime.datetime):
        self.start = start
        self.end = end
        
    def is_in_range(self, time: datetime.datetime) -> bool:
        return self.start <= time <= self.end
    # 현재 timerange안에 다른 timerange가 있는지 확인.
    # 일부라도 포함된다면 True를 반환한다.
    def overlaps(self, other: 'TimeRange') -> bool:
        # other의 start가 이 클래스의 start보다 이전이면, other의 end가 이 클래스의 start보다 이후인지 확인.
        if other.start < self.start:
            return other.end >= self.start
        # other의 start가 이 클래스의 start보다 이후이면, other의 start가 이 클래스의 end보다 이전인지 확인.
        else:
            return other.start <= self.end

def ensure_datetime(value):
    if isinstance(value, str):
        value = value.replace(" ", "+")
        parsed = parse_datetime(value)
        return parsed
    return value

# zulu time으로 변경하는 함수.
def datetime_to_zulu(dt) -> str:
    zulu_str = dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    return zulu_str

# timezone을 kst 기준으로 없앰.
def to_naive_kst(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt  # 이미 naive면 그대로
    return dt.astimezone(KST).replace(tzinfo=None)
