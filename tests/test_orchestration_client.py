"""Tests for orchestration client facade."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sdlc_control_plane.orchestration.config import ZeebeConfig


class TestConditionalImport:
    def test_module_imports_without_pyzeebe(self) -> None:
        """The orchestration.client module should import cleanly even
        when pyzeebe is not installed."""
        saved = {}
        to_remove = [k for k in sys.modules if k.startswith("pyzeebe")]
        for k in to_remove:
            saved[k] = sys.modules.pop(k)

        try:
            with patch.dict(sys.modules, {"pyzeebe": None, "pyzeebe.channel": None}):
                import importlib

                import sdlc_control_plane.orchestration.client as mod

                importlib.reload(mod)
                assert hasattr(mod, "ZeebeClient")
        finally:
            sys.modules.update(saved)
            import importlib

            import sdlc_control_plane.orchestration.client as mod

            importlib.reload(mod)

    def test_constructor_raises_without_pyzeebe(self) -> None:
        """ZeebeClient() should raise ImportError with install instructions."""
        saved = {}
        to_remove = [k for k in sys.modules if k.startswith("pyzeebe")]
        for k in to_remove:
            saved[k] = sys.modules.pop(k)

        try:
            with patch.dict(
                sys.modules, {"pyzeebe": None, "pyzeebe.channel": None}
            ):
                import importlib

                import sdlc_control_plane.orchestration.client as mod

                importlib.reload(mod)
                config = ZeebeConfig()
                with pytest.raises(ImportError, match="uv sync --extra camunda"):
                    mod.ZeebeClient(config)
        finally:
            sys.modules.update(saved)
            import importlib

            import sdlc_control_plane.orchestration.client as mod

            importlib.reload(mod)


def _make_client() -> Any:
    """Build a ZeebeClient with all pyzeebe internals mocked."""
    from sdlc_control_plane.orchestration.client import ZeebeClient

    config = ZeebeConfig(zeebe_grpc="localhost:36500")
    with patch(
        "sdlc_control_plane.orchestration.client.create_insecure_channel"
    ) as mock_channel, patch(
        "sdlc_control_plane.orchestration.client._SyncZeebeClient"
    ):
        mock_channel.return_value = MagicMock()
        zclient = ZeebeClient(config)
    return zclient


class TestZeebeClientWithMockedPyzeebe:
    @pytest.fixture()
    def client(self) -> Any:
        """Create a ZeebeClient with mocked pyzeebe."""
        return _make_client()

    def test_construction_succeeds(self, client: Any) -> None:
        assert client is not None

    def test_has_deploy_process(self, client: Any) -> None:
        assert hasattr(client, "deploy_process")
        assert callable(client.deploy_process)

    def test_has_create_instance(self, client: Any) -> None:
        assert hasattr(client, "create_instance")
        assert callable(client.create_instance)

    def test_has_run_worker(self, client: Any) -> None:
        assert hasattr(client, "run_worker")
        assert callable(client.run_worker)


class TestDeployProcess:
    def test_deploy_delegates_to_pyzeebe(self) -> None:
        from sdlc_control_plane.orchestration.client import DeploymentResult

        client = _make_client()

        mock_response = MagicMock()
        mock_response.deployments = [
            MagicMock(
                bpmn_process_id="issue-lifecycle",
                version=1,
                process_definition_key=12345,
            )
        ]

        client._sync_client = MagicMock()
        client._sync_client.deploy_resource.return_value = mock_response

        result = client.deploy_process(Path("test.bpmn"))
        assert isinstance(result, DeploymentResult)
        assert result.process_id == "issue-lifecycle"
        assert result.version == 1
        assert result.process_definition_key == 12345


class TestCreateInstance:
    def test_create_instance_delegates_to_pyzeebe(self) -> None:
        from sdlc_control_plane.orchestration.client import InstanceResult

        client = _make_client()

        mock_response = MagicMock()
        mock_response.process_instance_key = 99999
        mock_response.process_definition_key = 12345

        client._sync_client = MagicMock()
        client._sync_client.run_process.return_value = mock_response

        result = client.create_instance(
            "issue-lifecycle", {"issue_id": "TEST-1"}
        )
        assert isinstance(result, InstanceResult)
        assert result.process_instance_key == 99999
