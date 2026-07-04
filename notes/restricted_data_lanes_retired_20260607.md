# Restricted Data Lanes Retired - 2026-06-07

Status: retired for backend completion.

Retired lanes:
- beneficial_owner_final_recipient_lookthrough: configs/sources.yml lines 2185-2189, TIC custody and beneficial-owner limitation context.
- bank_iorb_retention_to_depositor_timing: configs/sources.yml lines 2491-2511, IORB and IOER administered-rate cashflow context with no depositor-timing bridge admitted.
- security_level_reset_financialization: configs/sources.yml lines 2871-2874, Compustat firm financialization restricted protocol.

Reopen trigger: reopen exactly one lane only when configs/restricted_lane_status.yml changes that lane status from retired to active in the same change that adds a source-backed unit-of-observation, required-fields bridge, and admission test for that lane.
