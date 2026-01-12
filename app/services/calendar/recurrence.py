"""반복 일정 유틸리티

RRULE 형식을 사용하여 반복 일정을 처리합니다.
https://icalendar.org/iCalendar-RFC-5545/3-8-5-3-recurrence-rule.html
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from dateutil.rrule import rrule, rrulestr, DAILY, WEEKLY, MONTHLY, YEARLY
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU


class RecurrenceFrequency(str, Enum):
    """반복 주기"""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Weekday(str, Enum):
    """요일"""
    MO = "MO"  # Monday
    TU = "TU"  # Tuesday
    WE = "WE"  # Wednesday
    TH = "TH"  # Thursday
    FR = "FR"  # Friday
    SA = "SA"  # Saturday
    SU = "SU"  # Sunday


WEEKDAY_MAP = {
    Weekday.MO: MO,
    Weekday.TU: TU,
    Weekday.WE: WE,
    Weekday.TH: TH,
    Weekday.FR: FR,
    Weekday.SA: SA,
    Weekday.SU: SU,
}

FREQ_MAP = {
    RecurrenceFrequency.DAILY: DAILY,
    RecurrenceFrequency.WEEKLY: WEEKLY,
    RecurrenceFrequency.MONTHLY: MONTHLY,
    RecurrenceFrequency.YEARLY: YEARLY,
}


def build_rrule(
    freq: RecurrenceFrequency,
    interval: int = 1,
    weekdays: Optional[list[Weekday]] = None,
    until: Optional[date] = None,
    count: Optional[int] = None,
) -> str:
    """RRULE 문자열 생성

    Args:
        freq: 반복 주기 (DAILY, WEEKLY, MONTHLY, YEARLY)
        interval: 반복 간격 (기본값: 1)
        weekdays: 요일 목록 (WEEKLY일 때만 사용)
        until: 반복 종료일
        count: 반복 횟수

    Returns:
        RRULE 문자열 (예: "FREQ=WEEKLY;BYDAY=MO,WE,FR")

    Examples:
        >>> build_rrule(RecurrenceFrequency.DAILY)
        'FREQ=DAILY;INTERVAL=1'

        >>> build_rrule(RecurrenceFrequency.WEEKLY, weekdays=[Weekday.MO, Weekday.WE, Weekday.FR])
        'FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR'

        >>> build_rrule(RecurrenceFrequency.MONTHLY, interval=2, count=12)
        'FREQ=MONTHLY;INTERVAL=2;COUNT=12'
    """
    parts = [f"FREQ={freq.value}", f"INTERVAL={interval}"]

    if weekdays and freq == RecurrenceFrequency.WEEKLY:
        days = ",".join(day.value for day in weekdays)
        parts.append(f"BYDAY={days}")

    if until:
        # UNTIL은 UTC 형식이어야 함
        until_dt = datetime.combine(until, datetime.max.time())
        parts.append(f"UNTIL={until_dt.strftime('%Y%m%dT%H%M%SZ')}")
    elif count:
        parts.append(f"COUNT={count}")

    return ";".join(parts)


def parse_rrule(
    rrule_str: str,
    dtstart: datetime,
) -> rrule:
    """RRULE 문자열 파싱

    Args:
        rrule_str: RRULE 문자열
        dtstart: 시작 날짜/시간

    Returns:
        dateutil.rrule.rrule 객체
    """
    # RRULE: 접두사 추가 (없는 경우)
    if not rrule_str.startswith("RRULE:"):
        rrule_str = f"RRULE:{rrule_str}"

    return rrulestr(rrule_str, dtstart=dtstart)


def get_occurrences(
    rrule_str: str,
    dtstart: datetime,
    range_start: date,
    range_end: date,
    excluded_dates: Optional[set[date]] = None,
) -> list[date]:
    """반복 일정의 발생 날짜 목록 반환

    Args:
        rrule_str: RRULE 문자열
        dtstart: 일정 시작 날짜/시간
        range_start: 조회 시작일
        range_end: 조회 종료일
        excluded_dates: 제외할 날짜 목록 (예외 처리된 날짜)

    Returns:
        발생 날짜 목록
    """
    if not rrule_str:
        return []

    excluded = excluded_dates or set()

    try:
        rule = parse_rrule(rrule_str, dtstart)

        # 조회 범위 내의 발생 날짜 계산
        start_dt = datetime.combine(range_start, datetime.min.time())
        end_dt = datetime.combine(range_end, datetime.max.time())

        occurrences = []
        for dt in rule.between(start_dt, end_dt, inc=True):
            occurrence_date = dt.date()
            if occurrence_date not in excluded:
                occurrences.append(occurrence_date)

        return occurrences

    except Exception:
        # 잘못된 RRULE인 경우 빈 목록 반환
        return []


def get_next_occurrence(
    rrule_str: str,
    dtstart: datetime,
    after: date,
) -> Optional[date]:
    """다음 발생 날짜 반환

    Args:
        rrule_str: RRULE 문자열
        dtstart: 일정 시작 날짜/시간
        after: 이 날짜 이후의 발생일 찾기

    Returns:
        다음 발생 날짜 또는 None
    """
    if not rrule_str:
        return None

    try:
        rule = parse_rrule(rrule_str, dtstart)
        after_dt = datetime.combine(after, datetime.max.time())
        next_dt = rule.after(after_dt)

        if next_dt:
            return next_dt.date()
        return None

    except Exception:
        return None
