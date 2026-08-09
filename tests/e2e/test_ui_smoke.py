"""Browser-driven smoke test for the server-rendered frontend.

Unlike test_fastapi_calculator.py (which talks to fastapi_server over plain
HTTP), this exercises the app through a real Playwright browser, so the
`browser_context`/`page` fixtures in app/conftest.py get genuine coverage
rather than staying unused infrastructure.
"""
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.test_fastapi_calculator import register_and_login


def test_homepage_renders_in_browser(page: Page, fastapi_server: str):
    """Test that the homepage loads in a real browser and shows the expected content."""
    page.goto(fastapi_server)

    assert "Welcome to the Calculations App" in page.content()
    assert page.get_by_role("link", name="Login").is_visible()
    assert page.get_by_role("link", name="Register").is_visible()

def test_login_page_navigation(page: Page, fastapi_server: str):
    """Test that clicking Login from the homepage navigates to the login page."""
    page.goto(fastapi_server)
    page.get_by_role("link", name="Login").click()

    page.wait_for_url("**/login")
    assert page.locator("form").is_visible()


@pytest.fixture
def logged_in_page(page: Page, fastapi_server: str) -> Page:
    """Log a fresh user in via the API and seed the browser's localStorage.

    The dashboard's own JS reads `access_token`/`username` from localStorage
    (see templates/dashboard.html), so registering/logging in over HTTP and
    seeding those keys gets a real, authenticated page without driving the
    register/login forms here too - that flow isn't the thing under test.
    """
    user_data = {
        "first_name": "Calc",
        "last_name": "Exponent",
        "email": f"calc.exp{uuid4()}@example.com",
        "username": f"calc_exp_{uuid4()}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    token_data = register_and_login(fastapi_server.rstrip("/"), user_data)

    # Must be on the app's origin before localStorage can be seeded for it.
    page.goto(fastapi_server)
    page.evaluate(
        "([token, username]) => { localStorage.setItem('access_token', token); "
        "localStorage.setItem('username', username); }",
        [token_data["access_token"], user_data["username"]],
    )
    return page


def test_dashboard_exponentiation_success(logged_in_page: Page, fastapi_server: str):
    """Test creating an exponentiation calculation end-to-end through the dashboard UI."""
    page = logged_in_page
    page.goto(f"{fastapi_server.rstrip('/')}/dashboard")

    page.locator("#calcType").select_option("exponentiation")
    page.locator("#calcInputs").fill("2, 3, 2")
    page.locator("#calculationForm button[type=submit]").click()

    # (2 ** 3) ** 2 = 64
    expect(page.locator("#successMessage")).to_contain_text("64")
    history_row = page.locator("#calculationsTable tr").first
    expect(history_row).to_contain_text("exponentiation")
    expect(history_row).to_contain_text("64")


def test_dashboard_exponentiation_zero_to_negative_power_shows_error(
    logged_in_page: Page, fastapi_server: str
):
    """Test that the UI surfaces a friendly error for zero raised to a negative power."""
    page = logged_in_page
    page.goto(f"{fastapi_server.rstrip('/')}/dashboard")

    page.locator("#calcType").select_option("exponentiation")
    page.locator("#calcInputs").fill("0, -1")
    page.locator("#calculationForm button[type=submit]").click()

    expect(page.locator("#errorMessage")).to_contain_text(
        "Cannot raise zero to a negative power", ignore_case=True
    )
