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

Production ingestion should run from the GitHub `Ingest Raw Sources` workflow.
It uses the same Python pollers as local development, but with GitHub OIDC AWS
credentials and bounded lookback windows so it can later move to
EventBridge/Lambda/ECS without rewriting the source-specific ingestion logic.

Required GitHub environment variables:

- `AWS_ROLE_ARN`
- `SWEDISH_MORTGAGES_S3_BUCKET`
- `DBT_ATHENA_STAGING_DIR`
- `DBT_ATHENA_DATA_DIR`
- `SWEDISH_FINANCE_RAW_SCHEMA`

Optional source-prefix variables:

- `SWEDISH_MORTGAGES_SE_RATES_PREFIX`
- `SWEDISH_MORTGAGES_BANK_RATES_PREFIX`
- `SWEDISH_MORTGAGES_SCB_PREFIX`

Scheduled production ingestion uses two source groups:

- Weekdays at 07:15 UTC: `daily`, meaning Riksbanken rates and listed bank
  rates
- Monthly on the 15th at 07:45 UTC: `scb`, meaning SCB mortgage average rates

Run the pollers manually:

```bash
python scripts/run_ingestion.py --source daily --setup
```

Use `--source all` for a one-off full refresh across every source, or select an
individual source with `se-rates`, `bank-rates`, or `scb`.

The `ops/launchd/*.plist` files are local-development examples only. They are
not the production ingestion control plane. Each plist uses a placeholder
absolute path and should be edited before loading.

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
