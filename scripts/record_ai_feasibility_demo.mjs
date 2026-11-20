import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const outputDir = path.join(root, 'docs', 'demo', 'video', 'browser');
const assetDir = path.join(root, 'docs', 'demo', 'video', 'assets');
const profileDir = path.join(root, 'test-results', 'demo-recording-profile');
const baseUrl = 'http://127.0.0.1:5000';

fs.mkdirSync(outputDir, { recursive: true });
fs.mkdirSync(assetDir, { recursive: true });
fs.rmSync(profileDir, { recursive: true, force: true });

const INTENT = 'Use AI in BPTco to streamline the processing and enrichment of business documents, such as invoices, contracts, and supporting attachments. Automatically classify documents, extract key information—including names, reference numbers, dates, and amounts—and enrich them with standardized metadata and concise summaries. Validate extracted information against business rules and route exceptions or low-confidence results for human review.';
const OUTCOME = 'Reduce manual data-entry effort by 60% and document-processing time by 50%, while targeting 95% accuracy for critical fields across supported document types. Improve document searchability, data consistency, and downstream reporting so employees can spend less time reviewing documents and more time resolving exceptions. Maintain controlled access, human approval for critical updates, and an audit trail.';

const manifest = {
  captured_at: new Date().toISOString(),
  base_url: baseUrl,
  assessment_id: '',
  clips: [],
};

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function hideOverlay(page) {
  await page.evaluate(() => document.getElementById('connectOverlay')?.classList.add('hidden'));
}

async function addRecordingChrome(page, sceneLabel) {
  await page.evaluate((label) => {
    document.getElementById('demo-recording-label')?.remove();
    document.getElementById('demo-recording-progress')?.remove();

    const watermark = document.createElement('div');
    watermark.id = 'demo-recording-label';
    watermark.textContent = 'Simulator prototype · Proposed Azure Migrate experience';
    Object.assign(watermark.style, {
      position: 'fixed', left: '24px', bottom: '20px', zIndex: '5000',
      padding: '8px 13px', borderRadius: '999px', color: '#dbeafe',
      background: 'rgba(6, 27, 44, .88)', border: '1px solid rgba(80, 230, 255, .42)',
      font: '600 12px Segoe UI, sans-serif', boxShadow: '0 8px 24px rgba(0,0,0,.25)',
      pointerEvents: 'none',
    });
    const progress = document.createElement('div');
    progress.id = 'demo-recording-progress';
    progress.textContent = label;
    Object.assign(progress.style, {
      position: 'fixed', right: '24px', bottom: '20px', zIndex: '5000',
      padding: '8px 13px', borderRadius: '999px', color: '#fff',
      background: 'rgba(0, 120, 212, .9)', border: '1px solid rgba(255,255,255,.25)',
      font: '600 12px Segoe UI, sans-serif', boxShadow: '0 8px 24px rgba(0,0,0,.25)',
      pointerEvents: 'none',
    });
    document.body.append(watermark, progress);
  }, sceneLabel);
}

async function clearGuidance(page) {
  await page.evaluate(() => {
    document.getElementById('demo-guide-card')?.remove();
    document.getElementById('demo-spotlight-box')?.remove();
  });
}

