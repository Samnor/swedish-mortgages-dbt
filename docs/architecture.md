# Architecture

## Scope

This repo owns the Swedish mortgage analysis stack:

- raw ingestion from Riksbanken, SCB, and bank websites
- Athena external tables in raw schema `swedish_finance`
- dbt staging and marts for funding-cost and mortgage spread analysis
- downstream dashboard metadata through dbt exposures

It does not own Home Assistant, room-plan, or apartment telemetry models.

## Layers

### Raw

Pollers write JSONL to S3 and register Athena external tables:

- `se_rates_raw`
- `bank_listed_rates_raw`
- `scb_mortgage_rates_raw`

### Staging

The staging layer standardizes types, applies deduplication, and exposes stable source semantics.

### Marts

The marts answer the business questions:

- `rates_daily`:
  normalized daily rate curve and covered-bond spreads
- `bank_margin_analysis`:
  latest listed rates against funding-cost proxies
- `bank_vs_market_analysis`:
  listed bank rates versus SCB market averages

## Exam-Oriented Features

This repo is designed to support practice for:

- GitHub-based version control
- CI validation on pull requests
- distinct `dev`, `ci`, and `prod` targets
- source freshness checks
- docs/Catalog metadata through descriptions and exposures
- merge-based production deployment design
- service-account deploy patterns

