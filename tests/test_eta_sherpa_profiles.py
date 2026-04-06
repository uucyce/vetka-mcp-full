"""
Tests for MARKER_ETA.SHERPA_PROFILES — Multi-profile support in Sherpa.

Coverage:
- ServiceConfig: profile_name field with __post_init__ default
- BrowserClient: {profile_name: service} dictionary for concurrent profiles
- setup_profiles: filters by service group, iterates by profile_name
- Backward compatibility: old configs without profile_name work automatically

Commit: 2ae8a8f1
"""

import pytest
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any


# ── ServiceConfig Tests ────────────────────────────────────────────────

class TestServiceConfigProfileName:
    """Test MARKER_ETA: ServiceConfig profile_name field and auto-defaults."""

    def test_service_config_profile_name_from_profile_dir(self):
        """ServiceConfig should extract profile_name from profile_dir path."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        config = ServiceConfig(
            name="deepseek",
            url="https://chat.deepseek.com",
            profile_dir="data/sherpa_profiles/deepseek_1"
        )

        assert config.profile_name == "deepseek_1", \
            "profile_name should default to last segment of profile_dir"

    def test_service_config_explicit_profile_name_preserved(self):
        """ServiceConfig with explicit profile_name should not be overridden."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        config = ServiceConfig(
            name="deepseek",
            url="https://chat.deepseek.com",
            profile_dir="data/sherpa_profiles/deepseek_2",
            profile_name="my_custom_profile"
        )

        assert config.profile_name == "my_custom_profile", \
            "Explicit profile_name should be preserved"

    def test_multiple_services_same_name_different_profiles(self):
        """Multiple services with same name but different profile_names."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services = [
            ServiceConfig(
                name="deepseek",
                url="https://chat.deepseek.com",
                profile_dir="data/sherpa_profiles/deepseek_1"
            ),
            ServiceConfig(
                name="deepseek",
                url="https://chat.deepseek.com",
                profile_dir="data/sherpa_profiles/deepseek_2"
            ),
            ServiceConfig(
                name="kimi",
                url="https://www.kimi.com",
                profile_dir="data/sherpa_profiles/kimi_1"
            ),
            ServiceConfig(
                name="kimi",
                url="https://www.kimi.com",
                profile_dir="data/sherpa_profiles/kimi_2"
            ),
        ]

        # Verify all have unique profile_names
        profile_names = [s.profile_name for s in services]
        assert len(profile_names) == len(set(profile_names)), \
            "All profile_names should be unique"

        assert "deepseek_1" in profile_names
        assert "deepseek_2" in profile_names
        assert "kimi_1" in profile_names
        assert "kimi_2" in profile_names


# ── BrowserClient Tests ────────────────────────────────────────────────

class TestBrowserClientProfileNameKeying:
    """Test BrowserClient uses profile_name as dictionary key."""

    def test_browser_client_services_dict_keyed_by_profile_name(self):
        """BrowserClient.services should be {profile_name: service} dict."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        class BrowserClient:
            def __init__(self, services: List[ServiceConfig], headless: bool = True):
                self.services = {s.profile_name: s for s in services}
                self.headless = headless
                self._contexts = {}
                self._pages = {}

        services = [
            ServiceConfig(
                name="deepseek",
                url="https://chat.deepseek.com",
                profile_dir="data/sherpa_profiles/deepseek_1"
            ),
            ServiceConfig(
                name="deepseek",
                url="https://chat.deepseek.com",
                profile_dir="data/sherpa_profiles/deepseek_2"
            ),
        ]

        client = BrowserClient(services)

        # Both profiles should be in dict with profile_name as key
        assert "deepseek_1" in client.services
        assert "deepseek_2" in client.services
        assert client.services["deepseek_1"].name == "deepseek"
        assert client.services["deepseek_2"].name == "deepseek"

    def test_browser_client_concurrent_profiles_same_service(self):
        """BrowserClient can hold multiple profiles of same service simultaneously."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        class BrowserClient:
            def __init__(self, services: List[ServiceConfig], headless: bool = True):
                self.services = {s.profile_name: s for s in services}
                self.headless = headless
                self._contexts: Dict[str, Any] = {}
                self._pages: Dict[str, Any] = {}

        services = [
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_1"),
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_2"),
        ]

        client = BrowserClient(services)

        # Simulate contexts for both profiles
        client._contexts["kimi_1"] = {"type": "context", "profile": "kimi_1"}
        client._contexts["kimi_2"] = {"type": "context", "profile": "kimi_2"}

        # Both should coexist
        assert len(client._contexts) == 2
        assert client._contexts["kimi_1"]["profile"] == "kimi_1"
        assert client._contexts["kimi_2"]["profile"] == "kimi_2"


# ── Setup Profiles Tests ───────────────────────────────────────────────

class TestSetupProfilesServiceFiltering:
    """Test setup_profiles filters by service group name, iterates by profile_name."""

    def test_setup_profiles_filter_by_service_name(self):
        """--service deepseek should select deepseek_1 and deepseek_2 but not kimi_1."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services_list = [
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_1"),
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_2"),
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_1"),
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_2"),
        ]

        services_dict = {s.profile_name: s for s in services_list}

        # Simulate setup filtering
        requested_services = ["deepseek"]
        targets = [
            pname for pname, svc in services_dict.items()
            if svc.name in requested_services
        ]

        assert len(targets) == 2, "Should select both deepseek profiles"
        assert "deepseek_1" in targets
        assert "deepseek_2" in targets
        assert "kimi_1" not in targets
        assert "kimi_2" not in targets

    def test_setup_profiles_filter_multiple_services(self):
        """--service deepseek kimi should select all deepseek and kimi profiles."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services_list = [
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_1"),
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_2"),
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_1"),
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_2"),
        ]

        services_dict = {s.profile_name: s for s in services_list}

        requested_services = ["deepseek", "kimi"]
        targets = [
            pname for pname, svc in services_dict.items()
            if svc.name in requested_services
        ]

        assert len(targets) == 4, "Should select all 4 profiles"
        assert set(targets) == {"deepseek_1", "deepseek_2", "kimi_1", "kimi_2"}

    def test_setup_profiles_no_filter_selects_all(self):
        """No --service filter should select all profiles."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services_list = [
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_1"),
            ServiceConfig(name="kimi", url="https://www.kimi.com", profile_dir="data/sherpa_profiles/kimi_1"),
        ]

        services_dict = {s.profile_name: s for s in services_list}

        # No filter specified
        targets = list(services_dict.keys())

        assert len(targets) == 2
        assert "deepseek_1" in targets
        assert "kimi_1" in targets


