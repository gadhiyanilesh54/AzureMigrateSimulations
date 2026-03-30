# Missing Features — Spec Index

Detailed specifications for features needed to complete the end-to-end migration journey.
Each spec is designed to be consumed by **speckit** (`speckit.specify` → `speckit.plan` → `speckit.tasks` → `speckit.implement`).

## Priority & Phase Matrix

### Tier 1: High Impact — Data Already Exists (Build Now)

| # | Spec | Phase | Status |
|---|------|-------|--------|
| 01 | [Terraform/Bicep Generation](./01-iac-generation.md) | PLAN | Not Started |
| 02 | [Dependency-Aware Wave Planning](./02-dependency-wave-planning.md) | PLAN | Not Started |
| 03 | [Side-by-Side Pricing Comparison](./03-pricing-comparison.md) | DECIDE | Not Started |
| 04 | [Application Grouping](./04-application-grouping.md) | DECIDE | Not Started |
| 05 | [Pre-Migration Validation Runbooks](./05-pre-migration-runbooks.md) | MIGRATE | Not Started |
| 06 | [Executive Report Export](./06-executive-report.md) | DECIDE | Not Started |

### Tier 2: Medium Impact — Moderate Effort

| # | Spec | Phase | Status |
|---|------|-------|--------|
| 07 | [Migration Status Tracker](./07-migration-tracker.md) | MIGRATE | Not Started |
| 08 | [NSG Rules from Dependencies](./08-nsg-generation.md) | PLAN | Not Started |
| 09 | [Tagging Strategy](./09-tagging-strategy.md) | PLAN | Not Started |
| 10 | [Docker Packaging](./10-docker-packaging.md) | PLATFORM | Not Started |
| 11 | [RVTools CSV Import](./11-rvtools-import.md) | DECIDE | Not Started |
| 12 | [Multi-Project Support](./12-multi-project.md) | PLATFORM | Not Started |

### Tier 3: Strategic — Longer Term

| # | Spec | Phase | Status |
|---|------|-------|--------|
| 13 | [Compliance Assessment](./13-compliance-assessment.md) | DECIDE | Not Started |
| 14 | [Post-Migration Validation](./14-post-migration-validation.md) | MIGRATE | Not Started |
| 15 | [Project Versioning & Snapshots](./15-project-versioning.md) | PLATFORM | Not Started |
| 16 | [Cost Optimization Engine](./16-cost-optimization.md) | PLAN | Not Started |

## Usage with Speckit

```bash
# 1. Review/refine a spec
speckit.specify "Read docs/missing_features/01-iac-generation.md and refine it"

# 2. Generate implementation plan
speckit.plan "Create plan for docs/missing_features/01-iac-generation.md"

# 3. Generate tasks
speckit.tasks "Generate tasks from docs/missing_features/01-iac-generation.md"

# 4. Implement
speckit.implement "Execute tasks for IaC generation feature"
```
