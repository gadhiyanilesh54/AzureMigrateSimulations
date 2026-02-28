"""Print a summary of the discovery report."""
import json
from collections import Counter

r = json.load(open("discovery_report.json"))
recs = r["recommendations"]
vms = r["vms"]

# Readiness breakdown
readiness = Counter(rec["migration_readiness"] for rec in recs)
print("=== Readiness Breakdown ===")
for k, v in readiness.most_common():
    print(f"  {k}: {v}")
print()

# Cost summary
total_cost = sum(rec["estimated_monthly_cost_usd"] for rec in recs)
print(f"Total estimated monthly Azure cost: ${total_cost:,.2f}")
print(f"Total estimated annual Azure cost:  ${total_cost * 12:,.2f}")
print()

# OS distribution
os_fam = Counter(vm.get("guest_os_family", "") for vm in vms)
print("=== OS Family Distribution ===")
for k, v in os_fam.most_common():
    print(f"  {k}: {v}")
print()

# Power state distribution
power = Counter(vm.get("power_state", "") for vm in vms)
print("=== Power State Distribution ===")
for k, v in power.most_common():
    print(f"  {k}: {v}")
print()

# Top 10 costliest VMs
print("=== Top 10 Costliest VMs ===")
top = sorted(recs, key=lambda x: x["estimated_monthly_cost_usd"], reverse=True)[:10]
for rec in top:
    name = rec["vm_name"]
    sku = rec["recommended_vm_sku"]
    cost = rec["estimated_monthly_cost_usd"]
    ready = rec["migration_readiness"]
    print(f"  {name:45s} {sku:20s} ${cost:>10.2f}/mo  {ready}")
print()

# SKU distribution
sku_dist = Counter(rec["recommended_vm_sku"] for rec in recs)
print("=== Recommended SKU Distribution ===")
for k, v in sku_dist.most_common():
    print(f"  {k}: {v}")
print()

# Hosts summary
hosts = r["hosts"]
print("=== ESXi Hosts ===")
for h in hosts:
    print(f"  {h['name']:30s}  {h['cpu_cores']} cores  {h['memory_mb'] // 1024}GB  {h['esxi_version']}")
print()

# Datastores summary
datastores = r["datastores"]
print("=== Datastores ===")
for ds in datastores:
    cap = ds["capacity_gb"]
    free = ds["free_space_gb"]
    used_pct = ((cap - free) / cap * 100) if cap > 0 else 0
    print(f"  {ds['name']:30s}  {cap:>10.1f} GB  {used_pct:>5.1f}% used  {ds['type']}")
