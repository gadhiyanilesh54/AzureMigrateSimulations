"""Grounded conversational experience for Azure Migrate Simulations.

The local engine answers migration questions exclusively from the currently
loaded discovery, assessment, pricing, workload, performance, and planning
records. A configured Microsoft Foundry model generates the final natural-language
answer from that evidence-constrained draft and recent persisted conversation
context. Local grounded output remains a resilience fallback when inference is
temporarily unavailable.
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)

MAX_CHAT_MESSAGE_LENGTH = 2_000
MAX_CHAT_HISTORY_ITEMS = 12

_STOP_WORDS = {
    "a", "about", "all", "an", "and", "are", "as", "at", "be", "by",
    "can", "could", "did", "do", "does", "for", "from", "give", "how",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "our", "please",
    "show", "tell", "that", "the", "this", "to", "us", "was", "what",
    "which", "why", "with", "would", "you",
}


def _money(value: Any) -> str:
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _number(value: Any, digits: int = 0) -> str:
    try:
        return f"{float(value or 0):,.{digits}f}"
    except (TypeError, ValueError):
        return "0"


def _citation(title: str, source: str, route: str, entity: str = "") -> dict[str, str]:
    result = {"title": title, "source": source, "route": route}
    if entity:
        result["entity"] = entity
    return result


def _action(label: str, target: str, action_type: str = "navigate", entity: str = "") -> dict[str, str]:
    result = {"label": label, "type": action_type, "target": target}
    if entity:
        result["entity"] = entity
    return result


def _normalise_readiness(value: str) -> str:
    return (value or "Unknown").strip().lower().replace("_", " ")


class MigrationChatEngine:
    """Answer migration questions from structured simulator evidence."""

    def classify_intent(self, message: str) -> str:
        text = message.casefold()
        if any(term in text for term in (
            "ai feasibility", "ai opportunity", "use ai", "leverage ai",
            "ai solution", "automate with ai", "automation using ai",
        )):
            return "ai_feasibility"
        if any(term in text for term in ("landing zone", "architecture", "topology", "target design")):
            return "landing_zone"
        if any(term in text for term in ("business case", "roi", "payback", "tco", "return on investment")):
            return "business_case"
        if any(term in text for term in ("application group", "app group", "applications grouped", "grouped application")):
            return "applications"
        if "why" in text and any(term in text for term in ("target", "service", "app service", "sql", "aks", "container")):
            return "service_explain"
        if any(term in text for term in ("cost", "price", "pricing", "expensive", "savings", "how much")):
            return "cost_explain"
        if any(term in text for term in ("not ready", "readiness", "migration issue", "blocker", "conditional")):
            return "readiness"
        if any(term in text for term in ("eol", "end of life", "vulnerab", "unsupported os", "security risk", "esu")):
            return "vulnerability"
        if any(term in text for term in ("performance", "cpu", "memory usage", "iops", "utilization", "utilisation")):
            return "performance"
        if any(term in text for term in ("database", "web app", "webapp", "container", "orchestrator", "workload")):
            return "workloads"
        if any(term in text for term in ("inventory", "discover", "how many", "list vm", "list host", "network", "datastore", "file share")):
            return "inventory"
        if any(term in text for term in ("override", "what-if", "what if", "saved preference")):
            return "overrides"
        if any(term in text for term in ("summary", "summarize", "summarise", "overview", "estate", "environment", "where should i start")):
            return "summary"
        if any(term in text for term in ("help", "what can you", "suggest question", "capabilities")):
            return "help"
        return "search"

    def answer(
        self,
        message: str,
        discovery: dict[str, Any],
        workload_data: dict[str, Any] | None = None,
        enrichment_data: dict[str, Any] | None = None,
        perf_history: dict[str, Any] | None = None,
        whatif_overrides: dict[str, Any] | None = None,
        *,
        business_case: dict[str, Any] | None = None,
        applications: list[dict[str, Any]] | None = None,
        landing_zones: dict[str, Any] | None = None,
        vulnerability: dict[str, Any] | None = None,
        performance_summary: dict[str, Any] | None = None,
        ai_feasibility_context: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Return a grounded chat response and its evidence references."""
        clean_message = " ".join(message.strip().split())
        if not clean_message:
            raise ValueError("Message is required.")
        if len(clean_message) > MAX_CHAT_MESSAGE_LENGTH:
            raise ValueError(
                f"Message must be {MAX_CHAT_MESSAGE_LENGTH:,} characters or fewer."
            )
        if not discovery or not discovery.get("vms"):
            return self._response(
                "Connect to vCenter or load a discovery report first. Once inventory is loaded, I can explain assessments, costs, target services, application groups, landing zones, and the business case.",
                "no_data",
                [],
                [_action("Start a new connection", "connect")],
                ["What can I ask?"],
            )

        workloads = workload_data or {}
        intent = self.classify_intent(clean_message)
        if (
            intent == "search"
            and (ai_feasibility_context or {}).get("stage")
            in {"select_application", "select_category", "describe_intent"}
        ):
            intent = "ai_feasibility"
        vm = self._find_vm(clean_message, discovery.get("vms", []))
        if vm is None:
            for historical_message in reversed((history or [])[-MAX_CHAT_HISTORY_ITEMS:]):
                vm = self._find_vm(
                    str(historical_message.get("content", "")),
                    discovery.get("vms", []),
                )
                if vm is not None:
                    break

        if intent == "ai_feasibility":
            return self._ai_feasibility(
                clean_message,
                ai_feasibility_context or {},
            )

        handlers = {
            "summary": lambda: self._summary(discovery, workloads, enrichment_data or {}),
            "inventory": lambda: self._inventory(clean_message, discovery, workloads),
            "readiness": lambda: self._readiness(discovery, vm),
            "cost_explain": lambda: self._cost(clean_message, discovery, vm),
            "service_explain": lambda: self._service_explain(clean_message, workloads),
            "workloads": lambda: self._workloads(clean_message, workloads),
            "landing_zone": lambda: self._landing_zones(landing_zones),
            "business_case": lambda: self._business_case(business_case),
            "applications": lambda: self._applications(applications or []),
            "vulnerability": lambda: self._vulnerability(vulnerability),
            "performance": lambda: self._performance(performance_summary, perf_history or {}),
            "overrides": lambda: self._overrides(whatif_overrides or {}),
            "help": self._help,
            "search": lambda: self._search(clean_message, discovery, workloads),
        }
        answer, citations, actions, suggestions = handlers[intent]()
        return self._response(answer, intent, citations, actions, suggestions)

    def _response(
        self,
        answer: str,
        intent: str,
        citations: list[dict[str, str]],
        actions: list[dict[str, str]],
        suggestions: list[str],
    ) -> dict[str, Any]:
        return {
            "id": f"chat-{uuid4().hex[:12]}",
            "role": "assistant",
            "answer": answer,
            "intent": intent,
            "provider": "local-grounded",
            "citations": citations,
            "actions": actions,
            "suggestions": suggestions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _summary(
        self,
        discovery: dict[str, Any],
        workloads: dict[str, Any],
        enrichment: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        vms = discovery.get("vms", [])
        recs = discovery.get("recommendations", [])
        readiness = Counter(_normalise_readiness(r.get("migration_readiness", "")) for r in recs)
        total_cost = sum(r.get("estimated_monthly_cost_usd", 0) or 0 for r in recs)
        workload_recs = workloads.get("recommendations", [])
        workload_counts = Counter(r.get("workload_type", "unknown") for r in workload_recs)
        text = (
            f"The current discovery contains {len(vms):,} VMs across {len(discovery.get('hosts', [])):,} hosts, "
            f"{len(discovery.get('networks', [])):,} networks, and {len(discovery.get('datastores', [])):,} datastores.\n\n"
            f"Assessment: {readiness.get('ready', 0):,} ready, "
            f"{readiness.get('ready with conditions', 0):,} ready with conditions, and "
            f"{readiness.get('not ready', 0):,} not ready. The estimated Azure run rate is "
            f"{_money(total_cost)}/month before scenario changes.\n\n"
            f"Workloads: {workload_counts.get('webapp', 0):,} web app recommendations, "
            f"{workload_counts.get('database', 0):,} database recommendations, "
            f"{workload_counts.get('container', 0):,} container recommendations, and "
            f"{workload_counts.get('orchestrator', 0):,} orchestrator recommendations. "
            f"Telemetry enrichment is available for {len(enrichment):,} entities."
        )
        return (
            text,
            [
                _citation("Discovery inventory", "data/vcenter_discovery.json", "/api/summary"),
                _citation("Workload assessment", "data/workload_discovery.json", "/api/workloads/results"),
            ],
            [_action("Open overview", "overview"), _action("Review assessment", "decide-discovery")],
            ["Explain the total Azure cost", "Which VMs have migration conditions?", "Show application groups"],
        )

    def _inventory(
        self,
        message: str,
        discovery: dict[str, Any],
        workloads: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        text = message.casefold()
        if "host" in text:
            hosts = discovery.get("hosts", [])
            names = ", ".join(h.get("name", "unknown") for h in hosts[:8]) or "none"
            answer = f"Discovered {len(hosts):,} ESXi hosts: {names}."
            route = "/api/hosts"
        elif "network" in text:
            items = discovery.get("networks", [])
            names = ", ".join(n.get("name", "unknown") for n in items[:10]) or "none"
            answer = f"Discovered {len(items):,} vSphere networks or port groups: {names}."
            route = "/api/networks"
        elif any(term in text for term in ("datastore", "file share", "storage")):
            items = discovery.get("datastores", [])
            names = ", ".join(d.get("name", "unknown") for d in items[:10]) or "none"
            capacity = sum(d.get("capacity_gb", 0) or 0 for d in items) / 1024
            answer = f"Discovered {len(items):,} datastores with {_number(capacity, 1)} TB total capacity: {names}."
            route = "/api/fileshares"
        elif any(term in text for term in ("database", "web app", "container", "workload")):
            return self._workloads(message, workloads)
        else:
            vms = discovery.get("vms", [])
            on = sum(v.get("power_state") == "poweredOn" for v in vms)
            windows = sum(v.get("guest_os_family") == "windows" for v in vms)
            linux = sum(v.get("guest_os_family") == "linux" for v in vms)
            names = ", ".join(v.get("name", "unknown") for v in vms[:10])
            answer = (
                f"Discovered {len(vms):,} VMs: {on:,} powered on, {len(vms) - on:,} powered off, "
                f"{windows:,} Windows, and {linux:,} Linux. First records: {names}."
            )
            route = "/api/vms"
        return (
            answer,
            [_citation("Discovery inventory", "data/vcenter_discovery.json", route)],
            [_action("Open inventory", "decide-inventory")],
            ["Summarize the assessment", "List databases", "How many networks were discovered?"],
        )

    def _readiness(
        self,
        discovery: dict[str, Any],
        vm: dict[str, Any] | None,
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        rec_by_vm = {r.get("vm_name", ""): r for r in discovery.get("recommendations", [])}
        if vm:
            rec = rec_by_vm.get(vm.get("name", ""), {})
            issues = rec.get("migration_issues", []) or []
            issue_text = "\n".join(f"• {issue}" for issue in issues) or "• No migration issues were recorded."
            answer = (
                f"{vm['name']} is assessed as {rec.get('migration_readiness', 'Unknown')} with "
                f"{_number(rec.get('confidence_score', 0), 0)}% confidence.\n\n{issue_text}"
            )
            citations = [_citation("VM assessment", "data/vcenter_discovery.json", "/api/vms", vm["name"])]
            actions = [_action("Open VM what-if", "vm-whatif", entity=vm["name"])]
        else:
            recs = discovery.get("recommendations", [])
            readiness = Counter(_normalise_readiness(r.get("migration_readiness", "")) for r in recs)
            issue_counts = Counter(
                issue
                for rec in recs
                for issue in (rec.get("migration_issues", []) or [])
            )
            top_issues = "\n".join(
                f"• {issue} ({count:,} VMs)" for issue, count in issue_counts.most_common(5)
            ) or "• No migration issues were recorded."
            answer = (
                f"Readiness distribution: {readiness.get('ready', 0):,} ready, "
                f"{readiness.get('ready with conditions', 0):,} ready with conditions, and "
                f"{readiness.get('not ready', 0):,} not ready.\n\nMost common conditions:\n{top_issues}"
            )
            citations = [_citation("Fleet readiness assessment", "data/vcenter_discovery.json", "/api/recommendations")]
            actions = [_action("Review VM assessment", "decide-vm-assessment")]
        return answer, citations, actions, ["Explain the total Azure cost", "Which operating systems are end of life?"]

    def _cost(
        self,
        message: str,
        discovery: dict[str, Any],
        vm: dict[str, Any] | None,
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        recs = discovery.get("recommendations", [])
        rec_by_vm = {r.get("vm_name", ""): r for r in recs}
        if vm:
            rec = rec_by_vm.get(vm.get("name", ""), {})
            pricing = rec.get("pricing", {}) or {}
            components = [
                ("VM compute", pricing.get("vm_payg_monthly")),
                ("Managed disks", pricing.get("disk_total_monthly")),
                ("OS licence", pricing.get("os_license_monthly")),
                ("Backup", pricing.get("backup_monthly")),
                ("Monitoring", pricing.get("monitoring_monthly")),
                ("Networking", pricing.get("networking_monthly")),
            ]
            component_lines = "\n".join(
                f"• {label}: {_money(value)}/month" for label, value in components if value is not None
            )
            total = rec.get("estimated_monthly_cost_usd", pricing.get("total_payg_monthly", 0))
            optimized = pricing.get("total_optimized_monthly")
            sizing = rec.get("right_sizing_note") or (
                f"The recommendation fits {vm.get('num_cpus', 0)} vCPUs and "
                f"{_number((vm.get('memory_mb', 0) or 0) / 1024, 1)} GB RAM."
            )
            answer = (
                f"{vm['name']} is mapped to {rec.get('recommended_vm_sku', 'manual assessment')} at "
                f"{_money(total)}/month in {rec.get('target_region', 'eastus')}.\n\n"
                f"Cost components:\n{component_lines or '• A component breakdown is not available.'}\n\n"
                f"Sizing basis: {sizing}"
            )
            if optimized is not None:
                answer += f"\nOptimized pricing estimate: {_money(optimized)}/month."
            citations = [
                _citation("VM cost assessment", "data/vcenter_discovery.json", "/api/vms", vm["name"]),
                _citation("Azure pricing model", "Azure Retail Prices cache / built-in estimates", "/api/pricing/status"),
            ]
            actions = [_action("Open VM what-if", "vm-whatif", entity=vm["name"])]
            suggestions = [f"Why was {rec.get('recommended_vm_sku', 'this SKU')} selected?", "Compare pricing models"]
            return answer, citations, actions, suggestions

        total = sum(r.get("estimated_monthly_cost_usd", 0) or 0 for r in recs)
        optimized = sum((r.get("pricing", {}) or {}).get("total_optimized_monthly", 0) or 0 for r in recs)
        family_cost = Counter()
        for rec in recs:
            family_cost[rec.get("recommended_vm_family") or "Manual assessment"] += rec.get("estimated_monthly_cost_usd", 0) or 0
        top_families = "\n".join(
            f"• {family}: {_money(cost)}/month" for family, cost in family_cost.most_common(5)
        )
        highest = sorted(recs, key=lambda r: r.get("estimated_monthly_cost_usd", 0) or 0, reverse=True)[:5]
        highest_text = "\n".join(
            f"• {r.get('vm_name')}: {_money(r.get('estimated_monthly_cost_usd'))}/month ({r.get('recommended_vm_sku')})"
            for r in highest
        )
        answer = (
            f"The assessed fleet run rate is {_money(total)}/month ({_money(total * 12)}/year). "
            f"The sum of per-VM optimized estimates is {_money(optimized)}/month.\n\n"
            f"Cost by recommended family:\n{top_families}\n\nHighest-cost VMs:\n{highest_text}"
        )
        return (
            answer,
            [
                _citation("Fleet cost assessment", "data/vcenter_discovery.json", "/api/summary"),
                _citation("Pricing source", "data/retail_price_cache.json", "/api/pricing/status"),
            ],
            [_action("Compare pricing models", "decide-pricing"), _action("Open business case", "decide-businesscase")],
            ["Build the business case", "Which VM costs the most?", "Explain a VM cost by name"],
        )

    def _service_explain(
        self,
        message: str,
        workloads: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        recs = workloads.get("recommendations", [])
        text = message.casefold()
        service_terms = [
            "app service", "azure sql", "sql managed instance", "postgresql", "mysql",
            "cosmos", "container apps", "kubernetes", "aks", "virtual machine", "azure files",
        ]
        requested_service = next((term for term in service_terms if term in text), "")
        matches = [
            rec for rec in recs
            if not requested_service
            or requested_service in str(rec.get("recommended_azure_service", "")).casefold()
        ]
        unique_matches: list[dict[str, Any]] = []
        seen_matches: set[tuple[str, str, str]] = set()
        for rec in matches:
            key = (
                str(rec.get("vm_name", "")).casefold(),
                str(rec.get("workload_name", "")).casefold(),
                str(rec.get("recommended_azure_service", "")).casefold(),
            )
            if key in seen_matches:
                continue
            seen_matches.add(key)
            unique_matches.append(rec)
        matches = unique_matches
        workload = self._find_workload(message, recs)
        if workload and workload not in matches:
            matches.insert(0, workload)
        if workload:
            matches = [workload]
        if not matches:
            return (
                "I could not find a workload recommendation matching that Azure service. Try naming the workload, source VM, or target service exactly as shown in Workload Assessment.",
                [_citation("Workload assessment", "data/workload_discovery.json", "/api/workloads/results")],
                [_action("Open workload assessment", "decide-workload-assessment")],
                ["Why was App Service selected?", "List database targets"],
            )

        selected = matches[:5]
        lines = []
        for rec in selected:
            source = rec.get("source_engine", "the discovered runtime")
            target = rec.get("recommended_azure_service", "Azure service")
            canonical_target = (
                f"Azure App Service ({target})"
                if "app service" in str(target).casefold()
                and not str(target).casefold().startswith("azure app service")
                else target
            )
            rationale = (
                f"{rec.get('workload_name', 'Workload')} on {rec.get('vm_name', 'unknown VM')}: "
                f"the assessment mapped {source} to {canonical_target} as a {rec.get('migration_approach', 'migration')} "
                f"target with {rec.get('migration_complexity', 'unknown')} complexity and "
                f"{_number(rec.get('confidence', 0), 0)}% confidence."
            )
            alternatives = rec.get("alternative_services", []) or []
            if alternatives:
                rationale += f" Alternatives: {', '.join(alternatives[:3])}."
            issues = rec.get("issues", []) or []
            if issues:
                rationale += f" Condition: {issues[0]}"
            lines.append(f"• {rationale}")
        prefix = (
            f"Found {len(matches):,} recommendation(s) targeting services that match '{requested_service}'.\n\n"
            if len(matches) > 1 else ""
        )
        return (
            prefix + "\n".join(lines),
            [_citation("Workload target recommendation", "data/workload_discovery.json", "/api/workloads/results")],
            [_action("Open workload assessment", "decide-workload-assessment")],
            ["Show application groups", "Generate PaaS-preferred landing zones", "Explain the workload cost"],
        )

    def _workloads(
        self,
        message: str,
        workloads: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        recs = workloads.get("recommendations", [])
        text = message.casefold()
        requested_type = next(
            (kind for term, kind in (
                ("database", "database"), ("web app", "webapp"), ("webapp", "webapp"),
                ("container", "container"), ("orchestrator", "orchestrator"),
                ("file share", "fileshare"), ("network", "network"),
            ) if term in text),
            "",
        )
        filtered = [r for r in recs if not requested_type or r.get("workload_type") == requested_type]
        counts = Counter(r.get("workload_type", "unknown") for r in recs)
        examples = "\n".join(
            f"• {r.get('workload_name')} on {r.get('vm_name')} → {r.get('recommended_azure_service')}"
            for r in filtered[:8]
        ) or "• No matching workload recommendations were found."
        answer = (
            f"There are {len(recs):,} workload recommendations: "
            f"{counts.get('webapp', 0):,} web apps, {counts.get('database', 0):,} databases, "
            f"{counts.get('container', 0):,} containers, {counts.get('orchestrator', 0):,} orchestrators, "
            f"{counts.get('fileshare', 0):,} file shares, and {counts.get('network', 0):,} networks.\n\n"
            f"Matching examples:\n{examples}"
        )
        return (
            answer,
            [_citation("Workload discovery and assessment", "data/workload_discovery.json", "/api/workloads/results")],
            [_action("Open workload assessment", "decide-workload-assessment")],
            ["Why was App Service selected?", "List database targets", "Show application groups"],
        )

    def _landing_zones(
        self,
        landing_zones: dict[str, Any] | None,
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        if not landing_zones:
            return (
                "I could not resolve application landing zones from the current assessment.",
                [],
                [_action("Open Landing Zone", "plan-landing-zone")],
                ["Show application groups"],
            )
        apps = landing_zones.get("applications", [])
        lines = "\n".join(
            f"• {app.get('name')}: {app.get('architecture_entry_id')} · "
            f"{app.get('source_member_count', 0)} members · {_money(app.get('monthly_cost'))}/month"
            for app in apps[:10]
        )
        answer = (
            f"Generated {len(apps):,} application landing-zone architecture(s) using "
            f"{landing_zones.get('strategy_label', 'the selected strategy')} in "
            f"{landing_zones.get('region', 'eastus')}.\n\n{lines}"
        )
        return (
            answer,
            [
                _citation("Application assessment", "data/vcenter_discovery.json + workload_discovery.json", "/api/applications"),
                _citation("CTD catalogue resolution", "CloudTopologyDesign Architecture Catalog", "/api/landing-zones"),
            ],
            [_action("View Landing Zone diagrams", "plan-landing-zone")],
            ["Why was App Service selected?", "Compare lift-and-shift with PaaS Preferred", "Show application groups"],
        )

    def _business_case(
        self,
        business_case: dict[str, Any] | None,
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        if not business_case:
            return "Business-case data is unavailable.", [], [], ["Summarize the assessment"]
        years = business_case.get("analysis_years", 3)
        payback = business_case.get("payback_months", -1)
        payback_text = f"{payback} months" if payback and payback > 0 else "not reached in this scenario"
        answer = (
            f"For {business_case.get('target_region', 'eastus')} using "
            f"{str(business_case.get('pricing_model', '')).replace('_', ' ')}, the model estimates:\n\n"
            f"• On-premises: {_money(business_case.get('onprem_monthly'))}/month\n"
            f"• Azure: {_money(business_case.get('azure_monthly'))}/month\n"
            f"• Annual savings: {_money(business_case.get('annual_savings'))}\n"
            f"• Savings rate: {_number(business_case.get('savings_pct'), 1)}%\n"
            f"• One-time migration investment: {_money(business_case.get('migration_one_time'))}\n"
            f"• Payback: {payback_text}\n"
            f"• {years}-year net savings: {_money(business_case.get('total_tco_savings'))}\n\n"
            "These are modeled estimates driven by the documented on-prem assumptions, assessed Azure compute, managed services, staffing, and optional PaaS savings—not a billing quote."
        )
        return (
            answer,
            [
                _citation("Business case model", "Current assessment + documented cost assumptions", "/api/businesscase"),
                _citation("Azure VM assessment", "data/vcenter_discovery.json", "/api/recommendations"),
            ],
            [_action("Open business case", "decide-businesscase")],
            ["Explain the total Azure cost", "Compare pricing models", "What assumptions drive the business case?"],
        )

    def _applications(
        self,
        applications: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        lines = "\n".join(
            f"• {app.get('name')}: {app.get('member_count', 0)} members, "
            f"{app.get('vm_count', 0)} VMs, {app.get('dependency_count', 0)} dependencies, "
            f"complexity {app.get('complexity_score', 0)}/10"
            for app in applications[:10]
        ) or "• No application groups were detected."
        return (
            f"Detected {len(applications):,} complete application group(s). Each group keeps its VMs, web apps, databases, containers, orchestrators, file shares, and dependencies together.\n\n{lines}",
            [_citation("Application grouping", "Discovery dependencies and workload membership", "/api/applications")],
            [_action("Open application groups", "plan-apps")],
            ["Generate landing zones", "Which application is most complex?", "Why was App Service selected?"],
        )

    def _ai_feasibility(
        self,
        message: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Guide application and pattern selection before consented generation."""
        from azure_migrate_simulations.ai_feasibility import (
            get_solution_categories,
            infer_solution_category,
        )

        applications = context.get("applications", [])
        categories = context.get("categories") or get_solution_categories()
        selected_application_id = str(context.get("selected_application_id", ""))
        selected_category_id = str(context.get("selected_category_id", ""))
        prior_stage = str(context.get("stage", ""))

        selected_application = next(
            (app for app in applications if app.get("id") == selected_application_id),
            None,
        )
        if selected_application is None:
            text = message.casefold()
            matching = [
                app for app in applications
                if str(app.get("name", "")).casefold() in text
            ]
            if matching:
                selected_application = max(
                    matching,
                    key=lambda app: len(str(app.get("name", ""))),
                )
                selected_application_id = str(selected_application.get("id", ""))

        if not selected_category_id:
            selected_category_id = infer_solution_category(message).get("category_id", "")
        selected_category = next(
            (item for item in categories if item.get("id") == selected_category_id),
            None,
        )

        if not applications:
            response = self._response(
                "No application groups are available yet. Load discovery and workload data, then detect Application Groups before starting an AI Feasibility Assessment.",
                "ai_feasibility",
                [],
                [_action("Open Application Groups", "plan-apps")],
                ["Show application groups"],
            )
            response["ai_feasibility_stage"] = "needs_applications"
            return response

        if selected_application is None:
            lines = "\n".join(
                f"• {app.get('name')}: {app.get('member_count', 0)} members — "
                f"{app.get('component_summary', {}).get('web_apps', 0)} web apps, "
                f"{app.get('component_summary', {}).get('databases', 0)} databases, "
                f"{app.get('component_summary', {}).get('containers', 0)} containers, and "
                f"{app.get('component_summary', {}).get('file_shares', 0)} file shares"
                for app in applications[:10]
            )
            response = self._response(
                "AI feasibility is assessed for one application plus one customer-owned business workflow. "
                "Choose the application to explore; discovery establishes technical context but does not infer business intent.\n\n"
                + lines,
                "ai_feasibility",
                [_citation("Application groups", "Current discovery and workload assessment", "/api/applications")],
                [
                    {
                        "label": f"Select {app.get('name')}",
                        "type": "chat_prompt",
                        "target": "ai-feasibility",
                        "entity": app.get("id", ""),
                        "prompt": f"Assess AI feasibility for application {app.get('name')}",
                    }
                    for app in applications[:10]
                ],
                ["Show application groups"],
            )
            response["ai_feasibility_stage"] = "select_application"
            return response

        if selected_category is None:
            category_lines = "\n".join(
                f"• {item.get('label')}: {item.get('description')}"
                for item in categories
            )
            response = self._response(
                f"Selected application: {selected_application.get('name')}.\n\n"
                "Choose the broad solution idea that best matches the business process. This choice starts the interview; it does not predetermine the Azure services or approve a build.\n\n"
                + category_lines,
                "ai_feasibility",
                [_citation("AI solution pattern catalog", "Versioned local assessment patterns", "/api/ai-feasibility/categories")],
                [
                    {
                        "label": item.get("label", "Select category"),
                        "type": "chat_prompt",
                        "target": "ai-feasibility",
                        "entity": selected_application_id,
                        "category": item.get("id", ""),
                        "prompt": (
                            f"Use {item.get('label')} for application "
                            f"{selected_application.get('name')}"
                        ),
                    }
                    for item in categories
                ],
                ["Open the guided AI Feasibility Assessment"],
            )
            response.update({
                "ai_feasibility_stage": "select_category",
                "selected_application_id": selected_application_id,
            })
            return response

        selection_markers = (
            "assess ai feasibility", "use audio processing", "use video and image",
            "use predictive", "use mlops", "use document processing",
            "use workflow automation", "use chat with data",
        )
        is_selection_message = any(marker in message.casefold() for marker in selection_markers)
        if prior_stage not in {"describe_intent", "intent_captured"} or is_selection_message:
            response = self._response(
                f"Selected {selected_category.get('label')} for {selected_application.get('name')}.\n\n"
                "Describe the business process or workload you want AI to improve or replace, who performs it today, and the measurable business outcome you expect. Include known volumes or constraints when available. You can also open the guided assessment to upload a Markdown, text, or DOCX intent document.",
                "ai_feasibility",
                [_citation("Selected application", "Current application assessment", "/api/applications", selected_application.get("name", ""))],
                [{
                    "label": "Open guided assessment or upload intent",
                    "type": "ai_feasibility_start",
                    "target": "decide-ai-feasibility",
                    "entity": selected_application_id,
                    "category": selected_category_id,
                }],
                ["The process today is… and the outcome we want is…"],
            )
            response.update({
                "ai_feasibility_stage": "describe_intent",
                "selected_application_id": selected_application_id,
                "selected_category_id": selected_category_id,
            })
            return response

        response = self._response(
            f"I captured the intent for {selected_application.get('name')} under {selected_category.get('label')}. "
            "Open the guided assessment to review the extracted intent, add a measurable business outcome and usage assumptions, confirm the data-processing notice, and generate the evidence-backed assessment. Cost arithmetic and service selection remain deterministic; Foundry only improves the final narrative.",
            "ai_feasibility",
            [
                _citation("Application assessment", "Current discovery and workload assessment", "/api/applications", selected_application.get("name", "")),
                _citation("AI assessment contract", "AI pattern and evidence catalog", "/api/ai-feasibility/categories"),
            ],
            [{
                "label": "Review and generate AI Feasibility Assessment",
                "type": "ai_feasibility_start",
                "target": "decide-ai-feasibility",
                "entity": selected_application_id,
                "category": selected_category_id,
                "intent": message,
            }],
            ["What evidence will the assessment require?"],
        )
        response.update({
            "ai_feasibility_stage": "intent_captured",
            "selected_application_id": selected_application_id,
            "selected_category_id": selected_category_id,
            "captured_intent": message,
        })
        return response

    def _vulnerability(
        self,
        vulnerability: dict[str, Any] | None,
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        summary = (vulnerability or {}).get("summary", {})
        answer = (
            f"Lifecycle analysis reports {summary.get('os_eol_count', 0):,} end-of-life OS records, "
            f"{summary.get('os_near_eol_count', 0):,} near end of life, and "
            f"{summary.get('os_supported_count', 0):,} supported. "
            f"It also identifies {summary.get('sw_critical_count', 0):,} critical software lifecycle findings and "
            f"{summary.get('esu_eligible_count', 0):,} ESU-eligible systems. Potential Azure Hybrid Benefit savings are "
            f"{_money(summary.get('ahub_potential_savings'))}."
        )
        return (
            answer,
            [_citation("Vulnerability and SLA assessment", "Current VM and workload lifecycle rules", "/api/vulnerability-sla")],
            [_action("Open vulnerability assessment", "decide-vulnerability")],
            ["Which VMs have migration conditions?", "Explain Azure Hybrid Benefit savings"],
        )

    def _performance(
        self,
        summary: dict[str, Any] | None,
        perf_history: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        summary = summary or {}
        if not summary.get("has_data"):
            answer = "No performance history is available yet. Start the performance collector or import monitoring enrichment before using utilization-based right-sizing."
        else:
            answer = (
                f"Performance data covers {summary.get('vms_monitored', 0):,} VMs and "
                f"{summary.get('samples_collected', 0):,} samples. Fleet averages are "
                f"{_number(summary.get('avg_cpu_pct'), 1)}% CPU and "
                f"{_number(summary.get('avg_mem_pct'), 1)}% memory, with "
                f"{_number(summary.get('total_iops'), 0)} aggregate IOPS in the latest summary. "
                f"Last collection: {summary.get('last_collection') or 'unknown'}."
            )
        return (
            answer,
            [_citation("Performance history", "data/perf_history.json", "/api/perf/summary")],
            [_action("Open performance monitoring", "decide-performance")],
            ["Explain the total Azure cost", "Which VM costs the most?"],
        )

    def _overrides(
        self,
        overrides: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        lines = "\n".join(
            f"• {name}: {value.get('sku', 'default SKU')} · {value.get('region', 'default region')} · {value.get('pricing', 'default pricing')}"
            for name, value in list(overrides.items())[:15]
        ) or "• No VM what-if overrides are saved."
        return (
            f"There are {len(overrides):,} saved VM what-if override(s).\n\n{lines}",
            [_citation("What-if overrides", "data/whatif_overrides.json", "/api/whatif_overrides")],
            [_action("Open VM assessment", "decide-vm-assessment")],
            ["Explain a VM cost by name", "Compare pricing models"],
        )

    def _help(self) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        answer = (
            "I can answer questions grounded in the loaded migration project, including:\n\n"
            "• Discovery inventory, VM details, hosts, networks, and datastores\n"
            "• Readiness, blockers, OS lifecycle, and performance\n"
            "• Per-VM and fleet cost explainability\n"
            "• Why a workload maps to App Service, Azure SQL, AKS, or another target\n"
            "• Application groups and CTD landing-zone architectures\n"
            "• Business-case savings, assumptions, and payback\n"
            "• Saved what-if overrides and next-step navigation\n\n"
            "Responses include evidence references. Cloud model enhancement is optional; local grounded answers work without it."
        )
        return answer, [], [], [
            "Summarize the assessment",
            "Explain the total Azure cost",
            "Why was App Service selected?",
            "Generate landing zones",
            "Build the business case",
        ]

    def _search(
        self,
        message: str,
        discovery: dict[str, Any],
        workloads: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[str]]:
        tokens = {
            token for token in re.findall(r"[a-z0-9][a-z0-9_.-]+", message.casefold())
            if len(token) > 2 and token not in _STOP_WORDS
        }
        records: list[tuple[int, str, str, str]] = []
        rec_by_vm = {r.get("vm_name", ""): r for r in discovery.get("recommendations", [])}
        for vm in discovery.get("vms", []):
            rec = rec_by_vm.get(vm.get("name", ""), {})
            haystack = " ".join(str(value) for value in (
                vm.get("name"), vm.get("guest_os"), vm.get("folder"), vm.get("host"),
                rec.get("recommended_vm_sku"), rec.get("migration_readiness"),
            )).casefold()
            score = sum(3 if token in str(vm.get("name", "")).casefold() else 1 for token in tokens if token in haystack)
            if score:
                records.append((score, "vm", vm.get("name", ""), (
                    f"{vm.get('name')} — {vm.get('guest_os')} — {rec.get('migration_readiness', 'Unknown')} — "
                    f"{rec.get('recommended_vm_sku', 'manual assessment')} — {_money(rec.get('estimated_monthly_cost_usd'))}/month"
                )))
        for rec in workloads.get("recommendations", []):
            haystack = " ".join(str(value) for value in (
                rec.get("workload_name"), rec.get("vm_name"), rec.get("workload_type"),
                rec.get("source_engine"), rec.get("recommended_azure_service"),
            )).casefold()
            score = sum(2 for token in tokens if token in haystack)
            if score:
                records.append((score, "workload", rec.get("workload_name", ""), (
                    f"{rec.get('workload_name')} on {rec.get('vm_name')} — "
                    f"{rec.get('source_engine')} → {rec.get('recommended_azure_service')}"
                )))
        records.sort(key=lambda item: (-item[0], item[2].casefold()))
        if records:
            lines = "\n".join(f"• {item[3]}" for item in records[:8])
            return (
                f"I found these assessment records related to your question:\n\n{lines}\n\nAsk a more specific follow-up for cost or recommendation explainability.",
                [
                    _citation("Discovery search", "data/vcenter_discovery.json", "/api/vms"),
                    _citation("Workload search", "data/workload_discovery.json", "/api/workloads/results"),
                ],
                [],
                ["Explain the total Azure cost", "What can I ask?"],
            )
        return self._help()

    def _find_vm(self, message: str, vms: list[dict[str, Any]]) -> dict[str, Any] | None:
        text = message.casefold()
        exact = [vm for vm in vms if vm.get("name") and vm["name"].casefold() in text]
        if exact:
            return max(exact, key=lambda vm: len(vm["name"]))
        query_tokens = set(re.findall(r"[a-z0-9_.-]+", text)) - _STOP_WORDS
        best: tuple[float, dict[str, Any] | None] = (0.0, None)
        for vm in vms:
            name = str(vm.get("name", ""))
            if not name:
                continue
            name_tokens = set(re.findall(r"[a-z0-9_.-]+", name.casefold()))
            token_overlap = len(query_tokens & name_tokens) / max(len(name_tokens), 1)
            similarity = SequenceMatcher(None, text, name.casefold()).ratio()
            score = max(token_overlap, similarity if similarity > 0.82 else 0)
            if score > best[0]:
                best = (score, vm)
        return best[1] if best[0] >= 0.75 else None

    def _find_workload(
        self,
        message: str,
        recommendations: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        text = message.casefold()
        matches = [
            rec for rec in recommendations
            if rec.get("workload_name") and str(rec["workload_name"]).casefold() in text
        ]
        if matches:
            return max(matches, key=lambda rec: len(str(rec.get("workload_name", ""))))
        vm_matches = [
            rec for rec in recommendations
            if rec.get("vm_name") and str(rec["vm_name"]).casefold() in text
        ]
        return vm_matches[0] if len(vm_matches) == 1 else None


class FoundryGenerativeProvider:
    """Microsoft Foundry generative provider constrained by local evidence."""

    def __init__(self) -> None:
        self._credential = None
        self.reload_configuration()

    def reload_configuration(self) -> None:
        """Reload non-secret provider configuration from the environment."""
        self.endpoint = os.environ.get("AZURE_MIGRATE_CHAT_ENDPOINT", "").strip()
        self.deployment = os.environ.get("AZURE_MIGRATE_CHAT_DEPLOYMENT", "").strip()
        self.api_version = os.environ.get(
            "AZURE_MIGRATE_CHAT_API_VERSION",
            "2024-12-01-preview",
        ).strip()
        self.api_key = os.environ.get("AZURE_MIGRATE_CHAT_API_KEY", "").strip()

    @property
    def _is_reasoning_deployment(self) -> bool:
        deployment = self.deployment.casefold()
        return deployment.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4"))

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.deployment)

    def status(self) -> dict[str, Any]:
        return {
            "mode": "foundry-generative" if self.configured else "local-grounded",
            "configured": self.configured,
            "generative_ai": self.configured,
            "deployment": self.deployment if self.configured else "",
            "cloud_data_notice": (
                "The question, recent conversation turns, selected local draft, and evidence labels are sent to the configured Foundry model."
                if self.configured else
                "No migration data leaves this application in local-grounded mode."
            ),
        }

    def enhance(
        self,
        question: str,
        response: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            return response
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["api-key"] = self.api_key
            else:
                from azure.identity import DefaultAzureCredential

                if self._credential is None:
                    self._credential = DefaultAzureCredential(
                        exclude_interactive_browser_credential=False,
                    )
                token = self._credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                )
                headers["Authorization"] = f"Bearer {token.token}"
            endpoint = self.endpoint.rstrip("/")
            if "/openai/deployments/" not in endpoint:
                endpoint = f"{endpoint}/openai/deployments/{self.deployment}/chat/completions"
            separator = "&" if "?" in endpoint else "?"
            url = f"{endpoint}{separator}api-version={self.api_version}"
            evidence = "\n".join(
                f"- {citation.get('title')}: {citation.get('source')} ({citation.get('route')})"
                for citation in response.get("citations", [])
            )
            messages: list[dict[str, str]] = [{
                "role": "system",
                "content": (
                    "You are Azure Migrate Copilot, a generative AI assistant for migration discovery, "
                    "assessment, planning, and explainability. Answer the current question naturally using "
                    "only the supplied grounded draft and evidence labels. Never invent inventory, prices, "
                    "calculations, readiness findings, target services, or Azure resources. Preserve every "
                    "numerical value and distinguish modeled estimates from billing quotes. Explain reasoning "
                    "clearly, acknowledge missing evidence, and return concise plain text without markdown tables."
                ),
            }]
            for item in (history or [])[-8:]:
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content[:4_000]})
            messages.append({
                "role": "user",
                "content": (
                    f"Current question: {question}\n\nGrounded local analysis:\n{response['answer']}\n\n"
                    f"Evidence labels:\n{evidence or '- Local structured assessment'}\n\n"
                    "Generate the final answer now."
                ),
            })
            payload: dict[str, Any] = {"messages": messages}
            if self._is_reasoning_deployment:
                payload["max_completion_tokens"] = 4_000
                if self.deployment.casefold().startswith("gpt-6"):
                    # The live GPT-6.1 deployment accepts low/xhigh reasoning,
                    # but only the default temperature. Low keeps grounded
                    # rewriting responsive while retaining reasoning support.
                    payload["reasoning_effort"] = "low"
            else:
                payload["temperature"] = 0.1
                payload["max_tokens"] = 1_200
            result = requests.post(url, headers=headers, json=payload, timeout=60)
            result.raise_for_status()
            content = result.json()["choices"][0]["message"]["content"].strip()
            if content:
                response["answer"] = content
                response["provider"] = "foundry-generative"
                response["model_deployment"] = self.deployment
        except Exception as exc:
            logger.warning("Foundry chat enhancement failed; using local grounded answer: %s", exc)
            response["provider_warning"] = "Foundry enhancement was unavailable; showing the local grounded answer."
        return response
