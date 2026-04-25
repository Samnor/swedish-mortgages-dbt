#!/usr/bin/env python3
"""
Swedish bank mortgage rate scraper.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from datetime import date, datetime, timezone
from collections.abc import Callable

import requests
from bs4 import BeautifulSoup

from common import env, put_jsonl, run_athena_ddl, state_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

S3_BUCKET = env("SWEDISH_MORTGAGES_S3_BUCKET", "example-data-lake")
S3_PREFIX = env("SWEDISH_MORTGAGES_BANK_RATES_PREFIX", "bank-listed-rates")
S3_REGION = env("AWS_REGION", "eu-north-1")
ATHENA_DB = env("SWEDISH_MORTGAGES_ATHENA_DATABASE", "swedish_finance")
ATHENA_STAGING = env("SWEDISH_MORTGAGES_BANK_RATES_ATHENA_STAGING", "s3://example-athena-results/bank-rates-setup/")
STATE_FILE = state_file("bank_rates_last_run")
USER_AGENT = env(
    "SWEDISH_MORTGAGES_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
)
REQUIRED_BANKS = {
    bank.strip()
    for bank in env("SWEDISH_MORTGAGES_REQUIRED_BANKS", "SBAB,Nordea,Swedbank").split(",")
    if bank.strip()
}

ATHENA_DDL = f"""
CREATE DATABASE IF NOT EXISTS {ATHENA_DB};

