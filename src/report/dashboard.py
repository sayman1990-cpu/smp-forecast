"""시장 대시보드 (Streamlit). DuckDB에 쌓인 데이터를 필터링해서 보여준다.

실행:
    streamlit run src/report/dashboard.py

지금 단계 목표(기획서 재구성): 전망 모델 없이, 쌓인 데이터를 내 입맛대로
기간·항목별로 조회하는 것. 전망은 데이터가 충분히 쌓인 뒤 다음 단계.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.db import get_connection  # noqa: E402

st.set_page_config(page_title="SMP 시장 대시보드", layout="wide")

TABLES = {
    "시간별 SMP / 수요예측": "smp_hourly",
    "5분 수급현황": "sukub_5min",
    "발전원별 발전량": "gen_by_source",
    "지역별 태양광": "solar_regional_hourly",
    "발전기별 변동비": "unit_cost_monthly",
    "기상(실황/예보)": "weather",
    "연료단가·환율": "fuel_fx_monthly",
    "원전 호기 현황": "nuclear_unit_status",
    "자사 호기 실적": "own_unit_actual",
}


@st.cache_resource
def _conn():
    return get_connection()


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table]
    ).fetchone()
    return row[0] > 0


def load(table: str, date_from: date, date_to: date) -> pd.DataFrame:
    conn = _conn()
    if not _table_exists(conn, table):
        return pd.DataFrame()

    cols = [r[0] for r in conn.execute(f"DESCRIBE {table}").fetchall()]
    date_col = "date" if "date" in cols else ("ts" if "ts" in cols else None)

    if date_col:
        query = f"SELECT * FROM {table} WHERE {date_col} BETWEEN ? AND ? ORDER BY {date_col}"
        return conn.execute(query, [date_from, date_to]).fetchdf()
    return conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchdf()


st.title("육지 SMP · 시장 대시보드")
st.caption("전망 모델 이전 단계 — 수집된 데이터를 원하는 기간·항목으로 조회")

with st.sidebar:
    st.header("필터")
    default_from = date.today() - timedelta(days=30)
    date_from = st.date_input("시작일", default_from)
    date_to = st.date_input("종료일", date.today())
    table_label = st.selectbox("데이터 항목", list(TABLES.keys()))
    table_name = TABLES[table_label]

df = load(table_name, date_from, date_to)

if df.empty:
    st.warning(
        f"'{table_label}' 테이블에 데이터가 없습니다. "
        f"수집기가 아직 안 돌았거나(scripts/daily.py) 스키마만 있고 적재 전입니다."
    )
else:
    st.subheader(table_label)
    st.dataframe(df, use_container_width=True, height=350)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        y_col = st.selectbox("차트로 볼 항목", numeric_cols)
        x_col = "date" if "date" in df.columns else ("ts" if "ts" in df.columns else df.columns[0])
        color_col = None
        for c in ["unit_id", "market_type", "region", "fuel_type", "kind"]:
            if c in df.columns and df[c].nunique() > 1:
                color_col = c
                break
        fig = px.line(df, x=x_col, y=y_col, color=color_col, markers=True)
        st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "CSV로 내려받기",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{table_name}_{date_from}_{date_to}.csv",
    )

st.divider()
st.subheader("수집 현황 요약")
conn = _conn()
rows = []
for label, tbl in TABLES.items():
    if _table_exists(conn, tbl):
        cols = [r[0] for r in conn.execute(f"DESCRIBE {tbl}").fetchall()]
        date_col = "date" if "date" in cols else ("ts" if "ts" in cols else None)
        cnt = conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        if date_col and cnt:
            span = conn.execute(f"SELECT min({date_col}), max({date_col}) FROM {tbl}").fetchone()
            rows.append({"항목": label, "행수": cnt, "시작": span[0], "끝": span[1]})
        else:
            rows.append({"항목": label, "행수": cnt, "시작": None, "끝": None})
    else:
        rows.append({"항목": label, "행수": 0, "시작": None, "끝": None})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
