"""End-to-end smoke test: manifest -> TestSuite.run() -> v2 results dict,
using the in-process rdflib reference engine (no docker, no binaries)."""

import bz2
import json
from pathlib import Path

import pytest

from sparql_conformance.config import Config
from sparql_conformance.engines.rdflib_manager import RdflibEngineManager
from sparql_conformance.extract_tests import extract_tests
from sparql_conformance.test_object import Status
from sparql_conformance.testsuite import TestSuite

FIXTURE_SUITE = str(Path(__file__).parent / "fixtures" / "mini-suite")


@pytest.fixture()
def run_results(tmp_path, monkeypatch):
    # The suite writes engine work files and reads server logs from the
    # current directory.
    monkeypatch.chdir(tmp_path)
    config = Config(
        image=None,
        system="native",
        port="7001",
        graph_store="sparql",
        testsuite_dir=FIXTURE_SUITE,
        type_alias=[],
        binaries_directory="",
        exclude=[],
        include=None,
    )
    tests, test_count = extract_tests(config)
    suite = TestSuite(
        name="e2e",
        tests=tests,
        test_count=test_count,
        config=config,
        engine_manager=RdflibEngineManager(),
        results_dir=str(tmp_path),
        report_mode="none",
    )
    suite.run()
    return suite


def statuses_by_name(suite):
    tests_dict, info = suite.build_results_dict()
    return {t["name"]: t["status"] for t in tests_dict.values()}, info


def test_all_supported_tests_pass(run_results):
    statuses, _ = statuses_by_name(run_results)
    expected_passed = [
        "select-basic", "select-int", "ask-true", "construct-basic",
        "syntax-good", "syntax-bad", "update-insert",
    ]
    for name in expected_passed:
        assert statuses[name] == Status.PASSED, (
            f"{name}: {statuses[name]}"
        )


def test_service_description_is_not_silently_counted_as_run(run_results):
    statuses, _ = statuses_by_name(run_results)
    assert statuses["service-description"] == Status.NOT_TESTED


def test_info_totals(run_results):
    _, info = statuses_by_name(run_results)
    assert info["tests"] == 8
    assert info["passed"] == 7
    assert info["failed"] == 0
    assert info["notTested"] == 1


def test_result_file_is_valid_v2_json(run_results, tmp_path):
    tests_dict, info = run_results.build_results_dict()
    output = {
        "version": 2,
        "suites": {"mini": {"tests": tests_dict, "info": info}},
        "info": {"name": "info", **info},
    }
    out_file = tmp_path / "e2e.json.bz2"
    run_results.compress_json_bz2(output, str(out_file))
    with bz2.open(out_file, "rt") as f:
        loaded = json.load(f)
    assert loaded["version"] == 2
    assert loaded["suites"]["mini"]["info"]["tests"] == 8
    # Every test entry carries the fields the web UI relies on.
    for entry in loaded["suites"]["mini"]["tests"].values():
        for field in ("name", "status", "typeName", "group", "errorType"):
            assert field in entry
