# Feature Spec: Compliance Assessment

**ID**: 13-compliance-assessment  
**Phase**: DECIDE  
**Priority**: Tier 3 — Strategic  
**Status**: Not Started  
**Depends On**: Assessment (✅), Vulnerability/SLA (✅)

## Problem Statement

Regulated industries (banking, healthcare, government, defence) cannot approve a migration without verifying compliance requirements. The assessment currently checks OS lifecycle and AHUB eligibility but has no knowledge of PCI-DSS, HIPAA, SOX, GDPR, or FedRAMP requirements.

## Goal

Add a compliance assessment layer that evaluates the proposed Azure architecture against common regulatory frameworks and flags gaps.

## User Stories

### US-1: Framework Selection (P1)
**Given** the compliance module, **When** the user selects one or more frameworks (PCI-DSS, HIPAA, SOX, GDPR, ISO 27001, FedRAMP), **Then** the assessment applies that framework's checks.

### US-2: Gap Analysis (P1)
**Given** a selected framework, **When** compliance is assessed, **Then** checks include:

| Framework | Checks |
|-----------|--------|
| **PCI-DSS** | Network segmentation (subnets isolate cardholder data), encryption at rest/transit, access logging, WAF presence |
| **HIPAA** | PHI data classification, encryption, audit logging, BAA requirement, backup policy |
| **SOX** | Change management controls, access controls, audit trail, data retention |
| **GDPR** | Data residency (EU region), data classification, consent tracking, right to erasure |
| **ISO 27001** | Risk assessment, access control, incident management, business continuity |

### US-3: Compliance Report (P2)
**Given** compliance gaps, **When** reported, **Then** each gap has: control ID, description, current status (Pass/Fail/N/A), remediation recommendation, Azure service to address it.

### US-4: MCP Tool (P1)
Tool: `assess_compliance` with `frameworks` parameter.

## Functional Requirements

- **FR-001**: Define compliance rules as a data structure (not hardcoded logic).
- **FR-002**: Evaluate CTD architecture against selected frameworks.
- **FR-003**: Check: region (data residency), encryption (disk type), network segmentation (subnets), monitoring (enrichment presence), backup (not yet tracked).
- **FR-004**: Generate pass/fail per control with remediation.
- **FR-005**: REST endpoint: `POST /api/compliance/assess`.
- **FR-006**: MCP tool: `assess_compliance`.
- **FR-007**: Include in executive report (spec 06).

## Acceptance Criteria

1. At least 5 frameworks supported, each with ≥10 checks.
2. Checks use data already in discovery/CTD (no new data sources needed for v1).
3. Clear pass/fail per control with remediation guidance.
