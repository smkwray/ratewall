RWTAM fixture variants are generated from `configs/rwtam` inside test temp directories.

`golden_wave2` is a no-scenario/TDC-off frozen invariance surface. It is not the
default-output master and must not be cited as the current RW_full headline.

`golden_wave1`, `golden_wave2`, and `golden_wave3` are retained annual-core-era
fixtures. `golden_wave4` is the sanctioned monthly-core re-baseline.

`golden_wave5` is the sanctioned tax-on re-baseline from the
`tax_layer_calibration_20260702` pack. It was refreshed in the tax-guardrail
wave after replacing the time-ramp 163(j) guard with shock-path-dependent
shield mechanics; wave1-4 remain retained predecessor surfaces. It was refreshed
again in the audit-4 fix wave for the sanctioned installment amortizing-survival
mechanics correction only.

`golden_wave6` is the sanctioned curve-consistency re-baseline. It replaces the
fixed impulse-beta public curve construction with yields derived from each
experiment's policy path plus the term-premium response pack. The old wave4
tax-off byte gate is retired because the curve construction changes those
surfaces; the live guard is now same-construction tax-off/tax-on extension
testing plus `golden_wave6_tax_off`, a same-construction tax-off byte fixture.
The old year-1 mode-invariance assumption is retired: term-premium response
differs by dose mode from month 1, so the test now asserts persistent and
transient year-1 surfaces are unequal.

2026-07-04 polish refreeze: `golden_wave6/out_scenario_axes_config.csv` was
deliberately refreshed to include the default-off `qt_supply_stress` S3 metadata
row already present in live output. This is a metadata-only byte-identity fix;
the demand headline and economic golden rows are unchanged.

2026-07-04 (beta-dial refreeze): golden_wave6 refreshed for the tdcest two-state beta doctrine (forward base 0.342 mid-transition point estimate; T25 beta rows + flow-size override table added; headline RW yr1 0.0504605 -> 0.0505301, cum 0.0585803 -> 0.0593951). Sanctioned cross-lane authority update; see configs/rwtam/packs/README.md for the doctrine and do/rwtam_beta_dial_report_20260704.md for old-vs-new.

`golden_wave7` is the sanctioned audit-round-6 BNPL scenario-only re-baseline.
It removes BNPL scenario-adjustment stocks from the default opening balance
sheet while retaining an explicit amortized BNPL scenario exhibit. The
combined-sinks leg was not promoted because the prior spec is horizon-pack
dependent; see `do/rwtam_audit_round6_report_20260707.md`.
