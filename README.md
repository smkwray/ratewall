# RateWall

RateWall is a structural-accounting model of monetary-policy transmission under
high public-debt conditions. It studies when higher rates can strengthen or
weaken the usual tightening channel through public interest flows, balance-sheet
composition, and sectoral income-routing effects. The project is a transparent
scenario and accounting engine, not a causal estimate or a forecast of a wall
date.

## Subsystems

The marginal empirical databook builds the current RateWall marginal surfaces:
assumption sets, parameter packs, source ledgers, Treasury Deposit Channel
inputs, public-interest terms, safe-yield terms, and claim-boundary audits.

The Rate Wall Transmission Accounting Model (RWTAM) builds a sectoral accounting
system for rate-wall transmission. It combines stock-flow accounting, rate-side
mechanics, sector cells, conversion parameters, and scenario layers into
auditable output tables and focused invariants.

## Install

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Run

Build the marginal databook and release surfaces:

```bash
python -m ratewall.cli databook build --output-dir outputs
python -m ratewall.cli release build --output-dir outputs
```

Run the default test suite:

```bash
python -m pytest
```

Run focused RWTAM checks:

```bash
python -m pytest tests/test_rwtam_accounting_primitives.py
```

This focused test exercises the reusable, channel-neutral primitive ledger:
units, ownership, overlap resolution, feasibility, measurement provenance, and
generic outcome aggregation. Applications supply their own inputs; this
contract governs how those inputs enter accounting outcomes.

Additional RWTAM builder scripts live under `scripts/build_rwtam_*.py`; they
write generated tables under `var/rwtam/`.

## Boundaries

RateWall outputs are labeled accounting and scenario objects. They should not be
read as pricing, welfare, incidence, MPC, holder-allocation, empirical
probability, or policy-failure claims unless a table explicitly says that claim
is enabled.
