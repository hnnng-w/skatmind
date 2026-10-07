"""Opt-in collection/execution accounting for the complete validation runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Real socket teardown/late-body observers have tight synchronization bounds.
# Run their complete modules after all parallel workers have exited.
SERIAL_FILES = frozenset({
    "tests/test_early_rejection_observer.py",
    "tests/test_local_learning_corpus_web.py",
    "tests/test_unified_rejection_transport.py",
    "tests/test_match_analysis_action_placement.py",
})


def assigned_phase(nodeid: str) -> str:
    return "serial" if nodeid.split("::", 1)[0] in SERIAL_FILES else "parallel"


def pytest_addoption(parser):
    parser.addoption("--validation-phase", choices=("all", "parallel", "serial"), default="all")
    parser.addoption("--validation-report")


def pytest_configure(config):
    config._validation_data = {"collected": [], "reports": [], "worker_collections": []}


def pytest_collection_modifyitems(config, items):
    phase = config.getoption("--validation-phase")
    selected = [item for item in items if phase == "all" or assigned_phase(item.nodeid) == phase]
    deselected = [item for item in items if item not in selected]
    config._validation_data["collected"] = [item.nodeid for item in selected]
    items[:] = selected
    if deselected:
        config.hook.pytest_deselected(items=deselected)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(node, ids):
    data = node.config._validation_data
    data["worker_collections"].append(list(ids))
    data["collected"] = list(ids)


class Reports:
    def __init__(self, config):
        self.config = config

    def pytest_runtest_logreport(self, report):
        self.config._validation_data["reports"].append({
            "nodeid": report.nodeid, "when": report.when,
            "outcome": report.outcome, "duration": report.duration,
        })


def pytest_sessionstart(session):
    session.config.pluginmanager.register(Reports(session.config))


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    destination = config.getoption("--validation-report")
    if destination and not hasattr(config, "workerinput"):
        data = config._validation_data
        data["exit_status"] = int(exitstatus)
        Path(destination).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
