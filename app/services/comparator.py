from collections import defaultdict
from datetime import date, timedelta
from ..models import Shift, ShiftType, TabellEntry

MONTH_MAP = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12,
}


def compare(
    shifts_by_employee: dict[str, list[Shift]],
    broken_shifts: list[Shift],
    tabell_entries: list[TabellEntry],
    date_from: date,
    date_to: date,
) -> dict:
    """Compare SKUD shifts with tabell data and produce a comparison result.

    Returns a dict ready for JSON serialization.
    """
    # Build date list
    dates = []
    current = date_from
    while current <= date_to:
        dates.append(current)
        current += timedelta(days=1)

    # Index tabell entries by employee_id
    # An employee may have entries for multiple months
    tabell_by_emp = defaultdict(list)
    for entry in tabell_entries:
        tabell_by_emp[entry.employee_id].append(entry)

    # Build SKUD hours index: {employee_id: {date: total_hours}}
    skud_hours = defaultdict(lambda: defaultdict(float))
    skud_shift_types = defaultdict(lambda: defaultdict(str))
    for emp_id, shifts in shifts_by_employee.items():
        for s in shifts:
            skud_hours[emp_id][s.attributed_date] += s.hours
            skud_shift_types[emp_id][s.attributed_date] = s.shift_type.value

    # Build broken shifts index: {employee_id: {date: True}}
    broken_dates = defaultdict(lambda: defaultdict(bool))
    for s in broken_shifts:
        broken_dates[s.employee_id][s.attributed_date] = True

    # All employee IDs from tabell (primary source)
    all_emp_ids = sorted(tabell_by_emp.keys())

    # Build comparison rows
    comparison = []
    for emp_id in all_emp_ids:
        entries = tabell_by_emp[emp_id]
        # Merge all entries for this employee (may span multiple months)
        name = entries[0].name
        job_title = entries[0].job_title

        days_data = {}
        for d in dates:
            # Find tabell hours for this date
            tabell_h = _get_tabell_hours(entries, d)
            # Get SKUD hours
            skud_h = skud_hours.get(emp_id, {}).get(d, 0.0)
            shift_type = skud_shift_types.get(emp_id, {}).get(d, None)
            is_broken = broken_dates.get(emp_id, {}).get(d, False)

            diff = round(tabell_h - skud_h, 1)

            days_data[d.isoformat()] = {
                'tabell': tabell_h,
                'skud': round(skud_h, 1),
                'diff': diff,
                'broken': is_broken,
                'shift_type': shift_type,
            }

        comparison.append({
            'employee_id': emp_id,
            'name': name,
            'job_title': job_title,
            'days': days_data,
        })

    # Format broken shifts for output
    broken_out = []
    for s in sorted(broken_shifts, key=lambda x: (x.employee_id, x.attributed_date)):
        # Find name from tabell
        name = ''
        if s.employee_id in tabell_by_emp:
            name = tabell_by_emp[s.employee_id][0].name
        broken_out.append({
            'employee_id': s.employee_id,
            'name': name,
            'attributed_date': s.attributed_date.isoformat(),
            'punch_time': s.start_punch.strftime('%Y-%m-%d %H:%M:%S'),
            'estimated_type': _estimate_shift_type(s.start_punch.hour),
        })

    # Summary
    matched = sum(1 for emp_id in all_emp_ids if emp_id in skud_hours)
    summary = {
        'total_employees_tabell': len(all_emp_ids),
        'total_employees_skud': len(shifts_by_employee) + len(set(s.employee_id for s in broken_shifts)),
        'matched_employees': matched,
        'broken_count': len(broken_shifts),
        'date_range': [date_from.isoformat(), date_to.isoformat()],
    }

    return {
        'comparison': comparison,
        'broken_shifts': broken_out,
        'summary': summary,
    }


def _get_tabell_hours(entries: list[TabellEntry], d: date) -> float:
    """Get hours from tabell entries for a specific date."""
    for entry in entries:
        month_num = MONTH_MAP.get(entry.month, 0)
        if month_num == d.month:
            return entry.daily_hours.get(d.day, 0.0)
    return 0.0


def _estimate_shift_type(hour: int) -> str:
    """Estimate what type of shift a single punch might belong to."""
    if 4 <= hour <= 10:
        return 'day_start?'
    elif 14 <= hour <= 20:
        return 'day_end?'
    elif 15 <= hour <= 23:
        return 'night_start?'
    elif 0 <= hour <= 4:
        return 'night_end?'
    else:
        return 'unknown'
