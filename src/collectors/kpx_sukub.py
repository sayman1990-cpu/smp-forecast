"""5분 수급현황 수집기 (4-1절). KPX 자체 OpenAPI (openapi.kpx.or.kr) — 공공데이터포털이 아니라
전력거래소가 직접 운영하는 별도 서버. 서비스키는 공공데이터포털에서 발급받은 것을 그대로 쓴다
(가이드 문서 "계통한계가격조회" 요청변수 설명에 명시됨).

데이터셋: "전력거래소 OpenAPI 활용자 가이드(ver1.6)" 2.2절 오늘전력수급현황조회
(data/전력거래소 OpenAPI 활용자가이드(ver1.6).pdf 참조, 사용자가 직접 확보한 정식 문서)

확인된 스펙:
    - End Point: https://openapi.kpx.or.kr/openapi/sukub5mToday/getSukub5mToday
    - 요청변수: ServiceKey (이것만 있으면 됨, 날짜 지정 불가 — 항상 "오늘" 하루치)
    - 응답: XML (JSON 옵션 없음)
    - 갱신주기 5분. "오늘" 데이터만 나오므로 과거 백필은 불가능 —
      매일 여러 번(또는 자정 직전 1번) 호출해서 우리가 직접 역사를 쌓아야 한다.
    - 응답 필드: baseDatetime(YYYYMMDDHHMMSS), suppAbility(공급능력),
      currPwrTot(현재수요), forecastLoad(최대예측수요), suppReservePwr(공급예비력),
      suppReserveRate(공급예비율%), operReservePwr(운영예비력), operReserveRate(운영예비율%)
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd

from src.collectors.base import BaseCollector, CollectorError

BASE_URL = "https://openapi.kpx.or.kr/openapi/sukub5mToday/getSukub5mToday"


class KpxSukubCollector(BaseCollector):
    source_name = "kpx_sukub"

    def __init__(self, service_key: str | None = None):
        self.service_key = service_key or os.environ.get("DATA_GO_KR_SERVICE_KEY")
        if not self.service_key:
            raise CollectorError("DATA_GO_KR_SERVICE_KEY 가 .env에 없음")

    def fetch_raw(self) -> dict:
        # 날짜 파라미터 없음 — 항상 오늘 하루치를 통째로 준다.
        resp = self._request(BASE_URL, {"ServiceKey": self.service_key})
        return {"raw_xml": resp.text}

    def parse(self, raw: dict) -> pd.DataFrame:
        root = ET.fromstring(raw["raw_xml"])

        result_code = root.findtext("./header/resultCode")
        if result_code not in (None, "00"):
            result_msg = root.findtext("./header/resultMsg")
            raise CollectorError(f"API 에러 응답: {result_code} {result_msg}")

        rows = []
        for item in root.findall("./body/items/item"):

            def num(tag: str) -> float | None:
                text = item.findtext(tag)
                return float(text) if text not in (None, "") else None

            base_dt = item.findtext("baseDatetime")
            rows.append(
                {
                    "ts": datetime.strptime(base_dt, "%Y%m%d%H%M%S") if base_dt else None,
                    "supply_capacity_mw": num("suppAbility"),
                    "demand_mw": num("currPwrTot"),
                    "forecast_load_mw": num("forecastLoad"),
                    "supply_reserve_mw": num("suppReservePwr"),
                    "supply_reserve_rate": num("suppReserveRate"),
                    "oper_reserve_mw": num("operReservePwr"),
                    "oper_reserve_rate": num("operReserveRate"),
                }
            )

        df = pd.DataFrame(rows)
        return df.dropna(subset=["ts"]).reset_index(drop=True) if not df.empty else df


if __name__ == "__main__":
    collector = KpxSukubCollector()
    df = collector.run()
    print(df.shape)
    print(df.tail())
