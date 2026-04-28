from __future__ import annotations

import re
from typing import Any


def normalize_vendor(vendor: str) -> str:
    return " ".join((vendor or "").strip().lower().split())


VENDOR_RULES: dict[str, dict[str, Any]] = {
    "cisco": {
        "domains": ["cisco.com"],
        "extra_queries": [
            "datasheet pdf",
            "official product page",
            "end of sale lifecycle",
        ],
        "spec_positive": ["datasheet", "data-sheet", "/products/collateral/", ".pdf"],
        "spec_negative": ["/support/", "field-notice", "release-notes", "/manual/"],
        "source_positive": ["/support/", "end-of-sale", "end of sale", "eol", "eosl", "lifecycle", "field notice"],
        "seed_bonus": ["/products/collateral/", "datasheet", "data-sheet", ".pdf"],
        "seed_penalty": ["/techdocs/", "/manual/", "guide", "release-notes"],
        "notes": [
            "Cisco support model pages often work better as lifecycle/source candidates than spec_url candidates.",
            "Cisco collateral datasheet URLs are the preferred spec_url shape.",
        ],
    },
    "juniper": {
        "domains": ["juniper.net"],
        "extra_queries": ["datasheet pdf", "product page", "end of life"],
        "spec_positive": ["datasheet", "data-sheet", ".pdf", "/us/en/products/"],
        "spec_negative": ["manual", "release-notes", "documentation"],
        "source_positive": ["end-of-life", "end of life", "eol", "lifecycle"],
        "seed_bonus": ["datasheet", ".pdf", "/us/en/products/"],
        "seed_penalty": ["documentation", "manual", "release-notes"],
        "notes": [
            "Juniper official datasheet pages are usually stable spec_url candidates.",
        ],
    },
    "arista": {
        "domains": ["arista.com"],
        "extra_queries": ["datasheet pdf", "network switch datasheet", "quick look datasheet"],
        "spec_positive": ["datasheet", "data-sheet", ".pdf", "/products/"],
        "spec_negative": ["quick-look"],
        "source_positive": ["end-of-sale", "eol", "lifecycle"],
        "seed_bonus": ["datasheet", ".pdf", "/products/"],
        "seed_penalty": ["quick-look", "manual", "release-notes"],
        "notes": [
            "Arista often exposes good spec candidates through URL patterns alone, even when fetched HTML titles are noisy.",
            "Quick Look sheets are weaker than the main datasheet/product page.",
        ],
    },
    "f5": {
        "domains": ["f5.com"],
        "extra_queries": ["datasheet pdf", "official product page", "end of support", "support lifecycle"],
        "spec_positive": ["datasheet", ".pdf", "big-ip", "/products/"],
        "spec_negative": ["manual", "release-notes", "training"],
        "source_positive": ["end of support", "end-of-support", "eol", "lifecycle"],
        "seed_bonus": ["datasheet", ".pdf", "big-ip", "/products/"],
        "seed_penalty": ["manual", "release-notes", "training"],
        "notes": ["F5 datasheets are often PDF-first and lifecycle pages more often use end-of-support language than EOSL."],
    },
    "a10 networks": {
        "domains": ["a10networks.com"],
        "extra_queries": ["datasheet pdf", "product page", "end of life"],
        "spec_positive": ["datasheet", ".pdf", "/products/", "thunder"],
        "spec_negative": ["release-notes", "deployment guide", "configuration guide"],
        "source_positive": ["end-of-life", "end of life", "eol", "lifecycle"],
        "seed_bonus": ["datasheet", ".pdf", "/products/", "thunder"],
        "seed_penalty": ["release-notes", "deployment guide", "configuration guide"],
        "notes": ["A10 often exposes clean product and datasheet URLs under /products/."],
    },
    "axgate": {
        "domains": ["axgate.com"],
        "extra_queries": ["NGFW product page", "specification", "datasheet", "brochure"],
        "spec_positive": ["/main/about/product/ngfw.php", "library", "brochure", "datasheet"],
        "spec_negative": ["blog", "newsroom", "recruit"],
        "source_positive": ["eol", "end of life", "lifecycle", "support"],
        "seed_bonus": ["/main/about/product/ngfw.php", "library", "brochure"],
        "seed_penalty": ["blog", "newsroom", "recruit"],
        "notes": ["AXGATE NGFW models share a product-family page with a model comparison/specification table; do not require per-model PDF."],
    },

    "secui": {
        "domains": ["secui.com"],
        "extra_queries": ["brochure", "datasheet", "download", "product brochure"],
        "spec_positive": ["/content/brochure", "/api/v1/posts", "/uploads/", "datasheet", "brochure"],
        "spec_negative": ["recruit", "news", "history"],
        "source_positive": ["eol", "end of life", "lifecycle", "support"],
        "seed_bonus": ["/content/brochure", "/uploads/", "datasheet", "brochure"],
        "seed_penalty": ["recruit", "news", "history"],
        "notes": ["SECUI exposes model datasheets/brochures through a React brochure page backed by /api/v1/posts; use brochure API/download links as official spec sources."],
    },

    "monitorapp": {
        "domains": ["monitorapp.com"],
        "extra_queries": ["support EOL", "End-of-Lifecycle", "hardware EOL", "product lifecycle"],
        "spec_positive": ["/products/aiwaap", "/products/aiswg", "/products/aisva"],
        "spec_negative": ["get-support", "newsletter"],
        "source_positive": ["/support", "eol", "end-of-lifecycle", "lifecycle", "제품 구매일"],
        "seed_bonus": ["/support", "eol", "end-of-lifecycle"],
        "seed_penalty": ["get-support", "newsletter"],
        "notes": ["MONITORAPP hardware specs may be gated behind brochure lead forms; do not auto-submit forms. Public support page provides relative H/W EOL policy: five years from purchase date for AIWAAP/AISWG/AISVA hardware models."],
    },

    "palo alto networks": {
        "domains": ["paloaltonetworks.com"],
        "extra_queries": ["datasheet pdf", "product page", "EOSL", "end of life summary", "hardware end of life", "hardware end-of-life dates"],
        "spec_positive": ["datasheet", ".pdf", "/network-security/", "/resources/datasheets/"],
        "spec_negative": ["release-notes", "administrator", "techdocs"],
        "source_positive": ["end-of-life", "end of life", "eol", "lifecycle"],
        "seed_bonus": ["hardware-end-of-life-dates", "end-of-life-announcements", "datasheet", ".pdf", "/network-security/", "/resources/datasheets/"],
        "seed_penalty": ["release-notes", "administrator", "techdocs"],
        "notes": ["Palo Alto commonly uses resource/datasheet URLs for specs and lifecycle summary pages for EOL."],
    },
    "fortinet": {
        "domains": ["fortinet.com"],
        "extra_queries": ["datasheet pdf", "product page", "fortiguard end of support", "product lifecycle"],
        "spec_positive": ["datasheet", ".pdf", "/products/", "fortigate"],
        "spec_negative": ["administration guide", "release-notes", "handbook"],
        "source_positive": ["end of support", "end-of-support", "eol", "lifecycle"],
        "seed_bonus": ["datasheet", ".pdf", "/products/", "fortigate"],
        "seed_penalty": ["administration guide", "release-notes", "handbook"],
        "notes": ["Fortinet lifecycle material often uses end-of-support terminology and lives in FortiGuard-backed pages."],
    },
    "dell": {
        "domains": ["dell.com"],
        "extra_queries": ["technical guidebook pdf", "spec sheet", "product support lifecycle"],
        "spec_positive": ["technical guide", "technical guidebook", "spec sheet", ".pdf", "/productdetails/"],
        "spec_negative": ["owners manual", "installation and service manual", "release-notes"],
        "source_positive": ["end of life", "end-of-life", "lifecycle", "support"],
        "seed_bonus": ["technical guide", "technical guidebook", "spec sheet", ".pdf"],
        "seed_penalty": ["owners manual", "installation and service manual", "release-notes"],
        "notes": ["Dell server specs are frequently best on technical guidebook PDFs rather than the bare product page."],
    },
    "ibm": {
        "domains": ["ibm.com"],
        "extra_queries": ["datasheet pdf", "product guide", "announcement letter"],
        "spec_positive": ["datasheet", "product guide", ".pdf", "/products/"],
        "spec_negative": ["documentation", "manual", "release-notes"],
        "source_positive": ["withdrawal", "end of support", "lifecycle", "announcement"],
        "seed_bonus": ["datasheet", "product guide", ".pdf", "/products/"],
        "seed_penalty": ["documentation", "manual", "release-notes"],
        "notes": ["IBM often publishes hardware lifecycle signals via announcement or withdrawal notices rather than a single EOL page."],
    },
    "netapp": {
        "domains": ["netapp.com"],
        "extra_queries": ["datasheet pdf", "product page", "end of availability", "support bulletin"],
        "spec_positive": ["datasheet", ".pdf", "/data-storage/", "/products/"],
        "spec_negative": ["docs.", "manual", "release-notes"],
        "source_positive": ["end of availability", "end of support", "eoa", "eol", "lifecycle"],
        "seed_bonus": ["datasheet", ".pdf", "/data-storage/", "/products/"],
        "seed_penalty": ["docs.", "manual", "release-notes"],
        "notes": ["NetApp lifecycle references frequently use EOA/EOS language in support bulletins."],
    },
    "pure storage": {
        "domains": ["purestorage.com"],
        "extra_queries": ["datasheet pdf", "product page", "end of support"],
        "spec_positive": ["datasheet", ".pdf", "/products/", "flasharray"],
        "spec_negative": ["documentation", "release-notes", "blog"],
        "source_positive": ["end of support", "end-of-support", "lifecycle", "eol"],
        "seed_bonus": ["datasheet", ".pdf", "/products/", "flasharray"],
        "seed_penalty": ["documentation", "release-notes", "blog"],
        "notes": ["Pure Storage often has strong product URLs, but lifecycle pages may be sparse."],
    },
    "aruba": {
        "domains": ["arubanetworks.com", "hpe.com"],
        "extra_queries": [
            "HPE Aruba Networking datasheet",
            "psnow datasheet",
            "switch series datasheet",
        ],
        "spec_positive": ["/psnow/doc/", "/psnow/downloaddoc/", "datasheet", ".pdf", "switch series"],
        "spec_negative": ["/techdocs/", "help.", "centralon-prem", "developer."],
        "source_positive": ["end-of-sale", "eol", "eosl", "lifecycle", "hardware-end-of-sale"],
        "seed_bonus": ["/psnow/doc/", "/psnow/downloaddoc/", "datasheet", ".pdf", "switch series"],
        "seed_penalty": ["/techdocs/", "help.", "centralon-prem", "developer.", "guide", "manual"],
        "notes": [
            "Aruba spec docs are often on HPE psnow, not only arubanetworks.com.",
            "Aruba techdocs/help pages are usually documentation, not spec_url targets.",
        ],
    },
}