CREATE EXTERNAL TABLE IF NOT EXISTS {ATHENA_DB}.bank_listed_rates_raw (
  bank STRING,
  period_label STRING,
  period_years DOUBLE,
  list_rate DOUBLE,
  avg_rate DOUBLE,
  valid_from STRING,
  scraped_at STRING,
  source STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES ('serialization.format' = '1')
LOCATION 's3://{S3_BUCKET}/{S3_PREFIX}/'
TBLPROPERTIES ('has_encrypted_data'='false');
"""

PERIOD_MAP = {
    "P_3_MONTHS": (0.25, "3M"),
    "P_1_YEAR": (1.0, "1Y"),
    "P_2_YEARS": (2.0, "2Y"),
    "P_3_YEARS": (3.0, "3Y"),
    "P_4_YEARS": (4.0, "4Y"),
    "P_5_YEARS": (5.0, "5Y"),
    "P_7_YEARS": (7.0, "7Y"),
    "P_10_YEARS": (10.0, "10Y"),
    "3 månader": (0.25, "3M"),
    "3 mån": (0.25, "3M"),
    "1 år": (1.0, "1Y"),
    "2 år": (2.0, "2Y"),
    "3 år": (3.0, "3Y"),
    "4 år": (4.0, "4Y"),
    "5 år": (5.0, "5Y"),
    "6 år": (6.0, "6Y"),
    "7 år": (7.0, "7Y"),
    "8 år": (8.0, "8Y"),
    "9 år": (9.0, "9Y"),
    "10 år": (10.0, "10Y"),
}


def _get(url: str, headers: dict | None = None) -> requests.Response | None:
    merged = {"User-Agent": USER_AGENT, "Accept-Language": "sv-SE,sv;q=0.9"}
    if headers:
        merged.update(headers)

    for attempt in range(3):
        try:
            response = requests.get(url, headers=merged, timeout=20)
            response.raise_for_status()
            return response
        except Exception as exc:
            log.warning("GET %s failed on attempt %s: %s", url, attempt + 1, exc)
            time.sleep(2 * (attempt + 1))
    return None


def _parse_rate(value: str) -> float | None:
    try:
        return float(value.replace("\xa0", "").replace("%", "").replace(",", ".").strip())
    except (AttributeError, ValueError):
        return None


def _record(bank: str, period_code: str, list_rate: float | None, avg_rate: float | None, valid_from: str, scraped_at: str, source: str) -> dict | None:
    mapping = PERIOD_MAP.get(period_code)
    if not mapping:
        return None

    years, label = mapping
    return {
        "bank": bank,
        "period_label": label,
        "period_years": years,
        "list_rate": list_rate,
        "avg_rate": avg_rate,
        "valid_from": valid_from,
        "scraped_at": scraped_at,
        "source": source,
    }


def scrape_sbab(scraped_at: str) -> list[dict]:
    response = _get(
        "https://www.sbab.se/api/interest-mortgage-service/api/external/v1/interest",
        {"Referer": "https://www.sbab.se/"},
    )
    if not response:
        return []

    records = []
    for item in response.json().get("listInterests", []):
        record = _record(
            bank="SBAB",
            period_code=item["period"],
            list_rate=float(item["interestRate"]),
            avg_rate=None,
            valid_from=item.get("validFrom", ""),
            scraped_at=scraped_at,
            source="sbab_api",
        )
        if record:
            records.append(record)
    return records


def scrape_nordea(scraped_at: str) -> list[dict]:
    response = _get("https://www.nordea.se/privat/produkter/bolan/listrantor.html")
    if not response:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    table = None
    for candidate in soup.find_all("table"):
        caption = candidate.find("caption")
        if caption and "listräntor" in caption.get_text().lower():
            table = candidate
            break
    if table is None:
        for candidate in soup.find_all("table"):
            if "%" in candidate.get_text():
                table = candidate
                break
    if table is None:
        return []

    records = []
    valid_from = ""
    for row in table.find_all("tr")[1:]:
        cells = [cell.get_text(strip=True).replace("\xa0", " ") for cell in row.find_all("td")]
        if len(cells) < 2:
            continue
        if len(cells) > 3:
            valid_from = cells[3].strip() or valid_from
        record = _record(
            "Nordea",
            cells[0].strip(),
            _parse_rate(cells[1]),
            None,
            valid_from,
            scraped_at,
            "nordea_html",
        )
        if record and record["list_rate"] is not None:
            records.append(record)
    return records


def scrape_swedbank(scraped_at: str) -> list[dict]:
    response = _get("https://www.swedbank.se/privat/boende-och-bolan/bolanerantor.html")
    if not response:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    table = None
    for candidate in soup.find_all("table"):
        caption = candidate.find("caption")
        if caption and "bolåneräntor" in caption.get_text().lower():
            table = candidate
            break
    if table is None or table.find("thead") is None or table.find("tbody") is None:
        return []

    headers = [th.get_text(strip=True).lower() for th in table.find("thead").find_all("th")]
    snittr_idx = next((i for i, header in enumerate(headers) if "snitt" in header), None)
    listr_idx = next((i for i, header in enumerate(headers) if "list" in header), 1)

    valid_from = ""
    for header in headers:
        match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", header)
        if match:
            valid_from = match.group(1)
            break

    records = []
    for row in table.find("tbody").find_all("tr"):
        cells = [cell.get_text(" ", strip=True).replace("\xa0", " ") for cell in row.find_all("td")]
        if len(cells) < 2:
            continue
        record = _record(
            "Swedbank",
            cells[0].strip(),
            _parse_rate(cells[listr_idx]) if listr_idx < len(cells) else None,
            _parse_rate(cells[snittr_idx]) if snittr_idx is not None and snittr_idx < len(cells) else None,
            valid_from,
            scraped_at,
            "swedbank_html",
        )
        if record and record["list_rate"] is not None:
            records.append(record)
    return records


def upload_records(today: str, records: list[dict]) -> None:
    year, month, day = today[:4], today[5:7], today[8:10]
    key = f"{S3_PREFIX}/{year}/{month}/{day}/rates.jsonl"
    put_jsonl(S3_BUCKET, key, records, S3_REGION)
    log.info("Uploaded s3://%s/%s (%s records)", S3_BUCKET, key, len(records))


def main(setup: bool = False) -> None:
    if setup:
        run_athena_ddl(S3_REGION, ATHENA_STAGING, ATHENA_DDL)

    today = date.today().isoformat()
    scraped_at = datetime.now(timezone.utc).isoformat()

    if STATE_FILE.exists() and STATE_FILE.read_text().strip() == today:
        log.info("Already ran today")
        return

    scrapers: tuple[Callable[[str], list[dict]], ...] = (
        scrape_sbab,
        scrape_nordea,
        scrape_swedbank,
    )
    all_records: list[dict] = []
    failed_scrapers: list[str] = []
    banks_with_records: set[str] = set()

    for scraper in scrapers:
        try:
            records = scraper(scraped_at)
            if not records:
                failed_scrapers.append(scraper.__name__)
            all_records.extend(records)
            banks_with_records.update(record["bank"] for record in records)
        except Exception as exc:
            log.error("%s failed: %s", scraper.__name__, exc)
            failed_scrapers.append(scraper.__name__)
        time.sleep(1)

    if not all_records:
        raise SystemExit("No records scraped")

    missing_required_banks = sorted(REQUIRED_BANKS - banks_with_records)
    if missing_required_banks:
        raise SystemExit(
            "Missing required bank records: "
            + ", ".join(missing_required_banks)
            + f". Failed or empty scrapers: {', '.join(failed_scrapers) or 'none'}"
        )

    upload_records(today, all_records)
    STATE_FILE.write_text(today)
    log.info("Done. %s total records.", len(all_records))


if __name__ == "__main__":
    main(setup="--setup" in sys.argv)
