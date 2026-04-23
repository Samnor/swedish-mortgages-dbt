#!/usr/bin/env python3
"""
SCB MFI mortgage rate poller — Statistics Sweden API → S3.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from common import env, put_jsonl, run_athena_ddl, state_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

S3_BUCKET = env("SWEDISH_MORTGAGES_S3_BUCKET", "dbt-data-lake-642948445774")
S3_PREFIX = env("SWEDISH_MORTGAGES_SCB_PREFIX", "scb-mortgage-rates")
S3_REGION = env("AWS_REGION", "eu-north-1")
ATHENA_DB = env("SWEDISH_MORTGAGES_ATHENA_DATABASE", "swedish_finance")
ATHENA_STAGING = env("SWEDISH_MORTGAGES_SCB_ATHENA_STAGING", "s3://athena-queries-funfun/scb-mortgage-setup/")
BACKFILL_START = env("SWEDISH_MORTGAGES_SCB_BACKFILL_START", "2020-01")
STATE_FILE = state_file("scb_mortgage_last_run")
SCB_URL = "https://api.scb.se/OV0104/v1/doris/sv/ssd/FM/FM5001/FM5001C/RantaT04N"

PERIOD_MAP: dict[str, tuple[str, float]] = {
    "1.1.1": ("3M", 0.25),
    "1.1.2.1": ("1Y", 1.0),
    "1.1.2.2.1.1": ("2Y", 2.0),
    "1.1.2.2.2": ("3-5Y", 4.0),
    "1.1.2.3": ("5Y+", 7.0),
}

LOAN_TYPE_NAMES = {
    "0100": "Nya och omförhandlade avtal",
    "0200": "Utestående avtal",
}

ATHENA_DDL = f"""
CREATE DATABASE IF NOT EXISTS {ATHENA_DB};

CREATE EXTERNAL TABLE IF NOT EXISTS {ATHENA_DB}.scb_mortgage_rates_raw (
  period_month STRING,
  loan_type STRING,
  loan_type_name STRING,
  period_code STRING,
  period_label STRING,
  rate DOUBLE,
  scraped_at STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES ('serialization.format' = '1')
LOCATION 's3://{S3_BUCKET}/{S3_PREFIX}/'
TBLPROPERTIES ('has_encrypted_data'='false');
"""


def _post(url: str, body: dict) -> dict | None:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            if exc.code == 429:
                wait = 30 * (attempt + 1)
                log.warning("SCB rate limited; sleeping %ss", wait)
                time.sleep(wait)
            else:
                log.error("SCB HTTP %s: %s", exc.code, body_text[:200])
                return None
        except Exception as exc:
            log.error("SCB request failed: %s", exc)
            if attempt < 3:
                time.sleep(5)
    return None


def _scb_month_to_iso(scb_month: str) -> str:
    return scb_month.replace("M", "-")


def fetch_mfi_rates(from_month: str) -> list[dict]:
    result = _post(
        SCB_URL,
        {
            "query": [
                {
                    "code": "Referenssektor",
                    "selection": {"filter": "item", "values": ["1.1"]},
                },
                {
                    "code": "Avtal",
                    "selection": {"filter": "item", "values": list(LOAN_TYPE_NAMES)},
                },
                {
                    "code": "Rantebindningstid",
                    "selection": {"filter": "item", "values": list(PERIOD_MAP)},
                },
            ],
            "response": {"format": "json"},
        },
    )
    if not result:
        return []

    column_codes = [column["code"] for column in result.get("columns", [])]
    try:
        loan_idx = column_codes.index("Avtal")
        period_idx = column_codes.index("Rantebindningstid")
        month_idx = column_codes.index("Tid")
    except ValueError as exc:
        raise RuntimeError(f"Unexpected SCB response shape: {column_codes}") from exc

    scraped_at = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []
    for row in result.get("data", []):
        raw_value = row["values"][0]
        if raw_value in ("", "..", None):
            continue

        iso_month = _scb_month_to_iso(row["key"][month_idx])
        if iso_month < from_month:
            continue

        rate = float(str(raw_value).replace(",", "."))
        loan_type = row["key"][loan_idx]
        period_code = row["key"][period_idx]
        period_label, _ = PERIOD_MAP.get(period_code, ("unknown", 0.0))

        records.append(
            {
                "period_month": iso_month,
                "loan_type": loan_type,
                "loan_type_name": LOAN_TYPE_NAMES.get(loan_type, loan_type),
                "period_code": period_code,
                "period_label": period_label,
                "rate": rate,
                "scraped_at": scraped_at,
            }
        )
    return records


def get_from_month() -> str:
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return BACKFILL_START


def current_month() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def save_state(current: str) -> None:
    STATE_FILE.write_text(current)


def upload_month_partition(month_str: str, records: list[dict]) -> None:
    year, month = month_str[:4], month_str[5:7]
    key = f"{S3_PREFIX}/{year}/{month}/rates.jsonl"
    put_jsonl(S3_BUCKET, key, records, S3_REGION)
    log.info("Uploaded s3://%s/%s (%s records)", S3_BUCKET, key, len(records))


def main(setup: bool = False) -> None:
    if setup:
        run_athena_ddl(S3_REGION, ATHENA_STAGING, ATHENA_DDL)

    from_month = get_from_month()
    to_month = current_month()
    if from_month >= to_month:
        log.info("Already up to date")
        return

    records = fetch_mfi_rates(from_month)
    if not records:
        raise SystemExit("No SCB mortgage records fetched")

    by_month: dict[str, list[dict]] = {}
    for record in records:
        by_month.setdefault(record["period_month"], []).append(record)

    for month_str in sorted(by_month):
        upload_month_partition(month_str, by_month[month_str])

    save_state(to_month)
    log.info("Done. State saved: %s", to_month)


if __name__ == "__main__":
    main(setup="--setup" in sys.argv)

