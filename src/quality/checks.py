"""품질 게이트 (5절): 하루 24행 존재 / SMP 범위(0~400) / 전일 대비 급변 플래그.
결측은 임의 보간 금지 — NaN 유지, 플래그만 남긴다.
"""

from __future__ import annotations

import pandas as pd

SMP_RANGE = (0, 400)
SPIKE_THRESHOLD_RATIO = 0.5  # 전일 대비 50% 이상 변하면 플래그


def check_hours_per_day(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """날짜별 행 수가 24가 아니면 리포트."""
    counts = df.groupby(date_col).size().rename("row_count").reset_index()
    counts["ok"] = counts["row_count"] == 24
    return counts[~counts["ok"]]


def check_smp_range(df: pd.DataFrame, col: str = "smp_krw_kwh") -> pd.DataFrame:
    lo, hi = SMP_RANGE
    out = df[(df[col].notna()) & ((df[col] < lo) | (df[col] > hi))]
    return out


def flag_spikes(df: pd.DataFrame, col: str = "smp_krw_kwh", date_col: str = "date") -> pd.DataFrame:
    """날짜별 평균이 전일 대비 급변하면 플래그. 2022 고유가 구간처럼 진짜 급변도 있으니
    자동 제거하지 말고 플래그만 남겨서 사람이 판단하게 한다."""
    daily = df.groupby(date_col)[col].mean().reset_index().sort_values(date_col)
    daily["prev"] = daily[col].shift(1)
    daily["change_ratio"] = (daily[col] - daily["prev"]).abs() / daily["prev"].replace(0, pd.NA)
    return daily[daily["change_ratio"] > SPIKE_THRESHOLD_RATIO]


def run_all(df: pd.DataFrame) -> dict:
    return {
        "missing_hours": check_hours_per_day(df),
        "out_of_range": check_smp_range(df),
        "spikes": flag_spikes(df),
    }
