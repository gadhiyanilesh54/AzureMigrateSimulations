import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helper: dismiss the connect overlay (data auto-loads from data/ folder)
// ---------------------------------------------------------------------------
async function dismissOverlay(page: Page) {
  await page.waitForLoadState('networkidle');
  const hidden = await page.locator('#connectOverlay').evaluate(
    (el) => el.classList.contains('hidden'),
  );
  if (!hidden) {
    await page.evaluate(async () => {
      const res = await fetch('/api/status');
      const s = await res.json();
      if (s.data_loaded) {
        document.getElementById('connectOverlay')!.classList.add('hidden');
      }
    });
  }
  await expect(page.locator('#connectOverlay')).toHaveClass(/hidden/, { timeout: 5_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  1. PAGE LOAD & AUTO-CONNECT
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Page Load', () => {
  test('loads without JS errors and auto-hides connect overlay', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');
    await dismissOverlay(page);

    await expect(page.locator('#journeyStepper')).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('navbar shows Azure Migrate Simulations branding', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);

    await expect(page.locator('.navbar-brand')).toContainText('Azure Migrate Simulations');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  2. MAIN STEPPER TABS (Overview → Decide → Plan → Execute)
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Main Stepper Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
  });

  test('Overview tab is active by default', async ({ page }) => {
    await expect(page.locator('#tab-dashboard')).toHaveClass(/active/);
    await expect(page.locator('#pane-dashboard')).toBeVisible();
  });

  test('can switch to Decide tab', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#tab-decide')).toHaveClass(/active/);
    await expect(page.locator('#pane-decide')).toBeVisible();
  });

  test('can switch to Plan tab', async ({ page }) => {
    await page.locator('#tab-plan').click();
    await expect(page.locator('#tab-plan')).toHaveClass(/active/);
    await expect(page.locator('#pane-plan')).toBeVisible();
  });

  test('can switch to Execute tab', async ({ page }) => {
    await page.locator('#tab-execute').click();
    await expect(page.locator('#tab-execute')).toHaveClass(/active/);
    await expect(page.locator('#pane-execute')).toBeVisible();
  });

  test('switching tabs hides content from other phases', async ({ page }) => {
    // Show Decide → then switch to Plan
    await page.locator('#tab-decide').click();
    await expect(page.locator('#decide-discovery')).toBeVisible();

    await page.locator('#tab-plan').click();
    await expect(page.locator('#decide-discovery')).not.toBeVisible();
    await expect(page.locator('#plan-ctd')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  3. OVERVIEW / DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Overview Dashboard', () => {
  test('shows summary stat cards with VM data', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);

    // The dashboard pane should be visible
    await expect(page.locator('#pane-dashboard')).toBeVisible();
    await expect(page.locator('#tab-dashboard')).toHaveClass(/active/);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  4. DECIDE PHASE — SUB-TABS
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Decide Phase', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();
  });

  test('Discovery & Assessment is the default sub-tab', async ({ page }) => {
    await expect(page.locator('#decide-discovery-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-discovery')).toBeVisible();
  });

  test('can switch to all Decide sub-tabs', async ({ page }) => {
    const subTabs = [
      { tabId: 'decide-enrichment-tab', paneId: 'decide-enrichment' },
      { tabId: 'decide-businesscase-tab', paneId: 'decide-businesscase' },
      { tabId: 'decide-pricing-tab', paneId: 'decide-pricing' },
      { tabId: 'decide-compliance-tab', paneId: 'decide-compliance' },
      { tabId: 'decide-report-tab', paneId: 'decide-report' },
    ];
    for (const { tabId, paneId } of subTabs) {
      await page.locator(`#${tabId}`).first().click();
      await expect(page.locator(`#${tabId}`).first()).toHaveClass(/active/);
      await expect(page.locator(`#${paneId}`)).toBeVisible();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  5. DISCOVERY SUB-TABS (Inventory, Topology, Assessment, Simulation, V&SLA)
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Discovery & Assessment Sub-tabs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.waitForTimeout(300);
  });

  test('Inventory tab shows VM stat cards', async ({ page }) => {
    await expect(page.locator('#subtab-inventory')).toHaveClass(/active/);
    // Check VM count card is visible
    await expect(page.locator('#wl-card-vms')).toBeVisible();
  });

  test('can switch to Topology sub-tab', async ({ page }) => {
    await page.locator('#subtab-topology').click();
    await expect(page.locator('#pane-topology')).toBeVisible();
  });

  test('Topology shows only Dependencies view, no Infrastructure toggle', async ({ page }) => {
    await page.locator('#subtab-topology').click();
    await expect(page.locator('#pane-topology')).toBeVisible();

    // Infrastructure toggle button should not exist
    await expect(page.locator('#topo-view-infra')).toHaveCount(0);

    // Dependencies view should be visible (not hidden)
    await expect(page.locator('#topo-deps-view')).toBeVisible();

    // Dependencies legend items should be present
    await expect(page.locator('#topo-deps-view .legend-item')).toHaveCount(7);
  });

  test('can switch to Assessment sub-tab', async ({ page }) => {
    await page.locator('#subtab-assessment').click();
    await expect(page.locator('#pane-assessment')).toBeVisible();
  });

  test('can switch to Simulation sub-tab', async ({ page }) => {
    await page.locator('#subtab-simulation').click();
    await expect(page.locator('#pane-simulation')).toBeVisible();
    await expect(page.locator('#sim-region')).toBeVisible();
    await expect(page.locator('#sim-pricing')).toBeVisible();
  });

  test('can switch to Vulnerability & SLA sub-tab', async ({ page }) => {
    await page.locator('#subtab-vulnsla').click();
    await expect(page.locator('#pane-vulnsla')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  6. SIMULATION — Run Simulation
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Simulation', () => {
  test('Run Simulation produces results', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.waitForTimeout(300);
    await page.locator('#subtab-simulation').click();
    await expect(page.locator('#pane-simulation')).toBeVisible();

    // Click Run Simulation
    await page.locator('#sim-vms-view button:has-text("Run Simulation")').click();

    // Wait for the API response
    await page.waitForResponse('**/api/simulate');

    // Results and cost card should become visible
    await expect(page.locator('#sim-results')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('#sim-cost-card')).toBeVisible();

    // Check cost values populated
    await expect(page.locator('#sim-original-cost')).not.toHaveText('—');
    await expect(page.locator('#sim-new-cost')).not.toHaveText('—');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  7. BUSINESS CASE
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Business Case', () => {
  test('Generate Business Case returns results', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.locator('#decide-businesscase-tab').first().click();
    await expect(page.locator('#decide-businesscase')).toBeVisible();

    // Click and wait for API in parallel
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/businesscase') && r.status() === 200),
      page.locator('button:has-text("Generate Business Case")').click(),
    ]);

    // Loading indicator should disappear
    await expect(page.locator('#bc-loading')).not.toBeVisible({ timeout: 15_000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  8. PRICING COMPARISON
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Pricing Comparison', () => {
  test('Compare All Models returns results', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.locator('#decide-pricing-tab').first().click();
    await expect(page.locator('#decide-pricing')).toBeVisible();

    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/pricing/comparison') && r.status() === 200),
      page.locator('button:has-text("Compare All Models")').click(),
    ]);

    // Results area should show pricing data
    await expect(page.locator('#pricing-results')).not.toContainText('Click "Compare All Models"', { timeout: 15_000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  9. COMPLIANCE
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Compliance', () => {
  test('Assess compliance returns results', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.locator('#decide-compliance-tab').first().click();
    await expect(page.locator('#decide-compliance')).toBeVisible();

    // Checkboxes should be visible
    await expect(page.locator('#fw-pci')).toBeVisible();

    // Click Assess and wait for API
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/compliance/assess') && r.status() === 200),
      page.locator('#decide-compliance button:has-text("Assess")').click(),
    ]);

    // Results should contain compliance data
    await expect(page.locator('#compliance-results')).not.toBeEmpty({ timeout: 10_000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  10. EXECUTIVE REPORT
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Executive Report', () => {
  test('Generate Report returns results', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.locator('#decide-report-tab').first().click();
    await expect(page.locator('#decide-report')).toBeVisible();

    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/reports/executive') && r.status() === 200),
      page.locator('button:has-text("Generate Report")').click(),
    ]);

    await expect(page.locator('#report-results')).not.toContainText('boardroom-ready', { timeout: 15_000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  11. PLAN PHASE — SUB-TABS
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Plan Phase', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-plan').click();
    await expect(page.locator('#pane-plan')).toBeVisible();
  });

  test('Cloud Topology is the default sub-tab', async ({ page }) => {
    await expect(page.locator('#plan-ctd-tab')).toHaveClass(/active/);
    await expect(page.locator('#plan-ctd')).toBeVisible();
  });

  test('can switch to Application Groups sub-tab', async ({ page }) => {
    await page.locator('#plan-apps-tab').click();
    await expect(page.locator('#plan-apps')).toBeVisible();
  });

  test('can switch to Cost Optimization sub-tab', async ({ page }) => {
    await page.locator('#plan-costopt-tab').click();
    await expect(page.locator('#plan-costopt')).toBeVisible();
  });

  test('can switch to Wave Planning sub-tab', async ({ page }) => {
    await page.locator('#plan-waves-tab').click();
    await expect(page.locator('#plan-waves-tab')).toHaveClass(/active/);
    await expect(page.locator('#plan-waves')).toBeVisible();
    await expect(page.locator('#wave-plan-results')).toBeVisible();
  });

  test('can switch to Tagging sub-tab', async ({ page }) => {
    await page.locator('#plan-tags-tab').click();
    await expect(page.locator('#plan-tags')).toBeVisible();
  });

  test('can switch to IaC Export sub-tab', async ({ page }) => {
    await page.locator('#plan-iac-tab').click();
    await expect(page.locator('#plan-iac')).toBeVisible();
  });

  test('can switch to Runbooks sub-tab', async ({ page }) => {
    await page.locator('#plan-runbooks-tab').click();
    await expect(page.locator('#plan-runbooks')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  12. PLAN — Feature Actions
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Plan Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-plan').click();
    await expect(page.locator('#pane-plan')).toBeVisible();
  });

  test('Cloud Topology — Generate Diagram', async ({ page }) => {
    await expect(page.locator('#ctd-generate-btn')).toBeVisible();

    // Click and wait for API in parallel
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/cloud-topology') && r.status() === 200),
      page.locator('#ctd-generate-btn').click(),
    ]);

    // The canvas or toolbar should appear
    await expect(page.locator('#ctd-toolbar')).toBeVisible({ timeout: 15_000 });
  });

  test('Application Groups — Detect Groups', async ({ page }) => {
    await page.locator('#plan-apps-tab').click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/applications') && r.status() === 200),
      page.locator('button:has-text("Detect Groups")').click(),
    ]);

    await expect(page.locator('#appgroups-results')).not.toContainText('Auto-discovers', { timeout: 10_000 });
  });

  test('Cost Optimization — Optimize', async ({ page }) => {
    await page.locator('#plan-costopt-tab').click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/cost-optimization') && r.status() === 200),
      page.locator('button:has-text("Optimize")').click(),
    ]);

    await expect(page.locator('#costopt-results')).not.toContainText('Per-VM pricing', { timeout: 10_000 });
  });

  test('Wave Planning — Generate Plan', async ({ page }) => {
    await page.locator('#plan-waves-tab').click();
    await expect(page.locator('#plan-waves')).toBeVisible();

    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/waves/smart-plan') && r.status() === 200),
      page.locator('button:has-text("Generate Plan")').click(),
    ]);

    // Summary cards should appear
    await expect(page.locator('#wave-plan-results .stat-card')).toHaveCount(4, { timeout: 10_000 });

    // Wave cards should appear
    await expect(page.locator('#wave-plan-results .wave-card').first()).toBeVisible();

    // Table with VM names should be present
    await expect(page.locator('#wave-plan-results table')).toHaveCount(4);
  });

  test('Tagging — Generate Tags', async ({ page }) => {
    await page.locator('#plan-tags-tab').click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/tags/strategy') && r.status() === 200),
      page.locator('button:has-text("Generate Tags")').click(),
    ]);

    await expect(page.locator('#tagging-results')).not.toContainText('Auto-generates', { timeout: 10_000 });
  });

  test('Runbooks — Generate Runbooks', async ({ page }) => {
    await page.locator('#plan-runbooks-tab').click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/runbooks/generate') && r.status() === 200),
      page.locator('button:has-text("Generate Runbooks")').click(),
    ]);

    await expect(page.locator('#runbooks-results')).not.toContainText('Pre-migration, execution', { timeout: 10_000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  13. EXECUTE PHASE — SUB-TABS
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Execute Phase', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-execute').click();
    await expect(page.locator('#pane-execute')).toBeVisible();
  });

  test('Migration Tracker is the default sub-tab', async ({ page }) => {
    await expect(page.locator('#exec-tracker-tab')).toHaveClass(/active/);
    await expect(page.locator('#exec-tracker')).toBeVisible();
  });

  test('can switch to NSG Rules sub-tab', async ({ page }) => {
    await page.locator('#exec-nsg-tab').click();
    await expect(page.locator('#exec-nsg')).toBeVisible();
    // Other sub-panes must be hidden
    await expect(page.locator('#exec-tracker')).not.toBeVisible();
    await expect(page.locator('#exec-postval')).not.toBeVisible();
    await expect(page.locator('#exec-snapshots')).not.toBeVisible();
  });

  test('can switch to Post-Migration Validation sub-tab', async ({ page }) => {
    await page.locator('#exec-postval-tab').click();
    await expect(page.locator('#exec-postval')).toBeVisible();
    await expect(page.locator('#exec-tracker')).not.toBeVisible();
    await expect(page.locator('#exec-nsg')).not.toBeVisible();
  });

  test('can switch to Snapshots sub-tab', async ({ page }) => {
    await page.locator('#exec-snapshots-tab').click();
    await expect(page.locator('#exec-snapshots')).toBeVisible();
    await expect(page.locator('#exec-tracker')).not.toBeVisible();
    await expect(page.locator('#exec-nsg')).not.toBeVisible();
    await expect(page.locator('#exec-postval')).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  14. EXECUTE — Feature Actions
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Execute Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-execute').click();
    await expect(page.locator('#pane-execute')).toBeVisible();
  });

  test('NSG Rules — Generate Rules', async ({ page }) => {
    await page.locator('#exec-nsg-tab').click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/nsg-rules') && r.status() === 200),
      page.locator('button:has-text("Generate Rules")').click(),
    ]);

    await expect(page.locator('#nsg-results')).not.toContainText('Auto-generates Azure NSG', { timeout: 10_000 });
  });

  test('Post-Migration — Generate Checks', async ({ page }) => {
    await page.locator('#exec-postval-tab').click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/validation/post-migration') && r.status() === 200),
      page.locator('button:has-text("Generate Checks")').click(),
    ]);

    await expect(page.locator('#postval-results')).not.toContainText('Health, connectivity', { timeout: 10_000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  15. ENRICHMENT
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Enrichment', () => {
  test('Enrichment tab shows status', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await page.locator('#decide-enrichment-tab').first().click();
    await expect(page.locator('#decide-enrichment')).toBeVisible();

    // Enrichment pane should have content
    await expect(page.locator('#decide-enrichment')).not.toBeEmpty();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//  16. CROSS-PHASE ISOLATION
// ═══════════════════════════════════════════════════════════════════════════
test.describe('Cross-Phase Isolation', () => {
  test('CTD is not visible when Decide tab is active', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();
    await expect(page.locator('#plan-ctd')).not.toBeVisible();
  });

  test('Decide sub-panes hidden when Plan tab is active', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);

    // First show Decide to make discovery visible
    await page.locator('#tab-decide').click();
    await expect(page.locator('#decide-discovery')).toBeVisible();

    // Switch to Plan
    await page.locator('#tab-plan').click();
    await expect(page.locator('#decide-discovery')).not.toBeVisible();
  });

  test('All phase content hidden on Overview', async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);

    // Show Decide first
    await page.locator('#tab-decide').click();
    await page.waitForTimeout(300);

    // Switch back to Overview
    await page.locator('#tab-dashboard').click();
    await expect(page.locator('#decide-discovery')).not.toBeVisible();
    await expect(page.locator('#plan-ctd')).not.toBeVisible();
  });
});
