# 진행 상황

> 집/회사 오가며 작업 — 다시 시작할 때 이 파일부터 읽을 것.
> 최종 수정: 2026-09-11

## 지금 한 줄 요약

**SMP 실제 수집 성공, DB에 15일치 쌓임, 대시보드로 조회 가능.** 다음 할 일은 운영계정 승인 기다리면서 다른 데이터 항목 수집기 추가하는 것.

## 큰 그림 (원래 기획에서 순서 재조정함)

원래 기획서(`README.md`)는 M-Core 엔진 위에 4단 전망 모델을 얹는 구조였는데,
**현재는 M-Core 데이터 접근이 어려워서 순서를 바꿨다**:

```
Phase 1 (지금 여기)                    Phase 2 (데이터 충분히 쌓이면, 나중)
────────────────────                   ──────────────────────────────
수집기 → DuckDB 장기 적재 → 대시보드     →   전망 엔진 → SMP 오차분석
```

전망 모델은 아직 안 만든다. 지금은 데이터를 최대한 많이, 길게 쌓고 눈으로 보는 것까지가 목표.

---

## 완료된 것

| 항목 | 파일 | 상태 |
|---|---|---|
| 프로젝트 뼈대 | `config/`, `src/`, `scripts/`, `data/` | ✅ |
| DuckDB 스키마 | `src/storage/schema.sql` | ✅ (9개 테이블, PK/UPSERT 설계) |
| DB 연결/적재 헬퍼 | `src/storage/db.py` | ✅ |
| 수집기 공통 베이스 | `src/collectors/base.py` | ✅ 재시도, 원본 무손실 저장, 파싱 분리 |
| **SMP+수요예측 수집기** | `src/collectors/kpx_smp.py` | ✅ **실제 API로 검증 완료** (아래 상세) |
| 품질 게이트 | `src/quality/checks.py` | ✅ 24행/일, SMP범위, 급변플래그 |
| cron 진입점 | `scripts/daily.py` | ✅ (아직 VPS/스케줄러 미등록, 수동 실행만 확인) |
| 백필 스크립트 | `scripts/backfill.py` | ✅ 동작 확인 (최근 14일치 실제로 채움) |
| **시장 대시보드** | `src/report/dashboard.py` | ✅ **로컬에서 실행 중** (`http://localhost:8501`) |
| M-Core 스냅샷 스크립트 | `src/mcore/snapshot.py` | ✅ (M-Core 접근 가능해지면 사용) |
| 로컬 git 저장소 | `smp-forecast/.git` | ✅ 커밋 이력으로 변경사항 추적 중 |

### kpx_smp.py 상세 (실제 확인된 스펙)

- **데이터셋**: 한국전력거래소_계통한계가격 및 수요예측(하루전 발전계획용)
- **End Point**: `https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand`
- **요청**: `serviceKey`, `pageNo`, `numOfRows`(100), `dataType`(json), `date`(YYYYMMDD)
- **계정 상태**: 개발계정, 자동승인, 활용기간 2025-08-18~2027-08-18, **트래픽 하루 100건**
- **응답 필드**: `date`, `hour`("01"~"24", -1해서 DB엔 0~23으로 저장), `areaName`("육지"만 씀), `smp`, `jlfd`/`slfd`/`mlfd`(부하예측 3종 — `slfd`를 육지 수요예측으로 잠정 사용, 공식 필드설명 없어 스케일 추정)
- **검증 완료**: 오늘 날짜 24시간 실 수집 성공, DB 적재 성공, 재실행해도 중복 없음(멱등성) 확인, `data/warehouse.duckdb`에 현재 **360행**(2026-08-28 ~ 2026-09-11)

---

## 지금 막혀서 기다리는 것

- **공공데이터포털 운영계정 전환 신청** — 진행 중 (개발계정은 하루 100건이라 과거 데이터 대량 백필이 느림). 신청서에 "대표 이미지(썸네일)" 등 요구하는 화면 나오는 중.
- **Hostinger VPS** — 있다고 확인만 됐고, 아직 실제 배포는 안 함. 지금은 로컬(이 PC)에서만 돈다.

## 다음에 할 일 (우선순위 순)

1. **운영계정 승인 기다리기** — 승인되면 `scripts/backfill.py --from 2015-01-01`로 과거 10년치 백필 가능
2. **다른 수집기 추가** — 지금은 SMP 하나뿐. 기획서 4-1절 나머지 항목(5분수급현황, 발전원별발전량, 태양광, 기상, 연료단가, 원전현황, 공휴일)도 `kpx_smp.py`와 같은 패턴(`BaseCollector` 상속, `fetch_raw`+`parse` 구현)으로 하나씩 추가 예정. **각 항목마다 이번처럼 마이페이지에서 API 상세페이지 캡처를 받아야 정확한 필드명을 알 수 있음**
3. **VPS 배포** — 수집기가 몇 개 더 붙으면, VPS에 옮겨서 cron으로 매일 자동 수집되게 설정
4. Phase 2(전망 모델)는 데이터가 충분히 쌓인 뒤 — 지금은 손대지 않음

---

## 백업 / 저장 위치

| | 저장 위치 | 용도 |
|---|---|---|
| 코드 | [GitHub: sayman1990-cpu/smp-forecast](https://github.com/sayman1990-cpu/smp-forecast) (private) | 백업 + 변경 이력 |
| 데이터 (DB, 원본 JSON) | OneDrive 자동 동기화 | 집/회사 PC 간 데이터 이동 |
| API 키 (`.env`) | 각 PC에 개별 설정, 어디에도 공유 저장 안 함 | 새 PC에서는 `.env.example` 복사해서 직접 키 입력 필요 |

## 집/회사 PC 전환 방법 (VPS 배포 전까지 임시방편)

프로젝트 폴더 자체가 OneDrive(`C:\Users\sayma\OneDrive\전망sys\`) 안에 있어서
**데이터 파일(`data/warehouse.duckdb` 등)도 OneDrive로 자동 동기화된다** (git과는 별개).

- ⚠ **PC를 옮기기 전에**: 대시보드(streamlit) 껐는지, 실행 중인 스크립트 없는지 확인하고
  OneDrive 동기화 완료(초록 체크) 확인 후 이동할 것 — DB 파일이 열린 채로 옮기면
  동기화가 덜 된 상태로 넘어갈 수 있음
- 회사 PC에서는: OneDrive 동기화 기다리기 → VS Code로 `전망sys` 폴더 열기 →
  이 `STATUS.md` 읽기 → 이어서 작업

## 다시 시작할 때 확인 명령어 (집/회사 PC 바뀔 때)

```bash
cd smp-forecast
pip install -e .              # 처음 여는 PC라면 패키지 설치
copy .env.example .env        # 처음이라면, 그다음 API 키 채우기
python -m src.storage.db      # DB 스키마 확인/초기화
streamlit run src/report/dashboard.py   # 대시보드 띄우기 (localhost:8501)
```

지금까지 쌓인 실제 데이터(`data/warehouse.duckdb`, `data/raw/`)는 git에는 안 올라가지만
(`.gitignore`로 제외) **OneDrive로는 자동 동기화됨** — 위 "집/회사 PC 전환 방법" 참고.

## 변경 이력 (git 커밋 기준)

1. `0주차: 프로젝트 뼈대 + M-Core 스냅샷 스크립트`
2. `Phase 1: 구조 재조정 - 데이터 수집/DB/대시보드 우선`
3. `kpx_smp 수집기: 실제 API 스펙 반영해서 완성`
4. `대시보드 차트 버그 수정: hour 인덱스가 y축에 잡히던 문제`