DEFAULT_RULE = {
    "domains": [],
    "extra_queries": ["official product page", "datasheet pdf", "EOS OR EOL OR EOSL lifecycle"],
    "spec_positive": ["datasheet", "data-sheet", ".pdf", "/products/"],
    "spec_negative": ["/support/", "/techdocs/", "guide", "manual", "help.", "centralon-prem"],
    "source_positive": ["end-of-sale", "end of sale", "eol", "eosl", "lifecycle"],
    "seed_bonus": ["datasheet", "data-sheet", ".pdf", "/products/"],
    "seed_penalty": ["/support/", "/techdocs/", "guide", "manual", "help.", "centralon-prem"],
    "notes": [],
}


def get_vendor_rule(vendor: str) -> dict[str, Any]:
    key = normalize_vendor(vendor)
    rule = dict(DEFAULT_RULE)
    specific = VENDOR_RULES.get(key) or {}
    for field in DEFAULT_RULE:
        default_value = DEFAULT_RULE[field]
        specific_value = specific.get(field)
        if isinstance(default_value, list):
            rule[field] = list(dict.fromkeys([*(default_value or []), *(specific_value or [])]))
        else:
            rule[field] = specific_value if specific_value is not None else default_value
    return rule


def build_search_queries(vendor: str, name: str, classification: str | None = None) -> list[str]:
    query_base = f'{vendor} {name}'.strip()
    rule = get_vendor_rule(vendor)
    queries = [f'{query_base} {suffix}'.strip() for suffix in rule.get('extra_queries') or []]
    if classification:
        queries.append(f'{query_base} {classification} datasheet')
    return list(dict.fromkeys(q for q in queries if q.strip()))


