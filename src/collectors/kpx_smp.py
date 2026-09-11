"""하루전 SMP + 수요예측 수집기 (4-1절 최우선 항목).

데이터셋: 공공데이터포털 "한국전력거래소_계통한계가격 및 수요예측(하루전 발전계획용)"
https://www.data.go.kr/data/15131225/openapi.do

확인된 요청 스펙 (2026-09-11, 마이페이지 활용신청 상세기능정보 + 미리보기 캡처 기준):
    - End Point: https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand
    - 요청변수: serviceKey, pageNo, numOfRows, dataType(json/xml), date(YYYYMMDD)
    - 일일 트래픽: 100건 (개발계정) — 백필 시 --sleep 넉넉히 줄 것

확인된 응답 필드 (미리보기 예시):
    {
      "response": {
        "header": {"resultCode": "00", "resultMsg": "OK"},
        "body": {
          "totalCount": "117909", "numOfRows": "10", "pageNo": "1",
          "items": {"item": [
            {"date": "20260914", "hour": "01", "areaName": "육지",
             "smp": 98.64, "jlfd": 649.0, "slfd": 51829.0, "mlfd": 51180.0, "rn": 1},
            ...
          ]}
        }
      }
    }
    - date: YYYYMMDD 문자열
    - hour: "01"~"24" 문자열. **거래시간 0시=0:00~01:00 구간(4-1절)이므로
      hour="01"을 우리 DB의 hour=0으로 저장** (즉 응답 hour - 1)
    - areaName: "육지" / "제주" 등 — 이 프로젝트는 육지만 다루므로 필터링
    - smp: 원/kWh
    - jlfd / slfd / mlfd: 부하(수요)예측 관련 3종 필드. 공식 필드 설명서를 아직
      못 받아서 정확한 의미는 불확실 — 값 스케일로 추정하면 slfd(4.8만~6만대)가
      육지 전체 수요예측치로 보여 일단 이걸 demand_forecast_mw로 쓴다.
      jlfd(600~800대)는 제주로 추정. mlfd는 slfd와 비슷하나 근소하게 낮음(수정치 추정).
      → 원본은 raw JSON에 그대로 보관되니, 정확한 의미 확인되면 매핑만 바꾸면 됨.

주의(기획서 4-1절):
- 구 `계통한계가격조회` API는 삭제 예정이므로 이 신규 API만 쓴다.
"""

from __future__ import annotations

import os

import pandas as pd

from src.collectors.base import BaseCollector, CollectorError

BASE_URL = "https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand"


class KpxSmpCollector(BaseCollector):
    source_name = "kpx_smp"

    def __init__(self, service_key: str | None = None):
        self.service_key = service_key or os.environ.get("DATA_GO_KR_SERVICE_KEY")
        if not self.service_key:
            raise CollectorError("DATA_GO_KR_SERVICE_KEY 가 .env에 없음")

    def _build_params(self, date: str, page_no: int = 1, num_of_rows: int = 100) -> dict:
        # numOfRows=100: 육지+제주 합쳐 최대 48행이면 충분하지만 여유있게.
        # 개발계정 트래픽 100건/일이므로 하루에 여러 번 부르지 않도록 한 번에 넉넉히 받는다.
        return {
            "serviceKey": self.service_key,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "dataType": "json",
            "date": date,  # YYYYMMDD
        }

    def fetch_raw(self, base_date: str) -> dict:
        """base_date: 'YYYYMMDD'. 하루치 24시간 데이터를 받아온다."""
        params = self._build_params(date=base_date)
        resp = self._request(BASE_URL, params)
        try:
            return resp.json()
        except ValueError as e:
            raise CollectorError(f"JSON 파싱 실패: {resp.text[:200]}") from e

    def parse(self, raw: dict) -> pd.DataFrame:
        header = raw.get("response", {}).get("header", {})
        if header.get("resultCode") not in (None, "00"):
            raise CollectorError(f"API 에러 응답: {header}")

        try:
            items = raw["response"]["body"]["items"]["item"]
        except (KeyError, TypeError) as e:
            raise CollectorError(f"예상 못한 응답 구조: {raw}") from e

        if isinstance(items, dict):  # 하루 1건뿐이면 dict로 올 수 있음
            items = [items]
        if not items:
            return pd.DataFrame(columns=["date", "hour", "market_type", "unit_id", "smp_krw_kwh", "demand_forecast_mw", "source"])

        df = pd.DataFrame(items)

        # 육지만 사용 (프로젝트 범위). areaName 컬럼이 없으면(응답 변형 대비) 전체 사용.
        if "areaName" in df.columns:
            df = df[df["areaName"] == "육지"].copy()

        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce").dt.date
        # 응답 hour는 "01"~"24" (거래시간, 1-based). DB는 0~23이므로 -1.
        df["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64") - 1
        df["smp_krw_kwh"] = pd.to_numeric(df["smp"], errors="coerce")
        df["demand_forecast_mw"] = pd.to_numeric(df.get("slfd"), errors="coerce")  # 잠정 매핑, 위 docstring 참조

        df["market_type"] = "day_ahead"
        df["unit_id"] = "MARKET"
        df["source"] = self.source_name

        keep = ["date", "hour", "market_type", "unit_id", "smp_krw_kwh", "demand_forecast_mw", "source"]
        return df[keep].reset_index(drop=True)


if __name__ == "__main__":
    import sys

    date_arg = sys.argv[1] if len(sys.argv) > 1 else pd.Timestamp.now().strftime("%Y%m%d")
    collector = KpxSmpCollector()
    df = collector.run(base_date=date_arg)
    print(df)
