# Marine Propeller Digital Twin

This repository contains a lightweight prototype for a **digital twin of propeller performance**. It now supports both:

- a baseline physics-style propeller model for thrust-aware telemetry
- a calibrated power-curve workflow for testing against real **FuelCast** ship data

The output analytics remain focused on the propeller monitoring use case you described:

- expected vs actual performance
- efficiency deviation %
- anomaly detection
- performance degradation trend

## Why this concept is important

The twin mirrors the workflow you described:

1. **Baseline ideal propeller model** using propeller geometry and nominal operating conditions.
2. **Real-time comparison** between expected and observed performance.
3. **Analytics layer** that produces deviation, anomaly score, and degradation trend.
4. **Monitoring-ready output** so it can later be paired with CFD-informed calibration, onboard telemetry, or streaming infrastructure.

That makes the current prototype a more realistic stepping stone toward an integrated stack where CFD + monitoring systems feed a real-time analytics loop.

## FuelCast dataset usage

The implementation now includes a reproducible evaluation path using a **FuelCast `cps_poseidon` preview slice** stored locally in `data/fuelcast_cps_poseidon_preview.csv`.

Why a preview slice instead of the full dataset?

- the runtime environment here could inspect the public Hugging Face dataset card and preview rows,
- but direct command-line download access to Hugging Face was blocked by the environment proxy,
- so the repo now includes a small real-data sample transcribed from the public viewer for repeatable evaluation.

The FuelCast card describes the dataset as 5-minute vessel telemetry with operational and environmental measurements from three ships, including propeller shaft power, shaft torque, vessel speed, and total fuel consumption.

## Combo A environmental conditioning (FuelCast + ERA5 + Copernicus currents)

You can now enrich FuelCast rows with optional environment columns and the twin will condition expected shaft power on:

- relative headwind component
- current aiding/opposing component
- Beaufort scale (from wind speed)
- wave proxy index

Optional CSV columns supported by `load_fuelcast_preview`:

- `environment_wind_speed_mps`
- `environment_wind_from_deg` (meteorological "from" direction)
- `environment_current_speed_mps`
- `environment_current_to_deg` (oceanographic "to" direction)
- `environment_wave_height_m`

If these columns are omitted, behavior falls back to the original FuelCast-only model.

## Project structure

- `digital_twin/model.py` — core digital twin model and analytics engine
- `digital_twin/fuelcast.py` — FuelCast row loader plus calibration/evaluation helpers
- `data/fuelcast_cps_poseidon_preview.csv` — real FuelCast preview rows used for local testing
- `demo.py` — runnable synthetic example with thrust-aware telemetry
- `evaluate_fuelcast.py` — runnable evaluation against the FuelCast preview slice
- `tests/test_model.py` — regression tests for both synthetic and FuelCast-backed flows

## Model behavior

### 1) Thrust-aware mode

When thrust is available, the twin estimates:

1. **Expected efficiency** from a simplified ideal-propeller baseline.
2. **Actual efficiency** from thrust, vessel speed, shaft RPM, and torque.
3. **Efficiency deviation %**, anomaly flag, and degradation trend.

### 2) FuelCast / real-data mode

FuelCast does not expose direct propeller thrust in the public preview rows. For that case, the twin uses a calibrated **ideal shaft-power curve**:

1. Fit an ideal power coefficient from a calibration window of observed samples.
2. Predict the **expected propeller shaft power** for each later speed point.
3. Convert `expected_power / actual_power` into an **efficiency proxy**.
4. Compute deviation %, anomaly flags, and degradation trend from that proxy.

This lets you test the digital twin on real ship telemetry now, while keeping a clear path to swap in CFD-derived thrust/efficiency maps later.


## Download ERA5 mirror data to `data/era5` (when CDS/ERA5 API is down)

Try the AWS Open Data mirror first:

```bash
python3 scripts/fetch_era5_from_aws.py --year 2024 --month 1 --filename data.nc
```

If your runtime proxy blocks direct download, use the bundled fallback sample so downstream processing can still run:

```bash
python3 scripts/fetch_era5_from_aws.py --year 2024 --month 1 --fallback-to-local-sample
```

The downloader writes to `data/era5/` by default.

## Download Copernicus data to `data/Copernicus`

Use the Copernicus downloader and provide a public Copernicus URL:

```bash
python3 scripts/fetch_copernicus_data.py --source-url "https://<copernicus-public-file-url>" --filename copernicus_data.nc
```

If a corporate proxy blocks download, run with fallback enabled to generate a local sample CSV under `data/Copernicus/`:

```bash
python3 scripts/fetch_copernicus_data.py --source-url "https://<copernicus-public-file-url>" --fallback-to-sample
```

The script writes either the downloaded file or `copernicus_sample_subset.csv` fallback into `data/Copernicus/`.

## Run the synthetic demo

```bash
python3 demo.py
```

## Run the FuelCast evaluation

```bash
python3 evaluate_fuelcast.py
```

## Run the tests

```bash
python3 -m pytest
```

## Next extensions

To evolve this into a more production-grade propeller twin, the next logical steps are:

- replace the simplified baseline with CFD-derived efficiency maps
- ingest the full FuelCast dataset or a live vessel telemetry stream
- incorporate weather and current terms into the expected shaft-power curve
- separate propulsion degradation from hotel-load and engine-side effects
- expose the analytics through an API or dashboard
