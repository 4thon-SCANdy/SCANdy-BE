import datetime

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
