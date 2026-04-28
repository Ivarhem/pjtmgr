# Catalog Research V2 Design (2026-04-23)

## Why rebuild

The current deep-research path proved stable only when prompts stayed very small, but then output density was too weak:
- official `spec_url` coverage remained near zero
- `eos/eosl` coverage remained near zero
- heavier prompt variants timed out
- Codex-only one-shot prompting mixed too many jobs into one call

The old shape remains useful only as a stability baseline, not as the long-term architecture.

## V2 goals

1. Separate source discovery from normalization.
2. Make each step debuggable in isolation.
3. Allow future insertion of search MCP / fetch MCP / alternate providers without redesigning the whole flow.
4. Keep auto-apply disabled until measurable benchmark quality beats baseline.

## V2 pipeline

### 1) Source finder

Input:
- vendor
- model
- classification
- optional reference URL

Output:
- candidate vendor domains
- search queries
- candidate source URLs grouped by type:
  - `product_page`
  - `datasheet`
  - `lifecycle_notice`

This stage is responsible only for finding likely evidence locations.

### 2) Page extractor

Input:
- candidate URLs

Output:
- extracted text snippets / metadata per URL
- canonical URL if redirects occur
- source type confidence

This stage should eventually support:
- direct HTTP fetch
- MCP fetch/read tools
- HTML/PDF extractors

### 3) Normalizer

Input:
- extracted evidence bundle

Output:
- normalized catalog payload:
  - `hardware_spec`
  - `eosl`
  - `interfaces`
  - `uncertain_fields`
  - `confidence`

The normalizer should cite which source block supported each populated field.

### 4) Quality gate

The quality gate decides whether the result is strong enough to become a review draft.

Minimum recommended gate:
- one of:
  - structured interfaces
  - official source URL
  - EOS/EOSL date
  - 2+ meaningful spec fields

Weak or source-less outputs remain `unverified`.

### 5) Applier

Only the applier writes to catalog state.
It must be isolated from research itself so benchmark experiments can run without mutating real rows.

## Prototype strategy

Build V2 alongside the current service:
- do **not** replace the stable route yet
- do **not** re-enable auto-apply yet
- keep benchmarking on a fixed sample set

## First prototype scope

Initial V2 prototype should provide:
- source-plan generation
- optional lightweight interface probe
- benchmarkability without touching production writes

## Next likely upgrade points

1. search MCP for candidate URL discovery
2. fetch/read MCP for page extraction
3. alternate provider for lifecycle/source extraction
4. source-to-field attribution in output
