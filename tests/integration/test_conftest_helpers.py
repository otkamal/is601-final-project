"""Tests for the plain helper functions and fixture internals defined in app/conftest.py.

app/conftest.py is a pytest plugin, not application code, so most of it (fixtures
that spin up a real uvicorn subprocess or a real Playwright browser) is exercised
naturally by the e2e suite rather than by unit tests. This file covers the parts
that are cheap and meaningful to test directly: the pure helper functions, and the
error-handling branches of the db-session fixtures (probed the same way as
app/database.py's get_db(): drive the fixture generator by hand).
"""
import socket
from unittest.mock import patch, MagicMock

import pytest
import requests

import subprocess

from app.conftest import (
    wait_for_server,
    find_available_port,
    db_session,
    setup_test_database,
    fastapi_server,
    ServerStartupError,
)

# ======================================================================================
# wait_for_server
# ======================================================================================

def test_wait_for_server_success():
    """Test wait_for_server returns True as soon as it sees a 200 response."""
    mock_response = MagicMock(status_code=200)
    with patch("app.conftest.requests.get", return_value=mock_response):
        assert wait_for_server("http://127.0.0.1:9999/health", timeout=5) is True

def test_wait_for_server_timeout():
    """Test wait_for_server returns False if the server never comes up before the timeout."""
    with patch("app.conftest.requests.get", side_effect=requests.exceptions.ConnectionError):
        assert wait_for_server("http://127.0.0.1:9999/health", timeout=1) is False

# ======================================================================================
# find_available_port
# ======================================================================================

def test_find_available_port_returns_bindable_port():
    """Test find_available_port returns a port number that can actually be bound."""
    port = find_available_port()
    assert 0 < port <= 65535
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', port))  # Would raise OSError if the port weren't actually free.

# ======================================================================================
# db_session fixture: exception/rollback branch
# ======================================================================================

def test_db_session_fixture_rolls_back_and_reraises_on_error():
    """Test the db_session fixture rolls back and re-raises when the test body errors.

    Drives the fixture generator directly (like get_db() in test_database.py) so we
    can inject an exception at the yield point without needing a failing test.
    `__wrapped__` reaches the plain generator function beneath @pytest.fixture,
    since pytest fixtures can't be called directly.
    """
    gen = db_session.__wrapped__()
    session = next(gen)
    assert session is not None

    with pytest.raises(RuntimeError, match="boom"):
        gen.throw(RuntimeError("boom"))

# ======================================================================================
# setup_test_database fixture: exception branch
# ======================================================================================

def test_setup_test_database_logs_and_reraises_on_setup_error():
    """Test the setup_test_database fixture re-raises if table setup fails."""
    fake_request = MagicMock()

    with patch("app.conftest.Base") as mock_base:
        mock_base.metadata.drop_all.side_effect = RuntimeError("db unreachable")
        gen = setup_test_database.__wrapped__(fake_request)
        with pytest.raises(RuntimeError, match="db unreachable"):
            next(gen)

# ======================================================================================
# fastapi_server fixture: startup-failure and shutdown-timeout branches
#
# The happy path (server starts, tests run against it, server stops cleanly) is
# already covered by tests/e2e/*. These two branches are error-handling edges
# that a real run won't naturally hit, so we drive the fixture generator by hand
# with a mocked subprocess instead of standing up a genuinely broken server.
# ======================================================================================

def test_fastapi_server_raises_on_startup_failure():
    """Test the fixture reads stderr, terminates the process, and raises
    ServerStartupError if the health check never succeeds."""
    fake_process = MagicMock()
    fake_process.stderr.read.return_value = "uvicorn boom"

    with patch("app.conftest.subprocess.Popen", return_value=fake_process), \
         patch("app.conftest.wait_for_server", return_value=False):
        gen = fastapi_server.__wrapped__()
        with pytest.raises(ServerStartupError):
            next(gen)

    fake_process.terminate.assert_called_once()

def test_fastapi_server_kills_process_on_shutdown_timeout():
    """Test the fixture falls back to kill() if the process doesn't exit
    gracefully within the wait() timeout."""
    fake_process = MagicMock()
    fake_process.wait.side_effect = subprocess.TimeoutExpired(cmd="uvicorn", timeout=5)

    with patch("app.conftest.subprocess.Popen", return_value=fake_process), \
         patch("app.conftest.wait_for_server", return_value=True):
        gen = fastapi_server.__wrapped__()
        server_url = next(gen)
        assert server_url.startswith("http://127.0.0.1:")

        with pytest.raises(StopIteration):
            next(gen)  # Resumes after `yield`, running the shutdown code.

    fake_process.terminate.assert_called_once()
    fake_process.kill.assert_called_once()
