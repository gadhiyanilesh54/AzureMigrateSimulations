# Feature Spec: Executive Report Export

**ID**: 06-executive-report  
**Phase**: DECIDE  
**Priority**: Tier 1 — High Impact  
**Status**: Not Started  
**Depends On**: Assessment (✅), Business Case (✅), CTD (✅), WAF (✅)

## Problem Statement

Migration architects need to present findings to steering committees and CxOs. Currently, they must manually compile data from the web dashboard into PowerPoint slides or Word documents. There is no one-click export that produces a boardroom-ready migration report.

## Goal

Generate a comprehensive **executive migration report** as structured JSON (renderable by any frontend) and downloadable **Markdown** that includes: estate summary, readiness analysis, business case, architecture diagram, wave plan, risk matrix, and strategic recommendations.

## User Stories

### US-1: One-Click Executive Report (P1)
**Given** completed assessment data (discovery + recommendations + business case + CTD), **When** the user clicks "Generate Executive Report", **Then** a structured report is generated containing all sections.

### US-2: Report Sections (P1)
The report must include:
1. **Executive Summary**: VM count, readiness %, estimated cost, payback period — in 3 sentences
2. **Estate Overview**: Discovered infrastructure (VMs, hosts, networks, datastores) with charts
3. **Migration Readiness**: Ready vs Conditions vs Not Ready breakdown with top blockers
4. **Business Case**: On-prem TCO vs Azure, monthly/annual/3yr savings, ROI
5. **Target Architecture**: CTD summary with landing zones, WAF scores, cost per LZ
6. **Wave Plan**: Migration waves with timeline, VMs per wave, cost ramp-up
7. **Risk Matrix**: Top risks identified (EOL OS, unsupported workloads, missing enrichment)
8. **Recommendations**: Strategic next steps (run enrichment, address blockers, commit to RI)
9. **Appendix**: Full VM assessment table, workload mapping table

### US-3: Markdown Export (P2)
**Given** the report, **When** exported as Markdown, **Then** it's renderable in GitHub, Notion, Confluence, or any Markdown viewer with embedded Mermaid diagrams.

### US-4: MCP Tool (P1)
**Given** the MCP server, **When** an agent calls `generate_executive_report`, **Then** the full report is returned as structured JSON that the agent can summarise or present section-by-section.

## Functional Requirements

- **FR-001**: Aggregate data from discovery, assessment, business case, CTD, wave plan, and vulnerability analysis.
- **FR-002**: Generate executive summary text automatically (3-sentence condensation).
- **FR-003**: Include risk matrix with severity ratings derived from readiness, EOL status, and enrichment gaps.
- **FR-004**: Include Mermaid diagram (from CTD) in Markdown export.
- **FR-005**: Add REST endpoint: `GET /api/reports/executive`.
- **FR-006**: Add MCP tool: `generate_executive_report`.
- **FR-007**: Add web UI button for report download.

## Acceptance Criteria

1. Report includes all 9 sections listed above.
2. Executive summary is ≤3 sentences and factually accurate.
3. Business case numbers match the business case API output.
4. Risk matrix correctly identifies EOL operating systems and low-confidence VMs.
5. Markdown export renders correctly in GitHub.
6. Report generates in <5 seconds for 202 VMs.
