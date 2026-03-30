# Feature Spec: RVTools CSV/XLSX Import

**ID**: 11-rvtools-import  
**Phase**: DECIDE  
**Priority**: Tier 2 — Medium Impact  
**Status**: Not Started  
**Depends On**: Models (✅), Azure Mapping (✅)

## Problem Statement

Many customers already have **RVTools** exports (the most popular VMware inventory tool). Currently, the only import options are live vCenter connection or the project's own JSON format. Supporting RVTools import would eliminate the need for vCenter credentials in many engagements — a consultant just needs the customer's existing RVTools export.

## Goal

Import RVTools `.xlsx` or `.csv` exports and convert them into the project's discovery data format, enabling the full assessment pipeline without vCenter access.

## User Stories

### US-1: RVTools XLSX Import (P1)
**Given** an RVTools Excel export, **When** uploaded via the web UI or API, **Then** the `vInfo`, `vCPU`, `vMemory`, `vDisk`, `vNetwork`, `vHost` sheets are parsed and converted to discovery data.

### US-2: RVTools CSV Import (P1)
**Given** individual RVTools CSV exports (vInfo.csv, vCPU.csv, etc.), **When** uploaded, **Then** they are merged and converted.

### US-3: Field Mapping (P1)
| RVTools Field | Maps To |
|---------------|---------|
| VM | `name` |
| Powerstate | `power_state` |
| CPUs | `num_cpus` |
| Memory (MB) | `memory_mb` |
| Provisioned (MB) | `total_disk_gb` |
| OS according to the configuration file | `guest_os` |
| Datacenter | `datacenter` |
| Cluster | `cluster` |
| Host | `host` |
| Folder | `folder` |
| Network #1-4 | `nics[]` |
| Disk #1-N | `disks[]` |

### US-4: MCP Tool (P1)
Tool: `import_rvtools` accepts file path and triggers import.

## Functional Requirements

- **FR-001**: Parse RVTools `.xlsx` (openpyxl — optional dependency, not added to core).
- **FR-002**: Parse RVTools `.csv` files.
- **FR-003**: Map RVTools fields to `DiscoveredVM` schema.
- **FR-004**: Trigger Azure mapping after import (generate recommendations).
- **FR-005**: REST endpoint: `POST /api/import/rvtools`.
- **FR-006**: MCP tool: `import_rvtools`.
- **FR-007**: Handle missing fields gracefully (e.g., no IOPS data → skip perf-based sizing).

## Acceptance Criteria

1. RVTools export with 500 VMs imports in <10 seconds.
2. All VMs from `vInfo` sheet appear in discovery data.
3. Assessment pipeline runs successfully on imported data.
4. Missing fields (no IOPS, no network) don't cause errors.
