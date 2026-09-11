"""과거 데이터 백필 (5절). 하루씩 돌며 kpx_smp를 채운다.

사용:
    python scripts/backfill.py --from 2015-01-01 --to 2026-09-01

주의: 공공데이터포털 개발계정은 트래픽 100건/일 — 운영계정 전환 전엔
--from을 최근 며칠로 좁혀서 테스트할 것. 2022 고유가·SMP상한제 구간은
값이 튀어도 정상일 수 있음 (기획서 5절 더미 플래그 처리 TODO).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.collectors.kpx_smp import KpxSmpCollector  # noqa: E402
from src.storage.db import get_connection, init_schema, upsert  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")


def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--sleep", type=float, default=0.3, help="호출 간 대기(초), API 과호출 방지")
    args = parser.parse_args()

    d_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
    d_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()

    conn = get_connection()
    init_schema(conn)
    collector = KpxSmpCollector()

    ok, fail = 0, 0
    for d in daterange(d_from, d_to):
        try:
            df = collector.run(base_date=d.strftime("%Y%m%d"))
            if not df.empty:
                upsert(conn, "smp_hourly", df, pk_cols=["date", "hour", "market_type", "unit_id"])
                ok += 1
            else:
                logger.warning("빈 결과: %s", d)
        except Exception:
            logger.exception("실패: %s", d)
            fail += 1
        time.sleep(args.sleep)

    logger.info("백필 완료: 성공 %d일 / 실패 %d일", ok, fail)


if __name__ == "__main__":
    main()
