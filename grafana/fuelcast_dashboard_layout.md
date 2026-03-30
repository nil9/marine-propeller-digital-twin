# FuelCast Dashboard Layout (Grafana)

This dashboard uses exported files from `scripts/export_fuelcast_metrics.py`:

- `data/grafana/fuelcast_metrics.csv`
- `data/grafana/fuelcast_baseline.json`

## Panel layout

### Top row: KPI stat cards
1. **Mean actual efficiency**
   - Source: `fuelcast_baseline.json`
   - Field: `mean_actual_efficiency`
2. **Mean efficiency gap %**
   - Source: `fuelcast_baseline.json`
   - Field: `mean_efficiency_gap_pct`
3. **Anomaly count**
   - Source: `fuelcast_baseline.json`
   - Field: `anomaly_count`

### Middle row: deviation + anomaly context
4. **Deviation line** (time series)
   - Source: `fuelcast_metrics.csv`
   - X-axis: `timestamp`
   - Y-axis: `efficiency_deviation_pct`
   - Add threshold lines at `+anomaly_threshold_pct` and `-anomaly_threshold_pct`
5. **Anomaly markers** (state timeline or annotations)
   - Source: `fuelcast_metrics.csv`
   - Use `anomaly_detected == 1` as marker condition

### Bottom row: power + environment
6. **Power gap** (bar or line)
   - Source: `fuelcast_metrics.csv`
   - X-axis: `timestamp`
   - Y-axis: `power_gap_w`
7. **Environmental context** (multi-line chart)
   - Source: `fuelcast_metrics.csv`
   - Lines:
     - `relative_head_wind_mps`
     - `current_aiding_mps`
     - `beaufort_scale`
     - `wave_proxy_index`

## Suggested panel titles

- Mean actual efficiency
- Mean efficiency gap %
- Anomaly count
- Efficiency deviation vs threshold
- Anomaly markers
- Power gap (actual - expected)
- Environmental context

## Export command

```bash
python3 scripts/export_fuelcast_metrics.py
```

If your Grafana datasource is SQL, import the CSV/JSON into a table first and map field names directly.
If your datasource is JSON API, convert the CSV with `scripts/export_fuelcast_json_api.py` and map:

- `metrics[*]` for time-series panels
- `baseline.*` for KPI stat panels
