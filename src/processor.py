from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any
import pandas as pd
from src.config import DATA_DIR, DATA_FILE_PATH, METADATA_PATH

def calculate_date_range(today: date | None = None) -> tuple[date, date, list[str]]:
    """
    실행일 기준 롤링 7일 날짜 범위와 조회 대상 연월(YYYYMM) 목록을 계산합니다.
    예: 9월 30일 -> 9월 24일 ~ 9월 30일, ['202609']
    예: 10월 3일 -> 9월 27일 ~ 10월 3일, ['202609', '202610']
    """
    if today is None:
        today = date.today()
    start_date = today - timedelta(days=6)
    end_date = today

    ymd_set = set()
    cur = start_date
    while cur <= end_date:
        ymd_set.add(cur.strftime("%Y%m"))
        # 다음달 1일로 넘어가거나 하루씩 증가
        cur += timedelta(days=1)

    return start_date, end_date, sorted(list(ymd_set))

def clean_price_string(price_val: Any) -> int:
    """거래금액 문자열('   15,000 ')에서 콤마 및 공백을 제거하고 정수(만원)로 변환합니다."""
    if price_val is None:
        return 0
    if isinstance(price_val, (int, float)):
        return int(price_val)
    
    s = str(price_val).replace(",", "").replace(" ", "").strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0

def process_raw_deals(raw_items: list[dict], start_date: date, end_date: date) -> pd.DataFrame:
    """
    국토부 API에서 수집된 원본 딕셔너리 리스트를 정제하고,
    롤링 7일 범위 필터링 및 파생 컬럼을 추가한 DataFrame을 생성합니다.
    """
    processed = []
    for item in raw_items:
        try:
            year = int(item.get("dealYear", 0))
            month = int(item.get("dealMonth", 0))
            day = int(item.get("dealDay", 0))
            if year == 0 or month == 0 or day == 0:
                continue
            deal_date = date(year, month, day)
        except (ValueError, TypeError):
            continue

        # 날짜 범위 체크 (최근 7일)
        if not (start_date <= deal_date <= end_date):
            continue

        sido = str(item.get("sido", "")).strip()
        sigungu = str(item.get("sigungu", "")).strip()
        dong = str(item.get("umdNm") or item.get("dong", "")).strip()
        apt_name = str(item.get("aptNm", "")).strip()
        
        try:
            area = float(item.get("excluUseAr", 0.0))
        except (ValueError, TypeError):
            area = 0.0

        try:
            floor = int(item.get("floor", 0))
        except (ValueError, TypeError):
            floor = 0

        try:
            build_year = int(item.get("buildYear", 0))
        except (ValueError, TypeError):
            build_year = 0

        price_manwon = clean_price_string(item.get("dealAmount"))
        price_eok = round(price_manwon / 10000.0, 2)
        
        # 평형 및 평당가 계산
        pyeong = round(area / 3.305785, 1) if area > 0 else 0.0
        price_per_py = round(price_manwon / pyeong, 1) if pyeong > 0 else 0.0
        deal_type = str(item.get("dealingGbn", "중개거래")).strip() or "중개거래"

        processed.append({
            "deal_date": deal_date,
            "sido": sido,
            "sigungu": sigungu,
            "dong": dong,
            "apt_name": apt_name,
            "area": area,
            "pyeong": pyeong,
            "floor": floor,
            "build_year": build_year,
            "price_manwon": price_manwon,
            "price_eok": price_eok,
            "price_per_py": price_per_py,
            "deal_type": deal_type
        })

    if not processed:
        cols = [
            "deal_date", "sido", "sigungu", "dong", "apt_name",
            "area", "pyeong", "floor", "build_year",
            "price_manwon", "price_eok", "price_per_py", "deal_type"
        ]
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(processed)
    # 정렬: 계약일 내림차순, 거래가 내림차순
    df.sort_values(by=["deal_date", "price_manwon"], ascending=[False, False], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def save_processed_data(df: pd.DataFrame, meta_extra: dict | None = None) -> None:
    """정제된 DataFrame을 Parquet 파일로 저장하고 metadata.json을 생성합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Parquet 저장
    df.to_parquet(DATA_FILE_PATH, engine="pyarrow", compression="snappy", index=False)
    
    # 메타데이터 생성
    now_kst = datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
    min_date = str(df["deal_date"].min()) if not df.empty else ""
    max_date = str(df["deal_date"].max()) if not df.empty else ""
    
    metadata = {
        "last_updated_at": now_kst,
        "start_date": min_date,
        "end_date": max_date,
        "total_deals": len(df),
    }
    if meta_extra:
        metadata.update(meta_extra)

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
