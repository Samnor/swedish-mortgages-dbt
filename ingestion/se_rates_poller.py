#!/usr/bin/env python3
"""
Swedish rates poller — Riksbanken SWEA API → S3.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from common import env, put_jsonl, run_athena_ddl, state_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

S3_BUCKET = env("SWEDISH_MORTGAGES_S3_BUCKET", "dbt-data-lake-642948445774")
S3_PREFIX = env("SWEDISH_MORTGAGES_SE_RATES_PREFIX", "se-rates")
S3_REGION = env("AWS_REGION", "eu-north-1")
ATHENA_DB = env("SWEDISH_MORTGAGES_ATHENA_DATABASE", "swedish_finance")
ATHENA_STAGING = env("SWEDISH_MORTGAGES_SE_RATES_ATHENA_STAGING", "s3://athena-queries-funfun/se-rates-setup/")
BACKFILL_START = env("SWEDISH_MORTGAGES_SE_RATES_BACKFILL_START", "2020-01-01")
STATE_FILE = state_file("se_rates_last_run")
BASE_URL = "https://api.riksbank.se/swea/v1"
REQUEST_DELAY = 2.2
MAX_RETRIES = 4

SERIES: dict[str, dict[str, str]] = {
    "SECBREPOEFF": {"name": "Policy rate", "category": "central_bank"},
    "SECBDEPOEFF": {"name": "Deposit rate", "category": "central_bank"},
    "SECBLENDEFF": {"name": "Lending rate", "category": "central_bank"},
    "SEDP3MSTIBORDELAYC": {"name": "STIBOR 3M", "category": "money_market"},
    "SETB3MBENCH": {"name": "T-bill 3M", "category": "money_market"},
    "SEGVB2YC": {"name": "Govt bond 2Y", "category": "government_bond"},
    "SEGVB5YC": {"name": "Govt bond 5Y", "category": "government_bond"},
    "SEGVB10YC": {"name": "Govt bond 10Y", "category": "government_bond"},
    "SEMB2YCACOMB": {"name": "Covered bond 2Y", "category": "covered_bond"},
    "SEMB5YCACOMB": {"name": "Covered bond 5Y", "category": "covered_bond"},
}

ATHENA_DDL = f"""
CREATE DATABASE IF NOT EXISTS {ATHENA_DB};

CREATE EXTERNAL TABLE IF NOT EXISTS {ATHENA_DB}.se_rates_raw (
  rate_date STRING,
  series_id STRING,
  series_name STRING,
  category STRING,
  value DOUBLE
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES ('serialization.format' = '1')
LOCATION 's3://{S3_BUCKET}/{S3_PREFIX}/'
TBLPROPERTIES ('has_encrypted_data'='false');
"""


def _get(url: str) -> list | dict:
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            if exc.code == 429:
                wait = REQUEST_DELAY * (2**attempt) + 30
                log.warning("Rate limited for %s; sleeping %.0fs", url, wait)
                time.sleep(wait)
            elif exc.code == 404:
                return []
            else:
                log.error("HTTP %s for %s: %s", exc.code, url, body[:200])
                return []
        except Exception as exc:
            log.error("Request failed for %s: %s", url, exc)
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY * 2)
    return []


def fetch_observations(series_id: str, from_date: str, to_date: str) -> list[dict]:
    result = _get(f"{BASE_URL}/Observations/{series_id}/{from_date}/{to_date}")
    return result if isinstance(result, list) else []


def get_from_date() -> str:
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return BACKFILL_START


def save_state(current_date: str) -> None:
    STATE_FILE.write_text(current_date)


def upload_date_partition(date_str: str, records: list[dict]) -> None:
    year, month, day = date_str[:4], date_str[5:7], date_str[8:10]
    key = f"{S3_PREFIX}/{year}/{month}/{day}/rates.jsonl"
    put_jsonl(S3_BUCKET, key, records, S3_REGION)
    log.info("Uploaded s3://%s/%s (%s records)", S3_BUCKET, key, len(records))


def main(setup: bool = False) -> None:
    if setup:
        run_athena_ddl(S3_REGION, ATHENA_STAGING, ATHENA_DDL)

    from_date = get_from_date()
    to_date = date.today().isoformat()

    if from_date >= to_date:
        log.info("Already up to date")
        return

    all_obs: dict[str, list] = {}
    for series_id, meta in SERIES.items():
        log.info("Fetching %s (%s)", series_id, meta["name"])
        all_obs[series_id] = fetch_observations(series_id, from_date, to_date)
        time.sleep(REQUEST_DELAY)

    by_date: dict[str, list[dict]] = {}
    for series_id, obs_list in all_obs.items():
        meta = SERIES[series_id]
        for obs in obs_list:
            day = obs["date"]
            by_date.setdefault(day, []).append(
                {
                    "rate_date": day,
                    "series_id": series_id,
                    "series_name": meta["name"],
                    "category": meta["category"],
                    "value": obs["value"],
                }
            )

    for date_str in sorted(by_date):
        upload_date_partition(date_str, by_date[date_str])

    save_state(to_date)
    log.info("Done. State saved: %s", to_date)


if __name__ == "__main__":
    main(setup="--setup" in sys.argv)

