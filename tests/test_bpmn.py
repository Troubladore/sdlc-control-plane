"""Tests for the BPMN process model artifact."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

BPMN_PATH = Path(__file__).resolve().parent.parent / "processes" / "issue-lifecycle.bpmn"

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
ZEEBE_NS = "http://camunda.org/schema/zeebe/1.0"

EXPECTED_PHASES = ["triage", "design", "planning", "implement", "review", "integrate"]


@pytest.fixture(scope="module")
def bpmn_process() -> Element:
    """Parse the BPMN file once per module and return the process element."""
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    ns = {"bpmn": BPMN_NS}
    process = root.find("bpmn:process", ns)
    assert process is not None
    return process


def test_bpmn_file_exists() -> None:
    assert BPMN_PATH.exists(), f"BPMN file not found at {BPMN_PATH}"


def test_bpmn_well_formed_xml() -> None:
    ET.parse(BPMN_PATH)  # Raises ParseError if malformed


def test_bpmn_process_id(bpmn_process: Element) -> None:
    assert bpmn_process.get("id") == "issue-lifecycle"
    assert bpmn_process.get("isExecutable") == "true"


def test_bpmn_zeebe_namespace_declared() -> None:
    text = BPMN_PATH.read_text()
    assert ZEEBE_NS in text, "Zeebe extension namespace not declared"


def test_bpmn_six_service_tasks(bpmn_process: Element) -> None:
    ns = {"bpmn": BPMN_NS}
    tasks = bpmn_process.findall("bpmn:serviceTask", ns)
    assert len(tasks) == 6, f"Expected 6 service tasks, got {len(tasks)}"


def test_bpmn_task_ids(bpmn_process: Element) -> None:
    ns = {"bpmn": BPMN_NS}
    tasks = bpmn_process.findall("bpmn:serviceTask", ns)
    task_ids = [t.get("id") for t in tasks]
    expected_ids = [f"Activity_{phase}" for phase in EXPECTED_PHASES]
    assert task_ids == expected_ids


def test_bpmn_job_types(bpmn_process: Element) -> None:
    ns = {"bpmn": BPMN_NS, "zeebe": ZEEBE_NS}
    tasks = bpmn_process.findall("bpmn:serviceTask", ns)
    job_types: list[str] = []
    for task in tasks:
        ext = task.find("bpmn:extensionElements", ns)
        assert ext is not None, f"No extensionElements on {task.get('id')}"
        td = ext.find("zeebe:taskDefinition", ns)
        assert td is not None, f"No zeebe:taskDefinition on {task.get('id')}"
        jt = td.get("type")
        assert jt is not None
        job_types.append(jt)
    assert job_types == EXPECTED_PHASES


def test_bpmn_sequence_flow_connectivity(bpmn_process: Element) -> None:
    """Verify start -> 6 tasks in order -> end via sequence flows."""
    ns = {"bpmn": BPMN_NS}

    # Build adjacency from sequence flows
    flows: dict[str, str] = {}
    for sf in bpmn_process.findall("bpmn:sequenceFlow", ns):
        src = sf.get("sourceRef")
        tgt = sf.get("targetRef")
        assert src is not None and tgt is not None
        flows[src] = tgt

    # Walk the chain: StartEvent_1 -> ... -> EndEvent_1
    expected_chain = (
        ["StartEvent_1"]
        + [f"Activity_{p}" for p in EXPECTED_PHASES]
        + ["EndEvent_1"]
    )
    for i in range(len(expected_chain) - 1):
        src = expected_chain[i]
        assert src in flows, f"No outgoing flow from {src}"
        assert flows[src] == expected_chain[i + 1], (
            f"Expected {src} -> {expected_chain[i + 1]}, got {src} -> {flows[src]}"
        )
