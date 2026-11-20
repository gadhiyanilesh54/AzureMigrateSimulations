# CLI Contract: dt-migrate risk

**Entry point**: `dt-migrate` (argparse subparser group `risk`)

## Commands

### dt-migrate risk heatmap

Compute and display the fleet-wide risk heatmap.

```
dt-migrate risk heatmap [--top N] [--format json|table] [--band green|yellow|red]
```

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--top` | int | No | 10 | Limit output to top-N riskiest VMs |
| `--format` | str | No | `table` | Output format: `json` (stdout) or `table` (Rich-formatted) |
| `--band` | str | No | (all) | Filter by risk band |

**Exit codes**:
- `0`: Success
- `1`: No discovery data available
- `2`: Invalid arguments

**JSON output** (stdout, `--format json`): Same schema as `GET /api/risk/heatmap` response.

**Table output** (stdout, `--format table`): Rich-formatted table with colored cells.

```
┌──────────────────┬──────┬────────┬────────┬────────┬──────┬──────┬───────────┐
│ VM Name          │ Deps │ OS EOL │ Wkload │ Perf   │ Comp │ Data │ Composite │
├──────────────────┼──────┼────────┼────────┼────────┼──────┼──────┼───────────┤
│ SQL-PROD-01      │  85  │  100   │   95   │  100   │  80  │  24  │    78     │
│ ORACLE-DB-03     │  60  │  100   │   90   │   45   │  80  │  65  │    76     │
│ ...              │      │        │        │        │      │      │           │
└──────────────────┴──────┴────────┴────────┴────────┴──────┴──────┴───────────┘
```

---

### dt-migrate risk score \<vm_name\>

Compute and display the risk score for a single VM.

```
dt-migrate risk score <vm_name> [--format json|table]
```

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `vm_name` | str | Yes | — | VM name (positional argument) |
| `--format` | str | No | `table` | Output format: `json` or `table` |

**Exit codes**:
- `0`: Success
- `1`: VM not found
- `2`: No discovery data available

**JSON output**: Same schema as `GET /api/risk/score/<vm_name>` response.

**Table output**: Rich panel with risk breakdown.

```
╭─── Risk Score: SQL-PROD-01 ─── Composite: 78 (RED) ───╮
│                                                         │
│  Factor                   Raw Value        Score  Band  │
│  ─────────────────────────────────────────────────────  │
│  Dependency Count         12 deps            85   RED   │
│  OS EOL                   EOL 2024-01-09    100   RED   │
│  Workload Complexity      MSSQL Ent (350G)   95   RED   │
│  Performance Sensitivity  P95 IOPS: 2400    100   RED   │
│  Compliance Scope         PCI-DSS, HIPAA     80   RED   │
│  Data Volume              480 GB             24   GREEN │
│                                                         │
│  Mitigations:                                           │
│  • [OS EOL] Upgrade OS to supported version or use ESU  │
│  • [Workload] Plan phased migration: DB to PaaS first   │
╰─────────────────────────────────────────────────────────╯
```