def build_lifecycle_queries(vendor: str, name: str, classification: str | None = None) -> list[str]:
    query_base = f'{vendor} {name}'.strip()
    rule = get_vendor_rule(vendor)
    lifecycle_suffixes = [
        'end of sale',
        'end of life',
        'end of support',
        'lifecycle',
        'support bulletin',
    ]
    queries = [f'{query_base} {suffix}'.strip() for suffix in lifecycle_suffixes]
    if classification:
        queries.append(f'{query_base} {classification} lifecycle')
    queries.extend(f'{query_base} {suffix}'.strip() for suffix in (rule.get('extra_queries') or []) if any(token in suffix.lower() for token in ['end of', 'lifecycle', 'support']))
    return list(dict.fromkeys(q for q in queries if q.strip()))


def vendor_domains(vendor: str) -> list[str]:
    return list(get_vendor_rule(vendor).get('domains') or [])


def model_tokens(name: str) -> list[str]:
    raw = (name or '').strip().lower()
    compact = re.sub(r'[^a-z0-9]+', '', raw)
    dashed = re.sub(r'\s+', '-', raw)
    spaced = re.sub(r'[-_/]+', ' ', raw)
    tokens = [raw, compact, dashed, spaced]
    return [token for token in dict.fromkeys(token for token in tokens if token)]


