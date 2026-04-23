from __future__ import annotations

import json
import time
from pathlib import Path

import boto3


def env(name: str, default: str) -> str:
    import os

    return os.getenv(name, default)


def state_file(name: str) -> Path:
    state_dir = Path(env("SWEDISH_MORTGAGES_STATE_DIR", str(Path.home() / ".swedish_mortgages")))
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / name


def run_athena_ddl(region_name: str, output_location: str, ddl: str) -> None:
    athena = boto3.client("athena", region_name=region_name)
    statements = [stmt.strip() for stmt in ddl.strip().split(";") if stmt.strip()]

    for stmt in statements:
        response = athena.start_query_execution(
            QueryString=stmt,
            ResultConfiguration={"OutputLocation": output_location},
        )
        query_id = response["QueryExecutionId"]

        state = "RUNNING"
        details = {}
        for _ in range(60):
            time.sleep(2)
            details = athena.get_query_execution(QueryExecutionId=query_id)
            state = details["QueryExecution"]["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break

        if state != "SUCCEEDED":
            reason = details["QueryExecution"]["Status"].get("StateChangeReason", "")
            if "already exists" not in reason.lower() and "alreadyexistsexception" not in reason.lower():
                raise RuntimeError(f"Athena DDL failed with state={state}: {reason}")


def put_jsonl(bucket: str, key: str, records: list[dict], region_name: str) -> None:
    body = "\n".join(json.dumps(record, ensure_ascii=True) for record in records)
    s3 = boto3.client("s3", region_name=region_name)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )

