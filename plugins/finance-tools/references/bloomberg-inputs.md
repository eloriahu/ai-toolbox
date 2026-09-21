# Bloomberg user inputs

Treat a user-supplied Bloomberg table as the preferred market-data source. Accept CSV, JSON and saved-value spreadsheet exports. A screenshot is also a supported first-class input: inspect it visually, transcribe only visible values to JSON, then run `scripts/normalize_market_input.py --source-kind bloomberg_screenshot`.

Do not run OCR against an image when direct visual inspection is available. Never infer a numerical sign from colour alone, guess cropped decimals or expand a truncated security name without separate evidence. Preserve the local filename as `source_artifact`; do not copy the image or proprietary rows into repository fixtures.

Record `ingested_at` separately from `data_as_of`. The upload or task time is not a market timestamp. When no on-screen/export timestamp is visible, leave `data_as_of` null and mark the timestamp unverified. OpenBB may fill or validate the affected live fields, but every substituted field retains fallback lineage.

For spreadsheet files containing Bloomberg formulas, use the saved cell values. Do not claim that BDP/BDH/BQL formulas refreshed outside the user's Bloomberg-enabled environment.

Canonical fields are `symbol`, `name`, `market`, `currency`, `last`, `prev_close`, `pct_change`, `open`, `high`, `low`, `volume`, `turnover`, `sector`, `benchmark` and `timestamp`. Common Bloomberg aliases such as `PX_LAST`, `CHG_PCT_1D`, `PREV_CLOSE_VALUE_REALTIME`, `GICS_SECTOR_NAME` and `CRNCY` are normalized by the helper.
