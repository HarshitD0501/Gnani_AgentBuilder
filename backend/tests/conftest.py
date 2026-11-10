"""
conftest.py - Pytest fixtures and test isolation for Sahayika.

Guarantees:
- Default test suite makes ZERO live calls to external LLMs/providers or networks.
- Live model-judged or external network tests require explicit flags:
    --run-integration  (for live LLM judging / provider calls)
    --run-external     (for live internet queries, e.g. OpenStreetMap)
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run tests that make live calls to external providers or LLM judges",
    )
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="Run tests that make live HTTP queries over the internet (e.g. OSM)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: test connects to external LLM or live provider API"
    )
    config.addinivalue_line(
        "markers", "external_network: test makes live network/HTTP request"
    )


def pytest_collection_modifyitems(config, items):
    run_integration = config.getoption("--run-integration")
    run_external = config.getoption("--run-external")

    skip_integration = pytest.mark.skip(
        reason="Skipping live integration test. Pass --run-integration to execute."
    )
    skip_external = pytest.mark.skip(
        reason="Skipping live external network test. Pass --run-external to execute."
    )

    for item in items:
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "external_network" in item.keywords and not run_external:
            item.add_marker(skip_external)

