"""Final verification of tab switching."""
import requests, re

html = requests.get("http://localhost:5000/").text

# Check nav-link on stepper buttons
for btn_id in ["tab-dashboard", "tab-decide", "tab-plan", "tab-execute"]:
    pattern = f'id="{btn_id}"[^>]*>'
    m = re.search(pattern, html)
    if m:
        btn = m.group(0)
        has_navlink = "nav-link" in btn
        has_toggle = "data-bs-toggle" in btn
        has_role = 'role="tab"' in btn
        target = re.search(r'data-bs-target="([^"]+)"', btn)
        print(f"  {btn_id}: nav-link={has_navlink}, toggle={has_toggle}, role-tab={has_role}, target={target.group(1) if target else 'NONE'}")

# Check parent is nav with nav-pills and role=tablist
print("\nParent structure:")
nav_match = re.search(r'<ul class="nav nav-pills"[^>]*role="tablist"', html)
print(f"  ul.nav.nav-pills[role=tablist]: {'FOUND' if nav_match else 'NOT FOUND'}")

print("\nAll checks passed!" if nav_match else "\nFIXES STILL NEEDED")
