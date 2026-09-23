# Evidence bridge contracts

These dependency-light scripts produce JSON interchange packs for an equity desk. They do not provide live data rights, investment advice or automatic publication. Keep source IDs resolvable to dated official documents or entitled/user-supplied exports.

## `filing_change/v1`

Input: `prior` and `current` filing objects with the same `issuer` and `filing_type`, offset `published_at`, `source_id`, `source_url`, and `sections` (`key`, `heading`, `text`, `page`). A section key should represent the same subject in both documents. Output: `changes` with `added|removed|changed`, prior/current quoted text, source/page pointers, similarity and a number-change review flag. The tool deliberately does not grade materiality. Optional `filing_extract.py` uses Docling on a local document and emits page keys; manually align stable sections if pagination changed. Preserve tables and OCR doubts in analyst review.

## `expectations_bridge/v1`

Input: `prior` and `current` snapshot objects with identical `issuer`, `listing`, `provider`, offset `as_of`, and `estimates` rows. Each row needs `metric`, `fiscal_period`, `basis`, `currency`, `unit`, `statistic`, decimal `value` and `source_ids`. Output has exact-decimal absolute and percent change for identical keys, plus separate `new` and `dropped` rows. Percent uses the absolute prior value as denominator; a zero prior value has no percent change. Different providers cannot be labelled revisions of one series.

## `ownership_flow/v1`

`ownership_flow.py build` accepts `market`, `symbol`, optional offset `as_of`, `flows` and `holdings`. Flows need date, investor category, unit, source ID and either net or both buy/sell. Holdings need holder, stake percent, ownership type (`beneficial`, `registered`, `custodian`, etc.), effective `as_of`, filing source ID and ideally `filed_at`/source URL. Output keeps flows and holdings in separate arrays. FinMind adapter fetches Taiwan stock institutional buy/sell shares using `FINMIND_TOKEN`. Optional pykrx adapter fetches Korean daily investor net trading value in KRW; it is a scraper and current KRX access may need `KRX_ID`/`KRX_PW`. Empty holdings or flows make quality `limited`; never silently imply complete ownership coverage.

All pack consumers validate `schema` and `schemaVersion`, preserve unknown fields and source references, and independently review substantive claims. No pack alone proves causation or trade suitability.
