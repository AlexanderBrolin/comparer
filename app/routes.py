import os
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, jsonify, current_app
from .auth import login_required
from .services.skud_parser import parse_skud_xlsx
from .services.sheets_reader import fetch_tabell
from .services.shift_detector import detect_all_shifts
from .services.comparator import compare
from .config import Config

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@main_bp.route('/api/compare', methods=['POST'])
@login_required
def api_compare():
    if 'xlsx_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['xlsx_file']
    if not file.filename or not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'File must be .xlsx'}), 400

    date_from_str = request.form.get('date_from')
    date_to_str = request.form.get('date_to')

    if not date_from_str or not date_to_str:
        return jsonify({'error': 'Date range is required'}), 400

    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if date_from > date_to:
        return jsonify({'error': 'Start date must be before end date'}), 400

    # Save uploaded file
    filename = f"{uuid.uuid4().hex}.xlsx"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # 1. Parse SKUD XLSX
        punches = parse_skud_xlsx(filepath, date_from, date_to)

        # 2. Fetch tabell from Google Sheets
        sheet_url = current_app.config['GOOGLE_SHEET_URL']
        spreadsheet_id, gid = Config.parse_sheet_url(sheet_url)
        tabell_entries = fetch_tabell(spreadsheet_id, gid, date_from, date_to)

        # 3. Detect shifts
        shifts_by_employee, broken_shifts = detect_all_shifts(punches, date_from, date_to)

        # 4. Compare
        result = compare(shifts_by_employee, broken_shifts, tabell_entries, date_from, date_to)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
