"""Quick health check for all new API endpoints."""
import requests
import json

base = "http://localhost:5000"
results = {}

# Tier 1
r = requests.get(f"{base}/api/pricing/comparison")
results["T1 pricing_comparison"] = f"{r.status_code} - {len(r.json().get('per_vm',[]))} VMs" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/applications")
results["T1 applications"] = f"{r.status_code} - {r.json().get('application_count')} groups" if r.ok else f"{r.status_code} FAIL"

r = requests.post(f"{base}/api/waves/smart-plan", json={"wave_count": 4})
results["T1 smart_waves"] = f"{r.status_code} - {r.json().get('wave_count')} waves" if r.ok else f"{r.status_code} FAIL"

r = requests.post(f"{base}/api/export/terraform", json={"naming_prefix": "contoso"})
results["T1 terraform"] = f"{r.status_code} - {r.json().get('file_count')} files" if r.ok else f"{r.status_code} FAIL"

r = requests.post(f"{base}/api/export/bicep", json={"naming_prefix": "contoso"})
results["T1 bicep"] = f"{r.status_code} - {r.json().get('file_count')} files" if r.ok else f"{r.status_code} FAIL"

r = requests.post(f"{base}/api/runbooks/generate", json={})
d = r.json() if r.ok else {}
results["T1 runbooks"] = f"{r.status_code} - pre:{len(d.get('pre_migration',[]))} exec:{len(d.get('execution',[]))} post:{len(d.get('post_migration',[]))}" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/reports/executive")
results["T1 exec_report"] = f"{r.status_code} - {len(r.json().get('sections',{}))} sections" if r.ok else f"{r.status_code} FAIL"

# Tier 2
r = requests.get(f"{base}/api/migration/progress")
results["T2 migration_tracker"] = f"{r.status_code}" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/nsg-rules")
results["T2 nsg_rules"] = f"{r.status_code} - {r.json().get('total_rules')} rules" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/tags/strategy")
results["T2 tagging"] = f"{r.status_code} - {r.json().get('tag_key_count')} keys" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/projects")
results["T2 projects"] = f"{r.status_code} - {len(r.json().get('projects',[]))} projects" if r.ok else f"{r.status_code} FAIL"

# Tier 3
r = requests.post(f"{base}/api/compliance/assess", json={"frameworks": ["pci-dss", "gdpr"]})
results["T3 compliance"] = f"{r.status_code} - {r.json().get('overall_compliance_pct')}%" if r.ok else f"{r.status_code} FAIL"

r = requests.post(f"{base}/api/validation/post-migration", json={})
results["T3 post_migration"] = f"{r.status_code}" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/snapshots")
results["T3 snapshots"] = f"{r.status_code}" if r.ok else f"{r.status_code} FAIL"

r = requests.get(f"{base}/api/cost-optimization")
results["T3 cost_optimization"] = f"{r.status_code} - {r.json().get('pricing_savings_pct')}% savings" if r.ok else f"{r.status_code} FAIL"

print("=== API Endpoint Health Check ===")
for k, v in results.items():
    status = "PASS" if "200" in v else "FAIL"
    print(f"  [{status}] {k}: {v}")
passed = sum(1 for v in results.values() if "200" in v)
print(f"\nTotal: {passed}/{len(results)} endpoints passing")
