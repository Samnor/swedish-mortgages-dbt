#!/usr/bin/env python3
"""Run raw source ingestion with cloud-friendly defaults.

The individual pollers are intentionally plain Python scripts. This wrapper
keeps orchestration concerns outside them so the same ingestion entry point can
run from GitHub Actions today and from EventBridge/Lambda/ECS later.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "se-rates": ROOT / "ingestion" / "se_rates_poller.py",
    "bank-rates": ROOT / "ingestion" / "bank_rates_scraper.py",
    "scb": ROOT / "ingestion" / "scb_mortgage_poller.py",
}

SOURCE_GROUPS = {
    "daily": ["se-rates", "bank-rates"],
    "all": list(SOURCES),
}


def month_lookback(months: int) -> str:
    today = date.today()
    month_index = today.year * 12 + today.month - 1 - months
    year = month_index // 12
    month = month_index % 12 + 1
    return f"{year:04d}-{month:02d}"


def run_source(source: str, env: dict[str, str], setup: bool) -> None:
    command = [sys.executable, str(SOURCES[source])]
    if setup:
        command.append("--setup")
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=[*SOURCE_GROUPS, *SOURCES],
        default="daily",
        help="Source or source group to ingest. Defaults to daily sources.",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Create raw Athena tables before ingestion.",
    )
    parser.add_argument(
        "--se-lookback-days",
        type=int,
        default=10,
        help="Default Riksbanken lookback when no persisted state exists.",
    )
    parser.add_argument(
        "--scb-lookback-months",
        type=int,
        default=3,
        help="Default SCB lookback when no persisted state exists.",
    )
    args = parser.parse_args()

    if args.se_lookback_days < 1:
        raise ValueError("--se-lookback-days must be at least 1.")
    if args.scb_lookback_months < 1:
        raise ValueError("--scb-lookback-months must be at least 1.")

    env = os.environ.copy()
    env.setdefault("AWS_REGION", "eu-north-1")
    env.setdefault("SWEDISH_MORTGAGES_SE_RATES_BACKFILL_START", (date.today() - timedelta(days=args.se_lookback_days)).isoformat())
    env.setdefault("SWEDISH_MORTGAGES_SCB_BACKFILL_START", month_lookback(args.scb_lookback_months))

    selected_sources = SOURCE_GROUPS.get(args.source, [args.source])
    for source in selected_sources:
        run_source(source, env, args.setup)


if __name__ == "__main__":
    main()
