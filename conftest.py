# Root conftest.py
#
# Registers app/conftest.py as a pytest plugin so its fixtures (fastapi_server,
# db_session, browser_context, page, ...), autouse fixtures (setup_test_database),
# and hooks (pytest_addoption for --preserve-db/--run-slow) are available across
# the whole test session, including tests/e2e and tests/integration which live
# in a sibling directory to app/ and wouldn't otherwise inherit it.
pytest_plugins = ["app.conftest"]
