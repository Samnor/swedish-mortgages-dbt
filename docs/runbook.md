# Runbook

## Local Validation

```bash
export DBT_PROFILES_DIR=$(pwd)
export DBT_TARGET=dev
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

## GitHub Workflow

- Pull request:
  run parse and lint checks
- Optional PR CI in dbt Cloud:
  triggered from the connected repo
- Merge to `main`:
  trigger production deployment job

## First dbt Cloud Tasks

1. Connect the repo to dbt Cloud with GitHub.
2. Create `Development`, `CI`, and `Production` environments.
3. Configure production to point at service-account warehouse credentials.
4. Mark production as the final source of truth.
5. Enable Catalog updates from production runs.

