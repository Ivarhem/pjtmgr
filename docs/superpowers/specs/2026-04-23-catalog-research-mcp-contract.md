# Catalog Research MCP Contract (2026-04-23)

## Goal
Let `pjtmgr` keep the catalog-research protocol while delegating actual lookup execution to an MCP tool.

## Backend env
- `CATALOG_RESEARCH_BACKEND=mcp`
- `CATALOG_RESEARCH_MCP_TOOL=catalog_research.lookup_hardware`
- `CATALOG_RESEARCH_MCP_SERVER=` (optional, when selector needs server prefix)
- `CATALOG_RESEARCH_MCPORTER_BIN=/home/clawd/.npm-global/node_modules/.bin/mcporter` (example)

## Expected MCP input
```json
{
  "vendor": "Cisco",
  "name": "Catalyst 9300",
  "reference_url": "https://vendor.example/product",
  "classification": "네트워크 > 스위치",
  "size_unit": 1,
  "power_count": null,
  "power_type": null,
  "power_watt": null
}
```

## Expected MCP output
```json
{
  "confidence": "high|medium|low",
  "hardware_spec": {
    "size_unit": 1,
    "width_mm": null,
    "height_mm": null,
    "depth_mm": null,
    "weight_kg": null,
    "power_count": null,
    "power_type": null,
    "power_watt": null,
    "cpu_summary": null,
    "memory_summary": null,
    "throughput_summary": null,
    "os_firmware": null,
    "spec_url": null
  },
  "eosl": {
    "eos_date": null,
    "eosl_date": null,
    "eosl_note": null,
    "source_url": null
  },
  "interfaces": [
    {
      "interface_type": "GE RJ45",
      "speed": "1G",
      "count": 8,
      "connector_type": "RJ-45",
      "capacity_type": "fixed",
      "note": null
    }
  ],
  "uncertain_fields": ["eosl_date"]
}
```

## Notes
- `pjtmgr` owns skip logic, normalization, and apply logic.
- MCP tool should only research and return structured data.
- If MCP returns wrapper JSON like `{ "result": { ... } }`, current backend unwraps it.


## Recommended pjtmgr wiring

### Backend env
```bash
CATALOG_RESEARCH_BACKEND=mcp
CATALOG_RESEARCH_MCP_SERVER=catalog-research
CATALOG_RESEARCH_MCP_TOOL=lookup_hardware
CATALOG_RESEARCH_MCP_CONFIG=/app/config/mcporter.json
# optional if PATH differs
CATALOG_RESEARCH_MCPORTER_BIN=mcporter
```

### Project config template
Start from: `config/mcporter.catalog-research.example.json`

Recommended live path inside container: `/app/config/mcporter.json`

### Selector rule
- If `CATALOG_RESEARCH_MCP_TOOL` already contains a dot, use it as-is.
- Otherwise compose `CATALOG_RESEARCH_MCP_SERVER.CATALOG_RESEARCH_MCP_TOOL`.
- Recommended selector: `catalog-research.lookup_hardware`

### Current gap
This repo now has a clean registration path, but it still needs a real MCP server implementation or remote MCP endpoint behind the `catalog-research` server entry.
