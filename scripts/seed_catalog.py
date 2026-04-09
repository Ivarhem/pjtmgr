"""Seed product catalog from spec.xlsx data."""
import urllib.request
import json
import http.cookiejar

BASE = "http://localhost:9000"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
data = json.dumps({"login_id": "admin", "password": "admin1234"}).encode()
req = urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/json"},
)
opener.open(req)

# Existing products
resp = opener.open(f"{BASE}/api/v1/product-catalog")
existing = {(p["vendor"], p["name"]): p["id"] for p in json.loads(resp.read())}
print(f"Existing: {list(existing.keys())}")


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    return json.loads(opener.open(req).read())


products = [
    {
        "product": {
            "vendor": "Fortinet",
            "name": "FortiGate 100F",
            "product_type": "hardware",
            "category": "\uBCF4\uC548",
            "reference_url": "https://www.fortinet.com/products/next-generation-firewall",
        },
        "spec": {
            "size_unit": 1,
            "width_mm": 420,
            "height_mm": 44,
            "depth_mm": 160,
            "weight_kg": 3.2,
            "power_count": 1,
            "power_type": "AC",
            "power_watt": 38,
            "cpu_summary": "Fortinet SoC4 (NP6XLite + CP9)",
            "memory_summary": "4 GB DDR4 / 128 GB SSD",
            "throughput_summary": "FW 20Gbps / IPS 2.6Gbps / NGFW 1.0Gbps",
            "os_firmware": "FortiOS 7.x",
        },
        "interfaces": [
            {
                "interface_type": "GE RJ45",
                "speed": "1G",
                "count": 22,
                "connector_type": "RJ-45",
                "note": "2x WAN, 1x DMZ, 1x Mgmt \uD3EC\uD568",
            },
            {"interface_type": "GE SFP", "speed": "1G", "count": 2, "connector_type": "SFP"},
            {"interface_type": "10GE SFP+", "speed": "10G", "count": 2, "connector_type": "SFP+"},
        ],
        "eosl": {},
    },
    {
        "product": {
            "vendor": "Dell",
            "name": "PowerEdge R750",
            "product_type": "hardware",
            "category": "\uC11C\uBC84",
            "reference_url": "https://www.dell.com/en-us/shop/dell-poweredge-servers/poweredge-r750",
        },
        "spec": {
            "size_unit": 2,
            "width_mm": 482,
            "height_mm": 87,
            "depth_mm": 794,
            "power_count": 2,
            "power_type": "AC",
            "power_watt": 1400,
            "cpu_summary": "Intel Xeon 3rd Gen Scalable (Ice Lake), \uCD5C\uB300 2\uC18C\uCF13 80\uCF54\uC5B4",
            "memory_summary": "\uCD5C\uB300 16 DIMM, DDR4-3200, \uCD5C\uB300 1TB",
            "os_firmware": "Windows Server 2019/2022, RHEL, Ubuntu, VMware ESXi",
        },
        "interfaces": [
            {"interface_type": "OCP 3.0", "speed": "10G/25G", "count": 1, "connector_type": "OCP"},
            {
                "interface_type": "PCIe Gen4",
                "count": 8,
                "connector_type": "PCIe",
                "note": "\uAD6C\uC131\uC5D0 \uB530\uB77C \uC0C1\uC774",
            },
            {
                "interface_type": "iDRAC9",
                "speed": "1G",
                "count": 1,
                "connector_type": "RJ-45",
                "note": "\uAD00\uB9AC \uD3EC\uD2B8",
            },
        ],
        "eosl": {},
    },
    {
        "product": {
            "vendor": "HPE",
            "name": "ProLiant DL380 Gen10 Plus",
            "product_type": "hardware",
            "category": "\uC11C\uBC84",
            "reference_url": "https://www.hpe.com/ProLiantDL380Gen10Plus",
        },
        "spec": {
            "size_unit": 2,
            "width_mm": 447,
            "height_mm": 87,
            "depth_mm": 800,
            "power_count": 2,
            "power_type": "AC",
            "power_watt": 1600,
            "cpu_summary": "Intel Xeon 3rd Gen Scalable (Ice Lake), \uCD5C\uB300 2\uC18C\uCF13, TDP 270W",
            "memory_summary": "\uCD5C\uB300 32 DIMM, DDR4-3200, RDIMM/LRDIMM",
            "throughput_summary": "\uBA54\uBAA8\uB9AC \uB300\uC5ED\uD3ED \uCD5C\uB300 204.8 GB/s per CPU",
            "os_firmware": "Windows Server 2019/2022, RHEL, SLES, VMware ESXi",
        },
        "interfaces": [
            {
                "interface_type": "SFF SAS/SATA/NVMe",
                "count": 24,
                "connector_type": "SFF 2.5\"",
                "note": "\uCD5C\uB300 \uAD6C\uC131",
            },
            {"interface_type": "PCIe Gen4", "count": 10, "connector_type": "PCIe"},
        ],
        "eosl": {},
    },
    {
        "product": {
            "vendor": "Palo Alto",
            "name": "PA-820",
            "product_type": "hardware",
            "category": "\uBCF4\uC548",
            "reference_url": "https://www.paloaltonetworks.com/network-security/next-generation-firewall/pa-800-series",
        },
        "spec": {
            "size_unit": 1,
            "width_mm": 432,
            "height_mm": 44,
            "depth_mm": 279,
            "weight_kg": 4.5,
            "power_count": 1,
            "power_type": "AC",
            "power_watt": 40,
            "cpu_summary": "\uC804\uC6A9 \uBCF4\uC548/\uB124\uD2B8\uC6CC\uD06C \uD504\uB85C\uC138\uC11C (\uBE44\uACF5\uAC1C)",
            "memory_summary": "4 GB RAM / 32 GB SSD",
            "throughput_summary": "App-ID 940Mbps / Threat 610Mbps / IPSec VPN 400Mbps",
            "os_firmware": "PAN-OS 10.x/11.x",
        },
        "interfaces": [
            {"interface_type": "GE copper", "speed": "1G", "count": 8, "connector_type": "RJ-45"},
            {"interface_type": "GE SFP", "speed": "1G", "count": 4, "connector_type": "SFP"},
        ],
        "eosl": {
            "eos_date": "2024-06-30",
            "eosl_date": "2029-06-30",
            "eosl_note": "EOS 2024-06-30, EOSL 2029-06-30",
        },
    },
    {
        "product": {
            "vendor": "SECUI",
            "name": "NGF 2100",
            "product_type": "hardware",
            "category": "\uBCF4\uC548",
            "reference_url": "https://www.secui.com",
        },
        "spec": None,
        "interfaces": [],
        "eosl": {},
    },
    {
        "product": {
            "vendor": "AXGATE",
            "name": "NF 4000",
            "product_type": "hardware",
            "category": "\uBCF4\uC548",
            "reference_url": "https://www.axgate.com",
        },
        "spec": None,
        "interfaces": [],
        "eosl": {},
    },
]

