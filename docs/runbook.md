# Runbook

## Local Validation

```bash
export DBT_PROFILES_DIR=$(pwd)
export DBT_TARGET=dev
export DBT_ATHENA_STAGING_DIR="s3://YOUR-QUERY-RESULTS-BUCKET/dbt-results/"
export DBT_ATHENA_DATA_DIR="s3://YOUR-DATA-BUCKET/dbt/"
export SWEDISH_MORTGAGES_S3_BUCKET="YOUR-DATA-BUCKET"
dbt deps
dbt parse
dbt source freshness --select source:swedish_finance
dbt build
```

## Poller Setup

Run the pollers manually:

```bash
python ingestion/se_rates_poller.py --setup
python ingestion/scb_mortgage_poller.py --setup
python ingestion/bank_rates_scraper.py --setup
```

Then install the matching `ops/launchd/*.plist` files if you want local schedules.
Each plist uses a placeholder absolute path and should be edited before loading.

## GitHub Workflow

- Pull request:
  run parse and lint checks
- Push to `develop` or manual `dev` dispatch:
  deploy dbt to the `dev` target
- Merge to `main`:
  deploy dbt to the `prod` target through the protected `prod` GitHub
  Environment
- Optional dbt Cloud:
  keep the dbt Cloud trigger workflow if you want dbt Cloud jobs and Catalog to
  be the production control plane

## First dbt Cloud Tasks

1. Connect the repo to dbt Cloud with GitHub.
2. Create `Development`, `CI`, and `Production` environments.
3. Configure production to point at service-account warehouse credentials.
4. Mark production as the final source of truth.
5. Enable Catalog updates from production runs.
