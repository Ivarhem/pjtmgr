#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from catalog_vendor_rules import build_search_queries, normalize_vendor, score_source_candidate, score_spec_candidate, vendor_domains

CODEX_BIN = os.getenv("CATALOG_RESEARCH_CODEX_BIN") or "/home/ivarhem/.npm-global/bin/codex"
CODEX_MODEL = (os.getenv("CATALOG_RESEARCH_CODEX_MODEL") or os.getenv("CODEX_MODEL") or "").strip()
CODEX_TIMEOUT = int(os.getenv("CATALOG_RESEARCH_V2_CODEX_TIMEOUT") or "45")
CODEX_AUTH_SRC = Path(os.getenv("CATALOG_RESEARCH_CODEX_AUTH_SRC") or "/run/catalog-research-secrets/codex-auth.json")
CODEX_HOME = Path.home() / ".codex"


def build_source_plan(vendor: str, name: str, classification: str | None = None, reference_url: str | None = None) -> dict[str, Any]:
    domains = vendor_domains(vendor)
    queries = build_search_queries(vendor, name, classification)
    return {
        "vendor_domains": domains,
        "reference_url": reference_url or None,
        "search_queries": queries,
        "candidate_url_types": ["product_page", "datasheet", "lifecycle_notice"],
    }


def _prepare_codex_auth() -> None:
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    target = CODEX_HOME / "auth.json"
    if not CODEX_AUTH_SRC.exists():
        return
    src_bytes = CODEX_AUTH_SRC.read_bytes()
    if not target.exists() or target.read_bytes() != src_bytes:
        target.write_bytes(src_bytes)
        target.chmod(0o600)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start:end + 1]
    return json.loads(text)


def _is_pdf_content(url: str, content_type: str | None, body: bytes | None) -> bool:
    value = ((content_type or '') + ' ' + (url or '')).lower()
    if 'application/pdf' in value or value.split('?')[0].endswith('.pdf'):
        return True
    return bool(body and body[:5] == b'%PDF-')


def _extract_pdf_text(body: bytes, timeout: int = 20) -> str:
    """Best-effort PDF text extraction using optional pdfminer.six or pdftotext."""
    if not body:
        return ''
    try:
        from io import BytesIO
        from pdfminer.high_level import extract_text  # type: ignore
        text = extract_text(BytesIO(body)) or ''
        return re.sub(r'[ \t]+', ' ', text).strip()
    except Exception:
        pass
    pdftotext = shutil.which('pdftotext')
    if pdftotext:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(body)
            src_path = src.name
        try:
            proc = subprocess.run([pdftotext, '-layout', src_path, '-'], capture_output=True, timeout=timeout, check=False)
            if proc.returncode == 0:
                text = proc.stdout.decode('utf-8', errors='ignore')
                return re.sub(r'[ \t]+', ' ', text).strip()
        except Exception:
            pass
        finally:
            try:
                os.unlink(src_path)
            except Exception:
                pass
    return ''


def fetch_source(url: str, timeout: int = 20) -> dict[str, Any]:
    body = None
    content_type = None
    final_url = url
    try:
        req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0 pjtmgr-v2-prototype"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get_content_type()
            final_url = resp.geturl()
            body = resp.read()
    except Exception as first_exc:
        proc = subprocess.run(
            ["curl", "-L", "--max-time", str(timeout), "-A", "Mozilla/5.0 pjtmgr-v2-prototype", "-D", "-", url],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise first_exc
        raw = proc.stdout
        header_end = raw.find(b"\r\n\r\n")
        header_sep_len = 4
        if header_end < 0:
            header_end = raw.find(b"\n\n")
            header_sep_len = 2
        headers = raw[:header_end].decode("utf-8", errors="ignore") if header_end >= 0 else ""
        body = raw[header_end + header_sep_len:] if header_end >= 0 else raw
        m = re.search(r"(?im)^content-type:\s*([^;\s]+)", headers)
        content_type = m.group(1).strip() if m else "text/html"
    result = {
        "url": url,
        "final_url": final_url,
        "content_type": content_type,
        "title": None,
        "description": None,
        "text_excerpt": None,
        "html_excerpt": None,
        "ok": True,
    }
    if _is_pdf_content(final_url or url, content_type, body):
        text = _extract_pdf_text(body or b"", timeout=timeout)
        result["content_type"] = content_type or "application/pdf"
        result["title"] = Path(urllib.request.url2pathname((final_url or url).split("?")[0])).name or None
        result["text_excerpt"] = text[:80000] if text else f"pdf text extraction unavailable ({content_type})"
    elif content_type == "text/html":
        html = body.decode("utf-8", errors="ignore")
        title_match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        desc_match = re.search(r"<meta[^>]+name=['\"]description['\"][^>]+content=['\"](.*?)['\"]", html, re.I | re.S)
        cleaned = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
        cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.I | re.S)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        result["title"] = title_match.group(1).strip() if title_match else None
        result["description"] = desc_match.group(1).strip() if desc_match else None
        result["html_excerpt"] = html[:120000] if html else None
        result["text_excerpt"] = cleaned[:50000] if cleaned else None
    else:
        result["text_excerpt"] = f"binary content skipped ({content_type})"
    return result


