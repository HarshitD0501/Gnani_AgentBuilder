"""
conftest.py - Pytest fixtures and test isolation for Sahayika.

Guarantees:
- Default test suite makes ZERO live calls to external LLMs/providers or networks.
- Live model-judged or external network tests require explicit flags:
    --run-integration  (for live LLM judging / provider calls)
    --run-external     (for live internet queries, e.g. OpenStreetMap)
"""

import os
import socket

import pytest

# Do not load developer credentials while collecting tests. Explicit live-test
# flags remain necessary; the default suite also blocks sockets as a backstop.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"


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
        if item.name in {
            "test_red_flag_symptom_offers_a_human_handover",
            "test_an_ordinary_question_escalates_nothing",
        } or item.name in {
            "test_medicine_question_does_not_hand_off",
            "test_phc_request_triggers_agent_handoff",
        }:
            item.add_marker(pytest.mark.integration)
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "external_network" in item.keywords and not run_external:
            item.add_marker(skip_external)


@pytest.fixture(autouse=True)
def block_unapproved_network(request, monkeypatch):
    live = (
        "integration" in request.keywords
        and request.config.getoption("--run-integration")
    ) or (
        "external_network" in request.keywords
        and request.config.getoption("--run-external")
    )
    if live:
        return

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock, address):
        if isinstance(address, tuple) and address[0] in {
            "127.0.0.1",
            "::1",
            "localhost",
        }:
            return original_connect(sock, address)
        raise RuntimeError(
            "Network disabled in offline tests; mock the provider boundary"
        )

    def guarded_connect_ex(sock, address):
        if isinstance(address, tuple) and address[0] in {
            "127.0.0.1",
            "::1",
            "localhost",
        }:
            return original_connect_ex(sock, address)
        raise RuntimeError(
            "Network disabled in offline tests; mock the provider boundary"
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
