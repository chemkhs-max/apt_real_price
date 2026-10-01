from pathlib import Path
from src.config import DAILY_SUMMARY_DB_PATH, get_gemini_api_key

def test_daily_summary_db_path():
    assert isinstance(DAILY_SUMMARY_DB_PATH, Path)
    assert DAILY_SUMMARY_DB_PATH.name == "daily_summaries.db"

def test_get_gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_123")
    assert get_gemini_api_key() == "test_key_123"
