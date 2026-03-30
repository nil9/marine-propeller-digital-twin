CREATE TABLE IF NOT EXISTS fuelcast_metrics (
  id BIGSERIAL PRIMARY KEY,
  source_timestamp TEXT NOT NULL,
  actual_efficiency DOUBLE PRECISION,
  efficiency_deviation_pct DOUBLE PRECISION,
  anomaly_detected BOOLEAN,
  anomaly_score DOUBLE PRECISION,
  anomaly_threshold_pct DOUBLE PRECISION,
  degradation_trend_pct_per_sample DOUBLE PRECISION,
  expected_shaft_power_w DOUBLE PRECISION,
  actual_shaft_power_w DOUBLE PRECISION,
  power_gap_w DOUBLE PRECISION,
  relative_head_wind_mps DOUBLE PRECISION,
  current_aiding_mps DOUBLE PRECISION,
  beaufort_scale INTEGER,
  wave_proxy_index DOUBLE PRECISION,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fuelcast_metrics_ts ON fuelcast_metrics (ts);

CREATE TABLE IF NOT EXISTS fuelcast_baseline (
  id BIGSERIAL PRIMARY KEY,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  mean_actual_efficiency DOUBLE PRECISION,
  mean_efficiency_gap_pct DOUBLE PRECISION,
  anomaly_count INTEGER,
  anomaly_threshold_pct DOUBLE PRECISION,
  rows_evaluated INTEGER,
  calibration_samples INTEGER
);

CREATE INDEX IF NOT EXISTS idx_fuelcast_baseline_captured_at ON fuelcast_baseline (captured_at);
