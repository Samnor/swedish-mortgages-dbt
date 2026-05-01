# Swedish Mortgages dbt

Standalone dbt project and ingestion repo for Swedish mortgage-rate analysis.

This repository is intentionally structured so it can be published publicly.
Account-specific infrastructure values are injected through environment
variables, and any path-like examples in the repo are templates that should be
replaced in your own environment.

This repo exists for two reasons:

1. Keep the Swedish mortgage work separate from the old mixed `dbt_athena` project.
2. Provide a clean repo shape for practicing dbt Architect exam topics such as GitHub CI, deployment environments, source freshness, docs/Catalog, and environment-aware deployments.

## Repo Structure

- `models/staging/`
  Raw-source cleanup and normalization.
- `models/marts/`
  Business-facing mortgage rate and margin models.
- `models/exposures.yml`
  Downstream dashboard declaration for docs and Catalog.
- `ingestion/`
  Pollers that land raw data in S3 and create Athena external tables.
- `ops/launchd/`
  Local macOS schedulers for the pollers.
- `docs/`
  Environment design, architecture notes, funding-proxy notes, and deployment
  workflow.
- `.github/workflows/`
  GitHub Actions validation and deploy scaffolding.

## Local Setup

1. Create a virtualenv and install dependencies.
2. Export `DBT_PROFILES_DIR=$(pwd)`.
3. Set `DBT_TARGET=dev`.
4. Set infrastructure environment variables for your own account, such as:

```bash
export DBT_ATHENA_STAGING_DIR="s3://YOUR-QUERY-RESULTS-BUCKET/dbt-results/"
export DBT_ATHENA_DATA_DIR="s3://YOUR-DATA-BUCKET/dbt/"
export SWEDISH_MORTGAGES_S3_BUCKET="YOUR-DATA-BUCKET"
```

5. Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
dbt deps
dbt parse
dbt source freshness --select source:swedish_finance
dbt build
```

## Environments

This repo is scaffolded for:

- `dev`
- `ci`
- `prod`

The `profiles.yml` uses environment variables so the same repo can back local development, GitHub validation, and production deployment jobs without branching the SQL.

Infrastructure defaults in the repo are intentionally non-production placeholders.
Replace them with your own S3, Athena, AWS, and dbt Cloud settings before real use.

## GitHub Deployments

GitHub Actions supports environment-aware deployments:

- pushes to `develop` deploy to the `dev` dbt target
- pushes to `main` deploy to the protected `prod` dbt target
- manual dispatch can deploy either target

Create matching GitHub Environments named `dev` and `prod`, and configure the
variables/secrets listed in `docs/environments.md`.

## dbt Cloud Design

Recommended dbt Cloud setup:

- Development environment:
  personal developer credentials, branch-based development
- CI deployment environment:
  service-account credentials, isolated CI schema, deferral against production
- Production deployment environment:
  service-account credentials, stable production schema, merge-triggered jobs

See `docs/environments.md` and `docs/runbook.md`.
