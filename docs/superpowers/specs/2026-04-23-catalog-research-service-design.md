# Catalog Research Service Design (2026-04-23)

## Goal

Move catalog research out of the main `pjtmgr` app process into a standalone service that can be deployed behind `ivarhem.asuscomm.com`, while keeping backend selection flexible (`service`, `http`, `mcp`).

## Final Direction

- `pjtmgr-app` uses `CATALOG_RESEARCH_BACKEND=service` by default.
- A dedicated `catalog-research-service` container runs on `127.0.0.1:8765`.
- Caddy reverse-proxies it at `/apps/catalog-research`.
- The service supports two internal providers:
  - `anthropic`: direct Anthropic API key usage
  - `codex`: Codex CLI execution using a logged-in local Codex session

## Why split it out

- Keeps LLM/provider concerns separate from app runtime.
- Makes external publishing and auth easier.
- Avoids container-local MCP transport coupling for the main app.
- Better matches business deployment than personal-machine SSH bridging.

## Auth model

- Service ingress uses `CATALOG_RESEARCH_SERVICE_TOKEN` bearer auth.
- For `codex` provider, host `~/.codex/auth.json` is mounted read-only into the service container and copied into a writable container-local `~/.codex/auth.json` before execution.

## Codex provider notes

- Verified working path uses `gpt-5.4` rather than `gpt-5-codex`, because the active ChatGPT-backed Codex login did not accept `gpt-5-codex`.
- Codex requests were initially too slow with the full normalization prompt, so the service now uses a much shorter Codex-specific prompt and normalizes the returned JSON into the broader catalog shape.
- Recommended starting envs for Codex mode:
  - `CATALOG_RESEARCH_PROVIDER=codex`
  - `CATALOG_RESEARCH_CODEX_MODEL=gpt-5.4`
  - `CATALOG_RESEARCH_CODEX_TIMEOUT=90`

## Operational shape

- Internal URL: `http://catalog-research-service:8765`
- External URL: `https://ivarhem.asuscomm.com/apps/catalog-research`
- Health: `GET /health`
- Research: `POST /lookup-hardware`

## Known limitations

- Codex provider currently favors short, high-signal responses over exhaustive hardware normalization.
- Service-level schema normalization is intentionally conservative for Codex output.
- For production-critical accuracy and repeatability, direct API-key provider mode is still the more stable baseline.
