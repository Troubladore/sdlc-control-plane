"""Integration test: issue-lifecycle happy path against live Camunda cluster.

Requires the Camunda CI cluster to be running (docker-compose-ci.yaml).
Skipped automatically if the cluster is not reachable.

Tests the full public facade: deploy_process, create_instance, run_worker.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from sdlc_control_plane.orchestration.client import ZeebeClient
from sdlc_control_plane.orchestration.config import ZeebeConfig

BPMN_PATH = Path(__file__).resolve().parent.parent / "processes" / "issue-lifecycle.bpmn"

EXPECTED_PHASES = ["triage", "design", "planning", "implement", "review", "integrate"]


@pytest.fixture()
def zeebe_client(
    zeebe_available: None, zeebe_grpc_address: str
) -> ZeebeClient:
    """Create a ZeebeClient connected to the CI cluster."""
    config = ZeebeConfig(zeebe_grpc=zeebe_grpc_address)
    return ZeebeClient(config)


@pytest.fixture()
def _deploy_process(zeebe_client: ZeebeClient) -> None:
    """Deploy the issue-lifecycle BPMN to Zeebe."""
    zeebe_client.deploy_process(BPMN_PATH)


def _poll_instance_completed(
    rest_url: str,
    instance_key: int,
    timeout: float = 10.0,
    interval: float = 1.0,
) -> str:
    """Poll Camunda REST API until instance reaches a terminal state.

    Uses ``zeebe_rest`` (the Zeebe REST API), not Operate. In the
    consolidated Camunda 8.8 image both are the same endpoint, but
    semantically this is querying the Zeebe-backed process instance
    search, not the Operate UI API.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = httpx.post(
            f"{rest_url}/v2/process-instances/search",
            json={
                # Camunda REST API requires processInstanceKey as a string.
                "filter": {"processInstanceKey": str(instance_key)},
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                state = items[0].get("state", "")
                if state in ("COMPLETED", "CANCELED", "TERMINATED"):
                    return state
        time.sleep(interval)
    raise TimeoutError(
        f"Instance {instance_key} did not reach terminal state within {timeout}s"
    )


@pytest.mark.integration
class TestIssueLifecycleHappyPath:
    def test_workflow_completes_all_phases(
        self,
        zeebe_client: ZeebeClient,
        camunda_rest_url: str,
        instance_cleanup: list[int],
        _deploy_process: None,
    ) -> None:
        """Deploy, start, drive all 6 phases via facade, verify completion.

        Uses ZeebeClient.run_worker() for each phase sequentially.
        The process is sequential, so each phase's job only becomes
        available after the previous one completes.
        """
        # Start instance via facade
        result = zeebe_client.create_instance(
            "issue-lifecycle",
            {"issue_id": "TEST-1", "issue_type": "Implementation"},
        )
        instance_key = result.process_instance_key
        assert instance_key > 0
        instance_cleanup.append(instance_key)

        # Drive all 6 phases sequentially through the facade.
        completed: list[str] = []
        for phase in EXPECTED_PHASES:
            result_types = zeebe_client.run_worker(
                job_type=phase, timeout=10.0, max_jobs=1
            )
            completed.extend(result_types)

        # Assert ordering
        assert completed == EXPECTED_PHASES, (
            f"Expected {EXPECTED_PHASES}, got {completed}"
        )

        # Assert completed state via Camunda REST API.
        state = _poll_instance_completed(camunda_rest_url, instance_key)
        assert state == "COMPLETED", f"Expected COMPLETED, got {state}"
