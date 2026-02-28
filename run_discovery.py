"""Stand-alone runner script to perform discovery, generate recs, and export report.

Set the following environment variables (or use a .env file):
  VCENTER_HOST, VCENTER_PORT, VCENTER_USER, VCENTER_PASSWORD, VCENTER_DISABLE_SSL
"""
import sys, json, time, dataclasses, logging, os

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from digital_twin_migrate.vcenter_discovery import discover_environment
from digital_twin_migrate.azure_mapping import generate_recommendations
from digital_twin_migrate.config import VCenterConfig, _load_dotenv

_load_dotenv()

cfg = VCenterConfig(
    host=os.getenv("VCENTER_HOST", ""),
    port=int(os.getenv("VCENTER_PORT", "443")),
    username=os.getenv("VCENTER_USER", ""),
    password=os.getenv("VCENTER_PASSWORD", ""),
    disable_ssl=os.getenv("VCENTER_DISABLE_SSL", "true").lower() == "true",
)

if not cfg.host or not cfg.username or not cfg.password:
    print("ERROR: Set VCENTER_HOST, VCENTER_USER, and VCENTER_PASSWORD environment variables (or .env file).")
    sys.exit(1)

print("Starting discovery...")
start = time.time()
env = discover_environment(cfg, collect_perf=False)
elapsed = time.time() - start
print(f"Discovery complete in {elapsed:.1f}s")
print(f"  Datacenters: {len(env.datacenters)}")
print(f"  Clusters: {len(env.clusters)}")
print(f"  Hosts: {len(env.hosts)}")
print(f"  VMs: {len(env.vms)}")
print(f"  Datastores: {len(env.datastores)}")
print(f"  Networks: {len(env.networks)}")

# Print some sample VMs
print("\nSample VMs discovered:")
for vm in env.vms[:20]:
    print(f"  {vm.name:40s}  {vm.power_state.value:12s}  {vm.num_cpus}vCPU  {vm.memory_mb // 1024}GB  {vm.total_disk_gb:.0f}GB  {vm.guest_os[:40]}")

print("\nGenerating Azure recommendations...")
recs = generate_recommendations(env)
total_cost = sum(r.estimated_monthly_cost_usd for r in recs)
print(f"Total estimated monthly Azure cost: ${total_cost:,.2f}")

# Print sample recommendations
print("\nSample recommendations:")
for r in recs[:20]:
    print(f"  {r.vm_name:40s}  -> {r.recommended_vm_sku:20s}  ${r.estimated_monthly_cost_usd:>8.2f}/mo  {r.migration_readiness}")

# Export full report
report = {
    "vcenter_host": env.vcenter_host,
    "summary": {
        "datacenters": len(env.datacenters),
        "clusters": len(env.clusters),
        "hosts": len(env.hosts),
        "vms": len(env.vms),
        "datastores": len(env.datastores),
        "networks": len(env.networks),
    },
    "vms": [dataclasses.asdict(vm) for vm in env.vms],
    "hosts": [dataclasses.asdict(h) for h in env.hosts],
    "clusters": [dataclasses.asdict(c) for c in env.clusters],
    "datastores": [dataclasses.asdict(ds) for ds in env.datastores],
    "networks": [dataclasses.asdict(n) for n in env.networks],
    "recommendations": [dataclasses.asdict(r) for r in recs],
    "total_monthly_cost_usd": round(total_cost, 2),
}
with open("discovery_report.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print("\nReport saved to discovery_report.json")
print("DONE")
