import json
from pathlib import Path
import pandas as pd
import streamlit as st

from src.config import DATA_FILE_PATH, METADATA_PATH, LAWD_CD_PATH
from src.dashboard_views import (
    filter_data,
    get_metrics,
    render_metrics_cards,
    render_trend_tab,
    render_top_rank_tab,
    render_map_tab,
    render_table_tab,
)

# 페이지 설정
st.set_page_config(
    page_title="전국 아파트 매매 실거래가 대시보드 (최근 7일)",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data(ttl=3600)
def load_data() -> tuple[pd.DataFrame, dict]:
    """Parquet 데이터와 metadata.json을 캐시 로드합니다."""
    if not DATA_FILE_PATH.exists():
        return pd.DataFrame(), {}

    df = pd.read_parquet(DATA_FILE_PATH)
    metadata = {}
    if METADATA_PATH.exists():
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            metadata = {}

    return df, metadata

@st.cache_data
def load_lawd_mapping() -> dict[str, list[str]]:
    """시도별 시군구 목록 매핑을 생성합니다."""
    if not LAWD_CD_PATH.exists():
        return {}
    with open(LAWD_CD_PATH, "r", encoding="utf-8") as f:
        lawd_list = json.load(f)

    mapping = {}
    for item in lawd_list:
        sido = item["sido"]
        sigungu = item["sigungu"]
        if sido not in mapping:
            mapping[sido] = []
        if sigungu not in mapping[sido]:
            mapping[sido].append(sigungu)
    return mapping

def main():
    df, metadata = load_data()
    lawd_mapping = load_lawd_mapping()

    # 상단 헤더
    st.title("🏢 전국 아파트 매매 실거래가 대시보드 (최근 7일 롤링)")
    
    if metadata:
        col_m1, col_m2 = st.columns([7, 3])
        with col_m1:
            st.caption(f"📅 데이터 수집 기간: **{metadata.get('start_date', '-')} ~ {metadata.get('end_date', '-')}** (전국 롤링 7일)")
        with col_m2:
            st.caption(f"🕒 최종 갱신: **{metadata.get('last_updated_at', '-')}**")
    st.markdown("---")

    # 데이터 미존재 시 안내 (Empty State)
    if df.empty:
        st.warning("⚠️ 아직 수집된 실거래가 데이터(`data/recent_7days.parquet`)가 없습니다.")
        st.info(
            "👉 **데이터 수집 방법**:\n"
            "1. 로컬 터미널에서 `uv run python src/collector.py` 명령을 실행하거나\n"
            "2. 테스트용 샘플 데이터를 생성하려면 `uv run python scripts/sample_data_generator.py`를 실행하세요.\n"
            "3. GitHub 저장소의 **Actions** 탭에서 **[Run workflow]**를 눌러 수동 수집할 수 있습니다."
        )
        return

    # 사이드바 필터 구성
    st.sidebar.header("🔍 상세 필터")

    # 1. 시도 선택
    sido_options = ["전체"] + sorted(list(lawd_mapping.keys()))
    selected_sido = st.sidebar.selectbox("📍 시/도 선택", options=sido_options, index=0)

    # 2. 시군구 선택 (시도에 연동)
    if selected_sido != "전체" and selected_sido in lawd_mapping:
        sigungu_options = sorted(lawd_mapping[selected_sido])
        selected_sigungu = st.sidebar.multiselect("📍 시/군/구 선택 (복수 가능)", options=sigungu_options)
    else:
        selected_sigungu = []

    # 3. 전용면적(평형대) 필터
    area_options = ["전체", "초소형(~40㎡)", "소형(~59㎡)", "국민평형(59~84㎡)", "대형(84㎡ 초과)"]
    selected_area = st.sidebar.selectbox("📐 전용면적(평형)", options=area_options, index=0)

    # 4. 거래금액 슬라이더
    max_price = float(df["price_eok"].max()) if not df.empty else 100.0
    price_range = st.sidebar.slider(
        "💵 거래금액 범위 (억원)",
        min_value=0.0,
        max_value=max(10.0, float(int(max_price) + 1)),
        value=(0.0, max(10.0, float(int(max_price) + 1))),
        step=0.5,
    )

    # 5. 아파트 단지명 / 법정동 검색
    search_query = st.sidebar.text_input("🔎 아파트 단지명 또는 동 검색", placeholder="예: 개포자이, 반포동")

    # 데이터 필터링 실행
    filtered_df = filter_data(
        df=df,
        sido=selected_sido,
        sigungu_list=selected_sigungu,
        area_category=selected_area,
        price_min=price_range[0],
        price_max=price_range[1],
        search_query=search_query
    )

    # 상단 4대 메트릭 요약 카드
    metrics = get_metrics(filtered_df)
    render_metrics_cards(metrics)
    st.markdown("---")

    # 메인 4개 분석 탭
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 거래 트렌드 & 가격분포",
        "🏆 최고가 TOP 랭킹",
        "🗺️ 지역별 지도 시각화",
        "📋 실거래 상세 내역"
    ])

    with tab1:
        render_trend_tab(filtered_df)

    with tab2:
        render_top_rank_tab(filtered_df)

    with tab3:
        render_map_tab(filtered_df)

    with tab4:
        render_table_tab(filtered_df)

if __name__ == "__main__":
    main()
