from datetime import date
from typing import Any
import pandas as pd
import plotly.express as px
import streamlit as st

def filter_data(
    df: pd.DataFrame,
    sido: str = "전체",
    sigungu_list: list[str] | None = None,
    area_category: str = "전체",
    price_min: float = 0.0,
    price_max: float = 100.0,
    search_query: str = ""
) -> pd.DataFrame:
    """사용자가 선택한 다차원 필터 조건에 따라 실거래가 DataFrame을 필터링합니다."""
    if df.empty:
        return df

    filtered = df.copy()

    # 시도 필터
    if sido and sido != "전체":
        filtered = filtered[filtered["sido"] == sido]

    # 시군구 필터
    if sigungu_list and len(sigungu_list) > 0:
        filtered = filtered[filtered["sigungu"].isin(sigungu_list)]

    # 면적 필터
    if area_category == "초소형(~40㎡)":
        filtered = filtered[filtered["area"] <= 40.0]
    elif area_category == "소형(~59㎡)":
        filtered = filtered[filtered["area"] <= 59.0]
    elif area_category == "국민평형(59~84㎡)":
        filtered = filtered[(filtered["area"] > 59.0) & (filtered["area"] <= 84.0)]
    elif area_category == "대형(84㎡ 초과)":
        filtered = filtered[filtered["area"] > 84.0]

    # 가격대 필터 (억원 기준)
    filtered = filtered[(filtered["price_eok"] >= price_min) & (filtered["price_eok"] <= price_max)]

    # 단지명/동 검색 필터
    if search_query and search_query.strip():
        q = search_query.strip().lower()
        match_mask = (
            filtered["apt_name"].str.lower().str.contains(q, na=False) |
            filtered["dong"].str.lower().str.contains(q, na=False)
        )
        filtered = filtered[match_mask]

    return filtered

def get_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """선택된 데이터셋의 주요 요약 통계 지표를 계산합니다."""
    if df.empty:
        return {
            "total_count": 0,
            "avg_price_eok": 0.0,
            "max_deal_title": "데이터 없음",
            "max_price_eok": 0.0,
            "avg_price_per_py": 0.0,
        }

    total_count = len(df)
    avg_price_eok = round(float(df["price_eok"].mean()), 2)
    avg_price_per_py = round(float(df["price_per_py"].mean()), 1)

    # 최고가 거래
    max_row = df.loc[df["price_eok"].idxmax()]
    max_price_eok = float(max_row["price_eok"])
    max_deal_title = f"{max_row['sigungu']} {max_row['apt_name']} ({max_price_eok:.1f}억)"

    return {
        "total_count": total_count,
        "avg_price_eok": avg_price_eok,
        "max_deal_title": max_deal_title,
        "max_price_eok": max_price_eok,
        "avg_price_per_py": avg_price_per_py,
    }

