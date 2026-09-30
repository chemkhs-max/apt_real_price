# 전국 아파트 매매 실거래가 롤링 7일 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 국토교통부 아파트 매매 실거래가 OpenAPI(15126469)를 연동하여 최근 7일 롤링 데이터를 수집·가공하고, GitHub Actions 수동 배치 및 Streamlit Community Cloud 기반 무료 웹 대시보드를 구축한다.

**Architecture:** 전국 ~250개 시군구 코드를 기반으로 월초 경계값을 자동 처리하는 멀티스레딩 고속 수집기를 구현하고, 정제된 7일간의 데이터를 Parquet 단일 파일로 저장한다. GitHub Actions로 데이터 수동 수집 및 자동 커밋을 지원하며, Streamlit을 통해 다차원 필터링, 핵심 KPI 메트릭, 4개 탭(트렌드/TOP랭킹/지도/상세테이블) 시각화를 제공한다.

**Tech Stack:** Python 3.11+, uv (패키지/가상환경 관리), Streamlit, Pandas, PyArrow, Requests, Tenacity, Plotly, Pydeck, Pytest

**Spec:** [docs/superpowers/specs/2026-09-30-apt-real-price-dashboard-design.md](file:///c:/Users/chemk/OneDrive/Desktop/교육과정%20크롤링/apt_real_price/docs/superpowers/specs/2026-09-30-apt-real-price-dashboard-design.md)

## Global Constraints

- Python 가상환경 및 패키지 실행은 반드시 `uv`만을 사용한다 (`uv sync`, `uv run python`, `uv run pytest`).
- 프로젝트 내부 파일 I/O 및 모듈 참조는 모두 상대경로(`data/`, `src/`)를 사용한다.
- 데이터 저장 파일은 롤링 7일 단일 파일(`data/recent_7days.parquet`) 및 메타데이터(`data/metadata.json`)로 유지한다.
- 공공데이터포털 API 키는 코드에 직접 하드코딩하지 않고 환경변수(`DATA_GO_KR_API_KEY`)를 통해 주입받는다.
- TDD 원칙: 모든 기능 모듈(전처리, 수집기 파서, 유틸 등)은 실패하는 테스트를 먼저 작성하고 최소 구현으로 통과시킨다.

## Review Focus

1. **월초(1~6일) 실행 시 7일 범위가 전월에 걸치는 경우**: 당월과 전월 2개 연월 데이터를 모두 조회하여 병합 후 정확한 7일 범위를 슬라이싱하는지 검증.
2. **공공데이터포털 API 금액 포맷 예외**: 공백이나 콤마(`"   15,000 "`, `"120,000"`)가 포함된 거래금액 문자열이 정수 및 실수(억원)로 결측치 없이 정제되는지 검증.
3. **특정 시군구 거래 0건 또는 일시적 API 오류 발생**: 전체 파이프라인이 중단되지 않고 건너뛰거나 재시도하여 정상 수집된 지역의 데이터를 보존하는지 검증.
4. **전용면적 0 또는 비정상 데이터**: 평형 환산 시 0으로 나누기 오류(ZeroDivisionError) 방지 및 결측치 안전 처리 검증.
5. **최초 실행 시 `recent_7days.parquet` 파일 부재**: 대시보드(`app.py`)가 오류로 크래시되지 않고 데이터 수집 안내 및 샘플 가이드를 사용자에게 보여주는지 검증.

---

### Task 1: 프로젝트 기반 환경 및 법정동 코드 설정

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `.env.example`
- Create: `data/lawd_cd.json`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `src/config.py`: `DATA_DIR: Path`, `LAWD_CD_PATH: Path`, `DATA_FILE_PATH: Path`, `METADATA_PATH: Path`, `API_URL: str`, `get_api_key() -> str`
  - `data/lawd_cd.json`: `list[dict[str, str]]` (keys: `code`, `sido`, `sigungu`)

- [ ] **Step 1: Write the failing test for configuration and lawd code loader**

```python
# tests/test_config.py
from pathlib import Path
import json
from src.config import DATA_DIR, LAWD_CD_PATH, DATA_FILE_PATH, METADATA_PATH, get_api_key

def test_paths_defined():
    assert DATA_DIR.name == "data"
    assert DATA_FILE_PATH.name == "recent_7days.parquet"
    assert METADATA_PATH.name == "metadata.json"
    assert LAWD_CD_PATH.exists()

def test_lawd_cd_format():
    with open(LAWD_CD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) >= 200
    first = data[0]
    assert "code" in first and len(first["code"]) == 5
    assert "sido" in first
    assert "sigungu" in first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.config')

- [ ] **Step 3: Implement pyproject.toml, src/config.py, and data/lawd_cd.json**

1. `pyproject.toml`에 프로젝트 메타데이터 및 의존성(`streamlit`, `pandas`, `pyarrow`, `requests`, `plotly`, `pydeck`, `pytest`) 명시.
2. `src/config.py`에 경로 상수 및 환경변수 로딩 로직 작성.
3. `data/lawd_cd.json`에 전국 17개 시도 산하 250개 시군구 5자리 코드 데이터 생성 저장.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ data/ tests/ .env.example
git commit -m "feat: initialize project configuration and lawd code dataset"
```

---

### Task 2: 롤링 7일 날짜 계산 및 데이터 전처리 엔진

**Files:**
- Create: `src/processor.py`
- Create: `tests/test_processor.py`

**Interfaces:**
- Consumes: `src.config`
- Produces:
  - `calculate_date_range(today: date | None = None) -> tuple[date, date, list[str]]`
    - 반환값: `(start_date, end_date, [YYYYMM 리스트])`
  - `clean_price_string(price_str: str) -> int`
    - 공백/콤마 제거 후 정수 만원 반환
  - `process_raw_deals(raw_items: list[dict], start_date: date, end_date: date) -> pd.DataFrame`
    - 날짜 필터링, 평형 계산, 억원 표기 컬럼 추가
  - `save_processed_data(df: pd.DataFrame, meta_extra: dict | None = None) -> None`
    - `recent_7days.parquet` 및 `metadata.json` 파일 원자적 저장

- [ ] **Step 1: Write the failing tests for processor functions**

```python
# tests/test_processor.py
from datetime import date
import pandas as pd
from src.processor import calculate_date_range, clean_price_string, process_raw_deals

def test_calculate_date_range_same_month():
    # 2026년 9월 30일 기준 -> 9월 24일 ~ 9월 30일 (202609)
    today = date(2026, 9, 30)
    start, end, ymd_list = calculate_date_range(today)
    assert start == date(2026, 9, 24)
    assert end == date(2026, 9, 30)
    assert ymd_list == ["202609"]

def test_calculate_date_range_cross_month():
    # 2026년 10월 3일 기준 -> 9월 27일 ~ 10월 3일 (202609, 202610)
    today = date(2026, 10, 3)
    start, end, ymd_list = calculate_date_range(today)
    assert start == date(2026, 9, 27)
    assert end == date(2026, 10, 3)
    assert ymd_list == ["202609", "202610"]

def test_clean_price_string():
    assert clean_price_string("   15,000 ") == 15000
    assert clean_price_string("285,000") == 285000
    assert clean_price_string(10000) == 10000

def test_process_raw_deals():
    raw_items = [
        {
            "dealYear": 2026, "dealMonth": 9, "dealDay": 28,
            "sido": "서울특별시", "sigungu": "강남구", "umdNm": "개포동",
            "aptNm": "개포자이", "excluUseAr": 84.97, "floor": 15,
            "buildYear": 2023, "dealAmount": " 285,000 ", "dealingGbn": "중개거래"
        },
        {
            # 범위 밖 (오래된 데이터)
            "dealYear": 2026, "dealMonth": 9, "dealDay": 10,
            "sido": "서울특별시", "sigungu": "강남구", "umdNm": "개포동",
            "aptNm": "옛날거래", "excluUseAr": 59.9, "floor": 5,
            "buildYear": 2020, "dealAmount": " 150,000 ", "dealingGbn": "중개거래"
        }
    ]
    df = process_raw_deals(raw_items, date(2026, 9, 24), date(2026, 9, 30))
    assert len(df) == 1
    row = df.iloc[0]
    assert row["apt_name"] == "개포자이"
    assert row["price_manwon"] == 285000
    assert row["price_eok"] == 28.5
    assert row["deal_date"] == date(2026, 9, 28)
    assert round(row["pyeong"], 1) == 25.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_processor.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.processor')

- [ ] **Step 3: Implement processor logic in `src/processor.py`**

1. `calculate_date_range`: `timedelta(days=6)` 적용 및 전월/당월 연월 문자열 추출.
2. `clean_price_string`: 공백 및 콤마 정규화.
3. `process_raw_deals`: XML 파싱 딕셔너리 리스트를 Pandas DataFrame으로 변환, 날짜 필터링, 파생 컬럼(`pyeong`, `price_eok`, `price_per_py`) 계산.
4. `save_processed_data`: Parquet 포맷으로 저장 및 `metadata.json` 작성.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_processor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/processor.py tests/test_processor.py
git commit -m "feat: implement 7-day rolling window calculation and deal preprocessor"
```

---

### Task 3: 국토교통부 OpenAPI 멀티스레딩 수집기 구현

**Files:**
- Create: `src/collector.py`
- Create: `tests/test_collector.py`

**Interfaces:**
- Consumes: `src.config`, `src.processor`
- Produces:
  - `fetch_sigungu_deals(lawd_cd: str, ymd: str, api_key: str) -> list[dict]`
    - 단일 시군구 1개월치 XML 요청 및 파싱
  - `parse_xml_response(xml_text: str) -> list[dict]`
    - 공공데이터 XML 결과 파서
  - `collect_all_7days(api_key: str | None = None, max_workers: int = 8) -> pd.DataFrame`
    - 전국 시군구 병렬 호출 및 저장 파이프라인 메인 엔트리포인트

- [ ] **Step 1: Write the failing tests for XML parsing and error handling**

```python
# tests/test_collector.py
from src.collector import parse_xml_response

MOCK_XML_SUCCESS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <dealAmount>   120,000 </dealAmount>
        <buildYear>2018</buildYear>
        <dealYear>2026</dealYear>
        <dealMonth>9</dealMonth>
        <dealDay>29</dealDay>
        <dong>역삼동</dong>
        <aptNm>역삼푸르지오</aptNm>
        <excluUseAr>84.9</excluUseAr>
        <floor>10</floor>
        <dealingGbn>중개거래</dealingGbn>
      </item>
    </items>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>1</totalCount>
  </body>
</response>
"""

MOCK_XML_EMPTY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items/>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>0</totalCount>
  </body>
</response>
"""

def test_parse_xml_success():
    items = parse_xml_response(MOCK_XML_SUCCESS)
    assert len(items) == 1
    assert items[0]["aptNm"] == "역삼푸르지오"
    assert items[0]["dealDay"] == "29"

def test_parse_xml_empty():
    items = parse_xml_response(MOCK_XML_EMPTY)
    assert items == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_collector.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.collector')

- [ ] **Step 3: Implement XML parser and threaded collector in `src/collector.py`**

1. `xml.etree.ElementTree`를 사용한 견고한 XML 파서 구현 (`parse_xml_response`).
2. `fetch_sigungu_deals`: `requests.get`에 3회 재시도(지수 백오프) 적용 및 실패 시 빈 리스트 반환(타 시군구 수집 보장).
3. `collect_all_7days`: `ThreadPoolExecutor`를 통해 250개 시군구를 병렬 수집하고, `process_raw_deals` 및 `save_processed_data`를 호출하여 원클릭 실행 완성.
4. CLI 실행 인터페이스 추가 (`if __name__ == "__main__": collect_all_7days()`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_collector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/collector.py tests/test_collector.py
git commit -m "feat: implement public data API multithreaded collector"
```

---

### Task 4: Streamlit 대시보드 UI/UX 구현

**Files:**
- Create: `app.py`
- Create: `src/dashboard_views.py`
- Create: `tests/test_dashboard_views.py`

**Interfaces:**
- Consumes: `data/recent_7days.parquet`, `data/metadata.json`
- Produces:
  - `src/dashboard_views.py`:
    - `filter_data(df, sido, sigungu, area_category, price_range, search_term) -> pd.DataFrame`
    - `render_metrics(df)`
    - `render_trend_tab(df)`
    - `render_top_rank_tab(df)`
    - `render_map_tab(df)`
    - `render_table_tab(df)`
  - `app.py`: Streamlit 메인 엔트리포인트

- [ ] **Step 1: Write the failing tests for dashboard filter logic**

```python
# tests/test_dashboard_views.py
import pandas as pd
from datetime import date
from src.dashboard_views import filter_data

def test_filter_data():
    sample_df = pd.DataFrame([
        {
            "deal_date": date(2026, 9, 28),
            "sido": "서울특별시", "sigungu": "강남구", "apt_name": "개포자이",
            "area": 84.0, "price_eok": 28.5
        },
        {
            "deal_date": date(2026, 9, 29),
            "sido": "경기도", "sigungu": "성남시 분당구", "apt_name": "판교푸르지오",
            "area": 59.0, "price_eok": 14.0
        }
    ])
    # 시도 필터
    filtered = filter_data(sample_df, sido="서울특별시", sigungu=[], area_cat="전체", price_min=0, price_max=50, search="")
    assert len(filtered) == 1
    assert filtered.iloc[0]["sido"] == "서울특별시"
    
    # 가격 필터
    filtered_price = filter_data(sample_df, sido="전체", sigungu=[], area_cat="전체", price_min=20, price_max=50, search="")
    assert len(filtered_price) == 1
    assert filtered_price.iloc[0]["price_eok"] == 28.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_views.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.dashboard_views')

- [ ] **Step 3: Implement `src/dashboard_views.py` and `app.py`**

1. `src/dashboard_views.py`:
   - 필터링 로직 분리 구현 (`filter_data`).
   - Plotly 기반 일자별 거래량 바 차트, 가격 분포 히스토그램, 평형별 도넛 차트 구현.
   - TOP 랭킹 테이블 및 Pydeck 지도 시각화 렌더러 구현.
2. `app.py`:
   - `st.set_page_config(layout="wide", page_title="전국 아파트 실거래가")`.
   - 데이터 미존재 시 안내 화면(Empty State) 렌더링.
   - 사이드바 필터 컴포넌트 및 상단 4대 KPI 메트릭 카드 배치.
   - 4개 탭(`st.tabs`)으로 분석 뷰 구성 및 CSV 다운로드 연동.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dashboard_views.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py src/dashboard_views.py tests/test_dashboard_views.py
git commit -m "feat: implement streamlit dashboard UI with multi-tab visualizations"
```

---

### Task 5: GitHub Actions 수동 수집 워크플로우 및 배포 가이드 구성

**Files:**
- Create: `.github/workflows/daily_collect.yml`
- Create: `README.md`
- Create: `scripts/sample_data_generator.py` (테스트/오프라인 데모용)

**Interfaces:**
- Produces:
  - `.github/workflows/daily_collect.yml`: GitHub Actions 자동화 워크플로우
  - `README.md`: 설치, 로컬 실행, Secrets 설정, Streamlit Cloud 배포 상세 가이드

- [ ] **Step 1: Write and verify sample data generator script**

1. `scripts/sample_data_generator.py`를 작성하여 실제 API 키 없이도 대시보드 로컬 테스트를 즉시 수행할 수 있도록 더미 7일 실거래 Parquet/Metadata 생성기 제공.
2. 실행: `uv run python scripts/sample_data_generator.py`
3. 검증: `data/recent_7days.parquet` 생성 및 `uv run streamlit run app.py`가 정상 구동되는지 확인.

- [ ] **Step 2: Implement `.github/workflows/daily_collect.yml`**

```yaml
name: Collect Real Price Data

on:
  workflow_dispatch:
  # 정기 실행을 원할 시 아래 주석 해제 (매일 KST 06:00 = UTC 21:00)
  # schedule:
  #   - cron: '0 21 * * *'

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run collector
        env:
          DATA_GO_KR_API_KEY: ${{ secrets.DATA_GO_KR_API_KEY }}
        run: uv run python src/collector.py

      - name: Commit and push if data changed
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          if git diff --cached --quiet; then
            echo "No data changes to commit."
          else
            git commit -m "chore: auto-update real price data [skip ci] ($(date +'%Y-%m-%d'))"
            git push
          fi
```

- [ ] **Step 3: Write comprehensive `README.md`**

프로젝트 개요, 로컬 시작 가이드(`uv sync`, `.env` 설정), GitHub Actions Secrets 설정법, Streamlit Community Cloud 3분 배포 절차를 상세히 기술.

- [ ] **Step 4: Verify test suite passes completely**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add .github/ README.md scripts/
git commit -m "feat: setup github actions collection workflow and deployment guide"
```
