"""Tests for orchestration configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sdlc_control_plane.orchestration.config import ZeebeConfig


class TestZeebeConfigDefaults:
    def test_defaults(self) -> None:
        config = ZeebeConfig()
        assert config.zeebe_grpc == "localhost:26500"
        assert config.zeebe_rest == "http://localhost:8088"
        assert config.camunda_operate_url == "http://localhost:8088"

    def test_custom_values(self) -> None:
        config = ZeebeConfig(
            zeebe_grpc="myhost:26500",
            zeebe_rest="http://myhost:8088",
            camunda_operate_url="http://myhost:8088",
        )
        assert config.zeebe_grpc == "myhost:26500"
        assert config.zeebe_rest == "http://myhost:8088"


class TestZeebeConfigFromEnv:
    def test_reads_env_vars(self) -> None:
        env = {
            "ZEEBE_GRPC": "remotehost:26500",
            "ZEEBE_REST": "http://remotehost:8088",
            "CAMUNDA_OPERATE_URL": "http://remotehost:9090",
        }
        with patch.dict(os.environ, env, clear=False):
            config = ZeebeConfig.from_env()
        assert config.zeebe_grpc == "remotehost:26500"
        assert config.zeebe_rest == "http://remotehost:8088"
        assert config.camunda_operate_url == "http://remotehost:9090"

    def test_uses_defaults_when_env_absent(self) -> None:
        env_keys = ["ZEEBE_GRPC", "ZEEBE_REST", "CAMUNDA_OPERATE_URL"]
        cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
        with patch.dict(os.environ, cleaned, clear=True):
            config = ZeebeConfig.from_env()
        assert config.zeebe_grpc == "localhost:26500"

    def test_partial_env(self) -> None:
        with patch.dict(os.environ, {"ZEEBE_GRPC": "custom:9999"}, clear=False):
            config = ZeebeConfig.from_env()
        assert config.zeebe_grpc == "custom:9999"
        assert config.zeebe_rest == "http://localhost:8088"


class TestZeebeConfigValidation:
    def test_zeebe_rest_requires_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="zeebe_rest"):
            ZeebeConfig(zeebe_rest="localhost:8088")

    def test_camunda_operate_url_requires_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="camunda_operate_url"):
            ZeebeConfig(camunda_operate_url="localhost:8088")

    def test_zeebe_rest_accepts_https(self) -> None:
        config = ZeebeConfig(zeebe_rest="https://secure:8088")
        assert config.zeebe_rest == "https://secure:8088"

    def test_zeebe_grpc_rejects_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="zeebe_grpc"):
            ZeebeConfig(zeebe_grpc="http://localhost:26500")

    def test_zeebe_grpc_accepts_host_port(self) -> None:
        config = ZeebeConfig(zeebe_grpc="myhost:26500")
        assert config.zeebe_grpc == "myhost:26500"

    def test_zeebe_grpc_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            ZeebeConfig(zeebe_grpc="")
