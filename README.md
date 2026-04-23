# Swedish Mortgages dbt

Standalone dbt project and ingestion repo for Swedish mortgage-rate analysis.

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
  Environment design, architecture notes, and deployment workflow.
- `.github/workflows/`
  GitHub Actions validation and deploy scaffolding.

## Local Setup

1. Create a virtualenv and install dependencies.
2. Export `DBT_PROFILES_DIR=$(pwd)`.
3. Set `DBT_TARGET=dev`.
4. Run:

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

## dbt Cloud Design

Recommended dbt Cloud setup:

- Development environment:
  personal developer credentials, branch-based development
- CI deployment environment:
  service-account credentials, isolated CI schema, deferral against production
- Production deployment environment:
  service-account credentials, stable production schema, merge-triggered jobs

See `docs/environments.md` and `docs/runbook.md`.

