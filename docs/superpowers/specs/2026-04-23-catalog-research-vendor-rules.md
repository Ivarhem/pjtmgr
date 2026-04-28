# Catalog Research Vendor Rules

This file documents durable vendor-specific heuristics used by the v2 catalog research path.

## Current vendors

### Cisco
- Prefer collateral datasheet URLs for `spec_url`.
- Treat support/model pages as better lifecycle/source candidates than primary spec links.

### Juniper
- Official datasheet pages are usually stable enough to use directly as `spec_url`.

### Arista
- URL patterns are often more reliable than fetched title text alone.
- Prefer main datasheet/product pages over Quick Look sheets.

### Aruba / HPE Aruba Networking
- Official spec docs often live on `hpe.com/psnow`, not only `arubanetworks.com`.
- `techdocs`, `help`, and developer pages are usually documentation traps, not `spec_url` targets.
- HPE psnow links can be fetch-fragile, so official ranked seeds may need fallback promotion.

## Rule split
- `scripts/catalog_vendor_rules.py` contains machine-used heuristics.
- This note is for maintainers and future debugging context.