async function spotlight(page, locator, step, title, detail, position = 'top-right') {
  await locator.scrollIntoViewIfNeeded();
  await delay(350);
  const box = await locator.boundingBox();
  if (!box) throw new Error(`Unable to spotlight ${title}`);
  await page.evaluate(({ bounds, stepText, heading, copy, cardPosition }) => {
    document.getElementById('demo-guide-card')?.remove();
    document.getElementById('demo-spotlight-box')?.remove();

    const padding = 10;
    const spotlightBox = document.createElement('div');
    spotlightBox.id = 'demo-spotlight-box';
    Object.assign(spotlightBox.style, {
      position: 'fixed',
      left: `${Math.max(8, bounds.x - padding)}px`,
      top: `${Math.max(76, bounds.y - padding)}px`,
      width: `${Math.min(window.innerWidth - Math.max(8, bounds.x - padding) - 8, bounds.width + padding * 2)}px`,
      height: `${Math.min(window.innerHeight - Math.max(76, bounds.y - padding) - 8, bounds.height + padding * 2)}px`,
      zIndex: '4990',
      border: '4px solid #50e6ff',
      borderRadius: '15px',
      background: 'transparent',
      boxShadow: '0 0 0 9999px rgba(3, 11, 22, .52), 0 0 36px rgba(80, 230, 255, .88)',
      pointerEvents: 'none',
      transition: 'all .35s ease',
    });

    const guide = document.createElement('div');
    guide.id = 'demo-guide-card';
    const onLeft = cardPosition === 'top-left';
    Object.assign(guide.style, {
      position: 'fixed',
      top: '92px',
      left: onLeft ? '28px' : 'auto',
      right: onLeft ? 'auto' : '28px',
      width: '470px',
      zIndex: '5100',
      padding: '17px 20px 18px',
      borderRadius: '14px',
      color: '#f8fafc',
      background: 'linear-gradient(135deg, rgba(6,27,44,.98), rgba(20,55,84,.98))',
      border: '1px solid rgba(80,230,255,.58)',
      borderLeft: '6px solid #50e6ff',
      boxShadow: '0 18px 54px rgba(0,0,0,.48)',
      fontFamily: 'Segoe UI, sans-serif',
      pointerEvents: 'none',
    });
    guide.innerHTML = `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
      <span style="display:inline-grid;place-items:center;min-width:34px;height:34px;padding:0 9px;border-radius:999px;background:#0078d4;color:white;font-size:14px;font-weight:800">${stepText}</span>
      <span style="color:#50e6ff;font-size:11px;font-weight:800;letter-spacing:.11em;text-transform:uppercase">What we’re doing</span>
    </div>
    <div style="font-size:24px;line-height:1.18;font-weight:760;margin-bottom:7px">${heading}</div>
    <div style="color:#c8d8e7;font-size:14px;line-height:1.45">${copy}</div>`;
    document.body.append(spotlightBox, guide);
  }, {
    bounds: box,
    stepText: step,
    heading: title,
    copy: detail,
    cardPosition: position,
  });
}

async function setSceneLabel(page, label) {
  await page.evaluate((value) => {
    const progress = document.getElementById('demo-recording-progress');
    if (progress) progress.textContent = value;
  }, label);
}

async function startContext(sceneId) {
  const context = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    screen: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: outputDir, size: { width: 1920, height: 1080 } },
    args: [
      '--start-maximized', '--hide-scrollbars', '--disable-notifications',
      '--force-device-scale-factor=1', '--disable-features=Translate',
    ],
  });
  const pages = context.pages();
  const page = pages[0] || await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await hideOverlay(page);
  await addRecordingChrome(page, sceneId);
  return { context, page };
}

async function closeAndSave(sceneId, context, page) {
  const video = page.video();
  await context.close();
  const sourcePath = await video.path();
  const targetPath = path.join(outputDir, `${sceneId}.webm`);
  fs.copyFileSync(sourcePath, targetPath);
  if (sourcePath !== targetPath) fs.rmSync(sourcePath, { force: true });
  manifest.clips.push({ id: sceneId, file: path.basename(targetPath) });
  return targetPath;
}

async function sceneTwo() {
  const sceneId = 'live_02_application_groups';
  const { context, page } = await startContext('2 · Application intelligence');
  await page.locator('#tab-plan').click();
  await delay(650);
  await page.locator('#plan-apps-tab').click();
  await delay(650);
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/api/applications'));
  await page.locator('#plan-apps button:has-text("Detect Groups")').click();
  await responsePromise;
  const card = page.locator('.application-group-card').filter({ hasText: 'BPTco' }).first();
  await spotlight(
    page,
    card,
    '1',
    'Select the application',
    'BPTco is the complete application boundary we will evaluate—not an isolated VM.',
  );
  await delay(3300);
  const details = card.locator('details');
  if (await details.count()) {
    await details.evaluate((element) => { element.open = true; });
    await spotlight(
      page,
      details,
      '1',
      'Review the application context',
      'Azure Migrate carries VMs, web apps, databases, containers, orchestrators, and file shares together.',
    );
    await delay(3000);
  }
  return closeAndSave(sceneId, context, page);
}

async function sceneThree() {
  const sceneId = 'live_03_base_architecture';
  const { context, page } = await startContext('3 · Current landing-zone design');
  await page.locator('#tab-plan').click();
  await delay(600);
  await page.locator('#plan-landing-zone-tab').click();
  await delay(550);
  await page.locator('#landing-zone-ai-feasibility').uncheck({ force: true });
  await spotlight(
    page,
    page.locator('.ai-lz-toggle-wrap'),
    '2',
    'Start with the current Azure design',
    'AI-ready architecture is off, so this is the migration assessment baseline.',
    'top-left',
  );
  await delay(2300);
  await clearGuidance(page);
  const responsePromise = page.waitForResponse((response) => response.url().includes('/api/landing-zones') && response.url().includes('include_ai=false'));
  await page.locator('#landing-zone-generate-btn').click();
  await responsePromise;
  const viewButton = page.locator('.landing-zone-card').filter({ hasText: 'BPTco' }).getByRole('button', { name: 'View Architecture' });
  await viewButton.click();
  await page.locator('#landing-zone-canvas svg').waitFor({ state: 'visible' });
  await spotlight(
    page,
    page.locator('#landing-zone-canvas'),
    '2',
    'Review the baseline landing zone',
    'This shows the assessed application, platform, data, and storage targets before an AI extension is added.',
  );
  await delay(4800);
  return closeAndSave(sceneId, context, page);
}

