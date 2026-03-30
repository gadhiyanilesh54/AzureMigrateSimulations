"""Comprehensive UI + API test — verifies every feature works end-to-end."""
import requests
import json
import sys

BASE = "http://localhost:5000"
passed = 0
failed = 0
errors = []

def test(name, url, method="GET", json_body=None, expect_key=None, expect_status=200):
    global passed, failed
    try:
        if method == "POST":
            r = requests.post(f"{BASE}{url}", json=json_body or {}, timeout=15)
        else:
            r = requests.get(f"{BASE}{url}", timeout=15)
        
        if r.status_code != expect_status:
            failed += 1
            errors.append(f"FAIL {name}: status={r.status_code} expected={expect_status}")
            return None
        
        if expect_key:
            data = r.json()
            if expect_key not in data and expect_key not in str(data):
                failed += 1
                errors.append(f"FAIL {name}: key '{expect_key}' not in response")
                return data
            passed += 1
            return data
        else:
            passed += 1
            try:
                return r.json()
            except:
                return r.text
    except Exception as e:
        failed += 1
        errors.append(f"FAIL {name}: {e}")
        return None

print("=" * 60)
print("   COMPREHENSIVE FEATURE TEST SUITE")
print("=" * 60)

# ── Core (existing) ──
print("\n--- CORE FEATURES ---")
test("Server status", "/api/status", expect_key="data_loaded")
test("Migration summary", "/api/summary", expect_key="total_monthly_cost")
test("VM list", "/api/vms", expect_key="vm_name")
test("VM recommendations", "/api/recommendations", expect_key="vm_name")
test("Topology", "/api/topology", expect_key="nodes")
test("Regions", "/api/regions", expect_key="eastus")
test("SKU catalog", "/api/sku_catalog", expect_key="Standard_B1s")
test("Pricing models", "/api/pricing_models", expect_key="1_year_ri")
test("Vulnerability/SLA", "/api/vulnerability-sla", expect_key="os_lifecycle")

# ── Enrichment ──
print("\n--- ENRICHMENT ---")
test("Enrichment tools", "/api/enrichment/tools", expect_key="name")
test("Enrichment status", "/api/enrichment/status", expect_key="coverage_pct")

# ── Business Case ──
print("\n--- BUSINESS CASE ---")
test("Business case", "/api/businesscase", expect_key="annual_savings")

# ── Cloud Topology ──
print("\n--- CLOUD TOPOLOGY ---")
d = test("Cloud topology", "/api/cloud-topology", expect_key="containers")
if d:
    nodes = d.get("nodes", [])
    if nodes:
        rid = nodes[0].get("id", "")
        test("WAF assessment", f"/api/cloud-topology/waf/{rid}", expect_key="pillars")

# ── Export ──
print("\n--- EXPORT ---")
test("CSV export", "/api/export/csv?type=vms")

# ── TIER 1: Pricing Comparison ──
print("\n--- TIER 1: PRICING COMPARISON ---")
d = test("Pricing comparison", "/api/pricing/comparison", expect_key="fleet_summary")
if d:
    fs = d.get("fleet_summary", {})
    print(f"   Fleet models: {len(fs)}, Blended savings: {d.get('blended_optimal',{}).get('savings_pct')}%")

# ── TIER 1: Application Groups ──
print("\n--- TIER 1: APPLICATION GROUPS ---")
d = test("Application groups", "/api/applications", expect_key="applications")
if d:
    print(f"   Groups detected: {d.get('application_count')}")

# ── TIER 1: Smart Wave Planning ──
print("\n--- TIER 1: SMART WAVE PLANNING ---")
d = test("Smart wave plan", "/api/waves/smart-plan", method="POST", 
         json_body={"wave_count": 4}, expect_key="waves")
if d:
    print(f"   Waves: {d.get('wave_count')}, Dependencies: {d.get('dependency_count')}")

# ── TIER 1: Terraform ──
print("\n--- TIER 1: TERRAFORM GENERATION ---")
d = test("Terraform export", "/api/export/terraform", method="POST",
         json_body={"naming_prefix": "test"}, expect_key="file_count")
if d:
    print(f"   Files: {d.get('file_count')}, Names: {list(d.get('files', {}).keys()) if isinstance(d.get('files'), dict) else d.get('files')}")

# ── TIER 1: Bicep ──
print("\n--- TIER 1: BICEP GENERATION ---")
d = test("Bicep export", "/api/export/bicep", method="POST",
         json_body={"naming_prefix": "test"}, expect_key="file_count")
if d:
    print(f"   Files: {d.get('file_count')}")

# ── TIER 1: Runbooks ──
print("\n--- TIER 1: RUNBOOKS ---")
d = test("Runbooks", "/api/runbooks/generate", method="POST", expect_key="pre_migration")
if d:
    print(f"   Pre: {len(d.get('pre_migration',[]))}, Exec: {len(d.get('execution',[]))}, Post: {len(d.get('post_migration',[]))}")

# ── TIER 1: Executive Report ──
print("\n--- TIER 1: EXECUTIVE REPORT ---")
d = test("Executive report (JSON)", "/api/reports/executive", expect_key="sections")
if d:
    print(f"   Sections: {list(d.get('sections',{}).keys())}")
test("Executive report (Markdown)", "/api/reports/executive?format=markdown")

