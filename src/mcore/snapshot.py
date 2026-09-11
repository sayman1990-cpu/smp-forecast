"""M-Core 실행 결과 + 입력 가정 스냅샷 저장 (기획서 8절).

M-Core는 사내 시스템이라 현재는 결과 파일(xlsx/csv)을 수동으로 받는다.
이 스크립트는 그 수동 인계 파일을 표준 폴더 구조로 정리·보관해서,
나중에 출력보정층(bias_correct)과 입력감사층(audit) 학습에 쓸 이력을 쌓는다.

지금 안 쌓으면 6개월 뒤에도 같은 고민을 반복한다 — 매 실행마다 바로 실행할 것.

사용 예:
    python -m src.mcore.snapshot ^
        --output "C:\path\to\mcore_result.xlsx" ^
        --assumptions "C:\path\to\assumptions.yaml" ^
        --executor "홍길동" ^
        --purpose "9월 정기 전망" ^
        --mcore-version "2026.08"

assumptions 인자를 아직 못 받았다면 생략 가능 (meta.json에 미확보로 기록되고,
assumptions.json은 빈 객체로 저장 — 나중에 --assumptions만 다시 넘겨
--update 로 채워 넣을 수 있다).

저장 결과 (기획서 8절 형식 그대로):
    data/mcore/YYYYMMDD_HHMM/
        ├── assumptions.json
        ├── output_hourly.csv
        └── meta.json
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MCORE_DATA_DIR = PROJECT_ROOT / "data" / "mcore"


def _load_assumptions(path: Path | None) -> dict:
    if path is None:
        return {}
    if path.suffix.lower() in {".yaml", ".yml"}:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    raise ValueError(f"assumptions 파일 형식을 알 수 없음: {path.suffix}")


def _load_output(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"output 파일 형식을 알 수 없음: {path.suffix}")


def take_snapshot(
    output_path: Path,
    assumptions_path: Path | None,
    executor: str,
    purpose: str,
    mcore_version: str,
    run_dir_name: str | None = None,
) -> Path:
    """스냅샷 폴더를 만들고 세 파일을 저장한다. 생성된 폴더 경로를 반환."""

    output_path = Path(output_path)
    if not output_path.exists():
        raise FileNotFoundError(f"output 파일이 없음: {output_path}")

    ts = datetime.now()
    dir_name = run_dir_name or ts.strftime("%Y%m%d_%H%M")
    run_dir = MCORE_DATA_DIR / dir_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # output_hourly.csv — 원본이 csv면 그대로 복사, xlsx면 변환
    df = _load_output(output_path)
    df.to_csv(run_dir / "output_hourly.csv", index=False, encoding="utf-8-sig")

    # 원본 파일도 무손실 보관 (엑셀 서식/시트가 여러 개일 수 있으므로)
    raw_copy_dir = run_dir / "raw_source"
    raw_copy_dir.mkdir(exist_ok=True)
    shutil.copy2(output_path, raw_copy_dir / output_path.name)

    # assumptions.json
    assumptions = _load_assumptions(Path(assumptions_path) if assumptions_path else None)
    with (run_dir / "assumptions.json").open("w", encoding="utf-8") as f:
        json.dump(assumptions, f, ensure_ascii=False, indent=2)

    # meta.json
    meta = {
        "executor": executor,
        "purpose": purpose,
        "mcore_version": mcore_version,
        "snapshot_taken_at": ts.isoformat(timespec="seconds"),
        "source_output_file": output_path.name,
        "assumptions_complete": assumptions_path is not None,
        "row_count": len(df),
        "columns": list(df.columns.astype(str)),
    }
    with (run_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, help="M-Core 결과 파일 (xlsx/csv)")
    parser.add_argument("--assumptions", default=None, help="입력 가정 파일 (yaml/json). 없으면 생략 가능")
    parser.add_argument("--executor", required=True, help="실행자")
    parser.add_argument("--purpose", required=True, help="실행 목적 (예: '9월 정기 전망')")
    parser.add_argument("--mcore-version", required=True, help="M-Core 버전/일자")
    args = parser.parse_args()

    run_dir = take_snapshot(
        output_path=Path(args.output),
        assumptions_path=Path(args.assumptions) if args.assumptions else None,
        executor=args.executor,
        purpose=args.purpose,
        mcore_version=args.mcore_version,
    )
    print(f"스냅샷 저장 완료: {run_dir}")
    if args.assumptions is None:
        print("⚠ assumptions 없이 저장됨. 가정 파일 받으면 같은 폴더의 assumptions.json을 채워 넣을 것.")


if __name__ == "__main__":
    main()
