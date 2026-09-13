"""발전원별 발전량 수집기 (4-1절). KPX 자체 OpenAPI (openapi.kpx.or.kr).

데이터셋: "전력거래소 OpenAPI 활용자 가이드(ver1.6)" 2.6절 원별발전량현황조회

확인된 스펙:
    - End Point: https://openapi.kpx.or.kr/openapi/sumperfuel5m/getSumperfuel5m
    - 요청변수: ServiceKey만
    - 응답: XML, 현재 시점 스냅샷 1건(서비스명에 "Today"가 없어 하루치 누적이 아닌
      "현재" 값으로 보임 — 예제 응답도 item 1개뿐). 과거 백필 불가, 주기적으로 불러서
      우리가 직접 이력을 쌓아야 한다.
    - 응답 필드(연료원별 발전량, 단위 MW): fuelPwr1~10 + ppa/btm 추정 + 시장수요(현재)
        fuelPwr1 수력, fuelPwr2 유류, fuelPwr3 유연탄, fuelPwr4 원자력, fuelPwr5 양수,
        fuelPwr6 가스, fuelPwr7 국내탄, fuelPwr8 태양광(시장), fuelPwr9 풍력, fuelPwr10 신재생,
        pEsmw ppa 추정, pEmsw btm 추정, fuelPwrTot 시장수요(현재)
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd

from src.collectors.base import BaseCollector, CollectorError

BASE_URL = "https://openapi.kpx.or.kr/openapi/sumperfuel5m/getSumperfuel5m"

FUEL_MAP = {
    "fuelPwr1": "수력",
    "fuelPwr2": "유류",
    "fuelPwr3": "유연탄",
    "fuelPwr4": "원자력",
    "fuelPwr5": "양수",
    "fuelPwr6": "가스",
    "fuelPwr7": "국내탄",
    "fuelPwr8": "태양광(시장)",
    "fuelPwr9": "풍력",
    "fuelPwr10": "신재생",
    "pEsmw": "ppa추정",
    "pEmsw": "btm추정",
}


class KpxGenFuelCollector(BaseCollector):
    source_name = "kpx_genfuel"

    def __init__(self, service_key: str | None = None):
        self.service_key = service_key or os.environ.get("DATA_GO_KR_SERVICE_KEY")
        if not self.service_key:
            raise CollectorError("DATA_GO_KR_SERVICE_KEY 가 .env에 없음")

    def fetch_raw(self) -> dict:
        resp = self._request(BASE_URL, {"ServiceKey": self.service_key})
        return {"raw_xml": resp.text}

    def parse(self, raw: dict) -> pd.DataFrame:
        root = ET.fromstring(raw["raw_xml"])

        result_code = root.findtext("./header/resultCode") or root.findtext("resultCode")
        if result_code not in (None, "00"):
            result_msg = root.findtext("./header/resultMsg") or root.findtext("resultMsg")
            raise CollectorError(f"API 에러 응답: {result_code} {result_msg}")

        rows = []
        for item in root.findall("./body/items/item"):
            base_dt = item.findtext("baseDatetime")
            ts = datetime.strptime(base_dt, "%Y%m%d%H%M%S") if base_dt else None
            market_demand = item.findtext("fuelPwrTot")
            market_demand_mw = float(market_demand) if market_demand not in (None, "") else None

            for tag, fuel_name in FUEL_MAP.items():
                val = item.findtext(tag)
                if val in (None, ""):
                    continue
                rows.append(
                    {
                        "ts": ts,
                        "fuel_type": fuel_name,
                        "gen_mw": float(val),
                        "market_demand_mw": market_demand_mw,
                    }
                )

        df = pd.DataFrame(rows)
        return df.dropna(subset=["ts"]).reset_index(drop=True) if not df.empty else df


if __name__ == "__main__":
    collector = KpxGenFuelCollector()
    df = collector.run()
    print(df.shape)
    print(df)