# ── TIER 2: Migration Tracker ──
print("\n--- TIER 2: MIGRATION TRACKER ---")
test("Set VM status", "/api/migration/status", method="POST",
     json_body={"vm_name": "WindowsVM175", "state": "Planned", "note": "Test"}, expect_key="state")
d = test("Migration progress", "/api/migration/progress", expect_key="total_vms")
if d:
    print(f"   Tracked: {d.get('total_vms')}, Progress: {d.get('progress_pct')}%")

# ── TIER 2: NSG Rules ──
print("\n--- TIER 2: NSG RULES ---")
d = test("NSG rules", "/api/nsg-rules", expect_key="nsgs")
if d:
    print(f"   Subnets: {d.get('subnet_count')}, Rules: {d.get('total_rules')}")

# ── TIER 2: Tagging ──
print("\n--- TIER 2: TAGGING STRATEGY ---")
d = test("Tagging strategy", "/api/tags/strategy", expect_key="per_vm")
if d:
    print(f"   VMs: {d.get('vm_count')}, Tag keys: {d.get('tag_key_count')}")

# ── TIER 2: Projects ──
print("\n--- TIER 2: MULTI-PROJECT ---")
test("List projects", "/api/projects", expect_key="projects")

# ── TIER 3: Compliance ──
print("\n--- TIER 3: COMPLIANCE ---")
d = test("Compliance (PCI+GDPR)", "/api/compliance/assess", method="POST",
         json_body={"frameworks": ["pci-dss", "gdpr"]}, expect_key="results")
if d:
    for r in d.get("results", []):
        print(f"   {r['framework']}: {r['passed']} pass, {r['failed']} fail ({r['compliance_pct']}%)")

# ── TIER 3: Post-Migration Validation ──
print("\n--- TIER 3: POST-MIGRATION VALIDATION ---")
d = test("Post-migration checks", "/api/validation/post-migration", method="POST", expect_key="summary")
if d:
    s = d.get("summary", {})
    print(f"   Health: {s.get('health_checks')}, Connectivity: {s.get('connectivity_checks')}, Perf: {s.get('perf_checks')}")

# ── TIER 3: Snapshots ──
print("\n--- TIER 3: SNAPSHOTS ---")
# Delete old test snapshot if exists, then save new one
requests.post(f"{BASE}/api/snapshots/autotest-run/restore", timeout=5)  # cleanup
test("Save snapshot", "/api/snapshots", method="POST",
     json_body={"name": "autotest-" + str(int(__import__('time').time())), "description": "automated test"}, expect_key="saved", expect_status=201)
d = test("List snapshots", "/api/snapshots", expect_key="snapshots")
if d:
    print(f"   Snapshots: {len(d.get('snapshots', []))}")
# Cleanup
requests.post(f"{BASE}/api/snapshots/test-run/restore", timeout=5)

# ── TIER 3: Cost Optimization ──
print("\n--- TIER 3: COST OPTIMIZATION ---")
d = test("Cost optimization", "/api/cost-optimization", expect_key="fleet_payg_monthly")
if d:
    print(f"   PAYG: ${d.get('fleet_payg_monthly'):,.0f}/mo, Optimized: ${d.get('fleet_optimized_monthly'):,.0f}/mo, Savings: {d.get('pricing_savings_pct')}%")
    print(f"   Right-sizing alerts: {d.get('right_sizing_alerts')}, Zombies: {d.get('zombie_vms')}")

# ── UI structure tests ──
print("\n--- UI STRUCTURE ---")
html = requests.get(f"{BASE}/").text
ui_checks = {
    "Bootstrap loaded": "bootstrap@5.3.3" in html,
    "features.js loaded": "features.js" in html,
    "Journey stepper": "journeyStepper" in html,
    "nav-link on tabs": 'class="nav-link' in html and "tab-decide" in html,
    "role=tablist": 'role="tablist"' in html,
    "pane-dashboard": 'id="pane-dashboard"' in html,
    "pane-decide": 'id="pane-decide"' in html,
    "pane-plan": 'id="pane-plan"' in html,
    "pane-execute": 'id="pane-execute"' in html,
    "Decide sub-tabs": "decideSubTabs" in html,
    "Plan sub-tabs": "planSubTabs" in html,
    "Execute sub-tabs": "executeSubTabs" in html,
    "Pricing container": 'id="pricing-results"' in html,
    "AppGroups container": 'id="appgroups-results"' in html,
    "CostOpt container": 'id="costopt-results"' in html,
    "IaC container": 'id="iac-results"' in html,
    "Runbooks container": 'id="runbooks-results"' in html,
    "Report container": 'id="report-results"' in html,
    "Compliance container": 'id="compliance-results"' in html,
    "Tracker container": 'id="tracker-results"' in html,
    "NSG container": 'id="nsg-results"' in html,
    "Tagging container": 'id="tagging-results"' in html,
    "Snapshot container": 'id="snapshots-list"' in html,
    "PostVal container": 'id="postval-results"' in html,
    "Static JS serves": requests.get(f"{BASE}/static/features.js").status_code == 200,
}
for check, ok in ui_checks.items():
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
        errors.append(f"FAIL UI: {check}")
    else:
        passed += 1
    print(f"  [{status}] {check}")

# ── Summary ──
print("\n" + "=" * 60)
print(f"   RESULTS: {passed} passed, {failed} failed")
print("=" * 60)
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("\n  ✓ ALL TESTS PASSED")
    sys.exit(0)