def score_seed_url(vendor: str, name: str, url: str) -> int:
    value = (url or '').lower()
    rule = get_vendor_rule(vendor)
    score = 0
    score += sum(3 for token in rule.get('seed_bonus') or [] if token in value)
    score -= sum(3 for token in rule.get('seed_penalty') or [] if token in value)
    if any(token in value for token in ['product', 'series']):
        score += 1
    for token in model_tokens(name):
        if token and token in value:
            score += 3
            break
    return score


def score_spec_candidate(vendor: str, url: str, title: str = '', excerpt: str = '', model_name: str = '') -> int:
    value = ((url or '') + ' ' + (title or '') + ' ' + (excerpt or '')).lower()
    rule = get_vendor_rule(vendor)
    score = 0
    score += sum(3 for token in rule.get('spec_positive') or [] if token in value)
    score -= sum(3 for token in rule.get('spec_negative') or [] if token in value)
    if 'product overview' in value:
        score += 2
    if 'specifications' in value:
        score += 2
    if model_name and any(token in value for token in model_tokens(model_name)):
        score += 3
    if '/datasheets' in (url or '').lower() and model_name and not any(token in value for token in model_tokens(model_name)):
        score -= 1
    if (url or '').lower().endswith('.md'):
        score -= 1
    return score


def score_source_candidate(vendor: str, url: str, title: str = '', excerpt: str = '', model_name: str = '') -> int:
    value = ((url or '') + ' ' + (title or '') + ' ' + (excerpt or '')).lower()
    rule = get_vendor_rule(vendor)
    score = sum(4 for token in rule.get('source_positive') or [] if token in value)
    if '/support/' in value or '/bulletins/' in value:
        score += 1
    if model_name and any(token in value for token in model_tokens(model_name)):
        score += 1
    if any(token in value for token in ['datasheet', 'data-sheet']) and not any(token in value for token in ['end-of-sale', 'end of sale', 'end-of-life', 'end of life', 'end of support', 'lifecycle']):
        score -= 1
    return score


def is_bad_spec_fallback(url: str) -> bool:
    value = (url or '').lower()
    return any(token in value for token in ['end-of-sale', 'end_of_sale', 'eol', 'eosl', 'lifecycle', '/support/', '/techdocs/', 'guide', 'manual', 'help.', 'centralon-prem'])


def is_preferred_lifecycle_url(vendor: str, url: str) -> bool:
    value = (url or '').lower()
    key = normalize_vendor(vendor)
    if not value:
        return False
    # generic bad lifecycle candidates
    if any(token in value for token in ['/attachments/', '/download/', '.pdf']) and not any(token in value for token in ['end-of-sale', 'end-of-life', 'end of support', 'lifecycle']):
        return False
    if key == 'cisco':
        return any(token in value for token in ['/support/', 'end-of-sale', 'field-notice', 'bulletin']) and '/collateral/' not in value
    if key == 'juniper':
        return any(token in value for token in ['end-of-life', 'end of life', 'lifecycle', '/support/']) and '/specs' not in value
    if key == 'fortinet':
        return ('fortiguard' in value or '/support/' in value or 'end-of-support' in value or 'product-life-cycle' in value or 'lifecycle' in value) and '/attachments/' not in value
    if key == 'dell':
        return (any(token in value for token in ['lifecycle', 'end-of-life']) or '/support/product-details/' in value) and 'spec-sheet' not in value and '/drivers' not in value
    if key == 'f5':
        return any(token in value for token in ['end-of-support', 'end of support', 'lifecycle', '/support/']) and '/products/' not in value
    if key == 'palo alto networks':
        return any(token in value for token in ['end-of-life', 'end of life', 'lifecycle']) and '/resources/datasheets/' not in value and '/hardware/' not in value
    if key == 'monitorapp':
        return '/support' in value and 'monitorapp.com' in value
    return is_bad_spec_fallback(url)
