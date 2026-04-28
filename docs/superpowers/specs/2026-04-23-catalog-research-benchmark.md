# Catalog Research Benchmark Baseline (2026-04-23)

## Goal

Before improving auto-apply behavior, measure deep-research quality on a fixed hardware sample set.

## Sample set

Stored in `scripts/fixtures/catalog_research_benchmark_samples.json`.

Current sample selection emphasizes:
- network switch / router interface richness
- firewall / ADC lifecycle coverage
- server / storage spec URL and RU coverage

## Primary quality signals

Each sample is scored on these output signals:
- `spec_url` present
- `size_unit` present
- `eosl_dates` present (`eos_date` or `eosl_date`)
- `eosl_url` present (`eosl.source_url`)
- `interfaces_any` present
- `interfaces_structured` present (`interface_type` + integer `count`)

## Performance signal

- `elapsed_sec` per request
- overall `avg_elapsed_sec`
- hard failure / timeout count

## Gate for future auto-apply

Do not auto-promote to `pending_review` unless research returns meaningful density.
Suggested minimum gate:
- at least one of:
  - structured interfaces
  - EOS/EOSL date
  - source/spec URL
  - 2+ meaningful spec fields

## Run

From the Ubuntu project host:

```bash
cd /service/services/pjtmgr
TOKEN=$(grep -E '^CATALOG_RESEARCH_SERVICE_TOKEN=' .env | cut -d= -f2-)
python3 scripts/catalog_research_benchmark.py \
  --service-url http://127.0.0.1:8765 \
  --token "$TOKEN" \
  --output /tmp/catalog_research_benchmark_baseline.json
```

For a quick smoke test:

```bash
python3 scripts/catalog_research_benchmark.py --max 3 --service-url http://127.0.0.1:8765 --token "$TOKEN"
```

## How to use this

1. Run baseline on current provider/prompt.
2. Change only one research variable at a time.
3. Re-run the same sample set.
4. Compare:
   - timeout count
   - average latency
   - URL coverage
   - EOSL coverage
   - structured interface coverage
5. Only then decide whether the new variant is safe enough to re-enable auto-apply.
