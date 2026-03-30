"""Diagnose tab issue - v2."""
import requests, re

html = requests.get("http://localhost:5000/").text

# Find all tab-pane divs
panes = re.findall(r'class="tab-pane[^"]*"\s*id="([^"]+)"', html)
print("All tab-pane elements:", panes)

# Check stepper area
idx = html.find('journeyStepper')
chunk = html[idx:idx+600]
print("\nStepper has role=tablist:", 'role="tablist"' in chunk)
print("Stepper tag:", chunk[:100])

# Check if pane-decide is INSIDE mainTabContent
mtc_start = html.find('id="mainTabContent"')
mtc_chunk = html[mtc_start:mtc_start+200]
print("\nmainTabContent context:", mtc_chunk[:150])

# Find positions
print("\nmainTabContent position:", mtc_start)
print("pane-dashboard position:", html.find('id="pane-dashboard"'))
print("pane-decide position:", html.find('id="pane-decide"'))
print("pane-plan position:", html.find('id="pane-plan"'))
print("pane-execute position:", html.find('id="pane-execute"'))

# Check closing of mainTabContent (the </div><!-- /tab-content --> comment)
tc_close = html.find("<!-- /tab-content -->")
print("tab-content close position:", tc_close)
print("pane-decide INSIDE tab-content:", mtc_start < html.find('id="pane-decide"') < tc_close if tc_close > 0 else "N/A")
print("pane-plan INSIDE tab-content:", mtc_start < html.find('id="pane-plan"') < tc_close if tc_close > 0 else "N/A")
print("pane-execute INSIDE tab-content:", mtc_start < html.find('id="pane-execute"') < tc_close if tc_close > 0 else "N/A")
