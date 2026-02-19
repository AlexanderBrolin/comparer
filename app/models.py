from dataclasses import dataclass, field
from datetime import date, time, datetime
from typing import Optional
from enum import Enum


class ShiftType(Enum):
    DAY = "day"
    NIGHT = "night"
    BROKEN = "broken"


@dataclass
class PunchRecord:
    employee_id: str
    punch_date: date
    punch_time: time
    punch_datetime: datetime


@dataclass
class Shift:
    employee_id: str
    shift_type: ShiftType
    attributed_date: date
    start_punch: datetime
    end_punch: Optional[datetime]
    hours: float


@dataclass
class TabellEntry:
    employee_id: str
    name: str
    job_title: str
    company: str
    month: str
    daily_hours: dict  # day_number (int) -> hours (float)
    project: str = ''


@dataclass
class DayComparison:
    tabell_hours: float
    skud_hours: float
    diff: float
    broken: bool
    shift_type: Optional[str] = None


@dataclass
class ComparisonRow:
    employee_id: str
    name: str
    job_title: str
    days: dict  # date string -> DayComparison
