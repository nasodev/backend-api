"""반복 일정 유틸리티 테스트"""

from datetime import date, datetime

import pytest

from app.services.calendar.recurrence import (
    RecurrenceFrequency,
    Weekday,
    build_rrule,
    get_occurrences,
    get_next_occurrence,
)


class TestBuildRrule:
    """RRULE 생성 테스트"""

    def test_daily(self):
        """매일 반복"""
        rrule = build_rrule(RecurrenceFrequency.DAILY)
        assert rrule == "FREQ=DAILY;INTERVAL=1"

    def test_weekly(self):
        """매주 반복"""
        rrule = build_rrule(RecurrenceFrequency.WEEKLY)
        assert rrule == "FREQ=WEEKLY;INTERVAL=1"

    def test_weekly_with_days(self):
        """매주 월,수,금 반복"""
        rrule = build_rrule(
            RecurrenceFrequency.WEEKLY,
            weekdays=[Weekday.MO, Weekday.WE, Weekday.FR],
        )
        assert rrule == "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR"

    def test_biweekly(self):
        """격주 반복"""
        rrule = build_rrule(RecurrenceFrequency.WEEKLY, interval=2)
        assert rrule == "FREQ=WEEKLY;INTERVAL=2"

    def test_monthly(self):
        """매월 반복"""
        rrule = build_rrule(RecurrenceFrequency.MONTHLY)
        assert rrule == "FREQ=MONTHLY;INTERVAL=1"

    def test_yearly(self):
        """매년 반복"""
        rrule = build_rrule(RecurrenceFrequency.YEARLY)
        assert rrule == "FREQ=YEARLY;INTERVAL=1"

    def test_with_count(self):
        """반복 횟수 지정"""
        rrule = build_rrule(RecurrenceFrequency.DAILY, count=10)
        assert rrule == "FREQ=DAILY;INTERVAL=1;COUNT=10"

    def test_with_until(self):
        """반복 종료일 지정"""
        rrule = build_rrule(
            RecurrenceFrequency.DAILY,
            until=date(2024, 12, 31),
        )
        assert "FREQ=DAILY;INTERVAL=1;UNTIL=20241231" in rrule


class TestGetOccurrences:
    """반복 일정 발생 날짜 테스트"""

    def test_daily_occurrences(self):
        """매일 반복 발생 날짜"""
        occurrences = get_occurrences(
            rrule_str="FREQ=DAILY;INTERVAL=1",
            dtstart=datetime(2024, 1, 1, 10, 0),
            range_start=date(2024, 1, 1),
            range_end=date(2024, 1, 5),
        )
        assert len(occurrences) == 5
        assert occurrences[0] == date(2024, 1, 1)
        assert occurrences[-1] == date(2024, 1, 5)

    def test_weekly_occurrences(self):
        """매주 반복 발생 날짜"""
        occurrences = get_occurrences(
            rrule_str="FREQ=WEEKLY;INTERVAL=1",
            dtstart=datetime(2024, 1, 1, 10, 0),  # 월요일
            range_start=date(2024, 1, 1),
            range_end=date(2024, 1, 31),
        )
        # 1/1, 1/8, 1/15, 1/22, 1/29 (5개의 월요일)
        assert len(occurrences) == 5

    def test_weekly_specific_days(self):
        """매주 특정 요일 반복"""
        occurrences = get_occurrences(
            rrule_str="FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR",
            dtstart=datetime(2024, 1, 1, 10, 0),  # 월요일
            range_start=date(2024, 1, 1),
            range_end=date(2024, 1, 7),
        )
        # 1/1(월), 1/3(수), 1/5(금)
        assert len(occurrences) == 3
        assert date(2024, 1, 1) in occurrences  # 월
        assert date(2024, 1, 3) in occurrences  # 수
        assert date(2024, 1, 5) in occurrences  # 금

    def test_monthly_occurrences(self):
        """매월 반복 발생 날짜"""
        occurrences = get_occurrences(
            rrule_str="FREQ=MONTHLY;INTERVAL=1",
            dtstart=datetime(2024, 1, 15, 10, 0),
            range_start=date(2024, 1, 1),
            range_end=date(2024, 6, 30),
        )
        # 1/15, 2/15, 3/15, 4/15, 5/15, 6/15
        assert len(occurrences) == 6

    def test_yearly_occurrences(self):
        """매년 반복 발생 날짜"""
        occurrences = get_occurrences(
            rrule_str="FREQ=YEARLY;INTERVAL=1",
            dtstart=datetime(2024, 3, 15, 10, 0),
            range_start=date(2024, 1, 1),
            range_end=date(2026, 12, 31),
        )
        # 2024/3/15, 2025/3/15, 2026/3/15
        assert len(occurrences) == 3

    def test_with_excluded_dates(self):
        """예외 날짜 제외"""
        excluded = {date(2024, 1, 2), date(2024, 1, 4)}
        occurrences = get_occurrences(
            rrule_str="FREQ=DAILY;INTERVAL=1",
            dtstart=datetime(2024, 1, 1, 10, 0),
            range_start=date(2024, 1, 1),
            range_end=date(2024, 1, 5),
            excluded_dates=excluded,
        )
        # 1, 2, 3, 4, 5 중 2, 4 제외 = 1, 3, 5
        assert len(occurrences) == 3
        assert date(2024, 1, 2) not in occurrences
        assert date(2024, 1, 4) not in occurrences

    def test_invalid_rrule(self):
        """잘못된 RRULE"""
        occurrences = get_occurrences(
            rrule_str="INVALID_RRULE",
            dtstart=datetime(2024, 1, 1, 10, 0),
            range_start=date(2024, 1, 1),
            range_end=date(2024, 1, 5),
        )
        assert occurrences == []

    def test_empty_rrule(self):
        """빈 RRULE"""
        occurrences = get_occurrences(
            rrule_str="",
            dtstart=datetime(2024, 1, 1, 10, 0),
            range_start=date(2024, 1, 1),
            range_end=date(2024, 1, 5),
        )
        assert occurrences == []


class TestGetNextOccurrence:
    """다음 발생 날짜 테스트"""

    def test_next_daily(self):
        """매일 반복의 다음 발생일"""
        next_date = get_next_occurrence(
            rrule_str="FREQ=DAILY;INTERVAL=1",
            dtstart=datetime(2024, 1, 1, 10, 0),
            after=date(2024, 1, 5),
        )
        assert next_date == date(2024, 1, 6)

    def test_next_weekly(self):
        """매주 반복의 다음 발생일"""
        next_date = get_next_occurrence(
            rrule_str="FREQ=WEEKLY;INTERVAL=1",
            dtstart=datetime(2024, 1, 1, 10, 0),  # 월요일
            after=date(2024, 1, 1),
        )
        assert next_date == date(2024, 1, 8)  # 다음 월요일

    def test_invalid_rrule(self):
        """잘못된 RRULE"""
        next_date = get_next_occurrence(
            rrule_str="INVALID",
            dtstart=datetime(2024, 1, 1, 10, 0),
            after=date(2024, 1, 1),
        )
        assert next_date is None
