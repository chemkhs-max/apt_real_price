from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.services.gemini_service import build_daily_stats_summary, generate_analyst_report


def test_build_daily_stats_summary_empty():
    df = pd.DataFrame()
    stats = build_daily_stats_summary(df, "2026-09-30")
    assert "거래 내역이 없습니다" in stats
    assert "2026-09-30" in stats


def test_build_daily_stats_summary_with_data():
    data = [
        {
            "deal_date": "2026-09-30",
            "sido": "서울특별시",
            "sigungu": "강남구",
            "dong": "압구정동",
            "apt_name": "현대",
            "area": 84.0,
            "pyeong": 25.4,
            "floor": 10,
            "price_manwon": 450000,
            "price_eok": 45.0,
            "deal_type": "중개거래",
        },
        {
            "deal_date": "2026-09-30",
            "sido": "경기도",
            "sigungu": "성남시 분당구",
            "dong": "서현동",
            "apt_name": "시범한양",
            "area": 59.0,
            "pyeong": 17.8,
            "floor": 5,
            "price_manwon": 120000,
            "price_eok": 12.0,
            "deal_type": "중개거래",
        },
    ]
    df = pd.DataFrame(data)
    stats = build_daily_stats_summary(df, "2026-09-30")

    assert "총 거래 건수: 2건" in stats
    assert "현대" in stats
    assert "45.0" in stats
    assert "서울특별시 강남구" in stats


def test_generate_analyst_report_no_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        generate_analyst_report("샘플 통계 데이터", api_key="")


@patch("src.services.gemini_service.genai.Client")
def test_generate_analyst_report_success(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "## 📌 오늘의 마켓 헤드라인\n부동산 시장 관망세 지속"
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    result = generate_analyst_report(
        "샘플 통계 데이터",
        api_key="valid_test_key",
        model="gemini-3.8-flash",
    )

    assert "오늘의 마켓 헤드라인" in result
    mock_client.models.generate_content.assert_called_once()
