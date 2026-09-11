"""수집기 공통 베이스 (5절 아키텍처).

모든 수집기는 이 패턴을 따른다:
    1. API 호출 (재시도 포함)
    2. 원본 응답을 data/raw/YYYY/MM/DD/<source>_<timestamp>.json 로 무손실 저장
    3. 표 형태(DataFrame)로 파싱
    4. 품질검사 (quality/checks.py)
    5. DuckDB UPSERT (storage/db.py)

개별 수집기(kpx_smp.py 등)는 fetch_raw()/parse() 두 개만 구현하면 된다.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


class CollectorError(Exception):
    """수집기 실패 (재시도 다 소진했거나 응답 형식이 이상함)."""


class BaseCollector(ABC):
    """소스 하나당 이 클래스를 상속해서 fetch_raw()/parse()만 구현한다."""

    source_name: str  # 예: "kpx_smp" — 파일명/로그/알림에 쓰임

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((requests.RequestException, CollectorError)),
        reraise=True,
    )
    def _request(self, url: str, params: dict, timeout: int = 15) -> requests.Response:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp

    @abstractmethod
    def fetch_raw(self, **kwargs) -> dict | list:
        """API를 호출해 원본 JSON(dict/list)을 반환. 재시도는 _request()가 처리."""

    @abstractmethod
    def parse(self, raw: dict | list) -> pd.DataFrame:
        """원본 JSON을 DB 스키마에 맞는 DataFrame으로 변환."""

    def save_raw(self, raw: dict | list, when: datetime | None = None) -> Path:
        when = when or datetime.now()
        day_dir = RAW_DIR / when.strftime("%Y") / when.strftime("%m") / when.strftime("%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{self.source_name}_{when.strftime('%H%M%S')}.json"
        path = day_dir / fname
        with path.open("w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2, default=str)
        return path

    def run(self, **kwargs) -> pd.DataFrame:
        """전체 파이프라인 실행: 호출 → 원본 저장 → 파싱. DB 적재는 scripts/daily.py에서."""
        raw = self.fetch_raw(**kwargs)
        self.save_raw(raw)
        df = self.parse(raw)
        logger.info("%s: %d행 수집", self.source_name, len(df))
        return df
