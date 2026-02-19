import csv
import io
import re
import urllib.request
from datetime import date
from ..models import TabellEntry

# Column indices (verified from actual CSV export)
COL_EMPLOYEE_ID = 0   # A: Employee ID with "ТН" prefix
COL_NAME = 1           # B: Full Name
COL_JOB_TITLE = 2     # C: Job title
COL_COMPANY = 3        # D: Company
COL_DAYS_START = 10    # K: Day 1
COL_DAYS_END = 40      # AO: Day 31
COL_MONTH = 118        # DO: Month name

HEADER_ROW_IDX = 1     # Row index in CSV (0-based), contains day numbers
DATA_START_ROW = 2     # First data row

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
}


def parse_hours(cell_value: str) -> float:
    """Parse cell value to hours. Numbers and numbers with brackets are valid.
    Everything else (letter codes like DOF, ALP, TER, etc.) returns 0."""
    val = cell_value.strip()
    if not val or val == '-':
        return 0.0
    # Strip trailing bracket: "10(" -> "10"
    val = val.rstrip('(')
    # Replace comma decimal separator
    val = val.replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return 0.0


def _detect_project_col(rows: list) -> int | None:
    """Find the 'Project' column index.

    Row 0 contains merged-cell artifacts ('Col1', 'Col2', ...) from Google Sheets.
    Row 1 contains the real column headers — search there.

    Uses exact match first (header == "project"), then falls back to a header
    that IS exactly 'project' after stripping newlines and spaces. Many other
    headers contain the word "project" as part of a longer phrase — those are
    excluded by requiring an exact match.
    """
    if len(rows) < 2:
        return None
    for i, cell in enumerate(rows[1]):
        if cell and str(cell).strip().lower().replace('\n', ' ').strip() == 'project':
            return i
    return None


def _load_sheet(spreadsheet_id: str, gid: str) -> list[list[str]]:
    url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read().decode('utf-8')
    return list(csv.reader(io.StringIO(data)))


def fetch_projects(spreadsheet_id: str, gid: str) -> list[str]:
    """Return sorted list of unique project names from the sheet."""
    rows = _load_sheet(spreadsheet_id, gid)
    project_col = _detect_project_col(rows)
    if project_col is None:
        return []
    projects: set[str] = set()
    for row in rows[DATA_START_ROW:]:
        if len(row) > project_col:
            val = row[project_col].strip()
            if val:
                projects.add(val)
    return sorted(projects)


def fetch_tabell(spreadsheet_id: str, gid: str, date_from: date, date_to: date) -> list[TabellEntry]:
    """Fetch tabell data from Google Sheets via CSV export.

    Returns list of TabellEntry objects filtered to months covered by the date range.
    """
    rows = _load_sheet(spreadsheet_id, gid)
    project_col = _detect_project_col(rows)

    if len(rows) < DATA_START_ROW + 1:
        return []

    # Determine which months we need
    needed_months = set()
    current = date_from
    while current <= date_to:
        needed_months.add(current.month)
        # Move to next month
        if current.month == 12:
            break
        next_month_first = date(current.year, current.month + 1, 1)
        if next_month_first > date_to:
            break
        current = next_month_first
    # Also add the month of date_from and date_to explicitly
    needed_months.add(date_from.month)
    needed_months.add(date_to.month)

    entries = []
    for row in rows[DATA_START_ROW:]:
        if len(row) <= COL_MONTH:
            continue

        # Parse employee ID - strip ТН prefix
        raw_id = row[COL_EMPLOYEE_ID].strip()
        if not raw_id:
            continue
        employee_id = re.sub(r'^ТН', '', raw_id, flags=re.IGNORECASE).strip()
        if not employee_id:
            continue

        # Parse month
        month_str = row[COL_MONTH].strip().lower()
        month_num = MONTH_MAP.get(month_str)
        if month_num is None or month_num not in needed_months:
            continue

        name = row[COL_NAME].strip() if len(row) > COL_NAME else ''
        job_title = row[COL_JOB_TITLE].strip() if len(row) > COL_JOB_TITLE else ''
        company = row[COL_COMPANY].strip() if len(row) > COL_COMPANY else ''
        project = row[project_col].strip() if project_col is not None and len(row) > project_col else ''

        # Parse daily hours (columns 10-40 = days 1-31)
        daily_hours = {}
        for col_idx in range(COL_DAYS_START, min(COL_DAYS_END + 1, len(row))):
            day_num = col_idx - COL_DAYS_START + 1  # 1-based day number
            cell_val = row[col_idx].strip() if row[col_idx] else ''
            daily_hours[day_num] = parse_hours(cell_val)

        entries.append(TabellEntry(
            employee_id=employee_id,
            name=name,
            job_title=job_title,
            company=company,
            month=month_str.capitalize(),
            daily_hours=daily_hours,
            project=project,
        ))

    return entries
