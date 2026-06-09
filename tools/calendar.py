"""Calendar and date manipulation tools."""
from __future__ import annotations

import calendar
import subprocess
from datetime import datetime, timedelta

from tools import tool


@tool(
    name="get_calendar",
    description="Show a calendar for the current month or a specific month.",
    parameters={
        "type": "object",
        "properties": {
            "month": {
                "type": "integer",
                "description": "Month number 1-12 (default: current month)",
            },
            "year": {
                "type": "integer",
                "description": "Year (default: current year)",
            },
        },
        "required": [],
    },
)
def get_calendar(month: int = 0, year: int = 0) -> str:
    now = datetime.now()
    month = month or now.month
    year = year or now.year

    if month < 1 or month > 12:
        return f"error: month must be 1-12"

    cal = calendar.TextCalendar(calendar.SUNDAY).formatmonth(year, month)
    month_name = calendar.month_name[month]

    is_current = (month == now.month and year == now.year)
    today_marker = f" (today is {now.strftime('%A, %B %d')})" if is_current else ""

    return f"{month_name} {year}{today_marker}\n{cal}"


@tool(
    name="date_difference",
    description="Calculate the difference between two dates in days, weeks, and months.",
    parameters={
        "type": "object",
        "properties": {
            "date1": {
                "type": "string",
                "description": "First date in YYYY-MM-DD format (or 'today')",
            },
            "date2": {
                "type": "string",
                "description": "Second date in YYYY-MM-DD format (or 'today')",
            },
        },
        "required": ["date1", "date2"],
    },
)
def date_difference(date1: str, date2: str) -> str:
    def parse_date(s: str) -> datetime:
        if s.lower() == "today":
            return datetime.now()
        return datetime.strptime(s, "%Y-%m-%d")

    try:
        d1 = parse_date(date1)
        d2 = parse_date(date2)
        delta = abs(d2 - d1)
        days = delta.days
        weeks = days // 7
        months = abs((d2.year - d1.year) * 12 + (d2.month - d1.month))

        return (
            f"Between {date1} and {date2}:\n"
            f"  Days: {days}\n"
            f"  Weeks: {weeks}\n"
            f"  Months: ~{months}"
        )
    except ValueError as e:
        return f"error: {e}. Use YYYY-MM-DD format or 'today'."


@tool(
    name="add_days",
    description="Add or subtract days from a date. Use to find future or past dates.",
    parameters={
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Starting date in YYYY-MM-DD format (or 'today')",
            },
            "days": {
                "type": "integer",
                "description": "Number of days to add (negative to subtract)",
            },
        },
        "required": ["date", "days"],
    },
)
def add_days(date: str, days: int) -> str:
    try:
        if date.lower() == "today":
            d = datetime.now()
        else:
            d = datetime.strptime(date, "%Y-%m-%d")

        result = d + timedelta(days=days)
        day_name = result.strftime("%A")

        direction = "after" if days >= 0 else "before"
        return f"{abs(days)} day(s) {direction} {date} is {result.strftime('%Y-%m-%d')} ({day_name})"
    except ValueError as e:
        return f"error: {e}"


@tool(
    name="day_of_week",
    description="Find out what day of the week a date falls on.",
    parameters={
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format",
            },
        },
        "required": ["date"],
    },
)
def day_of_week(date: str) -> str:
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
        return f"{date} is a {d.strftime('%A')}"
    except ValueError:
        return f"error: invalid date format. Use YYYY-MM-DD."


@tool(
    name="get_timezone_info",
    description="Get the current time in different timezones.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_timezone_info() -> str:
    from datetime import timezone, timedelta

    now = datetime.now()
    utc_now = datetime.now(timezone.utc)

    timezones = {
        "UTC": utc_now,
        "EST (New York)": utc_now.astimezone(timezone(timedelta(hours=-5))),
        "CST (Chicago)": utc_now.astimezone(timezone(timedelta(hours=-6))),
        "PST (LA)": utc_now.astimezone(timezone(timedelta(hours=-8))),
        "GMT (London)": utc_now.astimezone(timezone(timedelta(hours=0))),
        "CET (Paris)": utc_now.astimezone(timezone(timedelta(hours=1))),
        "IST (India)": utc_now.astimezone(timezone(timedelta(hours=5, minutes=30))),
        "JST (Tokyo)": utc_now.astimezone(timezone(timedelta(hours=9))),
        "AEST (Sydney)": utc_now.astimezone(timezone(timedelta(hours=10))),
    }

    lines = ["Current time worldwide:"]
    for name, tz_time in timezones.items():
        lines.append(f"  {name:20s} {tz_time.strftime('%I:%M %p')} ({tz_time.strftime('%A')})")

    return "\n".join(lines)