def run_interface_probe(vendor: str, name: str, classification: str | None = None) -> dict[str, Any]:
    codex = shutil.which(CODEX_BIN) if os.path.sep not in CODEX_BIN else (CODEX_BIN if os.path.exists(CODEX_BIN) else None)
    if not codex:
        return {"ok": False, "error": f"codex not found: {CODEX_BIN}"}
    _prepare_codex_auth()
    prompt = (
        'Return strict JSON only. '
        'JSON shape: {"confidence":"high|medium|low","interfaces":[],"uncertain_fields":[]} '
        f'Research built-in/default interfaces only for vendor="{vendor}" model="{name}" classification="{classification or "unknown"}". '
        'Use built-in knowledge only. No prose. '
        'For each interface include interface_type, speed, count, connector_type, capacity_type, note. '
        'If unsure, return an empty array and add "interfaces" to uncertain_fields.'
    )
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
        output_path = f.name
    cmd = [codex, "exec", "--skip-git-repo-check", "--sandbox", "read-only"]
    if CODEX_MODEL:
        cmd.extend(["--model", CODEX_MODEL])
    cmd.extend(["--output-last-message", output_path, prompt])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CODEX_TIMEOUT,
            check=False,
            cwd="/tmp",
            env={**os.environ, "CODEX_DISABLE_TELEMETRY": "1"},
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            return {"ok": False, "error": detail or "codex exec failed"}
        text = Path(output_path).read_text(encoding="utf-8").strip()
        return {"ok": True, "result": _extract_json(text)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass



def _clean_pdf_lines(text_value: str | None) -> list[str]:
    return [line.strip() for line in str(text_value or '').splitlines() if line.strip()]


def _parse_secui_count(value: str) -> tuple[int | None, str | None, str | None]:
    raw = str(value or '').strip()
    if not raw or raw == '-':
        return None, None, None
    m = re.search(r'(\d+)\s*\(\s*max\s*(\d+)\s*\)', raw, re.I)
    if m:
        return int(m.group(1)), 'max', f"Base {m.group(1)}, max {m.group(2)}"
    m = re.search(r'\(\s*max\s*(\d+)\s*\)', raw, re.I)
    if m:
        return int(m.group(1)), 'max', f"Max {m.group(1)}"
    m = re.search(r'\b(\d+)\b', raw)
    if m:
        return int(m.group(1)), 'fixed', None
    return None, None, None


def _extract_secui_specs(text_value: str | None, vendor: str = '') -> dict[str, Any]:
    """Extract model-local SECUI brochure/datasheet specs from PDF text."""
    if normalize_vendor(vendor) != 'secui' or not text_value:
        return {}
    lines = _clean_pdf_lines(text_value)
    try:
        start = next(i for i, line in enumerate(lines) if line.lower() == 'hardware specification')
    except StopIteration:
        return {}
    tail: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith('(주)') or 'Copyright' in line:
            break
        tail.append(line)
    if not tail:
        return {}
    joined = ' '.join(tail)
    result: dict[str, Any] = {}

    first_value_idx = next((i for i, line in enumerate(tail) if re.fullmatch(r'\d+\s*Core', line, re.I)), None)
    raw_labels = tail[:first_value_idx] if first_value_idx is not None else []
    # SECUI tables use group headers such as Storage/Interface that do not
    # consume a value column. Drop them before aligning labels to values.
    labels = [label for label in raw_labels if label not in {'Storage', 'Interface'}]
    values = tail[first_value_idx:] if first_value_idx is not None else []

    def value_for(label: str) -> str | None:
        if label in labels:
            idx = labels.index(label)
            if idx < len(values):
                return values[idx]
        return None

    cpu = value_for('CPU') or next((line for line in tail if re.fullmatch(r'\d+\s*Core', line, re.I)), None)
    if cpu:
        result['cpu_summary'] = re.sub(r'\s+', ' ', cpu)
    mem = value_for('Memory') or next((line for line in tail if re.fullmatch(r'\d+\s*GB', line, re.I)), None)
    if mem:
        result['memory_summary'] = re.sub(r'\s+', ' ', mem)

    system_storage = value_for('System')
    log_storage = value_for('Log')
    if system_storage and log_storage:
        result['storage_summary'] = f"System: {system_storage}; Log: {log_storage}"
    else:
        storage_values = [line for line in tail if re.search(r'\b(?:SSD|HDD|eMMC)?\s*\d+\s*(?:GB|TB)\b', line, re.I)]
        if mem and mem in storage_values:
            storage_values = storage_values[storage_values.index(mem) + 1:]
        if storage_values:
            result['storage_summary'] = f"System: {storage_values[0]}; Log: {storage_values[1]}" if len(storage_values) >= 2 else storage_values[0]

    power = value_for('Power Supply')
    if not power and 'Power Supply' in tail:
        idx = tail.index('Power Supply')
        if idx + 1 < len(tail) and re.fullmatch(r'Single|Dual|Redundant', tail[idx + 1], re.I):
            power = tail[idx + 1]
    if power and re.fullmatch(r'Single|Dual|Redundant', power, re.I):
        result['power_summary'] = f"{power} power supply"
        result['power_count'] = 2 if power.lower() in {'dual', 'redundant'} else 1
        result['power_type'] = 'AC'

    dim_value = value_for('Dimension (W× D× H)') or joined
    dim_match = re.search(r'\b(\d+)\s*U\s*\((\d+)\s*[×xX]\s*(\d+)\s*[×xX]\s*(\d+)\)', dim_value, re.I)
    if dim_match:
        result['size_unit'] = int(dim_match.group(1))
        result['width_mm'] = int(dim_match.group(2))
        result['depth_mm'] = int(dim_match.group(3))
        result['height_mm'] = int(dim_match.group(4))

    interfaces: list[dict[str, Any]] = []
    for label in ['100GF', '40GF', '10GF', '1GF', '1GC', '1G Fiber', '1G Copper']:
        value = value_for(label)
        count, capacity_type, note = _parse_secui_count(value or '')
        if not count:
            continue
        if label in {'1GC', '1G Copper'}:
            interfaces.append({'interface_type': 'GE RJ45', 'speed': '1G', 'count': count, 'connector_type': 'RJ-45', 'capacity_type': capacity_type or 'fixed', 'note': note})
        elif label in {'1GF', '1G Fiber'}:
            interfaces.append({'interface_type': 'GE SFP', 'speed': '1G', 'count': count, 'connector_type': 'SFP', 'capacity_type': capacity_type or 'fixed', 'note': note})
        elif label == '10GF':
            interfaces.append({'interface_type': 'SFP+', 'speed': '10G', 'count': count, 'connector_type': 'SFP+', 'capacity_type': capacity_type or 'fixed', 'note': note})
        elif label == '40GF':
            interfaces.append({'interface_type': 'QSFP+', 'speed': '40G', 'count': count, 'connector_type': 'QSFP+', 'capacity_type': capacity_type or 'fixed', 'note': note})
        elif label == '100GF':
            interfaces.append({'interface_type': 'QSFP28', 'speed': '100G', 'count': count, 'connector_type': 'QSFP28', 'capacity_type': capacity_type or 'fixed', 'note': note})
    if interfaces:
        result['interfaces'] = interfaces
    return result

def _extract_size_unit(text_value: str | None) -> int | None:
    if not text_value:
        return None
    for pattern in [r'\b(\d+)\s*RU\b', r'\b(\d+)\s*U\b', r'\b(\d+)RU\b', r'\b(\d+)U\b', r'\b(\d+)\s*rack\s*unit\b', r'\b(\d+)-RU\b']:
        m = re.search(pattern, text_value, re.I)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None


def _extract_power_info(text_value: str | None) -> dict[str, Any]:
    """Extract only explicit, conservative power supply facts from source text."""
    result: dict[str, Any] = {"power_count": None, "power_type": None, "power_watt": None}
    if not text_value:
        return result
    text = re.sub(r'\s+', ' ', text_value)
    low = text.lower()

    # Type: only set when explicit power wording appears nearby.
    power_window = low
    if 'dc power' in power_window or re.search(r'\bdc\s+power\s+supply', power_window):
        result['power_type'] = 'DC'
    if 'ac power' in power_window or re.search(r'\bac\s+power\s+supply', power_window):
        # Prefer AC/DC if both are explicitly supported.
        result['power_type'] = 'AC/DC' if result.get('power_type') == 'DC' else 'AC'

    # Explicit counts near PSU/power-supply wording.
    count_patterns = [
        r'(\d+)\s*[xX]\s*(?:hot[- ]?swap(?:pable)?\s*)?(?:AC|DC)?\s*power\s*(?:supplies|supply|units|unit|module|modules|PSU|PSUs)',
        r'(\d+)\s*(?:AC|DC)?\s*power\s*(?:supplies|supply|units|unit|module|modules|PSU|PSUs)',
        r'(?:power\s*(?:supplies|supply|units|unit|module|modules|PSU|PSUs))\D{0,40}(\d+)\s*[xX]',
        r'(?:dual|redundant)\s+(?:hot[- ]?swap(?:pable)?\s*)?(?:AC|DC)?\s*power\s*(?:supplies|supply|units|unit|module|modules|PSU|PSUs)',
    ]
    for pat in count_patterns:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        if pat.startswith('(?:dual'):
            result['power_count'] = 2
        else:
            try:
                value = int(m.group(1))
                if 1 <= value <= 12:
                    result['power_count'] = value
            except Exception:
                pass
        if result.get('power_count'):
            break

    # PSU wattage: only capture explicit W/PSU style values, not system max draw.
    m = re.search(r'(\d{2,5})\s*W\s*(?:AC|DC)?\s*(?:power\s*)?(?:supply|PSU)', text, re.I)
    if m:
        try:
            result['power_watt'] = int(m.group(1))
        except Exception:
            pass
    return result


def _extract_interfaces(text_value: str | None) -> list[dict[str, Any]]:
    if not text_value:
        return []
    interfaces: list[dict[str, Any]] = []
    patterns = [
        (r'(\d+)\s+(downlink )?ports?[^.]{0,160}?supporting\s+1-,\s*10-,\s*or\s*25-Gbps Ethernet', {
            'interface_type': 'SFP28', 'speed': '25G', 'connector_type': 'SFP28', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s+(uplink )?ports?[^.]{0,160}?configured as\s+40\s+or\s+100-Gbps Ethernet', {
            'interface_type': 'QSFP28', 'speed': '100G', 'connector_type': 'QSFP28', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s+downlink ports?[^.]{0,160}?1-,\s*10-,\s*or\s*25-Gbps Ethernet', {
            'interface_type': 'SFP28', 'speed': '25G', 'connector_type': 'SFP28', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s+uplink ports?[^.]{0,160}?40\s+or\s+100-Gbps Ethernet', {
            'interface_type': 'QSFP28', 'speed': '100G', 'connector_type': 'QSFP28', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s*x\s*1/10/25\s*Gbps\s*(SFP28|SFP\+)?\s*ports?', {
            'interface_type': 'SFP28', 'speed': '25G', 'connector_type': 'SFP28', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s*x\s*40/100\s*Gbps\s*(QSFP28|QSFP\+)?\s*ports?', {
            'interface_type': 'QSFP28', 'speed': '100G', 'connector_type': 'QSFP28', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s*x\s*100M/1/10\s*Gbps\s*(BASE-T|RJ-?45)\s*ports?', {
            'interface_type': 'Ethernet', 'speed': '10G', 'connector_type': 'RJ-45', 'capacity_type': 'fixed'
        }),
        (r'(\d+)\s*x\s*(1|10|25|40|100)Gb(?:E|ps)?\s*(SFP28|SFP\+|QSFP28|QSFP\+|RJ-?45)', None),
        (r'(\d+)\s+(?:x\s*)?(10/100/1000|1)\s*Gb?E?\s*(RJ-?45)?\s*(management|mgmt)', {
            'interface_type': 'Management Ethernet', 'connector_type': 'RJ-45', 'capacity_type': 'fixed'
        }),
    ]
    for pattern, template in patterns:
        for m in re.finditer(pattern, text_value, re.I):
            if template is None:
                count = int(m.group(1))
                speed = f"{m.group(2)}G" if m.group(2) != '10/100/1000' else '1G'
                connector = m.group(3).upper().replace('RJ45', 'RJ-45')
                interfaces.append({
                    'interface_type': connector.replace('RJ-45', 'Ethernet'),
                    'speed': speed,
                    'count': count,
                    'connector_type': connector,
                    'capacity_type': 'fixed',
                    'note': None,
                })
            else:
                count = int(m.group(1))
                row = dict(template)
                row['count'] = count
                row['note'] = None
                interfaces.append(row)
    dedup = []
    seen = set()
    for row in interfaces:
        key = (row.get('interface_type'), row.get('speed'), row.get('count'), row.get('connector_type'), row.get('capacity_type'))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)
    return dedup


