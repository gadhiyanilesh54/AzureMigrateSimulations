"""Test visualization using existing discovery_report.json data."""
import json
import sys
sys.path.insert(0, "src")

from digital_twin_migrate.models import (
    DiscoveredEnvironment, DiscoveredVM, DiscoveredHost, DiscoveredCluster,
    DiscoveredDatacenter, DiscoveredDatastore, DiscoveredNetwork,
    DiskInfo, NetworkInfo, PerformanceMetrics, PowerState, GuestOSFamily,
)
from digital_twin_migrate.azure_mapping import generate_recommendations
from digital_twin_migrate.visualization import (
    console, print_discovery_summary, print_topology_tree,
    print_vm_table, print_recommendations_table, print_issues_report,
)

# Load report
r = json.load(open("discovery_report.json"))

# Reconstruct data models from JSON
def _disk(d):
    return DiskInfo(**d)

def _nic(n):
    return NetworkInfo(**n)

def _perf(p):
    return PerformanceMetrics(**p)

def _vm(v):
    v2 = dict(v)
    v2["power_state"] = PowerState(v2["power_state"])
    v2["guest_os_family"] = GuestOSFamily(v2["guest_os_family"])
    v2["disks"] = [_disk(d) for d in v2["disks"]]
    v2["nics"] = [_nic(n) for n in v2["nics"]]
    v2["perf"] = _perf(v2["perf"])
    return DiscoveredVM(**v2)

env = DiscoveredEnvironment(
    vcenter_host=r["vcenter_host"],
    datacenters=[DiscoveredDatacenter(**d) for d in r.get("datacenters", [{"name": "INTSILAB", "vcenter_id": "datacenter-2"}])],
    clusters=[DiscoveredCluster(**c) for c in r.get("clusters", [])],
    hosts=[DiscoveredHost(**h) for h in r["hosts"]],
    datastores=[DiscoveredDatastore(**d) for d in r["datastores"]],
    networks=[DiscoveredNetwork(**n) for n in r["networks"]],
    vms=[_vm(v) for v in r["vms"]],
)

console.print()
print_discovery_summary(env)
console.print()
print_topology_tree(env)
console.print()

# Full VM table
print_vm_table(env)
console.print()

# Full Recommendations
recs = generate_recommendations(env)
print_recommendations_table(recs)
console.print()
print_issues_report(recs)
