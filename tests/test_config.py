"""Tests for config.py."""

import os

from digital_twin_migrate.config import VCenterConfig, AzureConfig, AppConfig, load_config


class TestVCenterConfig:
    def test_defaults(self):
        cfg = VCenterConfig()
        assert cfg.host == ""
        assert cfg.port == 443
        assert cfg.disable_ssl is True

    def test_repr_masks_password(self):
        cfg = VCenterConfig(host="vc.local", password="s3cret")
        r = repr(cfg)
        assert "s3cret" not in r
        assert "****" in r

    def test_repr_empty_password(self):
        cfg = VCenterConfig(host="vc.local", password="")
        r = repr(cfg)
        assert "****" not in r


class TestAzureConfig:
    def test_defaults(self):
        cfg = AzureConfig()
        assert cfg.location == "eastus"
        assert cfg.resource_group == "rg-azure-migrate-simulations"


class TestLoadConfig:
    def test_load_config_returns_app_config(self, monkeypatch):
        monkeypatch.setenv("VCENTER_HOST", "myhost")
        monkeypatch.setenv("VCENTER_USER", "admin")
        monkeypatch.setenv("VCENTER_PASSWORD", "pass")
        cfg = load_config()
        assert isinstance(cfg, AppConfig)
        assert cfg.vcenter.host == "myhost"
        assert cfg.vcenter.username == "admin"
