"""Verify DOM structure: all sub-tabs are INSIDE their parent phase pane."""
import requests, re

html = requests.get("http://localhost:5000/").text

def find_pos(text, pattern):
    idx = text.find(pattern)
    return idx if idx >= 0 else None

print("=== DOM HIERARCHY CHECK ===\n")

# pane-decide must contain decide-discovery, decide-businesscase, decide-enrichment
decide_open = find_pos(html, 'id="pane-decide"')
decide_close = find_pos(html, '/pane-decide')
print(f"pane-decide: {decide_open} to {decide_close}")
for sid in ['decide-discovery', 'decide-businesscase', 'decide-enrichment', 'decide-pricing', 'decide-compliance', 'decide-report']:
    pos = find_pos(html, f'id="{sid}"')
    inside = decide_open < pos < decide_close if (decide_open and decide_close and pos) else False
    print(f"  {sid}: pos={pos}, inside pane-decide={inside}")

# pane-plan must contain plan-ctd, plan-apps, etc.
plan_open = find_pos(html, 'id="pane-plan"')
plan_close = find_pos(html, '/pane-plan')
print(f"\npane-plan: {plan_open} to {plan_close}")
for sid in ['plan-ctd', 'plan-apps', 'plan-costopt', 'plan-iac', 'plan-runbooks']:
    pos = find_pos(html, f'id="{sid}"')
    inside = plan_open < pos < plan_close if (plan_open and plan_close and pos) else False
    print(f"  {sid}: pos={pos}, inside pane-plan={inside}")

# pane-execute
exec_open = find_pos(html, 'id="pane-execute"')
exec_close = find_pos(html, '/pane-execute')
print(f"\npane-execute: {exec_open} to {exec_close}")
for sid in ['exec-tracker', 'exec-nsg', 'exec-postval', 'exec-snapshots']:
    pos = find_pos(html, f'id="{sid}"')
    inside = exec_open < pos < exec_close if (exec_open and exec_close and pos) else False
    print(f"  {sid}: pos={pos}, inside pane-execute={inside}")

# Sub-tabs inside decide-discovery
disc_open = find_pos(html, 'id="decide-discovery"')
disc_close_candidates = [m.start() for m in re.finditer(r'decide-discovery', html)]
print(f"\ndecide-discovery starts at: {disc_open}")
for sid in ['subtab-inventory', 'subtab-topology', 'subtab-assessment', 'subtab-simulation', 'subtab-vulnsla']:
    pos = find_pos(html, f'id="{sid}"')
    in_disc = disc_open < pos if (disc_open and pos) else False
    print(f"  {sid}: pos={pos}, after decide-discovery={in_disc}")

# No _embedOldPane in features.js
js = requests.get("http://localhost:5000/static/features.js").text
print(f"\nfeatures.js has _embedOldPane: {'_embedOldPane' in js}")
print(f"features.js size: {len(js)} bytes")

# Final API check
r = requests.get("http://localhost:5000/api/status")
print(f"\nAPI status: {r.status_code}, data_loaded: {r.json().get('data_loaded')}")
