import pytest
from src.db.summary_repository import DailySummaryRepository

@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_summaries.db"
    return DailySummaryRepository(db_path=db_file)

def test_save_and_get_summary(repo):
    # 초기 상태 조회 시 None 반환
    assert repo.get_summary("2026-09-30") is None
    
    # 신규 요약 저장
    repo.save_summary(
        deal_date="2026-09-30",
        summary_content="## 마켓 총평\n거래 활발",
        model_name="gemini-2.5-flash",
        deal_count=150
    )
    
    record = repo.get_summary("2026-09-30")
    assert record is not None
    assert record["deal_date"] == "2026-09-30"
    assert record["summary_content"] == "## 마켓 총평\n거래 활발"
    assert record["model_name"] == "gemini-2.5-flash"
    assert record["deal_count"] == 150
    assert "created_at" in record
    assert "updated_at" in record

def test_upsert_summary(repo):
    repo.save_summary("2026-09-30", "초기 요약", "gemini-2.5-flash", 100)
    repo.save_summary("2026-09-30", "수정된 요약", "gemini-2.5-flash", 120)
    
    record = repo.get_summary("2026-09-30")
    assert record["summary_content"] == "수정된 요약"
    assert record["deal_count"] == 120

def test_delete_summary(repo):
    repo.save_summary("2026-09-30", "요약 내용", "gemini-2.5-flash", 100)
    assert repo.get_summary("2026-09-30") is not None
    
    deleted = repo.delete_summary("2026-09-30")
    assert deleted is True
    assert repo.get_summary("2026-09-30") is None
