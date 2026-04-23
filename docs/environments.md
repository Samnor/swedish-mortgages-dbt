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

## Recommended Jobs

- CI job:
  `dbt build --select state:modified+ --defer --state path/to/prod/artifacts`
- Source freshness job:
  `dbt source freshness --select source:swedish_finance`
- Production merge job:
  `dbt build`

