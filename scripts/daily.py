"""cron 진입점 (5절 수집 스케줄). VPS에서 이 스크립트를 등록해서 매일 돌린다.

지금은 kpx_smp 하나만 연결. 다른 수집기가 생기면 COLLECTORS 딕셔너리에 추가.
텔레그램 알림은 TODO — 기존 봇 토큰 붙이는 부분만 채우면 됨.
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.collectors.kpx_smp import KpxSmpCollector  # noqa: E402
from src.storage.db import get_connection, init_schema, upsert  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("daily")


def run_kpx_smp(target_date: date) -> None:
    collector = KpxSmpCollector()
    df = collector.run(base_date=target_date.strftime("%Y%m%d"))
    if df.empty:
        logger.warning("kpx_smp: 빈 결과 (%s)", target_date)
        return
    conn = get_connection()
    init_schema(conn)
    upsert(conn, "smp_hourly", df, pk_cols=["date", "hour", "market_type", "unit_id"])
    logger.info("kpx_smp: %d행 upsert (%s)", len(df), target_date)


def main() -> None:
    # 하루전 SMP는 전날 발표분 기준으로 어제/오늘 둘 다 시도 (발표 시점에 따라)
    for d in (date.today() - timedelta(days=1), date.today()):
        try:
            run_kpx_smp(d)
        except Exception:
            logger.exception("kpx_smp 실패 (%s)", d)
            # TODO: 텔레그램 알림 연동 (기획서 5절)


if __name__ == "__main__":
    main()
