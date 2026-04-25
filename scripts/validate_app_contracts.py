#!/usr/bin/env python3
"""Validate app contract JSON files and basic state-machine integrity."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "app_contracts"
SCHEMA_PATH = CONTRACT_DIR / "mortgage_haggle_state_machine.schema.json"
CONTRACT_PATHS = sorted(CONTRACT_DIR.glob("mortgage_haggle.v*.json"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def validate_integrity(contract: dict, path: Path) -> list[str]:
    errors: list[str] = []
    states = contract["states"]
    state_names = set(states)
    context_keys = set(contract.get("context_schema", {}))
    data_products = set(contract.get("data_products", {}))

    initial = contract["initial"]
    if initial not in state_names:
        errors.append(f"{path}: initial state {initial!r} does not exist")

    for terminal in contract.get("terminal", []):
        if terminal not in state_names:
            errors.append(f"{path}: terminal state {terminal!r} does not exist")

    for state_name, state in states.items():
        for key in state.get("requires_context", []) + state.get("writes_context", []):
            if key not in context_keys:
                errors.append(f"{path}: state {state_name!r} references unknown context key {key!r}")

        for key in state.get("data", []):
            if key not in data_products:
                errors.append(f"{path}: state {state_name!r} references unknown data product {key!r}")

        for transition in state.get("transitions", []):
            target = transition["target"]
            if target not in state_names:
                errors.append(f"{path}: state {state_name!r} transitions to unknown state {target!r}")

    if initial in state_names:
        reachable = {initial}
        queue: deque[str] = deque([initial])
        while queue:
            current = queue.popleft()
            for transition in states[current].get("transitions", []):
                target = transition["target"]
                if target in state_names and target not in reachable:
                    reachable.add(target)
                    queue.append(target)

        unreachable = sorted(state_names - reachable)
        if unreachable:
            errors.append(f"{path}: unreachable states: {', '.join(unreachable)}")

    return errors


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors: list[str] = []

    if not CONTRACT_PATHS:
        errors.append("No mortgage_haggle.v*.json contracts found")

    for path in CONTRACT_PATHS:
        contract = load_json(path)
        schema_errors = sorted(validator.iter_errors(contract), key=lambda error: error.path)
        for error in schema_errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{path}: schema error at {location}: {error.message}")
        if not schema_errors:
            errors.extend(validate_integrity(contract, path))

    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"Validated {len(CONTRACT_PATHS)} app contract(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
