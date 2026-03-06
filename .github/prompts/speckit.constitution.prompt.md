---
agent: speckit.constitution
---
# Web Application Development Constitution

This constitution defines the non-negotiable principles, constraints, and quality standards that govern all code, design, and architectural decisions in this project. Every contribution—human or AI-generated—must comply.

---

## 1. Clean Code

- **Readability over cleverness.** Code is read far more often than it is written. Prefer explicit, self-documenting names and straightforward control flow over terse or "clever" constructs.
- **Single Responsibility.** Every module, class, and function must do one thing well. If a function needs a conjunction ("and", "or") to describe its purpose, split it.
- **Small functions.** Functions should rarely exceed 20–30 lines. Extract helper functions rather than nesting logic.
- **Consistent style.** Follow the project's linter and formatter configuration without exception. Style debates are settled by tooling, not opinion.
- **No dead code.** Remove unused imports, commented-out blocks, and unreachable branches. Version control is the archive.
- **Meaningful abstractions.** Don't Repeat Yourself (DRY), but don't abstract prematurely. Duplicate code twice before extracting; three occurrences justify a shared utility.
- **Explicit error handling.** Never swallow exceptions silently. Log or surface every failure with enough context to diagnose it.
- **Type safety.** Use type annotations (Python type hints, TypeScript types) everywhere. Avoid `Any` / `any` unless absolutely necessary and documented.

---

## 2. Simple UX

- **Progressive disclosure.** Show only what the user needs at each step. Advanced options belong behind an expandable section, not on the primary surface.
- **Minimal interaction cost.** Reduce clicks, form fields, and navigation hops. Sensible defaults eliminate unnecessary decisions.
- **Immediate feedback.** Every user action must produce visible acknowledgment within 100 ms—loading spinners, optimistic UI updates, or inline validation.
- **Clear error states.** Errors must be human-readable, actionable, and displayed in context (next to the offending field, not in a generic toast).
- **Consistent patterns.** Reuse the same interaction patterns (buttons, modals, navigation) throughout the application. Users should never have to re-learn the UI.
- **Empty states & onboarding.** Every view must have a helpful empty state that guides the user toward their first action.
- **No jargon.** Labels, messages, and tooltips use plain language. Technical identifiers belong in developer tools, not the UI.

---

## 3. Responsive Design

- **Mobile-first.** Base styles target the smallest supported viewport. Larger breakpoints add complexity, not the other way around.
- **Fluid layouts.** Use relative units (`rem`, `%`, `vw/vh`, `fr`) and CSS Grid / Flexbox. Avoid fixed pixel widths for layout containers.
- **Breakpoint discipline.** Define a small, explicit set of breakpoints (e.g., `sm`, `md`, `lg`, `xl`). Never add one-off media queries for cosmetic fixes.
- **Touch-friendly targets.** Interactive elements must have a minimum tap area of 44 × 44 CSS pixels (WCAG 2.5.8).
- **Responsive images & media.** Serve appropriately sized assets. Use `srcset`, `<picture>`, or CSS `image-set()` where applicable.
- **Test on real devices.** Emulators supplement but do not replace testing on physical phones and tablets.

---

## 4. Minimal Dependencies

- **Justify every dependency.** Before adding a package, document: (a) what problem it solves, (b) why a built-in or small custom solution is insufficient, (c) its maintenance health (last release, open issues, bus factor).
- **Prefer the platform.** Use browser APIs, standard library modules, and language built-ins before reaching for a package.
- **Pin versions.** All dependencies must be pinned to exact versions or narrow ranges in lock files. Automated dependency update PRs (Dependabot, Renovate) must pass CI before merge.
- **Audit regularly.** Run `pip audit` / `npm audit` (or equivalent) in CI. Vulnerabilities with a known fix must be resolved within one sprint.
- **Bundle size budget.** For front-end assets, enforce a maximum bundle size. Every new dependency that increases the budget must be approved explicitly.
- **No kitchen-sink frameworks unless justified.** Prefer lightweight, composable libraries over monolithic frameworks when the project scope allows it.

---

## 5. Testing

### 5.1 Unit Tests

- **Mandatory for all business logic.** Every pure function, utility, model method, and state transformation must have unit tests.
- **Arrange-Act-Assert.** Tests follow a clear setup → execute → verify structure. One logical assertion per test.
- **Fast & isolated.** Unit tests must not touch the network, file system, or database. Use mocks, fakes, or in-memory substitutes.
- **Descriptive names.** Test names describe the scenario and expected outcome: `test_price_calculation_applies_discount_when_coupon_valid`.
- **Coverage floor.** Maintain a minimum of 80 % line coverage. Critical paths (auth, payments, data mutations) require 100 % branch coverage.

### 5.2 Integration Tests

- **Verify boundaries.** Integration tests exercise real interactions between components: API endpoints ↔ database, front-end ↔ back-end, service ↔ external API.
- **Deterministic fixtures.** Use factories, seeders, or containerized services (e.g., test databases) to guarantee repeatable state.
- **Run in CI.** Integration tests execute on every pull request. Flaky tests are treated as bugs and fixed or quarantined immediately.
- **Contract tests for APIs.** Public and internal APIs must have contract or schema tests that fail when the response shape changes unexpectedly.

