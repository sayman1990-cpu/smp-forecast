# 진행 상황 (구조 재조정 반영)

> 원래 기획(README.md)은 M-Core를 엔진으로 쓰는 4단 전망 시스템이었으나,
> 현재는 M-Core 데이터 접근이 어려워 **순서를 재조정**했다.

## 현재 원칙

전망 모델보다 **데이터 축적 + 대시보드가 먼저**다.

```
Phase 1 (지금 여기)              Phase 2 (데이터 충분히 쌓이면)
────────────────────             ──────────────────────────
수집기 (collectors)          →   전망 엔진 (models)
DuckDB 장기 적재               →   M-Core 재연동 또는 자체 급전 시뮬레이션
시장 대시보드 (조회·시각화)     →   SMP 오차분석 / 자동 채점
```

Phase 1의 목표: 필요한 시장 데이터를 내 입맛대로 조회하고, 장기 DB로 쌓아서
나중에 SMP 오차분석(벤치마크 대비, 시나리오 대비 등)을 할 수 있는 재료를 만드는 것.

## 완료

- [x] 프로젝트 뼈대 (`config/`, `src/`, `scripts/`, `data/`)
- [x] DuckDB 스키마 (`src/storage/schema.sql`) + UPSERT 헬퍼 (`src/storage/db.py`)
- [x] 수집기 공통 베이스 (`src/collectors/base.py`) — 재시도, 원본 무손실 저장, 파싱 분리
- [x] SMP+수요예측 수집기 뼈대 (`src/collectors/kpx_smp.py`) — **파라미터명 확인 필요 (아래 TODO)**
- [x] cron 진입점 (`scripts/daily.py`), 백필 스크립트 (`scripts/backfill.py`)
- [x] 품질 게이트 (`src/quality/checks.py`) — 24행/일, SMP 범위, 급변 플래그
- [x] 시장 대시보드 (`src/report/dashboard.py`, Streamlit) — 기간·항목 필터, 차트, CSV 다운로드, 수집 현황 요약
- [x] M-Core 결과 스냅샷 스크립트 (`src/mcore/snapshot.py`) — M-Core 접근 가능해지면 바로 사용

## 막힌 것 / 확인 필요

- [ ] **공공데이터포털 API 키 확인** — 있는지/개발·운영계정 여부 확인 중
- [ ] **`kpx_smp.py`의 정확한 요청 파라미터·응답 필드명** — Swagger UI가 이미지라 자동 확인 불가.
      키 확인 시 https://www.data.go.kr/data/15131225/openapi.do 에서 "Try it out"으로 실제
      요청/응답 예시를 받아서 `BASE_URL` / `_build_params()` / `parse()`의 TODO 채우기
- [ ] **Hostinger VPS 접속** — IP·SSH 확인 중. 확인되면 배포 진행 (systemd/cron 등록)
- [ ] 나머지 수집기 (5분수급현황, 발전원별발전량, 태양광, 기상, 연료단가, 원전현황, 공휴일) —
      `kpx_smp.py`와 같은 패턴으로 추가 예정. 우선순위는 "최대한 많은 데이터"로 정했으므로
      API 키 확인되는 대로 순서대로 붙여나감

## 로컬에서 지금 해볼 수 있는 것

```bash
pip install -e .
cp .env.example .env   # 키 채우기 (있으면)
python -m src.storage.db          # DuckDB 스키마 초기화만 먼저 확인
streamlit run src/report/dashboard.py   # 빈 대시보드라도 레이아웃 확인 가능
```
