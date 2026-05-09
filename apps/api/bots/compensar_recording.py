import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&_csrf=e42792d3-0389-46ad-ab2b-47b8602bcdeb&protocol=OIDC")
    page.get_by_label("Tipo de documento *").select_option("cc")
    page.get_by_label("Tipo de documento *").select_option("ni")
    page.get_by_role("textbox", name="Número de documento *").click()
    page.get_by_role("textbox", name="Número de documento *").click()
    page.get_by_role("textbox", name="Número de documento *").fill("860000452")
    page.get_by_role("textbox", name="Contraseña *").click()
    page.get_by_role("textbox", name="Contraseña *").press("CapsLock")
    page.get_by_role("textbox", name="Contraseña *").fill("E")
    page.get_by_role("textbox", name="Contraseña *").press("CapsLock")
    page.get_by_role("textbox", name="Contraseña *").fill("Eliot2025.")
    page.get_by_role("button", name="Mostrar contraseña").click()
    page.get_by_role("button", name="Ingresar").click()
    page.get_by_role("button").nth(2).click()
    page.get_by_role("button").nth(2).click()
    page.locator("#loginbutton").click()
    page.get_by_role("button").nth(2).click()
    page.get_by_role("button").nth(2).click()
    page.get_by_role("button").nth(2).click()
    page.get_by_role("button").nth(2).click()
    page.locator("#loginbutton").click()
    page.locator("html").click()
    page.get_by_role("button").nth(2).click()
    page.get_by_role("button").nth(2).click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
