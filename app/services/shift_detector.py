from collections import defaultdict
from datetime import date, timedelta
from ..models import PunchRecord, Shift, ShiftType


def detect_all_shifts(
    punches: list[PunchRecord],
    date_from: date,
    date_to: date,
) -> tuple[dict[str, list[Shift]], list[Shift]]:
    """Detect shifts for all employees from punch records.

    Returns:
        - shifts_by_employee: {employee_id: [Shift, ...]} with valid shifts
        - broken_shifts: list of broken (single-punch) shifts
    """
    by_employee = defaultdict(list)
    for p in punches:
        by_employee[p.employee_id].append(p)

    all_shifts = {}
    all_broken = []

    for emp_id, emp_punches in by_employee.items():
        shifts = _detect_employee_shifts(emp_id, emp_punches)
        valid = []
        broken = []
        for s in shifts:
            if s.attributed_date < date_from or s.attributed_date > date_to:
                continue
            if s.shift_type == ShiftType.BROKEN:
                broken.append(s)
            else:
                valid.append(s)
        if valid:
            all_shifts[emp_id] = valid
        all_broken.extend(broken)

    return all_shifts, all_broken


def _detect_employee_shifts(employee_id: str, punches: list[PunchRecord]) -> list[Shift]:
    """4-pass shift detection algorithm for a single employee.

    Priority order is critical:
    Pass 1: Day shifts FIRST (same-date pairs take priority to prevent
            afternoon punches from being stolen by night-shift matching)
    Pass 2: Night shifts (evening start 17:00-23:59 -> next day end 00:00-13:00)
    Pass 3: Post-midnight night shifts (00:00-04:00 -> same day 05:00-13:00)
    Pass 4: Remaining unmatched punches -> broken shifts
    """
    sorted_punches = sorted(punches, key=lambda p: p.punch_datetime)
    n = len(sorted_punches)
    used = set()
    shifts = []

    # PASS 1: Day shifts (morning start -> same day afternoon/evening end)
    # This runs FIRST so that same-date pairs like (06:00, 16:50) are correctly
    # identified as day shifts before the night pass can steal the 16:50 punch.
    for i in range(n):
        if i in used:
            continue
        p = sorted_punches[i]
        hour = p.punch_datetime.hour
        if not (4 <= hour <= 10):
            continue

        best_j = None
        for j in range(i + 1, n):
            if j in used:
                continue
            q = sorted_punches[j]
            if q.punch_date != p.punch_date:
                break
            if 14 <= q.punch_datetime.hour <= 20:
                best_j = j  # take the latest matching end on same date

        if best_j is not None:
            end = sorted_punches[best_j]
            hours = (end.punch_datetime - p.punch_datetime).total_seconds() / 3600
            # Reject implausibly long "day" shifts: a ~13h pairing of
            # a night-shift end (04:xx) with the next night-shift start (17:xx)
            # on the same calendar date must not be treated as a day shift.
            if hours > 12.5:
                continue
            shifts.append(Shift(
                employee_id=employee_id,
                shift_type=ShiftType.DAY,
                attributed_date=p.punch_date,
                start_punch=p.punch_datetime,
                end_punch=end.punch_datetime,
                hours=round(hours, 1),
            ))
            used.add(i)
            used.add(best_j)
            for k in range(i + 1, best_j):
                if k not in used and sorted_punches[k].punch_date == p.punch_date:
                    used.add(k)

    # PASS 2: Night shifts (evening start -> next morning end)
    # Window 15:00-23:59: safe because day shifts already claimed same-date pairs
    # in Pass 1, so remaining afternoon punches are genuine night shift starts.
    for i in range(n):
        if i in used:
            continue
        p = sorted_punches[i]
        hour = p.punch_datetime.hour
        if not (15 <= hour <= 23):
            continue

        next_date = p.punch_date + timedelta(days=1)
        best_j = None

        for j in range(i + 1, n):
            if j in used:
                continue
            q = sorted_punches[j]
            if q.punch_date > next_date:
                break
            if q.punch_date == next_date and q.punch_datetime.hour <= 13:
                best_j = j

        if best_j is not None:
            end = sorted_punches[best_j]
            hours = (end.punch_datetime - p.punch_datetime).total_seconds() / 3600
            shifts.append(Shift(
                employee_id=employee_id,
                shift_type=ShiftType.NIGHT,
                attributed_date=p.punch_date,
                start_punch=p.punch_datetime,
                end_punch=end.punch_datetime,
                hours=round(hours, 1),
            ))
            used.add(i)
            used.add(best_j)
            for k in range(i + 1, best_j):
                if k not in used:
                    mk = sorted_punches[k]
                    if mk.punch_date in (p.punch_date, next_date):
                        used.add(k)

    # PASS 3: Post-midnight night shifts (00:00-04:00 start -> same day 05:00-13:00 end)
    # Catches night shifts where both punches landed on the same calendar date
    # (e.g., employee arrived after midnight). Attributed to previous date.
    for i in range(n):
        if i in used:
            continue
        p = sorted_punches[i]
        hour = p.punch_datetime.hour
        if not (0 <= hour <= 4):
            continue

        best_j = None
        for j in range(i + 1, n):
            if j in used:
                continue
            q = sorted_punches[j]
            if q.punch_date != p.punch_date:
                break
            if 5 <= q.punch_datetime.hour <= 13:
                best_j = j

        if best_j is not None:
            end = sorted_punches[best_j]
            hours = (end.punch_datetime - p.punch_datetime).total_seconds() / 3600
            attr_date = p.punch_date - timedelta(days=1)
            shifts.append(Shift(
                employee_id=employee_id,
                shift_type=ShiftType.NIGHT,
                attributed_date=attr_date,
                start_punch=p.punch_datetime,
                end_punch=end.punch_datetime,
                hours=round(hours, 1),
            ))
            used.add(i)
            used.add(best_j)
            for k in range(i + 1, best_j):
                if k not in used and sorted_punches[k].punch_date == p.punch_date:
                    used.add(k)

    # PASS 4: Remaining unmatched punches -> broken shifts
    for i in range(n):
        if i in used:
            continue
        p = sorted_punches[i]
        attr_date = p.punch_date
        if 0 <= p.punch_datetime.hour <= 4:
            attr_date = p.punch_date - timedelta(days=1)
        shifts.append(Shift(
            employee_id=employee_id,
            shift_type=ShiftType.BROKEN,
            attributed_date=attr_date,
            start_punch=p.punch_datetime,
            end_punch=None,
            hours=0,
        ))

    return shifts
