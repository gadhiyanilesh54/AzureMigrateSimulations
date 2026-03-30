"""
Test the actual browser behavior by simulating what happens:
1. Load the page HTML
2. Check if the sub-tab targets exist inside pane-workloads
3. Verify that after DOM move, the tab targets would still be findable
"""
import requests
import re

html = requests.get("http://localhost:5000/").text

# The core issue: pane-workloads contains discoverySubTabs with pill buttons
# pointing to pane-inventory, pane-topology, etc.
# When we move pane-workloads children into decide-discovery,
# Bootstrap's data-bs-toggle="pill" needs to find the target panes.

# Check: Are the pane-inventory etc. INSIDE pane-workloads' tab-content?
wl_start = html.find('id="pane-workloads"')
wl_end = html.find('</div><!-- /pane-workloads -->')

if wl_end < 0:
    # The closing comment may have been removed
    # Find the next top-level tab-pane after pane-workloads
    panes_after = list(re.finditer(r'<div class="tab-pane fade"', html[wl_start+100:]))
    if panes_after:
        wl_end = wl_start + 100 + panes_after[0].start()
    else:
        wl_end = len(html)

print(f"pane-workloads: chars {wl_start} to {wl_end}")

wl_content = html[wl_start:wl_end]

# Check if inner tab-content with sub-panes is inside pane-workloads
inner_tab_content = '<div class="tab-content">' in wl_content
print(f"Has inner tab-content: {inner_tab_content}")

for pid in ['pane-inventory', 'pane-topology', 'pane-assessment', 'pane-simulation', 'pane-vulnsla']:
    inside = f'id="{pid}"' in wl_content
    print(f"  {pid} inside pane-workloads: {inside}")

# The PROBLEM: Bootstrap's pill plugin requires:
# 1. The trigger button to have class="nav-link" and data-bs-toggle="pill"
# 2. The target pane to have class="tab-pane"
# 3. BOTH to be in the same document (they are after move)
# 4. The target to be findable by document.querySelector(data-bs-target)
#    This SHOULD work after DOM move since querySelector searches globally.

# So the problem might NOT be the Tab plugin but something else.
# Let me check if there's a NESTED tab-content issue.

# If pane-workloads is a tab-pane inside mainTabContent,
# and it has its OWN nested tab-content with pane-inventory etc.,
# then when we move pane-workloads' children into decide-discovery,
# the nested tab-content is inside decide-discovery (not a tab-pane anymore).
# The inner panes (pane-inventory etc.) are class="tab-pane fade"
# but "show active" is only on pane-inventory.
# When user clicks subtab-topology, Bootstrap should add "show active" to pane-topology.

# BUT: decide-discovery is NOT a tab-pane! It's a plain <div>.
# After content move, the structure is:
#   decide-discovery (div, not tab-pane)
#     └── discoverySubTabs (ul.nav.nav-pills)
#     └── tab-content (div)
#           └── pane-inventory (tab-pane fade show active)
#           └── pane-topology (tab-pane fade)
#           └── ...

# This should work because Bootstrap Tab plugin does:
#   document.querySelector(selector) to find the target
# And the target IS in the document.

# Let me check if maybe the issue is that the OUTER pane-workloads
# was class="tab-pane fade" but NOT "show active", so its children
# are invisible (display:none from Bootstrap CSS).

# When we move children OUT of pane-workloads into decide-discovery,
# they should become visible since decide-discovery is display:''
# BUT the inner tab-content's panes still need "show active" class.

# Check: Does pane-inventory have "show active"?
inv_match = re.search(r'id="pane-inventory"[^>]*class="([^"]*)"', html)
if not inv_match:
    inv_match = re.search(r'class="([^"]*)"[^>]*id="pane-inventory"', html)
if inv_match:
    print(f"\npane-inventory classes: {inv_match.group(1)}")
else:
    print("\npane-inventory: class not found in expected pattern")
    # Try reverse
    idx = html.find('id="pane-inventory"')
    if idx > 0:
        chunk = html[idx-200:idx+50]
        print(f"  Context: ...{chunk[-100:]}...")

# REAL TEST: fetch the JS and see if the _embedOldPane reinit is correct
js = requests.get("http://localhost:5000/static/features.js").text
idx = js.find('_embedOldPane')
if idx > 0:
    print(f"\n_embedOldPane implementation:")
    func_end = js.find('\n}', idx)
    print(js[idx:func_end+2])

print("\n=== DIAGNOSIS ===")
print("The content-move approach should work in theory.")
print("If sub-tabs still don't switch, the issue is likely:")
print("1. Browser cache serving old features.js (hard refresh with Ctrl+Shift+R)")
print("2. The inner tab-content div is not visible because Bootstrap hides unfocused tab-panes")
print("3. A JS error in the console preventing Bootstrap from initializing")
