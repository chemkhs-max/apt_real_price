import pandas as pd
from datetime import date
import pytest
from src.dashboard_views import filter_data, get_metrics

@pytest.fixture
def sample_deals_df():
    return pd.DataFrame([
        {
            "deal_date": date(2026, 9, 28),
            "sido": "서울특별시", "sigungu": "강남구", "dong": "개포동",
            "apt_name": "개포자이", "area": 84.97, "pyeong": 25.7,
            "floor": 15, "build_year": 2023, "price_manwon": 285000,
            "price_eok": 28.5, "price_per_py": 11089.5, "deal_type": "중개거래"
        },
        {
            "deal_date": date(2026, 9, 29),
            "sido": "경기도", "sigungu": "성남시 분당구", "dong": "백현동",
            "apt_name": "판교푸르지오", "area": 59.9, "pyeong": 18.1,
            "floor": 8, "build_year": 2015, "price_manwon": 140000,
            "price_eok": 14.0, "price_per_py": 7734.8, "deal_type": "중개거래"
        },
        {
            "deal_date": date(2026, 9, 25),
            "sido": "부산광역시", "sigungu": "해운대구", "dong": "우동",
            "apt_name": "해운대아이파크", "area": 120.5, "pyeong": 36.5,
            "floor": 30, "build_year": 2011, "price_manwon": 190000,
            "price_eok": 19.0, "price_per_py": 5205.5, "deal_type": "중개거래"
        }
    ])

def test_filter_data_by_sido(sample_deals_df):
    filtered = filter_data(
        sample_deals_df,
        sido="서울특별시",
        sigungu_list=[],
        area_category="전체",
        price_min=0.0,
        price_max=100.0,
        search_query=""
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["sido"] == "서울특별시"
    assert filtered.iloc[0]["apt_name"] == "개포자이"

def test_filter_data_by_area_and_price(sample_deals_df):
    # 국민평형 (59㎡ ~ 84㎡): 판교푸르지오 (area: 59.9, price: 14.0억)
    filtered = filter_data(
        sample_deals_df,
        sido="전체",
        sigungu_list=[],
        area_category="국민평형(59~84㎡)",
        price_min=10.0,
        price_max=20.0,
        search_query=""
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["apt_name"] == "판교푸르지오"


def test_filter_data_by_search_query(sample_deals_df):
    filtered = filter_data(
        sample_deals_df,
        sido="전체",
        sigungu_list=[],
        area_category="전체",
        price_min=0.0,
        price_max=100.0,
        search_query="아이파크"
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["apt_name"] == "해운대아이파크"

def test_get_metrics(sample_deals_df):
    metrics = get_metrics(sample_deals_df)
    assert metrics["total_count"] == 3
    assert metrics["avg_price_eok"] == round((28.5 + 14.0 + 19.0) / 3, 2)
    assert "개포자이" in metrics["max_deal_title"]
    assert metrics["max_price_eok"] == 28.5
    assert metrics["avg_price_per_py"] > 0
