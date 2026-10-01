# 일자별 거래내역 조회 & Gemini 부동산 애널리스트 요약 시스템 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 수집된 아파트 실거래 데이터(`data/recent_7days.parquet`)를 기반으로 일자별 상세 거래 조회 및 Gemini 2.5 Flash 기반 부동산 애널리스트 리포트 자동 생성/SQLite 영구 캐싱 시스템을 구축합니다.

**Architecture:** SQLite 기반의 `DailySummaryRepository`로 일자별 요약을 캐싱(최초 1회 생성 후 재사용)하고, `GeminiService`에서 당일 실거래 통계표를 바탕으로 전문 마켓 리포트를 생성하며, Streamlit 멀티페이지(`pages/1_📅_일자별_거래분석.py`)에서 직관적인 UI로 제공합니다.

**Tech Stack:** Python 3.11, Streamlit 1.38+, `google-genai`, SQLite3, Pandas, PyArrow, Pytest

**Spec:** [docs/superpowers/specs/2026-10-01-daily-summary-gemini-design.md](file:///c:/Users/chemk/OneDrive/Desktop/교육과정%20크롤링/apt_real_price/docs/superpowers/specs/2026-10-01-daily-summary-gemini-design.md)

## Global Constraints

- 가상환경 관리는 오직 `uv`만 사용 (`uv add`, `uv run` 등).
- 경로는 특별한 경우를 제외하고 프로젝트 루트 기준 상대경로 사용.
- Gemini 모델은 `gemini-2.5-flash` 사용.
- API 키는 `.env`의 `GEMINI_API_KEY` 환경변수 사용 (미설정 시 크래시 없이 경고 UI 표출).
- 데이터베이스는 SQLite 파일 `data/daily_summaries.db` 사용.

## Review Focus

- API 키 미설정 또는 잘못된 키 입력 시 앱이 비정상 종료(White Screen)되지 않고 친절한 에러 UI 카드를 표시하는지.
- SQLite DB 파일이 없는 상태에서 최초 호출 시 자동으로 테이블(`daily_market_summaries`)이 생성되는지.
- 이미 DB에 저장된 일자 조회 시 외부 Gemini API를 호출하지 않고 DB 내용을 즉각 반환하는지.
- 특정 일자에 거래 건수가 0건이거나 데이터가 부족할 때 적절한 Empty State 안내가 나오는지.
- 사용자가 `🔄 요약 다시 생성` 버튼을 눌렀을 때 DB 내용이 신규 리포트로 올바르게 UPSERT 되는지.

---

### Task 1: 의존성 추가 (`google-genai`) 및 `src/config.py` 설정 확장

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `src.config.DAILY_SUMMARY_DB_PATH: Path`, `src.config.get_gemini_api_key() -> str`

- [ ] **Step 1: Write failing test for config additions**

```python
# tests/test_config.py
from pathlib import Path
from src.config import DAILY_SUMMARY_DB_PATH, get_gemini_api_key

def test_daily_summary_db_path():
    assert isinstance(DAILY_SUMMARY_DB_PATH, Path)
    assert DAILY_SUMMARY_DB_PATH.name == "daily_summaries.db"

def test_get_gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_123")
    assert get_gemini_api_key() == "test_key_123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`  
Expected: FAIL (ImportError or AttributeError for `DAILY_SUMMARY_DB_PATH`, `get_gemini_api_key`)

- [ ] **Step 3: Add `google-genai` dependency and update `src/config.py`**

Run: `uv add google-genai`  
Update `src/config.py` to define `DAILY_SUMMARY_DB_PATH = DATA_DIR / "daily_summaries.db"` and `get_gemini_api_key() -> str`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/config.py tests/test_config.py
git commit -m "feat: add google-genai dependency and config for gemini/sqlite"
```

---

### Task 2: SQLite 영구 저장소 (`src/db/summary_repository.py`) 구현 및 단위 테스트

**Files:**
- Create: `src/db/__init__.py`
- Create: `src/db/summary_repository.py`
- Create: `tests/test_summary_repository.py`

**Interfaces:**
- Consumes: `src.config.DAILY_SUMMARY_DB_PATH`
- Produces: `class DailySummaryRepository`:
  - `__init__(db_path: Path | str | None = None)`
  - `get_summary(deal_date: str) -> dict | None`
  - `save_summary(deal_date: str, summary_content: str, model_name: str, deal_count: int) -> None`
  - `delete_summary(deal_date: str) -> bool`

- [ ] **Step 1: Write failing tests for SQLite CRUD operations**

```python
# tests/test_summary_repository.py
import pytest
from src.db.summary_repository import DailySummaryRepository

@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_summaries.db"
    return DailySummaryRepository(db_path=db_file)

def test_save_and_get_summary(repo):
    # 초기 상태 조회
    assert repo.get_summary("2026-09-30") is None
    
    # 신규 저장
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

def test_upsert_summary(repo):
    repo.save_summary("2026-09-30", "초기 요약", "gemini-2.5-flash", 100)
    repo.save_summary("2026-09-30", "수정된 요약", "gemini-2.5-flash", 120)
    
    record = repo.get_summary("2026-09-30")
    assert record["summary_content"] == "수정된 요약"
    assert record["deal_count"] == 120
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_summary_repository.py -v`  
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `DailySummaryRepository` in `src/db/summary_repository.py`**

Implement connection handling, automatic table creation (`CREATE TABLE IF NOT EXISTS daily_market_summaries`), and `INSERT INTO ... ON CONFLICT(deal_date) DO UPDATE` UPSERT logic with context managers.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_summary_repository.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/db/ tests/test_summary_repository.py
git commit -m "feat: implement DailySummaryRepository with SQLite persistence"
```

---

### Task 3: 통계 요약 가공 및 Gemini 서비스 (`src/services/gemini_service.py`) 구현

**Files:**
- Create: `src/services/__init__.py`
- Create: `src/services/gemini_service.py`
- Create: `tests/test_gemini_service.py`

**Interfaces:**
- Consumes: `src.config.get_gemini_api_key`
- Produces:
  - `build_daily_stats_summary(daily_df: pd.DataFrame, deal_date: str) -> str`
  - `generate_analyst_report(stats_summary: str, api_key: str | None = None, model: str = "gemini-2.5-flash") -> str`

- [ ] **Step 1: Write failing tests for stats summary and mock report generation**

```python
# tests/test_gemini_service.py
import pandas as pd
import pytest
from src.services.gemini_service import build_daily_stats_summary, generate_analyst_report

def test_build_daily_stats_summary_empty():
    df = pd.DataFrame()
    stats = build_daily_stats_summary(df, "2026-09-30")
    assert "거래 내역이 없습니다" in stats

def test_build_daily_stats_summary_with_data():
    data = [
        {"deal_date": "2026-09-30", "sido": "서울특별시", "sigungu": "강남구", "dong": "압구정동", "apt_name": "현대", "area": 84.0, "pyeong": 25.4, "floor": 10, "price_manwon": 450000, "price_eok": 45.0},
        {"deal_date": "2026-09-30", "sido": "경기도", "sigungu": "성남시 분당구", "dong": "서현동", "apt_name": "시범한양", "area": 59.0, "pyeong": 17.8, "floor": 5, "price_manwon": 120000, "price_eok": 12.0}
    ]
    df = pd.DataFrame(data)
    stats = build_daily_stats_summary(df, "2026-09-30")
    assert "총 거래 건수: 2건" in stats
    assert "현대" in stats
    assert "서울특별시" in stats

def test_generate_analyst_report_no_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        generate_analyst_report("샘플 통계", api_key="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_gemini_service.py -v`  
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `gemini_service.py`**

Implement `build_daily_stats_summary` (calculating count, avg price, top 3 highest deals, top regions, area breakdown) and `generate_analyst_report` using `google.genai.Client` and `gemini-2.5-flash` with the real estate analyst system prompt.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_gemini_service.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/ tests/test_gemini_service.py
git commit -m "feat: implement gemini_service for stats summary and analyst report"
```

---

### Task 4: Streamlit 일자별 상세 분석 및 AI 리포트 페이지 (`pages/1_📅_일자별_거래분석.py`) 구현

**Files:**
- Create: `pages/1_📅_일자별_거래분석.py`

**Interfaces:**
- Consumes:
  - `src.config.DATA_FILE_PATH`, `src.config.get_gemini_api_key`
  - `src.db.summary_repository.DailySummaryRepository`
  - `src.services.gemini_service.build_daily_stats_summary`, `generate_analyst_report`

- [ ] **Step 1: Implement `pages/1_📅_일자별_거래분석.py`**

1. Page config 설정 (제목, 아이콘, 와이드 레이아웃).
2. `DATA_FILE_PATH`에서 데이터 로드 (없을 시 Empty State 가이드 표출).
3. 고유 거래 일자(`deal_date`) 목록을 최신순으로 추출하여 `st.selectbox` 제공 (예: `2026-09-30 (185건)`).
4. 당일 4대 메트릭 요약 카드 (거래량, 평균가, 최고가, 최고 거래 단지).
5. **AI 부동산 애널리스트 리포트 카드 영역**:
   - `repo.get_summary(deal_date)`로 SQLite 조회.
   - 이미 요약이 있으면: `st.info("💾 저장된 분석 리포트 ...")` 배지와 함께 마크다운 렌더링.
   - 요약이 없으면: `st.spinner()`로 `generate_analyst_report()` 자동 호출 후 `repo.save_summary()`로 영구 저장.
   - 우측 `🔄 요약 다시 생성` 버튼: 클릭 시 강제 재호출 및 DB UPSERT.
   - `GEMINI_API_KEY` 누락 시: 경고 카드 및 입력 안내 가이드 표출.
6. **당일 실거래 상세 내역 테이블**:
   - 지역/단지명 필터 및 컬럼 정렬, CSV 다운로드 버튼 제공.

- [ ] **Step 2: Syntax and Import validation**

Run: `uv run python -m py_compile pages/1_📅_일자별_거래분석.py`  
Expected: No syntax errors.

- [ ] **Step 3: Commit**

```bash
git add pages/1_📅_일자별_거래분석.py
git commit -m "feat: add daily transaction analysis and AI report Streamlit page"
```

---

### Task 5: 전체 통합 검증 및 E2E 테스트

**Files:**
- Test: All tests in `tests/`
- Verification: Running Streamlit application

- [ ] **Step 1: Run complete test suite**

Run: `uv run pytest -v`  
Expected: All tests pass.

- [ ] **Step 2: Verify Streamlit multipage navigation and caching**

Run: Test loading `pages/1_📅_일자별_거래분석.py` via headless streamlit test or script validation.  
Verify that selecting a date loads from DB instantly if present, or requests Gemini API when requested.

- [ ] **Step 3: Update documentation and README.md**

Update `README.md` to document the new Daily Analysis page, SQLite DB, and Gemini API setup.

- [ ] **Step 4: Commit and push**

```bash
git add README.md
git commit -m "docs: update README with daily analysis page and Gemini integration"
```
