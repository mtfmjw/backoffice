from datetime import date, time, timedelta

from django.utils.timezone import datetime, is_naive, localtime, make_aware
from django.utils.translation import gettext_lazy as _


def convert2localtime(original_datetime: datetime) -> datetime:
    """Convert a naive datetime to an aware datetime in the local timezone."""
    if original_datetime is None:
        return None
    if is_naive(original_datetime):
        return make_aware(original_datetime)
    return localtime(original_datetime)


def convert2str(original_datetime: datetime, format: str = "%Y/%m/%d %H:%M:%S") -> str:
    """Convert a datetime to a string in the specified format."""
    if original_datetime is None:
        return "-"
    return convert2localtime(original_datetime).strftime(format)


def convert2datetime(base_date: date, time: time) -> datetime:
    """Convert a date and time to a timezone-aware datetime object."""
    if base_date is None or time is None:
        return None

    return make_aware(datetime.combine(base_date, time))


def convert2duration(base_date: date, start_time: time, end_time: time) -> tuple[datetime, datetime]:
    """Convert a date and start/end times to a tuple of timezone-aware datetime objects."""
    if start_time is None or end_time is None:
        return None, None

    start_datetime = convert2datetime(base_date, start_time)
    end_datetime = convert2datetime(base_date, end_time)
    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)
    return start_datetime, end_datetime


def duration2minutes(duration: tuple[datetime, datetime]) -> int:
    """Return the duration in minutes, supporting overnight shifts."""
    start_time, end_time = duration
    if start_time and end_time:
        # If end_time is earlier than start_time, assume it crossed midnight and add 1 day
        if start_time > end_time:
            end_time += timedelta(days=1)

        return int((end_time - start_time).total_seconds() // 60)
    return 0


def duration2str(duration: tuple[time, time]) -> str:
    """Show duration in HH:MM - HH:MM format."""
    start_time, end_time = duration
    if start_time and end_time:
        return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
    return ""


def get_overlap_duration(duration1: tuple[datetime, datetime], duration2: tuple[datetime, datetime]) -> tuple[datetime, datetime]:
    """Return the overlapping duration between two time periods."""
    p1_start, p1_end = duration1
    p2_start, p2_end = duration2

    if p1_start is None or p1_end is None or p2_start is None or p2_end is None:
        return None, None

    # Calculate the overlapping duration
    overlap_start = max(p1_start, p2_start)
    overlap_end = min(p1_end, p2_end)

    if overlap_start < overlap_end:
        return overlap_start, overlap_end
    return None, None


def get_overlap_minutes(duration1: tuple[datetime, datetime], duration2: tuple[datetime, datetime]) -> int:
    """Return the overlapping duration in minutes."""
    overlap_start, overlap_end = get_overlap_duration(duration1, duration2)

    if overlap_start and overlap_end:
        return max(int((overlap_end - overlap_start).total_seconds() // 60), 0)
    return 0


def minutes2str(minutes: int) -> str:
    """Return the duration in HH:MM format."""
    return f"{int(minutes // 60):02d}:{int(minutes % 60):02d}" if minutes else "-"


def minutes2str_ja(minutes: int) -> str:
    """Return the duration in Japanese HH時間MM分 format."""
    return f"{int(minutes // 60):02d}時間{int(minutes % 60):02d}分" if minutes else "-"
