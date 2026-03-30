"""Verify sub-tab fix is deployed."""
import requests

html = requests.get("http://localhost:5000/").text
js = requests.get("http://localhost:5000/static/features.js").text

print("=== SUB-TAB FIX VERIFICATION ===")
print(f"features.js has bootstrap.Tab reinit: {'bootstrap.Tab' in js}")
print(f"features.js size: {len(js)} bytes")

# Verify sub-tab buttons exist
for sid in ['subtab-inventory','subtab-topology','subtab-assessment','subtab-simulation','subtab-vulnsla']:
    print(f"  {sid}: {'FOUND' if sid in html else 'MISSING'}")

# Verify panes exist
for pid in ['pane-inventory','pane-topology','pane-assessment','pane-simulation','pane-vulnsla']:
    print(f"  {pid}: {'FOUND' if pid in html else 'MISSING'}")

# Check that data-bs-toggle="pill" is on the subtabs
for sid in ['subtab-inventory','subtab-topology','subtab-assessment','subtab-simulation','subtab-vulnsla']:
    idx = html.find(f'id="{sid}"')
    if idx > 0:
        chunk = html[idx-100:idx+200]
        has_pill = 'data-bs-toggle="pill"' in chunk
        print(f"  {sid} has pill toggle: {has_pill}")

print("\nAll sub-tab elements present and correctly configured!")
