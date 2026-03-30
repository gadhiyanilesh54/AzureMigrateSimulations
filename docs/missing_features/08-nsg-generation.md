# Feature Spec: NSG Rules from Dependencies

**ID**: 08-nsg-generation  
**Phase**: PLAN  
**Priority**: Tier 2 — Medium Impact  
**Status**: Not Started  
**Depends On**: Guest Workload Discovery (✅), Cloud Topology (✅)

## Problem Statement

The CTD places VMs into subnets, but no Network Security Group (NSG) rules are generated. Customers must manually create NSG rules for every dependency — a tedious and error-prone process for 200+ VMs with dozens of inter-VM connections.

## Goal

Auto-generate Azure NSG rules from discovered TCP dependencies, applying least-privilege network access (allow only the ports actually in use).

## User Stories

### US-1: Auto-Generate NSG Allow Rules (P1)
**Given** TCP dependencies (VM-A port 3306 → VM-B), **When** NSG rules are generated, **Then** an allow rule is created: source subnet → dest subnet, TCP/3306, Allow.

### US-2: Default Deny (P1)
**Given** generated NSG rules, **Then** a `DenyAllInbound` rule is appended at lowest priority.

### US-3: Common Service Rules (P2)
Auto-add rules for common Azure services:
- Allow Azure Load Balancer health probes (source: AzureLoadBalancer)
- Allow Azure Bastion (if enabled in CTD)
- Allow outbound to Azure Monitor, Key Vault, Storage (service tags)

### US-4: Export as Part of IaC (P1)
Generated NSG rules are included in Terraform/Bicep output (spec 01).

### US-5: MCP Tool (P1)
Tool: `generate_nsg_rules` returns all rules per subnet.

## Functional Requirements

- **FR-001**: Map each TCP dependency to a source/dest subnet pair.
- **FR-002**: Generate inbound allow rules per destination subnet.
- **FR-003**: De-duplicate rules (multiple VMs on same subnet → one rule).
- **FR-004**: Add default deny rule at priority 4096.
- **FR-005**: Add common Azure service tag rules .
- **FR-006**: REST endpoint: `GET /api/nsg-rules`.
- **FR-007**: Include in IaC generation output.
