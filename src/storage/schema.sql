-- DuckDB 스키마 (5절). market_type 컬럼을 처음부터 넣는다:
-- 실시간시장이 전국 확대되면 가격이 '하루전'/'실시간'으로 갈라지기 때문.
-- PK: (date, hour, market_type, unit_id) — 시장 전체 SMP 행은 unit_id='MARKET'으로 고정.

CREATE TABLE IF NOT EXISTS smp_hourly (
    date         DATE    NOT NULL,
    hour         TINYINT NOT NULL,          -- 0~23, 0=00:00~01:00 구간 (인덱스 변환 주의, 4-1절)
    market_type  VARCHAR NOT NULL,           -- 'day_ahead' | 'real_time'
    unit_id      VARCHAR NOT NULL DEFAULT 'MARKET',
    smp_krw_kwh  DOUBLE,
    demand_forecast_mw DOUBLE,
    source       VARCHAR,                    -- 수집기 이름 (추적용)
    collected_at TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (date, hour, market_type, unit_id)
);

CREATE TABLE IF NOT EXISTS sukub_5min (
    ts               TIMESTAMP NOT NULL,
    demand_mw        DOUBLE,
    supply_capacity_mw DOUBLE,
    reserve_mw       DOUBLE,
    collected_at     TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (ts)
);

CREATE TABLE IF NOT EXISTS gen_by_source (
    date        DATE NOT NULL,
    hour        TINYINT NOT NULL,
    fuel_type   VARCHAR NOT NULL,
    gen_mwh     DOUBLE,
    PRIMARY KEY (date, hour, fuel_type)
);

CREATE TABLE IF NOT EXISTS solar_regional_hourly (
    date        DATE NOT NULL,
    hour        TINYINT NOT NULL,
    region      VARCHAR NOT NULL,
    gen_mwh     DOUBLE,
    PRIMARY KEY (date, hour, region)
);

CREATE TABLE IF NOT EXISTS unit_cost_monthly (
    year_month  VARCHAR NOT NULL,             -- 'YYYY-MM'
    unit_id     VARCHAR NOT NULL,
    fuel_type   VARCHAR,
    variable_cost_krw_per_mwh DOUBLE,
    heat_rate   DOUBLE,
    PRIMARY KEY (year_month, unit_id)
);

CREATE TABLE IF NOT EXISTS weather (
    date        DATE NOT NULL,
    hour        TINYINT NOT NULL,
    region      VARCHAR NOT NULL,
    kind        VARCHAR NOT NULL,             -- 'actual' | 'forecast' — 백테스트는 반드시 forecast 사용
    issued_at   TIMESTAMP,                    -- forecast일 때 발표 시각 (정보 시점 고정용)
    temp_c      DOUBLE,
    solar_rad   DOUBLE,
    cloud       DOUBLE,
    PRIMARY KEY (date, hour, region, kind, issued_at)
);

CREATE TABLE IF NOT EXISTS fuel_fx_monthly (
    year_month      VARCHAR NOT NULL,
    lng_import_price DOUBLE,
    dubai_oil_price  DOUBLE,
    fx_krw_usd       DOUBLE,
    PRIMARY KEY (year_month)
);

CREATE TABLE IF NOT EXISTS nuclear_unit_status (
    date        DATE NOT NULL,
    unit_id     VARCHAR NOT NULL,
    output_mw   DOUBLE,
    status      VARCHAR,                      -- 운전/정비/고장
    PRIMARY KEY (date, unit_id)
);

CREATE TABLE IF NOT EXISTS holidays (
    date        DATE NOT NULL,
    name        VARCHAR,
    PRIMARY KEY (date)
);

-- 자사 호기 실적 (4-4절 사내 자료)
CREATE TABLE IF NOT EXISTS own_unit_actual (
    date        DATE NOT NULL,
    hour        TINYINT NOT NULL,
    unit_id     VARCHAR NOT NULL,
    output_mw   DOUBLE,
    status      VARCHAR,                      -- on/off/제약운전
    PRIMARY KEY (date, hour, unit_id)
);

-- 자동 채점용 뷰는 evaluate/metrics.py 에서 쿼리로 생성 (여기서는 원장 테이블만 정의)
