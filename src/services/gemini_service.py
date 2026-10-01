import logging
from typing import Any
from google import genai
import pandas as pd

from src.config import get_gemini_api_key

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-3.7-flash", "gemini-3.5-flash"]


def build_daily_stats_summary(daily_df: pd.DataFrame, deal_date: str) -> str:
    """
    일자별 거래 데이터프레임을 Gemini 부동산 애널리스트 프롬프트용 텍스트 통계표로 가공합니다.
    """
    if daily_df.empty:
        return f"[{deal_date}] 해당 일자에는 수집된 아파트 실거래 내역이 없습니다."

    total_deals = len(daily_df)
    avg_price = daily_df["price_eok"].mean()
    median_price = daily_df["price_eok"].median()
    max_price = daily_df["price_eok"].max()
    min_price = daily_df["price_eok"].min()

    # 최고가 TOP 3
    top3_df = daily_df.sort_values(by="price_eok", ascending=False).head(3)
    top3_lines = []
    for idx, (_, row) in enumerate(top3_df.iterrows(), 1):
        top3_lines.append(
            f"  {idx}. {row.get('sido', '')} {row.get('sigungu', '')} {row.get('apt_name', '')} "
            f"({row.get('area', 0.0)}㎡, {row.get('floor', 0)}층) - {row.get('price_eok', 0.0)}억원"
        )
    top3_text = "\n".join(top3_lines) if top3_lines else "  내역 없음"

    # 지역별 거래량 TOP 5 (시도 + 시군구)
    df_copy = daily_df.copy()
    df_copy["region"] = df_copy["sido"].astype(str) + " " + df_copy["sigungu"].astype(str)
    region_counts = df_copy["region"].value_counts().head(5)
    region_lines = []
    for reg, count in region_counts.items():
        sub_mean = df_copy[df_copy["region"] == reg]["price_eok"].mean()
        region_lines.append(f"  - {reg}: {count}건 (평균 {sub_mean:.2f}억원)")
    region_text = "\n".join(region_lines) if region_lines else "  내역 없음"

    # 평형대별 분포
    small = len(df_copy[df_copy["area"] <= 59.0])
    mid = len(df_copy[(df_copy["area"] > 59.0) & (df_copy["area"] <= 84.0)])
    large = len(df_copy[df_copy["area"] > 84.0])

    small_pct = (small / total_deals) * 100
    mid_pct = (mid / total_deals) * 100
    large_pct = (large / total_deals) * 100

    summary_text = f"""[분석 대상 일자: {deal_date}]
1. 전체 시장 개요:
  - 총 거래 건수: {total_deals}건
  - 평균 거래가격: {avg_price:.2f}억원
  - 중간값 거래가격: {median_price:.2f}억원
  - 최고 거래가격: {max_price:.2f}억원 / 최저 거래가격: {min_price:.2f}억원

2. 당일 최고가 거래 TOP 3:
{top3_text}

3. 거래량 상위 5개 지역:
{region_text}

4. 평형대별 거래 비중:
  - 소형 (~59㎡): {small}건 ({small_pct:.1f}%)
  - 국민평형 (59~84㎡): {mid}건 ({mid_pct:.1f}%)
  - 대형 (84㎡ 초과): {large}건 ({large_pct:.1f}%)
"""
    return summary_text


def generate_analyst_report(
    stats_summary: str,
    api_key: str | None = None,
    model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    """
    구글 Gemini API를 호출하여 부동산 전문 애널리스트 톤의 마켓 리포트를 생성합니다.
    """
    if api_key is None:
        api_key = get_gemini_api_key()

    if not api_key or not str(api_key).strip():
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    system_instruction = (
        "당신은 15년 경력의 대한민국 아파트 시장 수석 부동산 애널리스트입니다.\n"
        "제공된 당일 아파트 실거래 통계 데이터를 면밀히 분석하여, 전문적이고 통찰력 있는 일일 마켓 리포트를 작성하세요.\n"
        "추측보다는 제공된 수치와 사실에 충실하며, 간결하고 신뢰도 높은 어조를 유지하세요.\n\n"
        "반드시 아래의 4가지 목차(마크다운 헤더)를 갖추어 출력하세요:\n"
        "## 📌 오늘의 마켓 헤드라인\n"
        "(당일 거래 시장의 분위기를 한 줄로 명쾌하게 요약)\n\n"
        "## 🏆 주요 거래 하이라이트\n"
        "(최고가 거래 단지의 입지·평형적 특징 및 가격 흐름 집중 분석)\n\n"
        "## 🗺️ 지역 및 평형별 거래 동향\n"
        "(거래가 집중된 지역과 국민평형 등 선호 평형대의 특징 분석)\n\n"
        "## 💡 애널리스트 관전 포인트\n"
        "(실수요자와 투자자 관점에서 주목할 시사점 및 단기 체크포인트 2~3가지)"
    )

    client = genai.Client(api_key=api_key)
    prompt = f"다음은 분석할 당일 아파트 실거래 통계 데이터입니다:\n\n{stats_summary}\n\n위 데이터를 바탕으로 부동산 애널리스트 리포트를 작성해 주세요."

    models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_error = None

    for attempt_model in models_to_try:
        try:
            logger.info(f"Gemini API 호출 시도 (모델: {attempt_model})...")
            response = client.models.generate_content(
                model=attempt_model,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.3,
                },
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e
            err_str = str(e)
            logger.warning(f"모델 [{attempt_model}] 호출 실패: {err_str[:150]}")
            # 503이나 일시적 과부하인 경우 다음 fallback 모델로 전환 시도
            if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                continue
            # 그 외의 치명적 오류(인증 실패 등)는 즉시 raise
            raise RuntimeError(f"Gemini API 호출 실패: {e}") from e

    raise RuntimeError(f"모든 Gemini 모델 호출 실패: {last_error}") from last_error
