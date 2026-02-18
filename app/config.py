import os
import re
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    LOGIN_USERNAME = os.getenv('LOGIN_USERNAME', 'admin')
    LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD', 'admin')
    GOOGLE_SHEET_URL = os.getenv('GOOGLE_SHEET_URL', '')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')

    @staticmethod
    def parse_sheet_url(url):
        """Extract spreadsheet_id and gid from Google Sheets URL."""
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        gid_match = re.search(r'gid=(\d+)', url)
        spreadsheet_id = sheet_id_match.group(1) if sheet_id_match else None
        gid = gid_match.group(1) if gid_match else None
        return spreadsheet_id, gid
