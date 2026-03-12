"""Shared test fixtures."""

from __future__ import annotations

import os
import socket
from typing import Generator

import pytest

# CI cluster defaults (unauthenticated, for automated testing)
CI_ZEEBE_GRPC = "localhost:36500"
CI_CAMUNDA_REST = "http://localhost:18088"


def _check_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _check_http(url: str, timeout: float = 2.0) -> bool:
    """Check if an HTTP endpoint returns a non-error response."""
    try:
        import httpx

        resp = httpx.get(f"{url}/v2/topology", timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def zeebe_grpc_address() -> str:
    """Zeebe gRPC address for integration tests."""
    return os.environ.get("ZEEBE_GRPC", CI_ZEEBE_GRPC)


@pytest.fixture(scope="session")
def camunda_rest_url() -> str:
    """Camunda REST API base URL for integration tests.

    In Camunda 8.8's consolidated image, the Zeebe REST API and
    Operate share the same base URL. We use ZEEBE_REST (not
    CAMUNDA_OPERATE_URL) because the /v2/process-instances/search
    endpoint is part of the Zeebe REST API, not Operate's UI API.
    The env var fallback chain: ZEEBE_REST -> CI cluster default.
    """
    return os.environ.get("ZEEBE_REST", CI_CAMUNDA_REST)


@pytest.fixture(scope="session")
def zeebe_available(zeebe_grpc_address: str, camunda_rest_url: str) -> None:
    """Skip test if the Camunda CI cluster is not reachable.

    Checks both Zeebe gRPC and the Camunda REST API.
    """
    host, port_str = zeebe_grpc_address.rsplit(":", 1)
    if not _check_tcp(host, int(port_str)):
        pytest.skip(
            f"Zeebe gRPC not reachable at {zeebe_grpc_address}"
        )
    if not _check_http(camunda_rest_url):
        pytest.skip(
            f"Camunda REST API not reachable at {camunda_rest_url}"
        )


@pytest.fixture()
def instance_cleanup(zeebe_grpc_address: str) -> Generator[list[int], None, None]:
    """Best-effort cancel of test process instances on teardown.

    Append instance keys to the yielded list during the test.
    On teardown, attempts to cancel each. Does not fail if already
    completed or gone.
    """
    keys: list[int] = []
    yield keys
    if not keys:
        return
    try:
        from pyzeebe import SyncZeebeClient
        from pyzeebe.channel import create_insecure_channel

        channel = create_insecure_channel(grpc_address=zeebe_grpc_address)
        client = SyncZeebeClient(grpc_channel=channel)
        for key in keys:
            try:
                client.cancel_process_instance(key)
            except Exception:
                pass  # Already completed or gone
    except ImportError:
        pass