for item in products:
    p = item["product"]
    key = (p["vendor"], p["name"])

    if key in existing:
        pid = existing[key]
        print(f"Skip (exists): {p['vendor']} {p['name']}")
    else:
        created = api("POST", "/api/v1/product-catalog", p)
        pid = created["id"]
        print(f"Created: {p['vendor']} {p['name']} (id={pid})")

    if item.get("spec"):
        api("PUT", f"/api/v1/product-catalog/{pid}/spec", item["spec"])
        print("  Spec saved")

    for iface in item.get("interfaces", []):
        try:
            api("POST", f"/api/v1/product-catalog/{pid}/interfaces", iface)
            print(f"  Interface: {iface['interface_type']} x{iface['count']}")
        except Exception as e:
            print(f"  Interface skip: {e}")

    if item.get("eosl"):
        api("PATCH", f"/api/v1/product-catalog/{pid}", item["eosl"])
        print("  EOSL saved")

# Update existing Cisco spec
cisco_id = existing.get(("Cisco", "Catalyst 9200L-24T-4G"))
if cisco_id:
    api(
        "PUT",
        f"/api/v1/product-catalog/{cisco_id}/spec",
        {
            "size_unit": 1,
            "width_mm": 445,
            "height_mm": 44,
            "depth_mm": 286,
            "power_count": 1,
            "power_type": "AC",
            "power_watt": 40,
            "cpu_summary": "Cisco ASIC",
            "memory_summary": "DRAM 1GB, Flash 2GB",
            "throughput_summary": "\uC2A4\uC704\uCE6D 56Gbps / \uD3EC\uC6CC\uB529 41.67Mpps",
            "os_firmware": "Cisco IOS XE 17.x",
        },
    )
    print("Updated Cisco spec")

print("=== DONE ===")
