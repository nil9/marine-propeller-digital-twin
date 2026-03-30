#!/usr/bin/env bash
set -euo pipefail

DB_URL="${1:-postgresql:///marine_twin}"
METRICS_CSV="${2:-data/grafana/fuelcast_metrics.csv}"
BASELINE_JSON="${3:-data/grafana/fuelcast_baseline.json}"
SCHEMA_SQL="${4:-sql_grafana_postgres_schema.sql}"

if [[ ! -f "$METRICS_CSV" || ! -f "$BASELINE_JSON" ]]; then
  echo "Grafana exports not found. Generate first:"
  echo "  python3 scripts/export_fuelcast_metrics.py"
  exit 1
fi

psql "$DB_URL" -f "$SCHEMA_SQL"

psql "$DB_URL" <<SQL
DROP TABLE IF EXISTS fuelcast_metrics_stage;
CREATE TEMP TABLE fuelcast_metrics_stage (
  source_timestamp text,
  actual_efficiency text,
  efficiency_deviation_pct text,
  anomaly_detected text,
  anomaly_score text,
  anomaly_threshold_pct text,
  degradation_trend_pct_per_sample text,
  expected_shaft_power_w text,
  actual_shaft_power_w text,
  power_gap_w text,
  relative_head_wind_mps text,
  current_aiding_mps text,
  beaufort_scale text,
  wave_proxy_index text
);
\copy fuelcast_metrics_stage FROM '$METRICS_CSV' WITH (format csv, header true)

INSERT INTO fuelcast_metrics (
  source_timestamp,
  actual_efficiency,
  efficiency_deviation_pct,
  anomaly_detected,
  anomaly_score,
  anomaly_threshold_pct,
  degradation_trend_pct_per_sample,
  expected_shaft_power_w,
  actual_shaft_power_w,
  power_gap_w,
  relative_head_wind_mps,
  current_aiding_mps,
  beaufort_scale,
  wave_proxy_index,
  ts
)
SELECT
  source_timestamp,
  NULLIF(actual_efficiency, '')::double precision,
  NULLIF(efficiency_deviation_pct, '')::double precision,
  (NULLIF(anomaly_detected, '')::int = 1),
  NULLIF(anomaly_score, '')::double precision,
  NULLIF(anomaly_threshold_pct, '')::double precision,
  NULLIF(degradation_trend_pct_per_sample, '')::double precision,
  NULLIF(expected_shaft_power_w, '')::double precision,
  NULLIF(actual_shaft_power_w, '')::double precision,
  NULLIF(power_gap_w, '')::double precision,
  NULLIF(relative_head_wind_mps, '')::double precision,
  NULLIF(current_aiding_mps, '')::double precision,
  NULLIF(beaufort_scale, '')::int,
  NULLIF(wave_proxy_index, '')::double precision,
  now() - interval '1 minute' * (
    (MAX(regexp_replace(source_timestamp, '.*:', '')::int) OVER ())
    - regexp_replace(source_timestamp, '.*:', '')::int
  )
FROM fuelcast_metrics_stage;
SQL

python3 - <<PY | psql "$DB_URL"
import json
from pathlib import Path
p = Path("$BASELINE_JSON")
doc = json.loads(p.read_text())
print("""
INSERT INTO fuelcast_baseline (
  mean_actual_efficiency,
  mean_efficiency_gap_pct,
  anomaly_count,
  anomaly_threshold_pct,
  rows_evaluated,
  calibration_samples
) VALUES (
  {mean_actual_efficiency},
  {mean_efficiency_gap_pct},
  {anomaly_count},
  {anomaly_threshold_pct},
  {rows_evaluated},
  {calibration_samples}
);
""".format(**doc))
PY

echo "Done. Database loaded at: $DB_URL"
echo "Tables: fuelcast_metrics, fuelcast_baseline"
