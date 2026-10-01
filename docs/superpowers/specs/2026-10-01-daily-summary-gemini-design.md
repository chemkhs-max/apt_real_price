# 일자별 아파트 거래내역 조회 & Gemini 부동산 애널리스트 요약 시스템 설계 명세서 (Design Spec)

## 1. 개요 및 목적
본 기능은 수집된 아파트 실거래가 데이터(`data/recent_7days.parquet`)를 기반으로 **일자별 상세 거래내역을 조회**하고, Google **Gemini API(`gemini-2.5-flash`)를 활용하여 전문 부동산 애널리스트 관점의 심층 마켓 리포트를 제공**하는 별도의 Streamlit 페이지를 구축하는 것을 목적으로 합니다.
또한 생성된 요약 분석은 **SQLite 데이터베이스(`data/daily_summaries.db`)에 영구 저장(캐싱)**하여 최초 1회만 생성되고 이후 요청에서는 즉각적으로 조회되도록 설계합니다.

---

## 2. 요구사항 명세

### 2.1 기능적 요구사항 (Functional Requirements)
1. **별도 페이지 구성 (Streamlit Multipage)**:
   - `pages/1_📅_일자별_거래분석.py` 형태로 구성하여 기존 대시보드와 손쉽게 상호 이동 가능.
2. **일자별 상세 조회**:
   - 데이터셋에 존재하는 실제 거래일자 목록을 최신순으로 정렬하여 선택 UI(Selectbox) 제공.
   - 선택된 일자의 거래 통계(거래량, 평균가, 최고가, 최다 거래 지역)를 요약 메트릭 카드로 표시.
   - 당일 발생한 전체 거래내역을 정렬/검색 가능한 데이터 테이블로 제공 및 CSV 다운로드 지원.
3. **Gemini 기반 부동산 애널리스트 AI 리포트**:
   - 15년 차 수석 부동산 애널리스트 페르소나를 기반으로 객관적인 데이터(당일 최고가 단지, 지역별 거래 집중도, 평형대별 분포 등)를 종합 분석.
   - 목차 구조:
     - 📌 오늘의 마켓 헤드라인 (한 줄 총평)
     - 🏆 주요 거래 하이라이트 (최고가 거래 단지 및 특징 분석)
     - 🗺️ 지역 및 평형별 거래 동향
     - 💡 애널리스트 관전 포인트 (실수요자/투자자 시사점)
4. **SQLite DB 기반 영구 캐싱 (1회 생성 후 재사용)**:
   - `daily_market_summaries` 테이블에 `deal_date`를 기본키로 저장.
   - 해당 일자 조회 시 DB에 저장된 요약이 있으면 API를 호출하지 않고 DB 데이터를 즉시 로드(0.1초 이내).
   - DB에 요약이 없을 경우에만 Gemini API를 자동 호출하여 생성 후 DB에 영구 저장.
   - 사용자가 원할 때 새로운 분석으로 갱신할 수 있는 `🔄 요약 다시 생성` 버튼 제공.
5. **안전한 환경변수 및 에러 핸들링**:
   - API 키는 `.env`의 `GEMINI_API_KEY`를 사용.
   - 키가 없거나 네트워크 오류, 쿼터 제한 시 친절한 안내 메시지 표시 및 앱 비정상 종료 방지.

### 2.2 비기능적 요구사항 (Non-Functional Requirements)
- **응답 속도**: 이미 분석된 일자는 DB에서 즉각(0.1초 내) 렌더링.
- **의존성 관리**: `uv`를 통한 `google-genai` 공식 SDK 관리.
- **테스트 용이성**: DB CRUD 및 Gemini 통계 가공 로직에 대한 단위 테스트(`pytest`) 작성.

---

## 3. 시스템 아키텍처 및 모듈 설계

### 3.1 디렉터리 구조
```text
apt_real_price/
├── data/
│   ├── recent_7days.parquet           # 실거래가 원본 데이터
│   └── daily_summaries.db             # 일자별 요약 저장용 SQLite DB
├── src/
│   ├── config.py                      # DB 경로 및 GEMINI_API_KEY 설정 추가
│   ├── db/
│   │   ├── __init__.py
│   │   └── summary_repository.py      # SQLite CRUD 저장소
│   └── services/
│       ├── __init__.py
│       └── gemini_service.py          # Gemini API 호출 및 통계 요약 가공
├── pages/
│   └── 1_📅_일자별_거래분석.py         # Streamlit 일자별 상세 및 AI 리포트 페이지
└── tests/
    ├── test_summary_repository.py     # SQLite DB CRUD 단위 테스트
    └── test_gemini_service.py         # Gemini 서비스 및 프롬프트 가공 테스트
```

