# 🏢 전국 아파트 매매 실거래가 대시보드 (최근 7일 롤링)

공공데이터포털(data.go.kr)의 국토교통부 아파트 매매 실거래가 OpenAPI(15126469)를 연동하여, **최근 7일간의 전국 아파트 실거래가**를 수집·시각화하고 **GitHub Actions**와 **Streamlit Community Cloud**를 통해 100% 무료로 운영되는 웹 대시보드입니다.

---

## 🌟 주요 기능

1. **롤링 7일 고속 수집 파이프라인**:
   - 전국 약 250개 시군구를 멀티스레딩(`ThreadPoolExecutor`)으로 15~25초 내에 수집
   - 월초 실행 시 전월/당월 데이터를 자동 병합하여 최근 7일 범위를 정확히 필터링
   - 가벼운 단일 Parquet 파일(`data/recent_7days.parquet`, ~1MB)로 저장하여 초고속 로딩
2. **상세 인터랙티브 대시보드 (`Streamlit`)**:
   - **사이드바 필터**: 시/도 및 시군구 연동 선택, 전용면적(평형) 구간, 거래금액 슬라이더, 단지명 검색
   - **4대 핵심 KPI 메트릭 카드**: 총 거래량, 평균 거래금액, 최고 거래가 단지, 평당 평균가
   - **4개 분석 탭**:
     - `📊 거래 트렌드 & 가격분포`: 일자별 거래량 추이 바 차트, 거래금액대별 히스토그램, 평형별 도넛 차트
     - `🏆 최고가 TOP 랭킹`: 최근 7일 최고가 상위 20개 단지 순위표
     - `🗺️ 지역별 지도 시각화`: 시군구별 거래량 대비 평균 거래가 분포 차트
     - `📋 실거래 상세 내역`: 정렬 가능 테이블 및 CSV 다운로드 기능
3. **완전 무료 자동화 및 배포**:
   - **GitHub Actions**: 웹에서 버튼 한 번으로 데이터 수집 및 자동 커밋 (`workflow_dispatch`)
   - **Streamlit Community Cloud**: GitHub 저장소와 연동하여 커밋 시 자동 새로고침 배포

---

## 🚀 빠른 시작 (로컬 개발)

본 프로젝트는 초고속 패키지 관리자 **`uv`**를 사용합니다.

### 1. 패키지 설치
```bash
uv sync
```

### 2. API 키 설정 (선택 사항)
공공데이터포털에서 발급받은 일반 인증키(Encoding/Decoding)를 `.env` 파일에 입력합니다:
```bash
cp .env.example .env
# .env 파일을 열고 DATA_GO_KR_API_KEY=발급받은_키 입력
```

> **API 키 없이 바로 대시보드를 테스트하고 싶은 경우**:
> ```bash
> uv run python scripts/sample_data_generator.py
> ```
> 위 명령어를 실행하면 최근 7일간의 사실적인 샘플 실거래가 300건이 즉시 생성됩니다.

### 3. 실제 데이터 수집 실행
```bash
uv run python src/collector.py
```
* 전국 250개 시군구의 최근 7일 롤링 데이터를 수집하여 `data/recent_7days.parquet` 및 `data/metadata.json`에 저장합니다.

### 4. 대시보드 실행
```bash
uv run streamlit run app.py
```
브라우저에서 `http://localhost:8501`이 자동으로 열립니다.

---

## ☁️ 무료 배포 가이드 (GitHub & Streamlit Cloud)

### 1단계: GitHub 저장소에 코드 푸시
```bash
git add .
git commit -m "feat: complete apt real price dashboard"
git branch -M main
git remote add origin https://github.com/당신의계정/당신의레포.git
git push -u origin main
```

### 2단계: GitHub Secrets 설정 (API 키 등록)
1. 생성한 GitHub 레포지토리의 **Settings** 메뉴로 이동합니다.
2. 좌측 메뉴에서 **Secrets and variables** $\rightarrow$ **Actions**를 클릭합니다.
3. **[New repository secret]** 버튼을 누릅니다:
   - **Name**: `DATA_GO_KR_API_KEY`
   - **Secret**: 공공데이터포털에서 발급받은 일반 인증키 붙여넣기
4. **[Add secret]**을 클릭하여 저장합니다.

### 3단계: GitHub Actions 수동 수집 실행
1. GitHub 레포지토리 상단의 **Actions** 탭으로 이동합니다.
2. 좌측 워크플로우 목록에서 **Collect Real Price Data**를 클릭합니다.
3. 우측의 **[Run workflow]** 버튼을 클릭하여 수집을 실행합니다.
4. 약 1분 후 워크플로우가 성공하면 최신 실거래가 데이터가 자동으로 레포지토리에 커밋 & 푸시됩니다!

> **정기 자동 수집(매일 아침 6시)을 켜고 싶으실 때**:
> `.github/workflows/daily_collect.yml` 파일에서 아래 2줄의 주석(`#`)을 해제하고 푸시하시면 매일 아침 자동으로 실행됩니다:
> ```yaml
>   schedule:
>     - cron: '0 21 * * *'
> ```

### 4단계: Streamlit Community Cloud 배포 (3분 완료)
1. [share.streamlit.io](https://share.streamlit.io)에 접속하여 GitHub 계정으로 로그인합니다.
2. **[Create app]** 버튼을 클릭합니다.
3. 배포 설정 입력:
   - **Repository**: 당신의 GitHub 저장소 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. **[Deploy!]** 버튼을 클릭합니다.
5. 몇 초 후 전 세계 누구나 접속할 수 있는 **무료 웹 서비스 URL**이 생성됩니다!
*(이후 GitHub Actions로 데이터가 커밋될 때마다 Streamlit Cloud가 이를 자동으로 감지하여 대시보드를 최신화합니다.)*

---

## 🧪 테스트 실행
TDD 원칙에 따라 작성된 모든 단위 테스트 및 통합 테스트를 실행합니다:
```bash
uv run pytest -v
```

---

## 📁 프로젝트 구조

```text
apt_real_price/
├── .github/
│   └── workflows/
│       └── daily_collect.yml       # GitHub Actions 수동/자동 수집 워크플로우
├── data/
│   ├── lawd_cd.json                # 전국 250개 시군구 법정동 코드
│   ├── recent_7days.parquet        # 최근 7일 롤링 실거래가 Parquet (~1MB)
│   └── metadata.json               # 마지막 수집 시각 및 통계 메타데이터
├── src/
│   ├── __init__.py
│   ├── config.py                   # 경로 및 환경변수 설정
│   ├── collector.py                # 국토부 API 병렬 수집기
│   ├── processor.py                # 7일 롤링 날짜 필터링 및 데이터 정제
│   └── dashboard_views.py          # Streamlit UI 컴포넌트 및 4개 분석 탭
├── scripts/
│   └── sample_data_generator.py    # 로컬 개발 및 오프라인 테스트용 샘플 데이터 생성기
├── tests/
│   ├── test_config.py              # 환경 설정 테스트
│   ├── test_processor.py           # 날짜 계산 및 데이터 전처리 테스트
│   ├── test_collector.py           # XML 파서 및 API 에러 핸들링 테스트
│   └── test_dashboard_views.py     # 대시보드 필터 및 통계 연산 테스트
├── app.py                          # Streamlit 메인 애플리케이션
├── pyproject.toml                  # uv 패키지 및 의존성 명세
├── .env.example                    # 환경변수 템플릿
├── .gitignore                      # 형상관리 제외 설정
└── README.md                       # 프로젝트 문서
```
