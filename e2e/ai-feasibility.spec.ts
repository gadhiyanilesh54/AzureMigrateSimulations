import { test, expect, type Page } from '@playwright/test';

async function dismissOverlay(page: Page) {
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => document.getElementById('connectOverlay')?.classList.add('hidden'));
  await expect(page.locator('#connectOverlay')).toHaveClass(/hidden/);
}

test.describe('AI Feasibility Assessment', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
  });

  test('chat starts with discovered application choices', async ({ page }) => {
    await page.evaluate(() => {
      bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('migrationChatPanel')!).show();
      document.getElementById('migration-chat-new')?.click();
    });
    await page.locator('#migration-chat-input').fill('Start an AI feasibility assessment');
    const responsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/chat') && response.request().method() === 'POST',
      { timeout: 90_000 },
    );
    await page.evaluate(() => (document.getElementById('migration-chat-form') as HTMLFormElement).requestSubmit());
    const response = await responsePromise;
    const payload = await response.json();

    expect(payload.intent).toBe('ai_feasibility');
    expect(payload.ai_feasibility_stage).toBe('select_application');
    expect(payload.actions.length).toBeGreaterThan(0);
    await expect(page.locator('.migration-chat-message.assistant').last()).toContainText('application');
    await expect(page.locator('.migration-chat-message.assistant').last().locator('.migration-chat-action').first()).toContainText('Select');

    await page.evaluate(async (conversationId) => {
      await fetch(`/api/chat/conversations/${encodeURIComponent(conversationId)}`, { method: 'DELETE' });
    }, payload.conversation_id);
  });

  test('generates a decision pack and AI-ready landing-zone architecture', async ({ page }) => {
    let assessmentId = '';
    try {
      await page.evaluate(async () => {
        bootstrap.Tab.getOrCreateInstance(document.getElementById('tab-decide')!).show();
        showDecideSub('decide-discovery');
        bootstrap.Tab.getOrCreateInstance(document.getElementById('subtab-assessment')!).show();
        await window.openAIFeasibilityAssessment();
      });
      await expect(page.locator('#ai-feasibility-workspace')).toBeVisible();
      await expect(page.locator('.ai-solution-card')).toHaveCount(7);

      const application = await page.locator('#ai-feasibility-application option').nth(1).getAttribute('value');
      expect(application).toBeTruthy();
      await page.locator('#ai-feasibility-application').selectOption(application!);

      await page.locator('#ai-feasibility-file').setInputFiles({
        name: 'customer-intent.md',
        mimeType: 'text/markdown',
        buffer: Buffer.from(
          '# Return workflow\nSupport employees read scanned return forms and approved policy files. ' +
          'Extract fields, find guidance, and draft a read-only response for employee approval.',
        ),
      });
      await expect(page.locator('#ai-feasibility-upload-status')).toContainText('customer-intent.md');
      await expect(page.locator('[data-category-id="document_processing_enrichment"]')).toHaveClass(/selected/);

      await page.locator('#ai-feasibility-outcome').fill(
        'Reduce median handling time by 25 percent while maintaining response quality and mandatory employee review.',
      );
      await page.locator('#ai-feasibility-consent').check();

      const createPromise = page.waitForResponse(
        (response) => response.url().endsWith('/api/ai-feasibility/assessments') && response.request().method() === 'POST',
        { timeout: 90_000 },
      );
      await page.locator('#ai-feasibility-generate').click();
      const createResponse = await createPromise;
      expect(createResponse.status()).toBe(201);
      const assessment = await createResponse.json();
      assessmentId = assessment.id;

      expect(assessment.generation.narrative_provider).toBe('foundry-generative');
      expect(assessment.generation.model_deployment).toBe('gpt-6.1-sol');
      expect(assessment.executive_decision.production_ready).toBe(false);
      await expect(page.locator('.ai-assessment-banner')).toBeVisible({ timeout: 90_000 });
      await expect(page.locator('.ai-dimension-card')).toHaveCount(6);
      await expect(page.locator('#ai-feasibility-result')).toContainText('Not an Azure quote');
      await expect(page.locator('#ai-feasibility-result')).toContainText('Azure AI Document Intelligence');

      const architecturePromise = page.waitForResponse(
        (response) => response.url().includes('/api/landing-zones') && response.url().includes('include_ai=true'),
      );
      await page.locator('[data-ai-architecture]').click();
      const architectureResponse = await architecturePromise;
      expect(architectureResponse.status()).toBe(200);
      const architecture = await architectureResponse.json();
      expect(architecture.summary.ai_ready_application_count).toBe(1);

      await expect(page.locator('#landing-zone-ai-feasibility')).toBeChecked();
      await expect(page.locator('#landing-zone-canvas svg title').first()).toContainText('AI-ready');
      await expect(page.locator('#landing-zone-canvas svg')).toContainText('AI capability extension');
      await expect(page.locator('#landing-zone-detail-meta')).toContainText(assessmentId);
    } finally {
      if (assessmentId) {
        await page.evaluate(async (id) => {
          await fetch(`/api/ai-feasibility/assessments/${encodeURIComponent(id)}`, { method: 'DELETE' });
        }, assessmentId);
      }
    }
  });
});
