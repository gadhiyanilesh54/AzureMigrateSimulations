"""Capture screenshots of every major dashboard tab using Playwright."""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000"
OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

WAIT = 3000  # ms to wait after each navigation / click for rendering


def shot(page, name, *, full_page=True):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    size_kb = path.stat().st_size // 1024
    print(f"  ✓ {path.name} ({size_kb} KB)")


def upload_discovery_file(page):
    """Upload vcenter_discovery.json via multipart file upload."""
    vc_file = DATA_DIR / "vcenter_discovery.json"
    if not vc_file.exists():
        print("  ⚠ No vcenter_discovery.json — skipping upload")
        return False

    data = vc_file.read_text(encoding="utf-8")
    # Use JS to create a File and upload via fetch
    result = page.evaluate("""async (jsonData) => {
        const blob = new Blob([jsonData], {type: 'application/json'});
        const file = new File([blob], 'vcenter_discovery.json', {type: 'application/json'});
        const form = new FormData();
        form.append('file', file);
        const resp = await fetch('/api/upload', {method: 'POST', body: form});
        return await resp.json();
    }""", data)
    print(f"  Upload result: {result}")
    return result.get("status") == "loaded"


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            color_scheme="dark",
        )
        page = ctx.new_page()

        # ── 0. Load the page and check if data is already loaded ──
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(2000)

        status = page.evaluate("async () => { const r = await fetch('/api/status'); return r.json(); }")
        print(f"App status: data_loaded={status.get('data_loaded')}, vms={status.get('vm_count')}")

        if not status.get("data_loaded"):
            print("  No data loaded — uploading sample discovery...")
            upload_discovery_file(page)
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(3000)

        # ── 1. Connect / Landing page ──────────────────────────
        # Take a clean connect-page screenshot (show the connect form)
        # We need to disconnect first to see the connect screen
        print("\n1. Connect page (showing connect form)")
        page.evaluate("async () => { await fetch('/api/disconnect', {method:'POST'}); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(2000)
        shot(page, "01_connect")

        # Re-upload to restore data
        upload_discovery_file(page)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(3000)

        # ── 2. Dashboard ───────────────────────────────────────
        print("\n2. Dashboard")
        page.click("#tab-dashboard")
        page.wait_for_timeout(WAIT)
        # Wait for charts to render
        page.wait_for_selector("canvas", timeout=5000)
        page.wait_for_timeout(1500)
        shot(page, "02_dashboard")

        # ── 3. Discovery & Assessment → Inventory ──────────────
        print("\n3. Discovery & Assessment - Inventory")
        page.click("#tab-workloads")
        page.wait_for_timeout(WAIT)
        page.click("#subtab-inventory")
        page.wait_for_timeout(WAIT)
        shot(page, "03_inventory")

        # ── 4. Topology ────────────────────────────────────────
        print("\n4. Topology")
        page.click("#subtab-topology")
        page.wait_for_timeout(4000)  # extra time for vis-network physics
        shot(page, "04_topology")

        # ── 4b. Discovery Settings (offcanvas drawer) ──────────
        print("\n4b. Discovery Settings (sidebar drawer)")
        # Open the offcanvas drawer
        drawer_btn = page.query_selector('[data-bs-target="#discoveryDrawer"]')
        if drawer_btn:
            drawer_btn.click()
            page.wait_for_timeout(2000)
            shot(page, "04b_discovery_settings", full_page=False)
            # Close drawer
            close_btn = page.query_selector('#discoveryDrawer .btn-close')
            if close_btn:
                close_btn.click()
                page.wait_for_timeout(1000)

        # ── 5. Assessment ──────────────────────────────────────
        print("\n5. VM Assessment")
        page.click("#subtab-assessment")
        page.wait_for_timeout(WAIT)
        shot(page, "05_vm_assessment")

        # ── 5b. VM What-If modal ──────────────────────────────
        print("   5b. VM What-If Assessment")
        # Wait for assessment table rows to load, then open what-if via JS
        page.wait_for_timeout(2000)
        opened = page.evaluate("""async () => {
            const tbody = document.getElementById('assess-tbody');
            if (!tbody) return 'no-tbody';
            const rows = tbody.querySelectorAll('tr');
            if (rows.length === 0) return 'no-rows';
            // Get the first VM name from the onclick attribute
            const onclick = rows[0].getAttribute('onclick') || '';
            const match = onclick.match(/openWhatIf\\('([^']+)'\\)/);
            if (match) {
                await openWhatIf(match[1]);
                return 'opened:' + match[1];
            }
            // Fallback: just click the row
            rows[0].click();
            return 'clicked';
        }""")
        print(f"     What-If trigger: {opened}")
        page.wait_for_timeout(4000)  # wait for modal + API call + charts
        # Check if the modal backdrop is visible
        visible = page.evaluate("document.getElementById('vm-whatif-backdrop')?.classList.contains('show')")
        if visible:
            shot(page, "05b_vm_whatif", full_page=False)
        else:
            print("     ⚠ What-If modal not visible, trying direct call...")
            # Try calling openWhatIf with a known VM name from the data
            page.evaluate("""async () => {
                const resp = await fetch('/api/vms');
                const data = await resp.json();
                if (data.vms && data.vms.length > 0) {
                    await openWhatIf(data.vms[0].name);
                }
            }""")
            page.wait_for_timeout(4000)
            shot(page, "05b_vm_whatif", full_page=False)
        # Close the what-if modal
        page.evaluate("typeof closeWhatIf === 'function' && closeWhatIf()")
        page.wait_for_timeout(1000)

        # ── 6. Simulation ─────────────────────────────────────
        print("\n6. Simulation")
        page.click("#subtab-simulation")
        page.wait_for_timeout(WAIT)
        shot(page, "06_simulation")

        # ── 7. Vulnerability & SLA ─────────────────────────────
        print("\n7. Vulnerability & SLA - OS Lifecycle")
        page.click("#subtab-vulnsla")
        page.wait_for_timeout(WAIT)
        shot(page, "07_vulnerability_sla")

        # ── Sub-tabs: Software Lifecycle ───────────────────────
        print("   7b. Software Lifecycle")
        sw_tab = page.query_selector('[data-bs-target="#vs-sw-tab"]')
        if sw_tab:
            sw_tab.click()
            page.wait_for_timeout(WAIT)
            shot(page, "07b_software_lifecycle")

        # ── Sub-tabs: Licensing Guidance ───────────────────────
        print("   7c. Licensing Guidance")
        lic_tab = page.query_selector('[data-bs-target="#vs-lic-tab"]')
        if lic_tab:
            lic_tab.click()
            page.wait_for_timeout(WAIT)
            shot(page, "07c_licensing_guidance")

        # ── 8. Business Case ──────────────────────────────────
        print("\n8. Business Case")
        page.click("#tab-businesscase")
        page.wait_for_timeout(WAIT)
        # Try to generate the business case
        gen_btn = page.query_selector("#btn-gen-bc")
        if not gen_btn:
            gen_btn = page.query_selector("button:has-text('Generate')")
        if gen_btn:
            gen_btn.click()
            page.wait_for_timeout(5000)  # business case generation takes a moment
        shot(page, "08_business_case")

        # ── 9. Enrichment ─────────────────────────────────────
        print("\n9. Enrichment")
        page.click("#tab-enrichment")
        page.wait_for_timeout(WAIT)
        shot(page, "09_enrichment")

        browser.close()

    # Summary
    files = sorted(OUT.glob("*.png"))
    print(f"\n{'='*50}")
    print(f"Done — {len(files)} screenshots in docs/screenshots/")
    for f in files:
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
