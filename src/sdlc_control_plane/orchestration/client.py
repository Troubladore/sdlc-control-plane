"""Thin facade over pyzeebe for Camunda/Zeebe interaction."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from sdlc_control_plane.orchestration.config import ZeebeConfig

# Lazy imports -- module loads cleanly without pyzeebe installed.
# The dependency is checked at ZeebeClient construction time.
try:
    from pyzeebe import Job as _Job
    from pyzeebe import SyncZeebeClient as _SyncZeebeClient
    from pyzeebe import ZeebeWorker as _ZeebeWorker
    from pyzeebe.channel import create_insecure_channel

    _PYZEEBE_AVAILABLE = True
except ImportError:
    _PYZEEBE_AVAILABLE = False

    # Provide stubs so the module can be imported for type checking
    create_insecure_channel = None  # type: ignore[assignment]


@dataclass(frozen=True)
class DeploymentResult:
    """Result of deploying a BPMN process to Zeebe."""

    process_id: str
    version: int
    process_definition_key: int


@dataclass(frozen=True)
class InstanceResult:
    """Result of starting a process instance."""

    process_instance_key: int
    process_definition_key: int


class ZeebeClient:
    """Synchronous facade over pyzeebe for Zeebe interaction.

    Requires the ``camunda`` extra to be installed.  If pyzeebe is not
    available, the constructor raises ``ImportError`` with install
    instructions.
    """

    def __init__(self, config: ZeebeConfig) -> None:
        if not _PYZEEBE_AVAILABLE:
            raise ImportError(
                "pyzeebe is required. Install with: uv sync --extra camunda"
            )
        self._config = config
        self._channel = create_insecure_channel(
            grpc_address=config.zeebe_grpc
        )
        self._sync_client = _SyncZeebeClient(grpc_channel=self._channel)

    def deploy_process(self, bpmn_path: Path) -> DeploymentResult:
        """Deploy a BPMN file to Zeebe."""
        response = self._sync_client.deploy_resource(str(bpmn_path))
        # We always deploy BPMN, so the first deployment is ProcessMetadata.
        proc: Any = response.deployments[0]
        return DeploymentResult(
            process_id=proc.bpmn_process_id,
            version=proc.version,
            process_definition_key=proc.process_definition_key,
        )

    def create_instance(
        self, process_id: str, variables: dict[str, Any] | None = None
    ) -> InstanceResult:
        """Start a workflow instance."""
        response = self._sync_client.run_process(
            bpmn_process_id=process_id, variables=variables
        )
        return InstanceResult(
            process_instance_key=response.process_instance_key,
            process_definition_key=response.process_definition_key,
        )

    def run_worker(
        self,
        job_type: str,
        handler: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
        timeout: float = 30.0,
        max_jobs: int = 1,
    ) -> list[str]:
        """Run a worker that processes jobs of the given type.

        Lifecycle: activates and completes up to ``max_jobs`` jobs of the
        given type, then stops.  If fewer than ``max_jobs`` arrive before
        ``timeout`` seconds, returns with whatever was completed.

        Args:
            job_type: Zeebe job type to handle.
            handler: Called with job variables dict.  Return dict is
                merged into output variables.  If *None*, jobs are
                auto-completed with no output.
            timeout: Max seconds to wait for jobs.
            max_jobs: Stop after completing this many jobs.  Default 1.

        Returns:
            List of completed job types (for order verification).

        Note:
            pyzeebe auto-calls ``set_success_status()`` after the
            handler returns -- do NOT call it manually.
        """
        completed: list[str] = []

        async def _run() -> list[str]:
            # Create a fresh channel for the worker's event loop.
            # Cannot share the SyncZeebeClient's channel across
            # event loop boundaries.
            channel = create_insecure_channel(
                grpc_address=self._config.zeebe_grpc
            )
            worker = _ZeebeWorker(grpc_channel=channel)

            @worker.task(task_type=job_type)  # type: ignore[arg-type]
            async def _handle(job: _Job) -> dict[str, Any]:
                result: dict[str, Any] = {}
                if handler is not None:
                    out = handler(dict(job.variables))
                    if out is not None:
                        result = out
                completed.append(job.type)
                return result

            worker_task = asyncio.create_task(worker.work())
            try:
                deadline = asyncio.get_event_loop().time() + timeout
                while len(completed) < max_jobs:
                    if asyncio.get_event_loop().time() > deadline:
                        break
                    await asyncio.sleep(0.2)
            finally:
                await worker.stop()
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
            return completed

        asyncio.run(_run())
        return completed
