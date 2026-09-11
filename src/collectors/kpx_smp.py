"""하루전 SMP + 수요예측 수집기 (4-1절 최우선 항목).

데이터셋: 공공데이터포털 "한국전력거래소_계통한계가격 및 수요예측(하루전 발전계획용)"
https://www.data.go.kr/data/15131225/openapi.do

⚠ 파라미터/응답 필드명은 TODO — 공공데이터포털 상세페이지의 Swagger UI가
이미지로 렌더링돼 있어 자동으로 못 긁어왔다. API 키 확인할 때 아래를 할 것:
    1. 위 URL 접속 → "Swagger 가이드" 펼치기 → "Try it out" 실행
    2. 실제 요청 URL, 파라미터명(날짜/페이지 등), 응답 JSON 예시를 확인
    3. 아래 BASE_URL / build_params() / parse()의 TODO 부분을 그 예시에 맞춰 수정

일단 데이터고 공공데이터포털 공통 규약(서비스키+페이지네이션+XML/JSON 응답)에
맞춰 뼈대를 짜뒀다 — 실제 필드명만 나중에 끼워 넣으면 됨.

주의(기획서 4-1절):
- 거래시간 0시 = 0:00~01:00 구간. 응답의 시간 인덱스가 1~24인지 0~23인지 반드시 확인.
- 구 `계통한계가격조회` API는 삭제 예정이므로 이 신규 API만 쓴다.
"""

from __future__ import annotations

import os

import pandas as pd

from src.collectors.base import BaseCollector, CollectorError

# TODO: Swagger 문서에서 실제 엔드포인트로 교체
BASE_URL = "https://apis.data.go.kr/B552115/PwrTradeSmpDamPreOpe/getSmpDamPreOpe"


class KpxSmpCollector(BaseCollector):
    source_name = "kpx_smp"

    def __init__(self, service_key: str | None = None):
        self.service_key = service_key or os.environ.get("DATA_GO_KR_SERVICE_KEY")
        if not self.service_key:
            raise CollectorError("DATA_GO_KR_SERVICE_KEY 가 .env에 없음")

    def _build_params(self, base_date: str, page_no: int = 1, num_of_rows: int = 100) -> dict:
        # TODO: 실제 파라미터명 확인 후 수정 (baseDate/searchDate 등 이름이 다를 수 있음)
        return {
            "serviceKey": self.service_key,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "dataType": "JSON",
            "baseDate": base_date,  # YYYYMMDD
        }

    def fetch_raw(self, base_date: str) -> dict:
        """base_date: 'YYYYMMDD'. 하루치 24시간 데이터를 받아온다."""
        params = self._build_params(base_date)
        resp = self._request(BASE_URL, params)
        try:
            return resp.json()
        except ValueError as e:
            raise CollectorError(f"JSON 파싱 실패: {resp.text[:200]}") from e

    def parse(self, raw: dict) -> pd.DataFrame:
        # TODO: 실제 응답 구조에 맞춰 경로 수정. 아래는 공공데이터포털 표준 응답 형태 가정:
        # {"response": {"header": {...}, "body": {"items": {"item": [...]}}}}
        try:
            items = raw["response"]["body"]["items"]["item"]
        except (KeyError, TypeError) as e:
            raise CollectorError(f"예상 못한 응답 구조: {raw}") from e

        if isinstance(items, dict):  # 단일 행이면 dict로 오는 경우 있음
            items = [items]

        df = pd.DataFrame(items)

        # TODO: 실제 컬럼명 확인 후 매핑 (예시 추정치)
        rename_map = {
            "baseDate": "date",
            "tradeHour": "hour",  # 1~24 이면 -1 필요 (기획서 4-1절 인덱스 주의)
            "smp": "smp_krw_kwh",
            "forecastDemand": "demand_forecast_mw",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce").dt.date
        if "hour" in df.columns:
            df["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64")

        df["market_type"] = "day_ahead"
        df["unit_id"] = "MARKET"
        df["source"] = self.source_name

        keep = ["date", "hour", "market_type", "unit_id", "smp_krw_kwh", "demand_forecast_mw", "source"]
        return df[[c for c in keep if c in df.columns]]


if __name__ == "__main__":
    import sys

    date_arg = sys.argv[1] if len(sys.argv) > 1 else pd.Timestamp.now().strftime("%Y%m%d")
    collector = KpxSmpCollector()
    df = collector.run(base_date=date_arg)
    print(df)
