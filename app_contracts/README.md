# App Contracts

This folder contains product-facing contracts shared by the future mortgage
haggling webapp, dbt, and Superset.

## State Machine

`mortgage_haggle.v1.json` is the source of truth for the webapp flow. The
frontend should load this file and use it to determine:

- which state/screen is active
- which user inputs are required
- which transitions are allowed
- which dbt-backed data products must be available
- which analytics event should be emitted

Flow logic should not be duplicated inside individual UI components.

## Ownership Boundary

- dbt owns market and bank data products such as `rates_daily`,
  `bank_margin_analysis`, and `bank_vs_market_analysis`.
- the webapp owns borrower-specific context, payment calculations, selected
  target rate, generated talking points, and negotiation outcome logging.
- Superset owns exploratory dashboards for validating the same dbt marts, not
  the user-facing negotiation flow.

## Validation

Run:

```bash
python3 scripts/validate_app_contracts.py
```

The validator checks the JSON Schema plus state-machine integrity:

- initial state exists
- terminal states exist
- transition targets exist
- referenced context keys exist
- referenced data products exist
- all states are reachable from the initial state
