from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any

from src.config import DAILY_SUMMARY_DB_PATH


class DailySummaryRepository:
    """일자별 Gemini 부동산 애널리스트 요약을 관리하는 SQLite 저장소 클래스입니다."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = DAILY_SUMMARY_DB_PATH
        else:
            self.db_path = Path(db_path)

        # 부모 디렉터리 자동 생성 (파일 경로인 경우)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """데이터베이스 및 테이블을 초기화합니다."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_market_summaries (
                    deal_date TEXT PRIMARY KEY,
                    summary_content TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    deal_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get_summary(self, deal_date: str) -> dict[str, Any] | None:
        """
        특정 거래 일자(YYYY-MM-DD)의 요약 레코드를 조회합니다.
        존재하지 않을 경우 None을 반환합니다.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT deal_date, summary_content, model_name, deal_count, created_at, updated_at
                FROM daily_market_summaries
                WHERE deal_date = ?
                """,
                (deal_date,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def save_summary(
        self,
        deal_date: str,
        summary_content: str,
        model_name: str,
        deal_count: int,
    ) -> None:
        """
        일자별 요약 내용을 저장하거나 이미 존재할 경우 갱신(UPSERT)합니다.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO daily_market_summaries (
                    deal_date, summary_content, model_name, deal_count, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(deal_date) DO UPDATE SET
                    summary_content = excluded.summary_content,
                    model_name = excluded.model_name,
                    deal_count = excluded.deal_count,
                    updated_at = excluded.updated_at
                """,
                (deal_date, summary_content, model_name, deal_count, now_str, now_str),
            )

    def delete_summary(self, deal_date: str) -> bool:
        """
        특정 일자의 요약 레코드를 삭제합니다.
        삭제 성공 시 True, 대상이 없을 시 False를 반환합니다.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM daily_market_summaries WHERE deal_date = ?",
                (deal_date,),
            )
            return cursor.rowcount > 0