async function openAssessmentWorkspace(page) {
  await page.evaluate(async () => {
    bootstrap.Tab.getOrCreateInstance(document.getElementById('tab-decide')).show();
    showDecideSub('decide-discovery');
    bootstrap.Tab.getOrCreateInstance(document.getElementById('subtab-assessment')).show();
    await window.openAIFeasibilityAssessment();
  });
  await page.locator('#ai-feasibility-workspace').waitFor({ state: 'visible' });
}

async function selectBptco(page) {
  const option = page.locator('#ai-feasibility-application option').filter({ hasText: 'BPTco' });
  const appId = await option.getAttribute('value');
  await page.locator('#ai-feasibility-application').selectOption(appId);
}

async function sceneFour() {
  const sceneId = 'live_04_application_selection';
  const { context, page } = await startContext('3 · Select application and opportunity');
  await openAssessmentWorkspace(page);
  await delay(1200);
  const applicationSelect = page.locator('#ai-feasibility-application');
  await spotlight(
    page,
    applicationSelect,
    '3',
    'Select BPTco',
    'The assessment is scoped to one discovered application and one business workflow.',
    'top-right',
  );
  await delay(2800);
  await selectBptco(page);
  await spotlight(
    page,
    page.locator('#ai-feasibility-application-context'),
    '3',
    'Use discovered application evidence',
    'The selected scope now includes BPTco members, dependencies, and assessed Azure targets.',
    'top-right',
  );
  await delay(2600);
  const category = page.locator('[data-category-id="document_processing_enrichment"]');
  await spotlight(
    page,
    category,
    '4',
    'Choose the AI opportunity',
    'Document Processing and Enrichment matches the customer’s workflow hypothesis.',
    'top-left',
  );
  await delay(2800);
  await category.click();
  await delay(1600);
  return closeAndSave(sceneId, context, page);
}

async function sceneFive() {
  const sceneId = 'live_05_intent_outcome';
  const { context, page } = await startContext('5 · Describe intent and outcome');
  await openAssessmentWorkspace(page);
  await selectBptco(page);
  await page.locator('[data-category-id="document_processing_enrichment"]').click();
  const intent = page.locator('#ai-feasibility-intent');
  await spotlight(
    page,
    intent,
    '5',
    'Describe the process to improve',
    'The customer supplies business meaning that infrastructure discovery cannot infer.',
    'top-left',
  );
  await page.locator('#ai-feasibility-intent').fill(INTENT);
  await delay(3600);
  const outcome = page.locator('#ai-feasibility-outcome');
  await spotlight(
    page,
    outcome,
    '5',
    'Define a measurable business outcome',
    'Targets make the future proof of concept testable: effort, cycle time, accuracy, controls, and auditability.',
    'top-left',
  );
  await outcome.fill(OUTCOME);
  await delay(3800);
  const consent = page.locator('#ai-feasibility-consent').locator('xpath=..');
  await spotlight(
    page,
    consent,
    '5',
    'Confirm the processing boundary',
    'The customer explicitly approves the minimized context sent to the configured Foundry model.',
    'top-left',
  );
  await page.locator('#ai-feasibility-consent').check({ force: true });
  await delay(2600);
  return closeAndSave(sceneId, context, page);
}

