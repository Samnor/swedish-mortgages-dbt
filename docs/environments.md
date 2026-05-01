# Environments

## Design

Use one repo and one dbt project across three targets:

- `dev`
  for local work and dbt Cloud development credentials
- `ci`
  for pull-request validation and deferred builds
- `prod`
  for the merge job and the production source of truth

## Credential Strategy

- `dev`:
  developer or SSO-backed credentials are acceptable
- `ci`:
  use service-account style credentials
- `prod`:
  use service-account style credentials

This follows the architect-certification pattern where SSO-style credentials are for development, while automated deployments use stable service principals.

## Schema Strategy

- `dev`:
  `swedish_mortgages_dev_*`
- `ci`:
  `swedish_mortgages_ci_<run id>_*`
- `prod`:
  `swedish_mortgages_prod_*`

The project config sets `staging` and `marts` custom schemas so each target gets isolated relation namespaces.

## dbt Cloud Mapping

- Development environment:
  target branch and developer credentials
- CI environment:
  pull-request jobs with deferral against production
- Production environment:
  merge job running from `main`

## GitHub Environments

Create two GitHub Environments:

- `dev`
  runs from `develop` or manual workflow dispatch and writes to
  `swedish_mortgages_dev_*` schemas
- `prod`
  runs from `main`, should require approval/protected branch rules, and writes
  to `swedish_mortgages_prod_*` schemas

Environment variables:

- `AWS_REGION`
- `DBT_ATHENA_DATABASE`
- `DBT_ATHENA_STAGING_DIR`
- `DBT_ATHENA_DATA_DIR`
- `SWEDISH_FINANCE_RAW_SCHEMA`
- `SWEDISH_MORTGAGES_S3_BUCKET`
- `DBT_DEV_SCHEMA`
- `DBT_PROD_SCHEMA`
- `DBT_THREADS`
- `AWS_ROLE_ARN`

`SWEDISH_MORTGAGES_S3_BUCKET` can be omitted for GitHub ingestion when the raw
landing bucket is the same bucket in `DBT_ATHENA_DATA_DIR`; the ingestion
workflow derives the bucket name from that S3 URI.

No AWS access-key secrets are required for dbt when GitHub OIDC is configured.
The deploy workflow assumes `AWS_ROLE_ARN` with GitHub's OIDC token.

Environment secrets:

- none required for the default OIDC dbt deployment path

Production should use a service account with least-privilege access to the raw
S3 prefixes, dbt-managed S3 prefix, Athena query-results bucket, and Glue/Athena
metadata operations needed by dbt.

For ingestion, the production role also needs `s3:PutObject` on these raw
landing prefixes:

- `arn:aws:s3:::dbt-data-lake-642948445774/se-rates/*`
- `arn:aws:s3:::dbt-data-lake-642948445774/bank-listed-rates/*`
- `arn:aws:s3:::dbt-data-lake-642948445774/scb-mortgage-rates/*`

## Recommended Jobs

- CI job:
  `dbt build --select state:modified+ --defer --state path/to/prod/artifacts`
- Source freshness job:
  `dbt source freshness --select source:swedish_finance`
- Raw ingestion job:
  GitHub `Ingest Raw Sources` workflow, scheduled on weekdays for daily sources,
  monthly for SCB, and runnable manually by source
- Production merge job:
  `dbt build`
