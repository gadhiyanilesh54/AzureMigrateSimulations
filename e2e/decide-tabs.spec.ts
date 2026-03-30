import { test, expect } from '@playwright/test';

test.describe('Decide tab and sub-tabs', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard and wait for the page to load
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // The app auto-dismisses the connect overlay when data is loaded,
    // but a pre-existing JS error can prevent the auto-dismiss flow.
    // Check the overlay state and dismiss it manually if data is loaded.
    const overlayHidden = await page.locator('#connectOverlay').evaluate(
      el => el.classList.contains('hidden')
    );
    if (!overlayHidden) {
      await page.evaluate(async () => {
        const res = await fetch('/api/status');
        const s = await res.json();
        if (s.data_loaded) {
          document.getElementById('connectOverlay')!.classList.add('hidden');
        }
      });
    }

    await expect(page.locator('#connectOverlay')).toHaveClass(/hidden/, { timeout: 5_000 });
    await expect(page.locator('#journeyStepper')).toBeVisible();
  });

  test('should navigate to the Decide tab', async ({ page }) => {
    // Click the Decide tab in the main stepper
    await page.locator('#tab-decide').click();

    // Verify the Decide pane is visible
    await expect(page.locator('#pane-decide')).toBeVisible();
    await expect(page.locator('#tab-decide')).toHaveClass(/active/);
  });

  test('should show Discovery & Assessment sub-tab by default', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    // Discovery & Assessment is the default active sub-tab
    await expect(page.locator('#decide-discovery-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-discovery')).toBeVisible();
  });

  test('should switch to Enrichment sub-tab', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    await page.locator('#decide-enrichment-tab').first().click();
    await expect(page.locator('#decide-enrichment-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-enrichment')).toBeVisible();
  });

  test('should switch to Business Case sub-tab', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    await page.locator('#decide-businesscase-tab').first().click();
    await expect(page.locator('#decide-businesscase-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-businesscase')).toBeVisible();
  });

  test('should switch to Pricing Comparison sub-tab', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    await page.locator('#decide-pricing-tab').first().click();
    await expect(page.locator('#decide-pricing-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-pricing')).toBeVisible();
  });

  test('should switch to Compliance sub-tab', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    await page.locator('#decide-compliance-tab').first().click();
    await expect(page.locator('#decide-compliance-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-compliance')).toBeVisible();
  });

  test('should switch to Executive Report sub-tab', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    await page.locator('#decide-report-tab').first().click();
    await expect(page.locator('#decide-report-tab').first()).toHaveClass(/active/);
    await expect(page.locator('#decide-report')).toBeVisible();
  });

  test('should cycle through all Decide sub-tabs', async ({ page }) => {
    await page.locator('#tab-decide').click();
    await expect(page.locator('#pane-decide')).toBeVisible();

    const subTabs = [
      { tabId: 'decide-discovery-tab', paneId: 'decide-discovery', label: 'Discovery & Assessment' },
      { tabId: 'decide-enrichment-tab', paneId: 'decide-enrichment', label: 'Enrichment' },
      { tabId: 'decide-businesscase-tab', paneId: 'decide-businesscase', label: 'Business Case' },
      { tabId: 'decide-pricing-tab', paneId: 'decide-pricing', label: 'Pricing Comparison' },
      { tabId: 'decide-compliance-tab', paneId: 'decide-compliance', label: 'Compliance' },
      { tabId: 'decide-report-tab', paneId: 'decide-report', label: 'Executive Report' },
    ];

    for (const { tabId, paneId, label } of subTabs) {
      // Click the sub-tab (use first() since there are duplicate tab elements)
      await page.locator(`#${tabId}`).first().click();

      // Verify the tab becomes active and its pane is visible
      await expect(page.locator(`#${tabId}`).first()).toHaveClass(/active/, {
        timeout: 5_000,
      });
      await expect(page.locator(`#${paneId}`)).toBeVisible({ timeout: 5_000 });

      // Verify other sub-panes are hidden
      for (const other of subTabs) {
        if (other.paneId !== paneId) {
          await expect(page.locator(`#${other.paneId}`)).not.toBeVisible();
        }
      }
    }
  });
});
