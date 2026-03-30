import { test, expect } from '@playwright/test';

test('no JS errors on page load and overlay auto-hides', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('http://localhost:5000/');
  await page.waitForLoadState('networkidle');
  // Give the auto-load flow time to run
  await page.waitForTimeout(2000);

  // The JS error that was blocking execution should now be fixed
  expect(errors).toEqual([]);

  // The overlay should auto-hide now that the JS error is fixed
  const cls = await page.locator('#connectOverlay').getAttribute('class');
  expect(cls).toContain('hidden');
});

test('CTD is not visible when Decide tab is active', async ({ page }) => {
  await page.goto('http://localhost:5000/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Click Decide tab
  await page.locator('#tab-decide').click();
  await expect(page.locator('#pane-decide')).toBeVisible();

  // plan-ctd should NOT be visible
  await expect(page.locator('#plan-ctd')).not.toBeVisible();
});