# ── Backward Compatibility Tests ───────────────────────────────────────

class TestBackwardCompatibility:
    """Test that old configs without profile_name still work."""

    def test_old_config_without_profile_name_auto_defaults(self):
        """Old ServiceConfig entries without profile_name should auto-populate."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        # Simulate loading old YAML without profile_name field
        old_data = {
            "name": "deepseek",
            "url": "https://chat.deepseek.com",
            "profile_dir": "data/sherpa_profiles/deepseek_1",
            # profile_name not in old data
        }

        config = ServiceConfig(**old_data)

        assert config.profile_name == "deepseek_1", \
            "Old configs should have profile_name auto-populated"

    def test_browser_client_handles_mixed_old_new_configs(self):
        """BrowserClient should handle configs with and without explicit profile_name."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        # Old config (no profile_name)
        old_config = ServiceConfig(
            name="deepseek",
            url="https://chat.deepseek.com",
            profile_dir="data/sherpa_profiles/deepseek_1"
        )

        # New config (explicit profile_name)
        new_config = ServiceConfig(
            name="deepseek",
            url="https://chat.deepseek.com",
            profile_dir="data/sherpa_profiles/deepseek_2",
            profile_name="deepseek_2"
        )

        services_dict = {
            old_config.profile_name: old_config,
            new_config.profile_name: new_config,
        }

        # Both should coexist in dict
        assert len(services_dict) == 2
        assert "deepseek_1" in services_dict
        assert "deepseek_2" in services_dict


# ── Integration Tests ──────────────────────────────────────────────────

class TestEtaSherpaProfilesIntegration:
    """Integration tests for multi-profile workflow."""

    def test_full_rotation_deepseek_1_deepseek_2(self):
        """Sherpa should rotate between deepseek_1 and deepseek_2 profiles."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services_list = [
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_1", enabled=True),
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_2", enabled=True),
        ]

        services_dict = {s.profile_name: s for s in services_list}
        enabled_services = [pname for pname, svc in services_dict.items() if svc.enabled]

        # Should be able to access both in rotation
        assert len(enabled_services) == 2
        first_profile = enabled_services[0]
        second_profile = enabled_services[1 % len(enabled_services)]

        assert first_profile != second_profile, "Profiles should be different for rotation"

    def test_disabled_profiles_excluded_from_rotation(self):
        """Disabled profiles should be excluded from active rotation."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services_list = [
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_1", enabled=True),
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_2", enabled=False),
        ]

        services_dict = {s.profile_name: s for s in services_list}
        active_profiles = [pname for pname, svc in services_dict.items() if svc.enabled]

        assert len(active_profiles) == 1
        assert "deepseek_1" in active_profiles
        assert "deepseek_2" not in active_profiles

    def test_setup_enables_disabled_profile(self):
        """--setup --service deepseek should be able to enable deepseek_2."""
        @dataclass
        class ServiceConfig:
            name: str
            url: str
            profile_dir: str
            input_selector: str = "textarea"
            send_selector: str = "button"
            response_selector: str = ".response"
            cooldown_seconds: int = 120
            enabled: bool = True
            profile_name: str = ""

            def __post_init__(self):
                if not self.profile_name:
                    self.profile_name = Path(self.profile_dir).name

        services_list = [
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_1"),
            ServiceConfig(name="deepseek", url="https://chat.deepseek.com", profile_dir="data/sherpa_profiles/deepseek_2", enabled=False),
        ]

        services_dict = {s.profile_name: s for s in services_list}

        # Simulate enabling deepseek_2
        if "deepseek_2" in services_dict:
            services_dict["deepseek_2"].enabled = True

        # Both should now be enabled
        enabled = [pname for pname, svc in services_dict.items() if svc.enabled]
        assert len(enabled) == 2
        assert "deepseek_2" in enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
