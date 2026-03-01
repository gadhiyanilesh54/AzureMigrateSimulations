"""Azure Retail Prices API integration for live pricing data.

Fetches real-time pricing from https://prices.azure.com/api/retail/prices
for VM SKUs and PaaS services, with in-memory + file-based caching.

Falls back gracefully to hardcoded prices when the API is unavailable.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RETAIL_API_URL = "https://prices.azure.com/api/retail/prices"
HOURS_PER_MONTH = 730
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours

# Pricing model keys used across the app
PRICING_MODELS = (
    "pay_as_you_go",
    "1_year_ri",
    "3_year_ri",
    "savings_plan_1yr",
    "savings_plan_3yr",
    "dev_test",
    "ea_mca",
)

# PaaS service → Retail API query mapping
# Each entry: (serviceName filter, productName substring, meterName substring,
#              unitOfMeasure, hours_multiplier_for_monthly)
_PAAS_METER_MAP: dict[tuple[str, str], dict] = {
    # --- SQL ---
    ("Azure SQL Database", "GP_Gen5_4"): {
        "serviceName": "SQL Database",
        "productContains": "General Purpose - Compute Gen5",
        "meterContains": "4 vCore",
        "unit_hours": True,
    },
    ("Azure SQL Managed Instance", "GP_Gen5_4"): {
        "serviceName": "SQL Managed Instance",
        "productContains": "General Purpose - Compute Gen5",
        "meterContains": "4 vCore",
        "unit_hours": True,
    },
    # --- MySQL ---
    ("Azure Database for MySQL", "GP_Standard_D4ds_v4"): {
        "serviceName": "Azure Database for MySQL",
        "productContains": "General Purpose",
        "meterContains": "D4ds",
        "unit_hours": True,
    },
    # --- PostgreSQL ---
    ("Azure Database for PostgreSQL", "GP_Standard_D4ds_v4"): {
        "serviceName": "Azure Database for PostgreSQL",
        "productContains": "General Purpose",
        "meterContains": "D4ds",
        "unit_hours": True,
    },
    ("Azure Database for PostgreSQL", "GP_Standard_D8ds_v4"): {
        "serviceName": "Azure Database for PostgreSQL",
        "productContains": "General Purpose",
        "meterContains": "D8ds",
        "unit_hours": True,
    },
    # --- Cosmos DB ---
    ("Azure Cosmos DB (MongoDB API)", "400_RUs"): {
        "serviceName": "Azure Cosmos DB",
        "productContains": "Request Units",
        "meterContains": "100 RU",
        "unit_hours": True,
        "units_needed": 4,  # 400 RUs = 4 × 100 RU blocks
    },
    # --- Redis ---
    ("Azure Cache for Redis", "Standard_C2"): {
        "serviceName": "Azure Cache for Redis",
        "productContains": "Standard",
        "meterContains": "C2",
        "unit_hours": True,
    },
    # --- App Service ---
    ("Azure App Service", "P1v3"): {
        "serviceName": "Azure App Service",
        "productContains": "Premium v3",
        "meterContains": "P1 v3",
        "unit_hours": True,
    },
    ("Azure App Service (Windows)", "P1v3"): {
        "serviceName": "Azure App Service",
        "productContains": "Premium v3",
        "meterContains": "P1 v3",
        "unit_hours": True,
        "productPrefer": "Windows",
    },
    # --- Container Apps ---
    ("Azure Container Apps", "Consumption"): {
        "serviceName": "Azure Container Apps",
        "productContains": "Container Apps",
        "meterContains": "vCPU",
        "unit_hours": True,
        "fallback_only": True,  # consumption model hard to map to fixed monthly
    },
    # --- AKS (control plane is free; node cost = VM cost) ---
    ("Azure Kubernetes Service", "Standard_D4s_v5"): {
        "use_vm_pricing": True,
        "vm_sku": "Standard_D4s_v5",
    },
    # --- Spring Apps ---
    ("Azure Spring Apps", "Standard"): {
        "serviceName": "Azure Spring Apps",
        "productContains": "Standard",
        "meterContains": "vCPU Duration",
        "unit_hours": True,
    },
}

# Dev/Test and EA/MCA are contract-level discounts not in the Retail API.
# We store the retail-API-sourced multiplier vs PayG for RI and Savings Plan,
# and keep estimates for DevTest / EA-MCA.
_ESTIMATED_DISCOUNT_DEVTEST = 0.55   # ~45% off PayG
_ESTIMATED_DISCOUNT_EA_MCA = 0.80    # ~20% off PayG


# ---------------------------------------------------------------------------
# Helper – query the Retail Prices API (handles pagination)
# ---------------------------------------------------------------------------

# Shared session with retry adapter for resilient API calls
_retry_strategy = Retry(
    total=3,
    backoff_factor=1.0,           # 0s, 1s, 2s between retries
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_http_adapter = HTTPAdapter(max_retries=_retry_strategy)
_session = requests.Session()
_session.mount("https://", _http_adapter)
_session.mount("http://", _http_adapter)


def _query_retail_api(odata_filter: str, *, timeout: float = 15.0) -> list[dict]:
    """Execute a paginated query against the Azure Retail Prices REST API.

    Uses automatic retry with exponential backoff for transient errors
    (429, 5xx) via urllib3 Retry.
    """
    items: list[dict] = []
    url = RETAIL_API_URL
    params = {"$filter": odata_filter, "currencyCode": "USD"}
    page = 0

    while url and page < 20:  # safety cap on pagination
        try:
            resp = _session.get(url, params=params if page == 0 else None, timeout=timeout)
            resp.raise_for_status()
            body = resp.json()
            items.extend(body.get("Items", []))
            url = body.get("NextPageLink")
            page += 1
        except Exception as exc:
            logger.warning("Retail API request failed (page %d): %s", page, exc)
            break

    return items


# ---------------------------------------------------------------------------
# VM pricing fetcher
# ---------------------------------------------------------------------------

def _build_vm_sku_filter(sku_names: list[str], region: str) -> str:
    """Build OData filter to fetch VM pricing for a list of SKUs in a region."""
    sku_clauses = " or ".join(f"armSkuName eq '{s}'" for s in sku_names)
    return (
        f"serviceName eq 'Virtual Machines' "
        f"and armRegionName eq '{region}' "
        f"and ({sku_clauses})"
    )


def _parse_vm_items(items: list[dict], sku_names: list[str]) -> dict[str, dict[str, float]]:
    """Parse API items into {sku: {pricing_model: monthly_cost}}.

    Filters out Low Priority, Spot, Windows-license entries so we get the
    base Linux compute price.
    """
    result: dict[str, dict[str, float]] = {s: {} for s in sku_names}

    for item in items:
        sku = item.get("armSkuName", "")
        if sku not in result:
            continue

        product = item.get("productName", "")
        meter = item.get("meterName", "")
        price_type = item.get("type", "")  # Consumption / Reservation / SavingsPlan
        reservation_term = item.get("reservationTerm", "")
        savings_term = item.get("savingsPlan", [])
        unit = item.get("unitOfMeasure", "")
        retail_price = item.get("retailPrice", 0)

        # Skip non-compute entries
        if any(skip in meter.lower() for skip in ("low priority", "spot")):
            continue
        if "windows" in product.lower():
            continue

        # We want the basic compute meter (unitOfMeasure = "1 Hour")
        if "hour" not in unit.lower():
            continue

        monthly = retail_price * HOURS_PER_MONTH

        if price_type == "Consumption":
            result[sku]["pay_as_you_go"] = round(monthly, 2)
        elif price_type == "Reservation":
            if "1 Year" in reservation_term:
                result[sku]["1_year_ri"] = round(monthly, 2)
            elif "3 Year" in reservation_term:
                result[sku]["3_year_ri"] = round(monthly, 2)

    # Savings Plan entries come back with a different structure.
    # The retail API returns savingsPlan as a nested list on Consumption items
    # or as separate SavingsPlan type items.
    for item in items:
        sku = item.get("armSkuName", "")
        if sku not in result:
            continue
        product = item.get("productName", "")
        meter = item.get("meterName", "")
        if any(skip in meter.lower() for skip in ("low priority", "spot")):
            continue
        if "windows" in product.lower():
            continue

        price_type = item.get("type", "")
        unit = item.get("unitOfMeasure", "")
        if "hour" not in unit.lower():
            continue

        # SavingsPlan type items
        if price_type == "SavingsPlan":
            term = item.get("savingsPlan", {})
            retail_price = item.get("retailPrice", 0)
            monthly = retail_price * HOURS_PER_MONTH
            reservation_term = item.get("reservationTerm", "")
            if "1 Year" in reservation_term:
                result[sku]["savings_plan_1yr"] = round(monthly, 2)
            elif "3 Year" in reservation_term:
                result[sku]["savings_plan_3yr"] = round(monthly, 2)

    # Fill in estimated discounts for models not available via API
    for sku in sku_names:
        payg = result[sku].get("pay_as_you_go", 0)
        if payg > 0:
            # DevTest: not in API — estimate
            if "dev_test" not in result[sku]:
                result[sku]["dev_test"] = round(payg * _ESTIMATED_DISCOUNT_DEVTEST, 2)
            # EA/MCA: contract-level — estimate
            if "ea_mca" not in result[sku]:
                result[sku]["ea_mca"] = round(payg * _ESTIMATED_DISCOUNT_EA_MCA, 2)
            # If savings plan data wasn't returned, estimate from RI ratios
            if "savings_plan_1yr" not in result[sku]:
                ri1 = result[sku].get("1_year_ri", payg * 0.65)
                result[sku]["savings_plan_1yr"] = round(ri1 * 1.05, 2)  # SP slightly above RI
            if "savings_plan_3yr" not in result[sku]:
                ri3 = result[sku].get("3_year_ri", payg * 0.45)
                result[sku]["savings_plan_3yr"] = round(ri3 * 1.12, 2)

    return result


# ---------------------------------------------------------------------------
# PaaS pricing fetcher
# ---------------------------------------------------------------------------

def _fetch_paas_price(
    service_name: str,
    sku_tier: str,
    region: str,
) -> float | None:
    """Fetch a single PaaS service monthly cost from the Retail API.

    Returns None if the meter cannot be resolved.
    """
    mapping = _PAAS_METER_MAP.get((service_name, sku_tier))
    if not mapping:
        return None

    # If this PaaS is really VM-priced (e.g., AKS nodes)
    if mapping.get("use_vm_pricing"):
        vm_sku = mapping["vm_sku"]
        prices = fetch_vm_prices([vm_sku], region)
        return prices.get(vm_sku, {}).get("pay_as_you_go")

    if mapping.get("fallback_only"):
        return None  # consumption model — can't map to a fixed monthly cost

    svc = mapping["serviceName"]
    prod_contains = mapping.get("productContains", "")
    meter_contains = mapping.get("meterContains", "")
    prefer_product = mapping.get("productPrefer", "")

    odata = (
        f"serviceName eq '{svc}' "
        f"and armRegionName eq '{region}' "
        f"and priceType eq 'Consumption'"
    )
    items = _query_retail_api(odata)
    if not items:
        return None

    # Filter to matching entries
    candidates = []
    for it in items:
        product = it.get("productName", "")
        meter = it.get("meterName", "")
        if prod_contains and prod_contains.lower() not in product.lower():
            continue
        if meter_contains and meter_contains.lower() not in meter.lower():
            continue
        if any(skip in meter.lower() for skip in ("low priority", "spot", "preview")):
            continue
        candidates.append(it)

    if not candidates:
        return None

    # Prefer a product-name match if requested (e.g., "Windows")
    if prefer_product:
        preferred = [c for c in candidates if prefer_product.lower() in c.get("productName", "").lower()]
        if preferred:
            candidates = preferred

    # Take the first matching entry
    best = candidates[0]
    price = best.get("retailPrice", 0)
    unit = best.get("unitOfMeasure", "")

    if "hour" in unit.lower():
        monthly = price * HOURS_PER_MONTH
    elif "month" in unit.lower():
        monthly = price
    elif "day" in unit.lower():
        monthly = price * 30
    else:
        monthly = price * HOURS_PER_MONTH  # assume hourly

    # Apply units multiplier (e.g., 4 × 100 RU blocks for 400 RUs)
    units_needed = mapping.get("units_needed", 1)
    monthly *= units_needed

    return round(monthly, 2)


# ---------------------------------------------------------------------------
# Public API – thread-safe caching wrapper
# ---------------------------------------------------------------------------

class AzureRetailPricing:
    """Thread-safe cached client for Azure Retail Prices API.

    Usage:
        pricing = AzureRetailPricing(cache_dir=Path("data"))
        prices = pricing.get_vm_prices(["Standard_D2s_v5", ...], "eastus")
        # prices = {"Standard_D2s_v5": {"pay_as_you_go": 70.08, "1_year_ri": 43.45, ...}}
    """

    def __init__(self, cache_dir: Path | None = None, ttl: int = CACHE_TTL_SECONDS):
        self._lock = threading.Lock()
        self._cache_dir = cache_dir
        self._ttl = ttl

        # In-memory caches
        self._vm_cache: dict[str, dict[str, dict[str, float]]] = {}   # region → sku → model → cost
        self._vm_cache_ts: dict[str, float] = {}                       # region → timestamp
        self._paas_cache: dict[str, float] = {}                        # "svc::sku::region" → cost
        self._paas_cache_ts: dict[str, float] = {}

        self._last_refresh: str = ""
        self._api_available: bool | None = None
        self._total_api_calls: int = 0
        self._total_cache_hits: int = 0

        self._load_file_cache()

    # ---- File cache persistence -------------------------------------------

    def _cache_file(self) -> Path | None:
        if self._cache_dir:
            return self._cache_dir / "retail_price_cache.json"
        return None

    def _load_file_cache(self) -> None:
        path = self._cache_file()
        if not path or not path.exists():
            return
        try:
            raw = path.read_text("utf-8")
            if not raw.strip():
                return
            data = json.loads(raw)
            ts = data.get("timestamp", 0)
            if time.time() - ts > self._ttl:
                logger.info("File price cache expired, will refetch")
                return
            self._vm_cache = data.get("vm", {})
            self._vm_cache_ts = {r: ts for r in self._vm_cache}
            self._paas_cache = data.get("paas", {})
            self._paas_cache_ts = {k: ts for k in self._paas_cache}
            self._last_refresh = data.get("last_refresh", "")
            logger.info(
                "Loaded price cache: %d VM regions, %d PaaS entries",
                len(self._vm_cache), len(self._paas_cache),
            )
        except Exception as exc:
            logger.warning("Failed to load price cache: %s", exc)

    def _save_file_cache(self) -> None:
        """Persist cache to disk using atomic write (write to tmp then rename)."""
        path = self._cache_file()
        if not path:
            return
        try:
            data = {
                "timestamp": time.time(),
                "last_refresh": self._last_refresh,
                "vm": self._vm_cache,
                "paas": self._paas_cache,
            }
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(path)  # atomic on same filesystem
        except Exception as exc:
            logger.warning("Failed to save price cache: %s", exc)

    # ---- VM prices --------------------------------------------------------

    def get_vm_prices(
        self,
        sku_names: list[str],
        region: str = "eastus",
    ) -> dict[str, dict[str, float]]:
        """Get monthly prices for each VM SKU across all pricing models.

        Returns:
            {sku_name: {pricing_model: monthly_cost_usd, ...}, ...}

        Falls back to empty dict per SKU if the API is unreachable.
        """
        with self._lock:
            # Check in-memory cache
            cached = self._vm_cache.get(region)
            ts = self._vm_cache_ts.get(region, 0)
            if cached and (time.time() - ts < self._ttl):
                # Return only requested SKUs
                hit = {s: cached[s] for s in sku_names if s in cached}
                missing = [s for s in sku_names if s not in cached]
                if not missing:
                    self._total_cache_hits += 1
                    return hit
            else:
                missing = sku_names
                cached = cached or {}

        # Fetch missing SKUs from the API
        self._total_api_calls += 1
        items = _query_retail_api(_build_vm_sku_filter(missing, region))
        if not items:
            logger.warning("No VM pricing items returned for region=%s", region)
            self._api_available = False
            return {s: {} for s in sku_names}

        self._api_available = True
        parsed = _parse_vm_items(items, missing)

        with self._lock:
            if region not in self._vm_cache:
                self._vm_cache[region] = {}
            self._vm_cache[region].update(parsed)
            self._vm_cache_ts[region] = time.time()
            self._last_refresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            merged = {s: self._vm_cache[region].get(s, {}) for s in sku_names}

        self._save_file_cache()
        return merged

    # ---- PaaS prices ------------------------------------------------------

    def get_paas_price(
        self,
        service_name: str,
        sku_tier: str,
        region: str = "eastus",
    ) -> float | None:
        """Get monthly PayG cost for a PaaS service option.

        Returns None if the service cannot be resolved from the API.
        """
        cache_key = f"{service_name}::{sku_tier}::{region}"

        with self._lock:
            if cache_key in self._paas_cache:
                ts = self._paas_cache_ts.get(cache_key, 0)
                if time.time() - ts < self._ttl:
                    self._total_cache_hits += 1
                    return self._paas_cache[cache_key]

        self._total_api_calls += 1
        price = _fetch_paas_price(service_name, sku_tier, region)

        if price is not None:
            with self._lock:
                self._paas_cache[cache_key] = price
                self._paas_cache_ts[cache_key] = time.time()
                self._last_refresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._save_file_cache()
            self._api_available = True

        return price

    # ---- Bulk PaaS prices -------------------------------------------------

    def get_paas_prices_bulk(
        self,
        services: list[tuple[str, str]],
        region: str = "eastus",
    ) -> dict[tuple[str, str], float | None]:
        """Fetch pricing for multiple (service_name, sku_tier) pairs.

        Returns {(service_name, sku_tier): monthly_cost | None, ...}
        """
        return {
            (svc, tier): self.get_paas_price(svc, tier, region)
            for svc, tier in services
        }

    # ---- Cache management -------------------------------------------------

    def refresh_cache(self, sku_names: list[str], regions: list[str]) -> dict:
        """Force-refresh VM pricing for all given SKUs × regions.

        Returns a summary dict.
        """
        with self._lock:
            self._vm_cache.clear()
            self._vm_cache_ts.clear()
            self._paas_cache.clear()
            self._paas_cache_ts.clear()

        refreshed_regions = 0
        total_skus = 0
        for region in regions:
            prices = self.get_vm_prices(sku_names, region)
            populated = sum(1 for v in prices.values() if v)
            total_skus += populated
            refreshed_regions += 1

        return {
            "regions_refreshed": refreshed_regions,
            "skus_with_live_prices": total_skus,
            "api_available": self._api_available,
            "last_refresh": self._last_refresh,
        }

    @property
    def status(self) -> dict:
        """Return current pricing engine status."""
        return {
            "api_available": self._api_available,
            "last_refresh": self._last_refresh,
            "cached_vm_regions": list(self._vm_cache.keys()),
            "cached_paas_entries": len(self._paas_cache),
            "total_api_calls": self._total_api_calls,
            "total_cache_hits": self._total_cache_hits,
            "cache_ttl_hours": self._ttl / 3600,
        }


# ---------------------------------------------------------------------------
# Module-level convenience (used by workload_mapping update path)
# ---------------------------------------------------------------------------

_default_client: AzureRetailPricing | None = None


def get_default_client() -> AzureRetailPricing | None:
    return _default_client


def set_default_client(client: AzureRetailPricing) -> None:
    global _default_client
    _default_client = client


def fetch_vm_prices(sku_names: list[str], region: str = "eastus") -> dict[str, dict[str, float]]:
    """Convenience wrapper using the module-level default client."""
    client = get_default_client()
    if client is None:
        return {s: {} for s in sku_names}
    return client.get_vm_prices(sku_names, region)


def resolve_paas_sku_tier(service_name: str) -> str:
    """Find the default (first matching) SKU tier for a PaaS service name.

    Searches ``_PAAS_METER_MAP`` keys for an entry whose service part
    matches *service_name* (case-insensitive substring).  Returns the
    SKU tier string, or ``""`` if nothing matches.

    This is useful when the caller only knows the service display name
    but not the specific SKU tier.
    """
    svc_lower = service_name.lower()
    for (svc, tier) in _PAAS_METER_MAP:
        if svc.lower() == svc_lower:
            return tier
        if svc_lower in svc.lower() or svc.lower() in svc_lower:
            return tier
    return ""
