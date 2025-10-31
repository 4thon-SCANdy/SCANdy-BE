from datetime import timedelta
from dateutil.relativedelta import relativedelta
import copy

from django.utils.dateparse import parse_datetime

from external.time_manager import TimeRange

# daily, weekly, monthly를 분리해서 여러개의 json 리스트 형태로 변환하는 함수.
# 성능 저하가 심하기에 이전 필터링을 모두 거치고 호출하여야 한다.
# start_datetime, end_datetime, until이 모두 있는 serialized 된 sched만 정상 동작한다.
def expand_repeating_schedule(sched_list: list) -> list:
    expanded_scheds = []

    for sched in sched_list:
        repeat = sched.get('repeat', 'NONE')
        start = parse_datetime(sched['start_datetime'])
        end = parse_datetime(sched['end_datetime'])
        until = parse_datetime(sched['until'])

        # 반복이 없는 경우 그대로 추가
        if repeat == 'NONE':
            expanded_scheds.append(sched)
            continue

        current_start = start
        current_end = end

        # until까지 반복하며, 인스턴스 생성.
        while current_start <= until:
            # 새로운 인스턴스 복사
            new_sched = copy.deepcopy(sched)
            new_sched['start_datetime'] = current_start.isoformat()
            new_sched['end_datetime'] = current_end.isoformat()
            # until은 그대로 유지
            expanded_scheds.append(new_sched)

            # 다음 반복 계산
            if repeat == 'DAILY':
                current_start += timedelta(days=1)
                current_end += timedelta(days=1)
            elif repeat == 'WEEKLY':
                current_start += timedelta(weeks=1)
                current_end += timedelta(weeks=1)
            elif repeat == 'MONTHLY':
                current_start += relativedelta(months=1)
                current_end += relativedelta(months=1)
            elif repeat == 'YEARLY':
                current_start += relativedelta(years=1)
                current_end += relativedelta(years=1)
            else:
                # UNKNOWN repeat, 종료
                break

    return expanded_scheds


# json list를 filtering해서 
def filter_querysets_by_time_range(filter_range: TimeRange, queryset):
    # 일단 나중에 구현.
    pass
