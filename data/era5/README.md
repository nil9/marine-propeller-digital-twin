# ERA5 mirror and fallback sample data

This directory is the default output for `scripts/fetch_era5_from_aws.py`.

## Mirror download

```bash
python3 scripts/fetch_era5_from_aws.py --year 2024 --month 1 --filename data.nc
```

## Proxy-blocked fallback

```bash
python3 scripts/fetch_era5_from_aws.py --year 2024 --month 1 --fallback-to-local-sample
```

The fallback command copies `era5_sample_subset.csv` into this folder so downstream pipelines can proceed even when outbound download is blocked.
