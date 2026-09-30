from pathlib import Path
import json
import pytest

def test_paths_defined():
    from src.config import DATA_DIR, LAWD_CD_PATH, DATA_FILE_PATH, METADATA_PATH, get_api_key
    assert DATA_DIR.name == "data"
    assert DATA_FILE_PATH.name == "recent_7days.parquet"
    assert METADATA_PATH.name == "metadata.json"
    assert LAWD_CD_PATH.exists()

def test_lawd_cd_format():
    from src.config import LAWD_CD_PATH
    with open(LAWD_CD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) >= 200
    first = data[0]
    assert "code" in first and len(first["code"]) == 5
    assert "sido" in first
    assert "sigungu" in first
