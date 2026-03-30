"""Diagnose tab navigation issue."""
import requests, re

html = requests.get("http://localhost:5000/").text

# 1. Check stepper structure
stepper_match = re.search(r'id="journeyStepper"[^>]*>(.*?)</div>', html, re.DOTALL)
if stepper_match:
    # Count buttons in stepper
    buttons = re.findall(r'<button[^>]*id="(tab-[^"]+)"[^>]*>', stepper_match.group(0))
    print("Stepper buttons:", buttons)
else:
    print("ERROR: Stepper not found")

# 2. Check if stepper buttons have correct data-bs attributes
for btn_id in ["tab-dashboard", "tab-decide", "tab-plan", "tab-execute"]:
    pattern = f'id="{btn_id}"[^>]*'
    m = re.search(pattern, html)
    if m:
        btn_html = m.group(0)
        has_toggle = "data-bs-toggle" in btn_html
        target = re.search(r'data-bs-target="([^"]+)"', btn_html)
        print(f"  {btn_id}: toggle={has_toggle}, target={target.group(1) if target else 'NONE'}")
    else:
        print(f"  {btn_id}: NOT FOUND")

# 3. Check if target panes exist and have correct classes
for pane_id in ["pane-dashboard", "pane-decide", "pane-plan", "pane-execute"]:
    pattern = f'id="{pane_id}"[^>]*'
    m = re.search(pattern, html)
    if m:
        pane_html = m.group(0)
        has_tabpane = "tab-pane" in pane_html
        has_fade = "fade" in pane_html
        print(f"  {pane_id}: class has tab-pane={has_tabpane}, fade={has_fade}")
    else:
        print(f"  {pane_id}: NOT FOUND IN HTML")

# 4. Check if stepper is inside a nav/tablist container or just a div
stepper_context = re.search(r'(.{200})id="journeyStepper"', html, re.DOTALL)
if stepper_context:
    ctx = stepper_context.group(1)[-100:]
    print("\nStepper parent context:", ctx.strip())

# 5. Check if both old and new panes are siblings under mainTabContent
tab_content_match = re.search(r'id="mainTabContent"(.*?)$', html, re.DOTALL)
if tab_content_match:
    tc = tab_content_match.group(1)[:5000]
    panes_in_tc = re.findall(r'class="tab-pane[^"]*"\s+id="([^"]+)"', tc)
    print("\nPanes inside mainTabContent:", panes_in_tc)

# 6. Check Bootstrap JS is loaded
print("\nBootstrap JS loaded:", "bootstrap" in html.lower() and "bundle" in html.lower() or "bootstrap.min.js" in html)
bs_script = re.search(r'<script[^>]*bootstrap[^>]*>', html)
print("Bootstrap script tag:", bs_script.group(0) if bs_script else "NOT FOUND")
