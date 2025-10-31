from external.time_manager import TimeRange


# 하나의 Schedule object가 들어왔을 때, 그 Schedule을 repeat에 따라 변환할 필요성이 있다.
# daily, weekly, monthly를 분리해서 여러개의 json 형태로 변환하는 함수.
# 성능 저하가 심하기에 이전 필터링을 모두 거치고 호출하여야 한다.
def expand_repeating_schedule():
    pass


# json list를 filtering해서 
def filter_querysets_by_time_range(filter_range: TimeRange, queryset):
    # 일단 나중에 구현.
    pass
