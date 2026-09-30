"""
로컬 개발 및 테스트를 위한 사실적인 7일 롤링 샘플 데이터 생성 스크립트.
실제 API 키가 없어도 대시보드 화면 및 기능을 완벽히 시뮬레이션할 수 있습니다.
"""
from datetime import date, timedelta
from pathlib import Path
import random
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.processor import save_processed_data


APT_NAMES = [
    ("서울특별시", "강남구", "개포동", "개포자이프레지던스", 84.9, 280000, 310000),
    ("서울특별시", "서초구", "반포동", "아크로리버파크", 84.9, 360000, 420000),
    ("서울특별시", "송파구", "잠실동", "잠실엘스", 84.8, 220000, 260000),
    ("서울특별시", "마포구", "아현동", "마포래미안푸르지오", 59.9, 140000, 165000),
    ("서울특별시", "노원구", "상계동", "상계주공7단지", 45.2, 52000, 68000),
    ("경기도", "성남시 분당구", "백현동", "판교푸르지오그랑블", 84.9, 210000, 245000),
    ("경기도", "수원시 영통구", "이의동", "광교중흥S-클래스", 84.9, 140000, 160000),
    ("경기도", "과천시", "원문동", "과천위버필드", 59.9, 135000, 155000),
    ("경기도", "화성시", "청계동", "동탄역시범우남퍼스트빌", 84.9, 95000, 115000),
    ("인천광역시", "연수구", "송도동", "송도더샵퍼스트파크", 84.9, 78000, 92000),
    ("부산광역시", "해운대구", "우동", "해운대두산위브더제니스", 120.4, 160000, 210000),
    ("부산광역시", "수영구", "남천동", "삼익비치", 84.8, 105000, 130000),
    ("대구광역시", "수성구", "범어동", "힐스테이트범어", 84.9, 110000, 135000),
    ("대전광역시", "유성구", "도룡동", "도룡SK뷰", 84.9, 90000, 115000),
    ("광주광역시", "남구", "봉선동", "봉선한국아델리움", 84.9, 85000, 105000),
    ("세종특별자치시", "세종시", "새롬동", "새뜸마을1단지", 84.9, 65000, 80000),
]

def generate_sample_data(days: int = 7, count: int = 250) -> pd.DataFrame:
    today = date.today()
    start_date = today - timedelta(days=days - 1)
    
    rows = []
    for _ in range(count):
        sido, sigungu, dong, apt_name, base_area, min_p, max_p = random.choice(APT_NAMES)
        
        # 날짜 랜덤 선택 (최근 7일)
        rand_days = random.randint(0, days - 1)
        deal_date = start_date + timedelta(days=rand_days)
        
        # 면적 및 가격 살짝 변동
        area = round(base_area * random.uniform(0.95, 1.05), 1)
        pyeong = round(area / 3.305785, 1)
        price_manwon = random.randint(min_p, max_p) // 100 * 100
        price_eok = round(price_manwon / 10000.0, 2)
        price_per_py = round(price_manwon / pyeong, 1) if pyeong > 0 else 0.0
        
        floor = random.randint(1, 35)
        build_year = random.randint(2005, 2024)
        deal_type = random.choice(["중개거래", "중개거래", "중개거래", "직거래"])

        rows.append({
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

    df = pd.DataFrame(rows)
    df.sort_values(by=["deal_date", "price_manwon"], ascending=[False, False], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

if __name__ == "__main__":
    print("[*] 롤링 7일 샘플 실거래가 데이터 생성 중...")
    df = generate_sample_data(days=7, count=300)
    meta_extra = {
        "is_sample_data": True,
        "note": "로컬 테스트 및 데모용 샘플 데이터셋입니다."
    }
    save_processed_data(df, meta_extra)
    print(f"[*] 생성 완료: 총 {len(df)}건 데이터가 data/recent_7days.parquet 에 저장되었습니다.")
