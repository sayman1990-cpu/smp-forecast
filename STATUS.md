# 진행 상황

> 집/회사 오가며 작업 — 다시 시작할 때 이 파일부터 읽을 것.
> 최종 수정: 2026-09-13

## 지금 한 줄 요약

**SMP 실제 수집 성공, DB에 쌓이는 중, 대시보드로 조회 가능.** 5분수급현황/발전원별발전량 수집기도 코드는 완성했지만 **운영계정 승인 대기 중이라 아직 실제 수집은 안 됨**. 전망 모델(Phase 2)은 손대지 않고 있음 — 데이터 쌓는 것에만 집중하기로 확정.

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
| **5분 수급현황 수집기** | `src/collectors/kpx_sukub.py` | ⏸ 코드 완성, **API 승인 대기라 실 테스트 못 함** (아래 상세) |
| **발전원별 발전량 수집기** | `src/collectors/kpx_genfuel.py` | ⏸ 코드 완성, **API 승인 대기라 실 테스트 못 함** (아래 상세) |
| GitHub 백업 | [sayman1990-cpu/smp-forecast](https://github.com/sayman1990-cpu/smp-forecast) (private) | ✅ 커밋마다 push |

### kpx_sukub.py / kpx_genfuel.py 상세

- **출처**: 공공데이터포털이 아니라 **전력거래소(KPX) 자체 OpenAPI** (`openapi.kpx.or.kr`).
  사용자가 "전력거래소 OpenAPI 활용자가이드(ver1.6).pdf"를 `data/` 폴더에 직접 넣어줘서
  정확한 스펙(엔드포인트/필드명)을 그 문서 기준으로 확정함 — 추측 없이 만든 코드
- **kpx_sukub.py**: `getSukub5mToday` — 오늘 하루치 5분단위 수급현황(공급능력/현재수요/
  최대예측수요/공급·운영예비력·예비율). **날짜 파라미터가 없어 항상 "오늘"만 나옴** →
  과거 백필 불가, 하루에 여러 번 불러서 우리가 직접 이력을 쌓아야 함
- **kpx_genfuel.py**: `getSumperfuel5m` — 연료원별(수력/유류/유연탄/원자력/양수/가스/
  국내탄/태양광/풍력/신재생/ppa추정/btm추정) 현재 발전량 스냅샷 1건. 이것도 "현재"만
  나와서 주기적으로 불러야 이력이 쌓임
- **응답 형식이 XML** (SMP API는 JSON이었는데 이건 다름) — `xml.etree.ElementTree`로 파싱,
  가이드 문서의 예시 XML로 parse() 유닛테스트 통과 확인
- **막힌 지점**: 실제 API 호출 시 `30 SERVICE KEY IS NOT REGISTERED ERROR` —
  이 두 데이터셋을 공공데이터포털에서 **아직 승인 못 받은 상태로 추정** (운영계정 심사 대기 중일
  가능성 높음). **승인 나면 재시도만 하면 됨**, 코드 수정 불필요할 것으로 예상

### kpx_smp.py 상세 (실제 확인된 스펙)

- **데이터셋**: 한국전력거래소_계통한계가격 및 수요예측(하루전 발전계획용)
- **End Point**: `https://apis.data.go.kr/B552115/SmpWithForecastDemand/getSmpWithForecastDemand`
- **요청**: `serviceKey`, `pageNo`, `numOfRows`(100), `dataType`(json), `date`(YYYYMMDD)
- **계정 상태**: 개발계정, 자동승인, 활용기간 2025-08-18~2027-08-18, **트래픽 하루 100건**
- **응답 필드**: `date`, `hour`("01"~"24", -1해서 DB엔 0~23으로 저장), `areaName`("육지"만 씀), `smp`, `jlfd`/`slfd`/`mlfd`(부하예측 3종 — `slfd`를 육지 수요예측으로 잠정 사용, 공식 필드설명 없어 스케일 추정)
- **검증 완료**: 오늘 날짜 24시간 실 수집 성공, DB 적재 성공, 재실행해도 중복 없음(멱등성) 확인, `data/warehouse.duckdb`에 현재 **360행**(2026-08-28 ~ 2026-09-11)

---

## 지금 막혀서 기다리는 것

- **공공데이터포털 운영계정 전환 신청** — 진행 중 (주말이라 승인 지연 중). 개발계정은 하루 100건이라 과거 데이터 대량 백필이 느림.
- **5분수급현황 / 발전원별발전량 API 승인** — 신청은 돼있는데 실제 호출하면 "서비스키 미등록" 에러. 마이페이지에서 이 두 항목 "처리상태"가 승인인지 확인 필요.
- **Hostinger VPS** — 있다고 확인만 됐고, 아직 실제 배포는 안 함. 지금은 로컬(이 PC)에서만 돈다.

## 다음에 할 일 (우선순위 순)

1. **API 승인 확인/기다리기** — 마이페이지에서 SMP(이미 승인됨), 수급현황, 발전량 각각 처리상태 확인. 승인되면:
   - SMP: `scripts/backfill.py --from 2015-01-01`로 과거 10년치 백필
   - 수급현황/발전량: 승인만 나면 `kpx_sukub.py`/`kpx_genfuel.py` 바로 재테스트 (코드는 이미 완성)
2. **다른 수집기 추가** — 남은 항목(태양광, 기상, 연료단가, 원전현황, 공휴일)도 같은 패턴으로 추가 예정. 기상청/ECOS 등은 공공데이터포털이라 이번 SMP처럼 마이페이지 캡처로, KPX 소속 항목은 이번에 확보한 "전력거래소 OpenAPI 활용자가이드" PDF에 더 있는지 확인
3. **VPS 배포** — 수집기가 몇 개 더 붙으면, VPS에 옮겨서 cron으로 매일 자동 수집되게 설정
4. **Phase 2(전망 모델)는 지금 손대지 않기로 확정** — 방향만 "우리가 직접 급전 시뮬레이션(merit-order)"으로 잠정 검토했으나 설계도 미착수. 데이터 충분히 쌓인 뒤 시작

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
5. `STATUS.md 현재 상태로 업데이트`
6. `STATUS.md: PC 전환은 OneDrive 자동동기화로 처리하기로 결정`
7. `STATUS.md: GitHub 백업 저장소 정보 추가`
8. `5분 수급현황 / 발전원별 발전량 수집기 추가 (승인 대기 중, 테스트는 미완)`
