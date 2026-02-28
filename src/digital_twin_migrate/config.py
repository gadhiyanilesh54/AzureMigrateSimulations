"""Configuration management - loads settings from .env and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader (avoids external dependency)."""
    candidates = [
        path,
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    env_path = None
    for candidate in candidates:
        if candidate and candidate.exists():
            env_path = candidate
            break
    if env_path is None:
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class VCenterConfig:
    host: str = ""
    port: int = 443
    username: str = ""
    password: str = ""
    disable_ssl: bool = True


@dataclass
class AzureConfig:
    subscription_id: str = ""
    resource_group: str = "rg-azure-migrate-simulations"
    location: str = "eastus"
    dt_instance_name: str = "dt-migrate-lab"


@dataclass
class DiscoveryConfig:
    collect_perf_data: bool = True
    perf_interval_seconds: int = 300


@dataclass
class AppConfig:
    vcenter: VCenterConfig = field(default_factory=VCenterConfig)
    azure: AzureConfig = field(default_factory=AzureConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)


def load_config() -> AppConfig:
    """Load configuration from environment / .env file."""
    _load_dotenv()

    vcenter = VCenterConfig(
        host=os.getenv("VCENTER_HOST", ""),
        port=int(os.getenv("VCENTER_PORT", "443")),
        username=os.getenv("VCENTER_USER", ""),
        password=os.getenv("VCENTER_PASSWORD", ""),
        disable_ssl=os.getenv("VCENTER_DISABLE_SSL", "true").lower() == "true",
    )

    azure = AzureConfig(
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", ""),
        resource_group=os.getenv("AZURE_RESOURCE_GROUP", "rg-azure-migrate-simulations"),
        location=os.getenv("AZURE_LOCATION", "eastus"),
        dt_instance_name=os.getenv("AZURE_DT_INSTANCE_NAME", "dt-migrate-lab"),
    )

    discovery = DiscoveryConfig(
        collect_perf_data=os.getenv("DISCOVERY_COLLECT_PERF_DATA", "true").lower() == "true",
        perf_interval_seconds=int(os.getenv("DISCOVERY_PERF_INTERVAL_SECONDS", "300")),
    )

    return AppConfig(vcenter=vcenter, azure=azure, discovery=discovery)
