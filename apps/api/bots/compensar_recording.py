import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&_csrf=e42792d3-0389-46ad-ab2b-47b8602bcdeb&protocol=OIDC")
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
