from datetime import timedelta
from dateutil.relativedelta import relativedelta
import copy

from external.time_manager import TimeRange, ensure_datetime

# expand를 진행할 때 until이 없으면 무조건 집어넣는다.
def expand_repeating_schedule(sched_list: list, filter_range: TimeRange) -> list:
    expanded_scheds = []

    for sched in sched_list:
        repeat = sched.get('repeat', 'NONE')
        start = ensure_datetime(sched['start_datetime'])
        end = ensure_datetime(sched['end_datetime'])
        until = ensure_datetime(sched.get('until')) if sched.get('until') else None

        # 반복이 없는 경우 그대로 추가
        if repeat == 'NONE' and filter_range.overlaps(TimeRange(start, end)):
            expanded_scheds.append(sched)
            continue
        
        current_start = start
        current_end = end

        # 마지막까지 반복하며, 인스턴스 생성.
        if until:
            end_repeat = min(until, filter_range.end)
        else:
            end_repeat = filter_range.end
            
        while current_start <= end_repeat:
            new_sched = {
                **sched,
                'start_datetime': current_start.isoformat(),
                'end_datetime': current_end.isoformat(),
            }
            new_sched['start_datetime'] = current_start.isoformat()
            new_sched['end_datetime'] = current_end.isoformat()
            # 만약 시작지점이 filter_range보다 작으면 append하지 않음.
            if current_start >= filter_range.start:
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
