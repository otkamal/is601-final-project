"""Browser-driven smoke test for the server-rendered frontend.

Unlike test_fastapi_calculator.py (which talks to fastapi_server over plain
HTTP), this exercises the app through a real Playwright browser, so the
`browser_context`/`page` fixtures in app/conftest.py get genuine coverage
rather than staying unused infrastructure.
"""
from playwright.sync_api import Page


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