def render_metrics_cards(metrics: dict[str, Any]):
    """상단 4대 KPI 메트릭 카드를 렌더링합니다."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="📊 총 거래 건수", value=f"{metrics['total_count']:,} 건")
    with col2:
        st.metric(label="💰 평균 거래 금액", value=f"{metrics['avg_price_eok']:.2f} 억원")
    with col3:
        st.metric(label="🏆 최고가 거래", value=f"{metrics['max_price_eok']:.2f} 억원", help=metrics['max_deal_title'])
    with col4:
        st.metric(label="📐 평당 평균 가격", value=f"{metrics['avg_price_per_py']:,.0f} 만원/평")

def render_trend_tab(df: pd.DataFrame):
    """[탭 1] 일자별 거래량 추이 및 가격 분포 시각화"""
    if df.empty:
        st.info("조회된 데이터가 없습니다.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 일자별 거래량 추이")
        daily_counts = df.groupby("deal_date").size().reset_index(name="거래건수")
        daily_counts["deal_date_str"] = daily_counts["deal_date"].astype(str)
        fig_bar = px.bar(
            daily_counts,
            x="deal_date_str",
            y="거래건수",
            text="거래건수",
            color_discrete_sequence=["#1f77b4"],
            labels={"deal_date_str": "계약일자", "거래건수": "거래량 (건)"}
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(xaxis_title="", yaxis_title="거래 건수", margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("💵 거래 금액대별 분포")
        fig_hist = px.histogram(
            df,
            x="price_eok",
            nbins=25,
            color_discrete_sequence=["#2ca02c"],
            labels={"price_eok": "거래금액 (억원)"}
        )
        fig_hist.update_layout(xaxis_title="거래금액 (억원)", yaxis_title="건수", margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader("📐 평형대별 거래 비중")
    area_labels = []
    for a in df["area"]:
        if a <= 40:
            area_labels.append("초소형(~40㎡)")
        elif a <= 59:
            area_labels.append("소형(40~59㎡)")
        elif a <= 84:
            area_labels.append("국민평형(59~84㎡)")
        else:
            area_labels.append("대형(84㎡ 초과)")
    
    area_df = pd.Series(area_labels).value_counts().reset_index()
    area_df.columns = ["평형구분", "건수"]
    fig_donut = px.pie(
        area_df,
        names="평형구분",
        values="건수",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_donut.update_layout(margin=dict(t=20, b=20, l=10, r=10))
    st.plotly_chart(fig_donut, use_container_width=True)

def render_top_rank_tab(df: pd.DataFrame, top_n: int = 20):
    """[탭 2] 최근 7일 최고 거래가 TOP 단지 랭킹 리스트"""
    if df.empty:
        st.info("조회된 데이터가 없습니다.")
        return

    st.subheader(f"🏆 최근 7일 최고가 거래 TOP {top_n}")
    top_df = df.nlargest(top_n, "price_eok")[
        ["deal_date", "sido", "sigungu", "dong", "apt_name", "price_eok", "area", "pyeong", "floor", "price_per_py"]
    ].copy()
    top_df.reset_index(drop=True, inplace=True)
    top_df.index += 1

    top_df.columns = [
        "계약일자", "시도", "시군구", "법정동", "아파트명", "거래금액(억)", "전용면적(㎡)", "평형", "층", "평당가(만원)"
    ]

    st.dataframe(
        top_df.style.format({
            "거래금액(억)": "{:.2f}억",
            "전용면적(㎡)": "{:.1f}",
            "평형": "{:.1f}평",
            "층": "{:d}층",
            "평당가(만원)": "{:,.0f}만"
        }),
        use_container_width=True
    )

def render_map_tab(df: pd.DataFrame):
    """[탭 3] 시군구별 평균 실거래가 및 거래량 요약 시각화"""
    if df.empty:
        st.info("조회된 데이터가 없습니다.")
        return

    st.subheader("🗺️ 지역별 실거래 요약 맵 & 차트")
    region_summary = df.groupby(["sido", "sigungu"]).agg(
        거래건수=("apt_name", "count"),
        평균거래가=("price_eok", "mean"),
        최고거래가=("price_eok", "max"),
        평균평당가=("price_per_py", "mean")
    ).reset_index()

    region_summary["평균거래가"] = region_summary["평균거래가"].round(2)
    region_summary["평균평당가"] = region_summary["평균평당가"].round(0)
    region_summary.sort_values(by="거래건수", ascending=False, inplace=True)

    fig = px.scatter(
        region_summary,
        x="평균거래가",
        y="거래건수",
        size="거래건수",
        color="sido",
        hover_name="sigungu",
        text="sigungu",
        labels={"평균거래가": "평균 거래금액 (억원)", "거래건수": "거래량 (건)"},
        title="시군구별 거래량 대비 평균 실거래가 분포"
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(margin=dict(t=40, b=20, l=10, r=10), height=550)
    st.plotly_chart(fig, use_container_width=True)

def render_table_tab(df: pd.DataFrame):
    """[탭 4] 실거래가 상세 테이블 및 CSV 다운로드 기능"""
    if df.empty:
        st.info("조회된 데이터가 없습니다.")
        return

    st.subheader("📋 실거래 상세 내역")
    
    col1, col2 = st.columns([8, 2])
    with col1:
        st.caption(f"총 {len(df):,}건의 거래 내역이 표시됩니다.")
    with col2:
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv_data,
            file_name=f"apt_real_price_recent_7days_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    display_df = df[[
        "deal_date", "sido", "sigungu", "dong", "apt_name",
        "price_eok", "area", "pyeong", "floor", "build_year",
        "price_per_py", "deal_type"
    ]].copy()

    display_df.columns = [
        "계약일자", "시도", "시군구", "법정동", "단지명",
        "거래가(억)", "면적(㎡)", "평형", "층", "건축년도",
        "평당가(만원)", "거래유형"
    ]

    st.dataframe(
        display_df.style.format({
            "거래가(억)": "{:.2f}",
            "면적(㎡)": "{:.1f}",
            "평형": "{:.1f}",
            "층": "{:d}",
            "건축년도": "{:d}",
            "평당가(만원)": "{:,.0f}"
        }),
        use_container_width=True,
        height=600
    )