### 5.3 End-to-End Tests

- **Cover critical user journeys.** E2E tests validate the highest-value workflows (sign-up, core task completion, checkout) through a real browser.
- **Keep the suite small.** E2E tests are slow and brittle. Prefer pushing coverage down to unit and integration layers.

---

## 6. Accessibility (a11y)

- **WCAG 2.2 AA compliance** is the minimum standard. Strive for AAA where feasible.
- **Semantic HTML first.** Use `<button>`, `<nav>`, `<main>`, `<table>`, `<label>`, etc., before reaching for ARIA attributes. ARIA is a repair tool, not a substitute for correct markup.
- **Keyboard navigable.** Every interactive element must be reachable and operable via keyboard alone. Visible focus indicators are required—never remove `outline` without a visible replacement.
- **Color is not the only channel.** Information conveyed through color must also be conveyed through text, icons, or patterns. Maintain a minimum contrast ratio of 4.5:1 for normal text, 3:1 for large text.
- **Alt text & labels.** Every `<img>` has a meaningful `alt` (or `alt=""` for decorative images). Every form input has an associated `<label>`.
- **Announce dynamic changes.** Use ARIA live regions (`aria-live`, `role="status"`, `role="alert"`) to surface content updates to screen readers.
- **Automated + manual audits.** Run axe-core or Lighthouse accessibility checks in CI. Supplement with periodic manual testing using a screen reader (NVDA, VoiceOver).

---

## 7. Performance

- **Perceived speed matters most.** Optimize First Contentful Paint (FCP) and Largest Contentful Paint (LCP). Target LCP < 2.5 s.
- **Lazy load non-critical resources.** Defer off-screen images, heavy scripts, and below-the-fold components.
- **Minimize network requests.** Bundle, compress (`gzip`/`brotli`), and cache aggressively. Use HTTP `Cache-Control` headers intentionally.
- **No layout shifts.** Reserve space for async content (images, ads, embeds). Target Cumulative Layout Shift (CLS) < 0.1.
- **Profile before optimizing.** Use browser dev tools and server-side profiling to identify real bottlenecks. Never optimize on intuition alone.

---

## 8. Security

- **Never trust client input.** Validate and sanitize all user-supplied data on the server side, regardless of client-side validation.
- **Parameterized queries only.** No string-concatenated SQL or NoSQL queries—ever.
- **Authentication & authorization by default.** Every endpoint and view is protected unless explicitly marked public with a documented reason.
- **Secrets out of code.** API keys, tokens, and credentials live in environment variables or a secrets manager—never in source control.
- **HTTPS everywhere.** All traffic is encrypted in transit. Redirect HTTP to HTTPS. Set `Strict-Transport-Security` headers.
- **Content Security Policy.** Define and enforce a CSP that blocks inline scripts and restricts resource origins.
- **Dependency scanning.** Vulnerable dependencies fail the CI pipeline.

---

## 9. Architecture & Code Organization

- **Separation of concerns.** Presentation, business logic, and data access occupy distinct layers with clear interfaces.
- **Convention over configuration.** Follow established project directory structure and naming conventions. New contributors should be productive within an hour.
- **API-first design.** Back-end functionality is exposed through well-documented, versioned APIs before building UI on top.
- **Stateless services.** Application servers must not rely on local state. Session and cache data live in external stores.
- **Configuration via environment.** All environment-specific values (URLs, feature flags, credentials) are injected through environment variables—never hard-coded.

---

## 10. Documentation

- **README as entry point.** The README must contain: project purpose, prerequisites, setup instructions, how to run tests, and how to deploy.
- **Inline comments explain _why_, not _what_.** The code shows what happens; comments explain non-obvious reasoning.
- **API documentation.** All public APIs are documented with request/response schemas, error codes, and examples (OpenAPI / Swagger preferred).
- **Architecture Decision Records (ADRs).** Significant architectural choices are recorded with context, options considered, and rationale.
- **Keep docs in sync.** Documentation updates ship in the same PR as the code change they describe.

---

## 11. CI / CD & DevOps

- **Every PR goes through CI.** Linting, type checking, unit tests, integration tests, and accessibility audits run automatically.
- **Trunk-based development.** Short-lived feature branches merge into `main` frequently. Long-lived branches are prohibited.
- **Automated deployments.** Merges to `main` trigger automated deployment to staging. Production deploys require a single manual approval gate.
- **Rollback plan.** Every deployment must be reversible within minutes—blue/green, canary, or feature flags.
- **Observability.** Applications emit structured logs, metrics, and traces. Alerts fire on error rate spikes and latency degradation.

---

## Enforcement

- **Automated gates** (linters, formatters, test suites, accessibility scanners, bundle-size checks) enforce these principles in CI. A red pipeline blocks merge—no exceptions.
- **Code review** validates architectural alignment, UX consistency, and adherence to this constitution.
- **This document is living.** Propose amendments via pull request. Changes require team review and approval before merge.