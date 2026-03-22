import os

from langchain_google_community import CalendarToolkit
from langchain_google_community.calendar.utils import (
    build_calendar_service,
    get_google_credentials,
)

# ═══════════════════════════════════════════════════════════════
# HELPER — Tìm file credentials/token
# ═══════════════════════════════════════════════════════════════

_DEEPAGENTS_DIR = os.path.dirname(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.dirname(_DEEPAGENTS_DIR)

# Tìm credentials.json và token.json (ưu tiên DeepAgents/, fallback project root)
_CREDENTIALS_FILE = os.path.join(_DEEPAGENTS_DIR, "credentials.json")
if not os.path.exists(_CREDENTIALS_FILE):
    _CREDENTIALS_FILE = os.path.join(_PROJECT_ROOT, "credentials.json")

_TOKEN_FILE = os.path.join(_DEEPAGENTS_DIR, "token.json")
if not os.path.exists(_TOKEN_FILE):
    _TOKEN_FILE = os.path.join(_PROJECT_ROOT, "token.json")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


# ═══════════════════════════════════════════════════════════════
# CALENDAR TOOLKIT — Khởi tạo và lấy danh sách tools
# ═══════════════════════════════════════════════════════════════

def _build_calendar_toolkit() -> CalendarToolkit:
    """Tạo CalendarToolkit với xác thực OAuth2 từ credentials.json/token.json."""
    credentials = get_google_credentials(
        token_file=_TOKEN_FILE,
        scopes=SCOPES,
        client_secrets_file=_CREDENTIALS_FILE,
    )
    api_resource = build_calendar_service(credentials=credentials)
    return CalendarToolkit(api_resource=api_resource)


def get_calendar_tools() -> list:
    """Trả về danh sách các LangChain tools cho Google Calendar."""
    toolkit = _build_calendar_toolkit()
    return toolkit.get_tools()
