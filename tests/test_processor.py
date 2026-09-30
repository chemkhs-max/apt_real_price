from datetime import date
import json
import pandas as pd
import pytest
from src.processor import (
    calculate_date_range,
    clean_price_string,
    process_raw_deals,
    save_processed_data,
)
from src.config import DATA_FILE_PATH, METADATA_PATH

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
    assert clean_price_string("") == 0
    assert clean_price_string(None) == 0

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
    assert row["price_per_py"] > 0

def test_save_processed_data(tmp_path, monkeypatch):
    import src.processor as proc
    fake_data_file = tmp_path / "recent_7days.parquet"
    fake_meta_file = tmp_path / "metadata.json"
    monkeypatch.setattr(proc, "DATA_FILE_PATH", fake_data_file)
    monkeypatch.setattr(proc, "METADATA_PATH", fake_meta_file)


    sample_df = pd.DataFrame([{
        "deal_date": date(2026, 9, 28),
        "sido": "서울특별시", "sigungu": "강남구", "dong": "개포동",
        "apt_name": "개포자이", "area": 84.97, "pyeong": 25.7,
        "floor": 15, "build_year": 2023, "price_manwon": 285000,
        "price_eok": 28.5, "price_per_py": 11089.5, "deal_type": "중개거래"
    }])

    save_processed_data(sample_df, {"total_deals": 1})
    assert fake_data_file.exists()
    assert fake_meta_file.exists()
    
    # Read back parquet
    read_df = pd.read_parquet(fake_data_file)
    assert len(read_df) == 1
    assert read_df.iloc[0]["apt_name"] == "개포자이"