### 3.2 SQLite 데이터베이스 스키마 (`data/daily_summaries.db`)
```sql
CREATE TABLE IF NOT EXISTS daily_market_summaries (
    deal_date TEXT PRIMARY KEY,          -- 거래일자 (YYYY-MM-DD)
    summary_content TEXT NOT NULL,       -- Gemini 마크다운 리포트
    model_name TEXT NOT NULL,            -- 사용 모델 (gemini-2.5-flash)
    deal_count INTEGER NOT NULL,         -- 당일 거래 건수
    created_at TEXT NOT NULL,            -- 생성 일시 (YYYY-MM-DD HH:MM:SS)
    updated_at TEXT NOT NULL             -- 수정 일시 (YYYY-MM-DD HH:MM:SS)
);
```

### 3.3 모듈 인터페이스 정의

#### (1) `src/db/summary_repository.py`
```python
class DailySummaryRepository:
    def __init__(self, db_path: Path | str | None = None):
        """DB 연결 및 테이블 초기화"""
        ...
    def get_summary(self, deal_date: str) -> dict | None:
        """일자(YYYY-MM-DD) 기준 저장된 요약 레코드 반환"""
        ...
    def save_summary(self, deal_date: str, summary_content: str, model_name: str, deal_count: int) -> None:
        """일자별 요약 신규 저장 또는 갱신 (UPSERT)"""
        ...
    def delete_summary(self, deal_date: str) -> bool:
        """특정 일자 요약 삭제"""
        ...
```

#### (2) `src/services/gemini_service.py`
```python
def build_daily_stats_summary(daily_df: pd.DataFrame, deal_date: str) -> str:
    """
    일자별 거래 데이터프레임을 애널리스트 프롬프트용 텍스트 통계표로 가공:
    - 총 거래건수, 평균 거래가, 중간값 거래가
    - 최고가 거래 Top 3 단지 (단지명, 지역, 전용면적, 가격)
    - 최다 거래 지역 상위 5개 및 평균가
    - 평형대별 분포 비중
    """
    ...

def generate_analyst_report(stats_summary: str, api_key: str | None = None) -> str:
    """
    google-genai SDK를 사용하여 gemini-2.5-flash 모델로 부동산 애널리스트 리포트 생성
    """
    ...
```

#### (3) `pages/1_📅_일자별_거래분석.py` (UI 흐름)
1. `data/recent_7days.parquet` 로드 (미존재 시 안내 배너)
2. 고유 거래일자 추출 및 최신 일자 기본 선택
3. 일간 4대 핵심 지표 카드 렌더링 (`st.columns(4)`)
4. **AI 리포트 섹션**:
   - `summary_repo.get_summary(deal_date)` 확인
   - 캐시 존재 시: `st.markdown(summary)` 표시 및 저장 일시 배지 안내
   - 캐시 미존재 시: `st.spinner`와 함께 `generate_analyst_report()` 호출 후 `save_summary()` 호출
   - 우측 `🔄 요약 다시 생성` 버튼 클릭 시: 강제 재호출 및 DB 업데이트
5. **일자별 상세 거래 테이블**:
   - 아파트명/지역 필터링, 컬럼 정렬, CSV 다운로드 버튼 제공

---

## 4. 에러 처리 및 보안

1. **API 키 관리**:
   - `.env`에 `GEMINI_API_KEY` 설정 지원.
   - 키 미등록 시 앱 크래시 대신 `st.warning("⚠️ .env 파일에 GEMINI_API_KEY를 등록해 주세요.")` 안내 카드 노출.
2. **API 호출 장애 대응**:
   - 네트워크 타임아웃 또는 API 할당량 소진 시 에러 로그 기록 및 사용자에게 친절한 실패 메시지와 재시도 유도.
3. **DB 트랜잭션 안전성**:
   - `sqlite3` context manager(`with conn:`)를 사용하여 안전한 커밋 및 롤백 보장.
   - `.gitignore`에 `*.db` 또는 필요에 따라 관리 정책 반영.

---

## 5. 테스트 계획

1. `tests/test_summary_repository.py`:
   - 메모리 DB(`:memory:`)를 생성하여 `get_summary`, `save_summary`의 신규 생성 및 중복 저장(덮어쓰기) 검증.
2. `tests/test_gemini_service.py`:
   - 샘플 데이터프레임을 통해 `build_daily_stats_summary`가 통계 데이터를 올바르게 집계하는지 검증.
   - Mock을 활용하여 API 호출 성공 및 예외 발생 시의 반환값 검증.
3. E2E 수동 검증:
   - Streamlit 브라우저에서 날짜 전환 시 최초 로딩(API 호출) 및 재조회(DB 즉시 로딩) 속도 비교 검증.