def _build_model_tokens(name: str) -> list[str]:
    raw = (name or '').strip()
    tokens = {raw}
    compact = re.sub(r'[^A-Za-z0-9]+', '', raw)
    dashed = re.sub(r'\s+', '-', raw)
    spaced = re.sub(r'[-_/]+', ' ', raw)
    for value in [compact, dashed, spaced]:
        if value:
            tokens.add(value)
    return [token for token in sorted(tokens, key=len, reverse=True) if token]


def _slice_relevant_text(text_value: str | None, model_name: str) -> str:
    if not text_value:
        return ''
    haystack = str(text_value)
    if not model_name:
        return haystack

    # Priority 1: exact model anchor with a short trailing window, good for table rows
    exact = re.search(re.escape(model_name) + r'[^\n\.]{0,260}', haystack, re.I)
    if exact:
        window = exact.group(0)
        sibling = re.search(r'\b(?:Cisco\s+)?Nexus\s+[A-Z0-9-]{4,}\s+Switch\b', window[len(model_name):], re.I)
        if sibling:
            window = window[:len(model_name) + sibling.start()]
        return window

    lowered = haystack.lower()
    best_pos = -1
    best_token = None
    for token in _build_model_tokens(model_name):
        pos = lowered.find(token.lower())
        if pos >= 0 and (best_pos < 0 or pos < best_pos):
            best_pos = pos
            best_token = token
    if best_pos < 0:
        return haystack
    start = max(0, best_pos - 200)
    end = min(len(haystack), best_pos + 1200)
    window = haystack[start:end]
    sibling = re.search(r'\b(?:Cisco\s+)?Nexus\s+[A-Z0-9-]{4,}\s+Switch\b', window[(best_pos - start) + len(best_token or ''):], re.I)
    if sibling:
        cutoff = (best_pos - start) + len(best_token or '') + sibling.start()
        window = window[:cutoff]
    return window


