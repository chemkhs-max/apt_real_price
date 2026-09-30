from pathlib import Path
import os
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 디렉터리 경로
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 데이터 파일 경로
LAWD_CD_PATH = DATA_DIR / "lawd_cd.json"
DATA_FILE_PATH = DATA_DIR / "recent_7days.parquet"
METADATA_PATH = DATA_DIR / "metadata.json"

# 공공데이터포털 국토교통부 아파트 매매 실거래가 API 엔드포인트
API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


def get_api_key() -> str:
    """환경변수에서 공공데이터포털 API 인증키를 조회합니다."""
    key = os.getenv("DATA_GO_KR_API_KEY", "").strip()
    return key
