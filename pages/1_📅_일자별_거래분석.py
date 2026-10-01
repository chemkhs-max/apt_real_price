from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

from src.config import DATA_FILE_PATH, get_gemini_api_key
from src.db.summary_repository import DailySummaryRepository
from src.services.gemini_service import (
    DEFAULT_GEMINI_MODEL,
    build_daily_stats_summary,
    generate_analyst_report,
)

# 페이지 설정
st.set_page_config(
    page_title="일자별 실거래 분석 & AI 마켓 리포트",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=3600)
def load_parquet_data() -> pd.DataFrame:
    """Parquet 데이터를 로드하고 deal_date 형식을 정제합니다."""
    if not DATA_FILE_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(DATA_FILE_PATH)
    if "deal_date" in df.columns:
        df["deal_date_str"] = df["deal_date"].astype(str)
    return df


def main():
    st.title("📅 일자별 아파트 실거래 상세 분석 & AI 마켓 리포트")
    st.caption("수집된 최근 실거래 데이터를 바탕으로 일자별 상세 내역과 Gemini AI 부동산 애널리스트의 심층 리포트를 제공합니다.")
    st.markdown("---")

    df = load_parquet_data()

    if df.empty:
        st.warning("⚠️ 아직 수집된 실거래가 데이터(`data/recent_7days.parquet`)가 없습니다.")
        st.info("메인 대시보드나 GitHub Actions를 통해 먼저 데이터를 수집해 주세요.")
        return

    # 일자 목록 추출 (최신 일자순)
    available_dates = sorted(df["deal_date_str"].unique(), reverse=True)
    if not available_dates:
        st.warning("조회 가능한 거래 일자가 없습니다.")
        return

    # 날짜별 건수 매핑 레이블 생성
    date_counts = df["deal_date_str"].value_counts().to_dict()
    date_options = [f"{d} ({date_counts.get(d, 0):,}건)" for d in available_dates]
    date_map = {f"{d} ({date_counts.get(d, 0):,}건)": d for d in available_dates}

    # 사이드바 날짜 선택
    st.sidebar.header("🗓️ 일자 선택")
    selected_option = st.sidebar.selectbox("조회할 거래 일자", options=date_options, index=0)
    selected_date = date_map[selected_option]

    # 해당 일자 데이터 필터링
    day_df = df[df["deal_date_str"] == selected_date].copy()
    total_deals = len(day_df)

    # 1. 당일 4대 핵심 지표 카드
    col1, col2, col3, col4 = st.columns(4)
    avg_price = day_df["price_eok"].mean() if not day_df.empty else 0.0
    max_row = day_df.sort_values(by="price_eok", ascending=False).iloc[0] if not day_df.empty else None

    # 최다 거래 지역 계산
    top_region = "집계 불가"
    if not day_df.empty:
        day_df["region"] = day_df["sido"].astype(str) + " " + day_df["sigungu"].astype(str)
        top_region_series = day_df["region"].value_counts()
        if not top_region_series.empty:
            top_region = f"{top_region_series.index[0]} ({top_region_series.iloc[0]}건)"

    with col1:
        st.metric("당일 총 거래량", f"{total_deals:,} 건")
    with col2:
        st.metric("평균 거래가격", f"{avg_price:.2f} 억원")
    with col3:
        if max_row is not None:
            max_desc = f"{max_row.get('apt_name', '')} ({max_row.get('sigungu', '')})"
            st.metric("당일 최고 거래가", f"{max_row.get('price_eok', 0.0):.2f} 억원", help=max_desc)
        else:
            st.metric("당일 최고 거래가", "-")
    with col4:
        st.metric("최다 거래 지역", top_region)

    st.markdown("---")

    # 2. 🤖 AI 부동산 애널리스트 리포트 섹션
    st.subheader(f"🤖 Gemini AI 부동산 애널리스트 리포트 ({selected_date})")

    repo = DailySummaryRepository()
    saved_record = repo.get_summary(selected_date)

    header_col1, header_col2 = st.columns([8, 2])
    with header_col2:
        regenerate_clicked = st.button("🔄 요약 다시 생성", use_container_width=True)

    api_key = get_gemini_api_key()

    # 요약이 존재하고 재분석 클릭이 아닌 경우 -> DB 캐시 조회
    if saved_record and not regenerate_clicked:
        st.success(
            f"💾 **저장된 분석 리포트** | 모델: `{saved_record['model_name']}` | "
            f"생성 일시: `{saved_record['updated_at']}` | 대상 거래: {saved_record['deal_count']}건"
        )
        st.markdown(saved_record["summary_content"])
    else:
        # 요약 생성 로직
        if not api_key:
            st.warning("⚠️ **GEMINI_API_KEY 미등록**: `.env` 파일에 GEMINI_API_KEY를 등록하시면 전문 부동산 애널리스트 분석이 자동으로 생성 및 영구 저장됩니다.")
            st.info("💡 [Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료로 API 키를 발급받아 `.env` 파일의 `GEMINI_API_KEY=...`에 저장해 주세요.")
        else:
            with st.spinner("🤖 Gemini AI가 당일 실거래 데이터를 심층 분석하여 부동산 애널리스트 리포트를 생성하고 있습니다..."):
                stats_text = build_daily_stats_summary(day_df, selected_date)
                try:
                    report = generate_analyst_report(stats_text, api_key=api_key, model=DEFAULT_GEMINI_MODEL)
                    repo.save_summary(
                        deal_date=selected_date,
                        summary_content=report,
                        model_name=DEFAULT_GEMINI_MODEL,
                        deal_count=total_deals,
                    )
                    st.success("✅ AI 애널리스트 분석이 성공적으로 생성되어 SQLite DB에 저장되었습니다!")
                    st.markdown(report)
                except Exception as e:
                    st.error(f"❌ AI 요약 생성 중 오류가 발생했습니다: {e}")
                    st.caption("입력하신 GEMINI_API_KEY가 유효한지 확인해 주세요.")

    st.markdown("---")

    # 3. 📋 당일 실거래 상세 내역 테이블
    st.subheader(f"📋 당일 실거래 상세 내역 ({total_deals:,}건)")

    # 상세 필터
    tcol1, tcol2 = st.columns([5, 5])
    with tcol1:
        sido_list = ["전체"] + sorted(day_df["sido"].unique().tolist())
        selected_sido = st.selectbox("시/도 필터", options=sido_list, index=0)
    with tcol2:
        search_kw = st.text_input("아파트 단지명 또는 동 검색", placeholder="예: 현대, 반포동")

    view_df = day_df.copy()
    if selected_sido != "전체":
        view_df = view_df[view_df["sido"] == selected_sido]
    if search_kw.strip():
        kw = search_kw.strip()
        view_df = view_df[
            view_df["apt_name"].str.contains(kw, case=False, na=False)
            | view_df["dong"].str.contains(kw, case=False, na=False)
        ]

    # 표시할 컬럼 정리
    display_cols = [
        "deal_date_str",
        "sido",
        "sigungu",
        "dong",
        "apt_name",
        "price_eok",
        "price_manwon",
        "area",
        "pyeong",
        "floor",
        "build_year",
        "deal_type",
    ]
    avail_cols = [c for c in display_cols if c in view_df.columns]
    renamed_map = {
        "deal_date_str": "계약일",
        "sido": "시도",
        "sigungu": "시군구",
        "dong": "법정동",
        "apt_name": "아파트명",
        "price_eok": "거래금액(억)",
        "price_manwon": "거래금액(만원)",
        "area": "전용면적(㎡)",
        "pyeong": "평형",
        "floor": "층",
        "build_year": "건축년도",
        "deal_type": "거래유형",
    }

    styled_df = view_df[avail_cols].rename(columns=renamed_map).sort_values(by="거래금액(억)", ascending=False)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # CSV 다운로드 버튼
    csv_bytes = styled_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label=f"📥 {selected_date} 실거래 내역 CSV 다운로드",
        data=csv_bytes,
        file_name=f"apt_real_price_{selected_date}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