def normalize_extracted_sources(extracted_sources: list[dict[str, Any]], model_name: str = "", vendor: str = "") -> dict[str, Any]:
    combined_text = ' '.join((item.get('title') or '') + ' ' + (item.get('description') or '') + ' ' + (item.get('text_excerpt') or '') for item in extracted_sources if item.get('ok'))
    focused_text = _slice_relevant_text(combined_text, model_name) if model_name else combined_text
    spec_url = None
    source_url = None
    best_spec_score = -10**9
    best_source_score = -10**9
    for item in extracted_sources:
        if not item.get('ok'):
            continue
        final_url = item.get('final_url') or item.get('url')
        title = (item.get('title') or '').lower()
        excerpt = ((item.get('text_excerpt') or '') + ' ' + (item.get('html_excerpt') or '')).lower()
        url_text = ((item.get('final_url') or '') + ' ' + (item.get('url') or '')).lower()
        spec_score = score_spec_candidate(vendor, final_url, title, excerpt, model_name)
        if spec_score > best_spec_score and spec_score > 0:
            best_spec_score = spec_score
            spec_url = final_url

        source_score = score_source_candidate(vendor, final_url, title, excerpt, model_name)
        if source_score > best_source_score and source_score > 0:
            best_source_score = source_score
            source_url = final_url
    secui_info = _extract_secui_specs(combined_text, vendor)
    size_unit = secui_info.get('size_unit') or _extract_size_unit(focused_text)
    height_mm = secui_info.get('height_mm') or (int(round(float(size_unit) * 44.45)) if size_unit is not None else None)
    power_info = _extract_power_info(focused_text)
    for key in ('power_count', 'power_type', 'power_watt'):
        if secui_info.get(key) is not None:
            power_info[key] = secui_info.get(key)
    interfaces = secui_info.get('interfaces') or _extract_interfaces(focused_text)
    uncertain_fields = []
    if not spec_url:
        uncertain_fields.append('hardware_spec.spec_url')
    if size_unit is None:
        uncertain_fields.append('hardware_spec.size_unit')
    if not interfaces:
        uncertain_fields.append('interfaces')
    uncertain_fields.extend(['eosl.eos_date', 'eosl.eosl_date'])
    confidence = 'medium' if (spec_url or size_unit or interfaces) else 'low'
    return {
        'confidence': confidence,
        'hardware_spec': {
            'size_unit': size_unit,
            'height_mm': height_mm,
            'power_count': power_info.get('power_count'),
            'power_type': power_info.get('power_type'),
            'power_watt': power_info.get('power_watt'),
            'power_summary': secui_info.get('power_summary'),
            'cpu_summary': secui_info.get('cpu_summary'),
            'memory_summary': secui_info.get('memory_summary'),
            'storage_summary': secui_info.get('storage_summary'),
            'width_mm': secui_info.get('width_mm'),
            'depth_mm': secui_info.get('depth_mm'),
            'spec_url': spec_url,
        },
        'eosl': {
            'eos_date': None,
            'eosl_date': None,
            'source_url': source_url,
        },
        'interfaces': interfaces,
        'uncertain_fields': uncertain_fields,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prototype catalog research v2 pipeline.")
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--classification", default="")
    ap.add_argument("--reference-url", default="")
    ap.add_argument("--with-interface-probe", action="store_true")
    ap.add_argument("--seed-url", action="append", default=[])
    args = ap.parse_args()

    source_plan = build_source_plan(args.vendor, args.name, args.classification or None, args.reference_url or None)
    interface_probe = run_interface_probe(args.vendor, args.name, args.classification or None) if args.with_interface_probe else None
    extracted_sources = []
    for seed_url in args.seed_url:
        try:
            extracted_sources.append(fetch_source(seed_url))
        except Exception as exc:
            extracted_sources.append({"url": seed_url, "ok": False, "error": str(exc)})

    response = {
        "request": {
            "vendor": args.vendor,
            "name": args.name,
            "classification": args.classification or None,
            "reference_url": args.reference_url or None,
        },
        "source_plan": source_plan,
        "stages": {
            "source_finder": {"ok": True},
            "page_extractor": {"ok": bool(extracted_sources), "status": "implemented" if extracted_sources else "not_implemented", "sources": extracted_sources},
            "normalizer": {"ok": bool(extracted_sources), "status": "implemented" if extracted_sources else "not_implemented", "result": normalize_extracted_sources(extracted_sources, args.name, args.vendor) if extracted_sources else None},
            "interface_probe": interface_probe,
        },
        "ready_for_apply": False,
        "notes": [
            "This is a v2 prototype scaffold.",
            "It is intentionally write-free and does not mutate product catalog rows.",
            "Search/fetch extraction is the next implementation step.",
        ],
    }
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