async function sceneSix() {
  const sceneId = 'live_06_decision_pack';
  const { context, page } = await startContext('6 · Evidence-backed decision pack');
  await page.evaluate(async () => {
    bootstrap.Tab.getOrCreateInstance(document.getElementById('tab-decide')).show();
    showDecideSub('decide-discovery');
    bootstrap.Tab.getOrCreateInstance(document.getElementById('subtab-assessment')).show();
    await window.openAIFeasibilityAssessment();
  });
  await page.locator('#ai-feasibility-workspace').waitFor({ state: 'visible' });
  const option = page.locator('#ai-feasibility-application option').filter({ hasText: 'BPTco' });
  const appId = await option.getAttribute('value');
  await page.locator('#ai-feasibility-application').selectOption(appId);
  await page.locator('[data-category-id="document_processing_enrichment"]').click();
  await page.locator('#ai-feasibility-intent').fill(INTENT);
  await page.locator('#ai-feasibility-outcome').fill(OUTCOME);
  await page.locator('#ai-feasibility-consent').check({ force: true });
  await page.locator('#ai-feasibility-generate').scrollIntoViewIfNeeded();
  await delay(800);
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/ai-feasibility/assessments') && response.request().method() === 'POST',
    { timeout: 120000 },
  );
  await page.locator('#ai-feasibility-generate').click();
  const response = await responsePromise;
  const assessment = await response.json();
  manifest.assessment_id = assessment.id;
  await page.locator('.ai-assessment-banner').waitFor({ state: 'visible', timeout: 120000 });
  await spotlight(
    page,
    page.locator('.ai-assessment-banner'),
    '6',
    'Review the feasibility decision',
    'The executive summary links the application, customer outcome, disposition, and assessment revision.',
  );
  await delay(4300);
  await spotlight(
    page,
    page.locator('.ai-dimension-grid'),
    '6',
    'Inspect six decision dimensions',
    'Business, data, integration, governance, operations, and economics remain independently explainable.',
  );
  await delay(4200);
  await spotlight(
    page,
    page.locator('.ai-service-list').first(),
    '6',
    'Review proposed Azure AI services',
    'Every service has a workflow role and remains explicitly proposed until validated.',
  );
  await delay(4100);
  await spotlight(
    page,
    page.locator('.card-dark').filter({ hasText: 'Indicative incremental AI cost' }),
    '6',
    'Compare indicative cost scenarios',
    'Low, base, and high ranges expose usage assumptions and the planning reserve.',
  );
  await delay(4300);
  const poc = page.locator('.card-dark').filter({ hasText: 'Bounded PoC acceptance plan' });
  await spotlight(
    page,
    poc,
    '6',
    'Define the proof-of-concept gates',
    'The recommendation becomes actionable only with owners, evaluation tests, fallback, and production gates.',
  );
  await delay(4200);
  return closeAndSave(sceneId, context, page);
}

async function sceneSeven() {
  const sceneId = 'live_07_ai_ready_architecture';
  const { context, page } = await startContext('7 · AI-ready architecture');
  await page.locator('#tab-plan').click();
  await delay(550);
  await page.locator('#plan-landing-zone-tab').click();
  await delay(550);
  await page.locator('#landing-zone-ai-feasibility').check({ force: true });
  await spotlight(
    page,
    page.locator('.ai-lz-toggle-wrap'),
    '7',
    'Enable the AI-ready variant',
    'The landing zone will use the exact assessment revision created for BPTco.',
    'top-left',
  );
  await delay(2300);
  await clearGuidance(page);
  if (manifest.assessment_id) {
    await page.locator('#landing-zone-ai-feasibility').evaluate((element, assessmentId) => {
      element.dataset.assessmentId = assessmentId;
    }, manifest.assessment_id);
  }
  const responsePromise = page.waitForResponse((response) => response.url().includes('/api/landing-zones') && response.url().includes('include_ai=true'));
  await page.locator('#landing-zone-generate-btn').click();
  await responsePromise;
  const viewButton = page.locator('.landing-zone-card').filter({ hasText: 'BPTco' }).getByRole('button', { name: 'View Architecture' });
  await viewButton.click();
  await page.locator('#landing-zone-canvas svg').waitFor({ state: 'visible' });
  await spotlight(
    page,
    page.locator('#landing-zone-canvas'),
    '7',
    'See where AI fits',
    'The purple tier is the proposed Document Processing and Enrichment capability extension.',
    'top-right',
  );
  await delay(5600);
  const reasoning = page.locator('#landing-zone-reasoning');
  await spotlight(
    page,
    reasoning,
    '7',
    'Keep the design traceable',
    'Architecture reasoning links the AI extension back to the versioned assessment and its evidence gates.',
    'top-left',
  );
  await delay(3600);
  return closeAndSave(sceneId, context, page);
}

async function main() {
  const status = await fetch(`${baseUrl}/api/status`).then((response) => response.json());
  if (!status.data_loaded) throw new Error('The simulator does not have discovery data loaded.');
  await sceneTwo();
  await sceneThree();
  await sceneFour();
  await sceneFive();
  await sceneSix();
  await sceneSeven();
  fs.writeFileSync(path.join(outputDir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
