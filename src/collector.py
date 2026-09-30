import concurrent.futures
from datetime import date
import json
import logging
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
import requests

from src.config import API_URL, LAWD_CD_PATH, get_api_key
from src.processor import calculate_date_range, process_raw_deals, save_processed_data

logger = logging.getLogger(__name__)

def parse_xml_response(xml_text: str) -> list[dict]:
    """공공데이터 국토교통부 아파트 실거래가 XML 응답을 파싱하여 딕셔너리 리스트로 변환합니다."""
    if not xml_text or not xml_text.strip():
        return []

    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError as e:
        logger.warning(f"XML 파싱 실패: {e}")
        return []

    # 결과 코드 확인
    header = root.find("header")
    if header is not None:
        result_code = header.findtext("resultCode", "")
        if result_code not in ("00", "000"):
            result_msg = header.findtext("resultMsg", "Unknown error")
            logger.warning(f"API 오류 응답: [{result_code}] {result_msg}")
            return []

    items_node = root.find(".//items")
    if items_node is None:
        return []

    results = []
    for item in items_node.findall("item"):
        record = {}
        for child in item:
            record[child.tag] = child.text.strip() if child.text else ""
        results.append(record)

    return results

def fetch_sigungu_deals(
    lawd_cd: str,
    ymd: str,
    api_key: str,
    sido: str = "",
    sigungu: str = "",
    timeout: int = 10,
    retries: int = 3
) -> list[dict]:
    """
    단일 시군구와 특정 연월(YYYYMM)의 실거래가 데이터를 공공데이터포털 API로부터 수집합니다.
    일시적인 네트워크 장애 시 최대 retries 횟수만큼 재시도합니다.
    """
    if not api_key:
        logger.error("API 키가 제공되지 않았습니다.")
        return []

    # 공공데이터포털 인증키 디코딩 (requests가 params 전달 시 인코딩하므로 이미 인코딩된 키의 이중인코딩 방지)
    decoded_key = urllib.parse.unquote(api_key)

    params = {
        "serviceKey": decoded_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": ymd,
        "numOfRows": 1000,
        "pageNo": 1
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/xml"
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(API_URL, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                items = parse_xml_response(resp.text)
                for item in items:
                    item["sido"] = sido
                    item["sigungu"] = sigungu
                return items
            else:
                logger.warning(f"[{lawd_cd}-{ymd}] HTTP {resp.status_code} (시도 {attempt}/{retries})")
        except Exception as e:
            logger.warning(f"[{lawd_cd}-{ymd}] 요청 오류: {e} (시도 {attempt}/{retries})")

    logger.error(f"[{lawd_cd}-{ymd}] {retries}회 재시도 후 수집 실패")
    return []

def collect_all_7days(
    api_key: str | None = None,
    max_workers: int = 8,
    today: date | None = None
) -> pd.DataFrame:
    """
    전국 250개 시군구의 최근 7일 롤링 아파트 실거래가를 병렬 수집하고 저장합니다.
    """
    if not api_key:
        api_key = get_api_key()
    if not api_key:
        raise ValueError("공공데이터포털 API 키(DATA_GO_KR_API_KEY)가 설정되지 않았습니다.")

    start_date, end_date, ymd_list = calculate_date_range(today)
    print(f"[*] 최근 7일 롤링 수집 시작: {start_date} ~ {end_date} (대상 연월: {ymd_list})")

    # 시군구 목록 로드
    with open(LAWD_CD_PATH, "r", encoding="utf-8") as f:
        lawd_list = json.load(f)

    # 병렬 태스크 목록 생성
    tasks = []
    for ymd in ymd_list:
        for item in lawd_list:
            tasks.append({
                "code": item["code"],
                "ymd": ymd,
                "sido": item.get("sido", ""),
                "sigungu": item.get("sigungu", "")
            })

    total_tasks = len(tasks)
    print(f"[*] 총 {total_tasks}개 수집 태스크를 {max_workers}개 스레드로 실행합니다...")

    all_raw_deals = []
    success_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(
                fetch_sigungu_deals,
                t["code"],
                t["ymd"],
                api_key,
                t["sido"],
                t["sigungu"]
            ): t for t in tasks
        }

        for i, future in enumerate(concurrent.futures.as_completed(future_to_task), 1):
            t = future_to_task[future]
            try:
                deals = future.result()
                all_raw_deals.extend(deals)
                success_count += 1
            except Exception as e:
                logger.error(f"태스크 오류 ({t['code']}): {e}")

            if i % 50 == 0 or i == total_tasks:
                print(f"  - 진행률: {i}/{total_tasks} ({i*100//total_tasks}%) 완료 (현재 누적 {len(all_raw_deals)}건)")

    print(f"[*] 원본 데이터 수집 완료: 총 {len(all_raw_deals)}건 수집됨 (성공 태스크: {success_count}/{total_tasks})")

    # 데이터 정제 및 7일 필터링
    df = process_raw_deals(all_raw_deals, start_date, end_date)
    print(f"[*] 롤링 7일 정제 완료: 유효 거래 {len(df)}건")

    # Parquet 및 metadata 저장
    meta_extra = {
        "total_tasks": total_tasks,
        "successful_tasks": success_count,
        "total_deals": len(df)
    }
    save_processed_data(df, meta_extra)
    print("[*] 데이터 저장 완료 (data/recent_7days.parquet, data/metadata.json)")

    return df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        collect_all_7days()
    except Exception as err:
        print(f"[!] 오류 발생: {err}")
