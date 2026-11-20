import { test, expect, type Page } from '@playwright/test';

async function dismissOverlay(page: Page) {
  await page.waitForLoadState('networkidle');
  await page.evaluate(async () => {
    const status = await (await fetch('/api/status')).json();
    if (status.data_loaded) document.getElementById('connectOverlay')?.classList.add('hidden');
  });
  await expect(page.locator('#connectOverlay')).toHaveClass(/hidden/);
}

async function openChat(page: Page) {
  await page.locator('#btnMigrationChat').click();
  await expect(page.locator('#migrationChatPanel')).toHaveClass(/show/);
  await page.locator('#migration-chat-new').click();
  await expect(page.locator('#migration-chat-messages')).toContainText('Ask me about this migration project');
}

async function ask(page: Page, message: string) {
  await page.locator('#migration-chat-input').fill(message);
  await Promise.all([
    page.waitForResponse((response) => response.url().endsWith('/api/chat') && response.status() === 200),
    page.locator('#migration-chat-send').click(),
  ]);
  await expect(page.locator('[data-thinking="true"]')).toHaveCount(0);
  const assistantMessages = page.locator('.migration-chat-message.assistant');
  await expect(assistantMessages.last()).not.toContainText('Analyzing');
  return assistantMessages.last();
}

test.describe('Migration Copilot', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOverlay(page);
  });

  test('Chat appears after New Connection and opens grounded workspace', async ({ page }) => {
    const buttonIds = await page.locator('.navbar .d-flex.align-items-center.gap-3 > button').evaluateAll(
      (buttons) => buttons.map((button) => button.id),
    );
    expect(buttonIds.indexOf('btnMigrationChat')).toBe(buttonIds.indexOf('btnDisconnect') + 1);

    await openChat(page);
    await expect(page.locator('#migration-chat-provider-label')).toHaveText('Foundry AI · gpt-6.1-sol');
    await expect(page.locator('#migration-chat-context-label')).toHaveText('Project loaded · History persisted');
    await expect(page.locator('#migration-chat-disclaimer')).toContainText('Conversations persist in the local project database');
  });

  test('answers assessment summary with evidence citations', async ({ page }) => {
    await openChat(page);
    const response = await ask(page, 'Summarize the assessment');

    await expect(response.locator('.migration-chat-meta')).toContainText('Foundry generative · gpt-6.1-sol');
    await expect(response.locator('.migration-chat-citation')).toHaveCount(2);
    await expect(response.locator('.migration-chat-action')).toContainText(['Open overview', 'Review assessment']);
  });

  test('explains a VM cost and retains VM context for follow-up', async ({ page }) => {
    const vmName = await page.evaluate(async () => {
      const vms = await (await fetch('/api/vms')).json();
      return vms[0].name as string;
    });
    await openChat(page);
    await ask(page, `Tell me about ${vmName}`);
    const response = await ask(page, 'How did this cost get calculated?');

    await expect(response).toContainText(vmName);
    await expect(response.locator('.migration-chat-citation').first()).toContainText(vmName);
  });

  test('explains App Service target recommendation', async ({ page }) => {
    await openChat(page);
    const response = await ask(page, 'Why was App Service selected?');

    await expect(response).toContainText(/(?:Azure )?App Service/);
    await expect(response).toContainText('confidence');
    await expect(response.locator('.migration-chat-action')).toContainText('Open workload assessment');
  });

  test('generates landing-zone answer and navigates to diagrams', async ({ page }) => {
    await openChat(page);
    const response = await ask(page, 'Generate landing zones');

    await expect(response).toContainText(/application landing[- ]zone architectures?/i);
    const action = response.getByRole('button', { name: 'View Landing Zone diagrams' });
    await action.click();

    await expect(page.locator('#migrationChatPanel')).not.toHaveClass(/show/);
    await expect(page.locator('#tab-plan')).toHaveClass(/active/);
    await expect(page.locator('#plan-landing-zone')).toBeVisible();
    await expect(page.locator('#landing-zone-results .landing-zone-card').first()).toBeVisible({ timeout: 15_000 });
  });

  test('conversation persists across reload and can be deleted', async ({ page }) => {
    await openChat(page);
    await ask(page, 'Summarize the assessment');
    const conversationId = await page.locator('#migration-chat-conversation-select').inputValue();
    expect(conversationId).toMatch(/^conv-/);

    await page.reload({ waitUntil: 'networkidle' });
    await dismissOverlay(page);
    await page.locator('#btnMigrationChat').click();
    await expect(page.locator('#migrationChatPanel')).toHaveClass(/show/);
    await expect(page.locator('#migration-chat-conversation-select')).toHaveValue(conversationId);
    await expect(page.locator('.migration-chat-message.user')).toContainText('Summarize the assessment');
    await expect(page.locator('.migration-chat-message.assistant').last().locator('.migration-chat-citation')).toHaveCount(2);

    await page.locator('#migration-chat-clear').click();

    await expect(page.locator('.migration-chat-message.user')).toHaveCount(0);
    await expect(page.locator('.migration-chat-message.assistant')).toHaveCount(1);
    await expect(page.locator('#migration-chat-conversation-select')).toHaveValue('');
    const status = await page.evaluate(async (id) => (await fetch(`/api/chat/conversations/${id}`)).status, conversationId);
    expect(status).toBe(404);
  });
});
