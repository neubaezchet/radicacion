"""
Bot SURA — Playwright con evasión de Cloudflare y flujo correcto.
La URL de login ya va directo al formulario de empleadores — no hay paso de clic.
"""

from __future__ import annotations

import asyncio
import logging
import re

from bots.base import (
    BotRadicacionEPS,
    DatosIncapacidad,
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
)
from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SURA] %(message)s")
log = logging.getLogger("sura")

SURA_LOGIN_URL = (
    "https://login.sura.com/sso/servicelogin.aspx"
    "?continueTo=https%3A%2F%2Fepsapps.suramericana.com%2FSemp%2F"
    "&service=epssura"
)


# ── Helpers ───────────────────────────────────────────────────────────────

async def _esperar_cloudflare(page) -> None:
    """
    Espera hasta 20 segundos a que Cloudflare termine su challenge.
    Cloudflare muestra 'Verificando' o 'Checking your browser' antes
    de redirigir al formulario real.
    """
    log.info("Esperando posible challenge de Cloudflare...")
    for _ in range(20):
        titulo = await page.title()
        url = page.url
        log.info("  title='%s' url=%s", titulo, url[:80])
        # Si ya no estamos en la página de challenge, seguimos
        if "verificando" not in titulo.lower() and "checking" not in titulo.lower() and "just a moment" not in titulo.lower():
            log.info("Cloudflare superado o no presente")
            return
        await page.wait_for_timeout(1000)
    log.warning("Cloudflare puede seguir activo — continuando de todas formas")


async def _cerrar_modal_inicial(page) -> None:
    for selector in [
        "button:has-text('Aceptar')",
        "button:has-text('Cerrar')",
        "button:has-text('Continuar')",
        ".modal-close",
        "#btnAceptar",
    ]:
        try:
            loc = page.locator(selector).first
            if await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(400)
                log.info("Modal cerrado: %s", selector)
                break
        except Exception:
            pass


async def _seleccionar_tipo_documento(page, tipo: str) -> None:
    if tipo not in TIPOS_DOCUMENTO_VALIDOS:
        raise ValueError(f"Tipo de documento '{tipo}' no válido.")
    log.info("Seleccionando tipo documento: %s", tipo)

    # Intentar <select> nativo
    try:
        sel = page.locator("select").first
        if await sel.is_visible():
            await sel.select_option(label=tipo)
            log.info("Tipo doc seleccionado via <select>")
            return
    except Exception:
        pass

    # Dropdown personalizado
    await page.locator(".dropdown, .select-custom, [class*='tipo']").first.click()
    await page.wait_for_timeout(300)
    await page.locator(f"li:has-text('{tipo}'), option:has-text('{tipo}')").first.click()
    log.info("Tipo doc seleccionado via dropdown personalizado")


async def _ingresar_clave_virtual(page, clave: str) -> None:
    log.info("Ingresando clave virtual (%d dígitos)", len(clave))

    KEY_SELECTORS = [
        "table.teclado td",
        "#virtualKeyboard button",
        ".teclado button",
        ".keyboard button",
        ".tecla",
        "[class*='key'] span",
        "table[id*='teclado'] td",
        "table[id*='keyboard'] td",
    ]

    async def _click_digito(digito: str) -> bool:
        for sel in KEY_SELECTORS:
            try:
                loc = page.locator(f"{sel}:has-text('{digito}')").first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    await page.wait_for_timeout(200)
                    log.info("Dígito '%s' clickeado con: %s", digito, sel)
                    return True
            except Exception:
                continue
        try:
            loc = page.get_by_text(digito, exact=True).first
            if await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(200)
                log.info("Dígito '%s' via get_by_text", digito)
                return True
        except Exception:
            pass
        return False

    for i, digito in enumerate(clave):
        ok = await _click_digito(digito)
        if not ok:
            try:
                html = await page.locator("body").inner_html()
                log.error("HTML teclado (3000 chars):\n%s", html[:3000])
            except Exception:
                pass
            raise Exception(
                f"Tecla '{digito}' (pos {i+1}) no encontrada en teclado virtual. "
                "Ver HTML en logs de Railway y ajustar KEY_SELECTORS."
            )


async def _capturar_radicado(page) -> str | None:
    try:
        contenido = await page.locator(
            ".mensaje-exito, .alert-success, .resultado, .radicado, "
            "[class*='success'], [class*='exito'], [class*='confirmacion']"
        ).first.text_content()
    except Exception:
        contenido = await page.locator("body").text_content()

    if not contenido:
        return None
    log.info("Confirmación: %s", contenido[:300])
    for patron in [
        r"[Nn]úmero\s+[Rr]adicado[:\s]+(\w[\w\-]+)",
        r"[Rr]adicado[:\s#]+(\w[\w\-]+)",
        r"[Nn]o[\.:]?\s+[Rr]adicaci[oó]n[:\s]+(\w[\w\-]+)",
        r"[Cc][oó]digo[:\s]+(\d{5,})",
    ]:
        m = re.search(patron, contenido)
        if m:
            log.info("Radicado: %s", m.group(1))
            return m.group(1).strip()
    return "RADICADO_CAPTURADO"


# ── Bot principal ─────────────────────────────────────────────────────────

class BotSura(BotRadicacionEPS):
    eps_id = "sura"

    async def radicar(self, datos: DatosIncapacidad, *, headless: bool = True) -> ResultadoRadicacion:
        settings = get_settings()

        if settings.mock_radicacion:
            log.info("MOCK activo")
            await asyncio.sleep(0.5)
            return ResultadoRadicacion(True, "MOCK-0001", "Radicación simulada.")

        from playwright.async_api import async_playwright, TimeoutError as PWTimeout

        log.info("=== INICIO RADICACIÓN SURA ===")
        log.info("Empleador tipo=%s num=%s | Trabajador=%s | Incap=%s-%s | Transcript=%s",
                 datos.credenciales.tipo_documento, datos.credenciales.numero_documento,
                 datos.cedula_trabajador, datos.prefijo_incapacidad,
                 datos.numero_incapacidad, datos.es_transcripcion)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    # Ayuda a evadir detección de Cloudflare
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                locale="es-CO",
                timezone_id="America/Bogota",
                # Simular que no es webdriver
                extra_http_headers={"Accept-Language": "es-CO,es;q=0.9"},
            )

            # Ocultar que es Playwright/webdriver
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                Object.defineProperty(navigator, 'languages', { get: () => ['es-CO', 'es'] });
            """)

            page = await context.new_page()
            page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

            try:
                # PASO 1 — Abrir login (ya es el formulario de empleadores directo)
                log.info("PASO 1: Abriendo login SURA")
                await page.goto(SURA_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                log.info("PASO 1 OK — URL: %s | Title: %s", page.url, await page.title())

                # Esperar Cloudflare si aparece
                await _esperar_cloudflare(page)
                await _cerrar_modal_inicial(page)

                # Log del estado real de la página
                log.info("Página tras Cloudflare — Title: %s | URL: %s", await page.title(), page.url)

                # PASO 2 — Tipo de documento
                log.info("PASO 2: Tipo de documento")
                await _seleccionar_tipo_documento(page, datos.credenciales.tipo_documento)
                log.info("PASO 2 OK")

                # PASO 3 — Número de documento
                log.info("PASO 3: Número de documento")
                await page.fill(
                    'input[name*="numero"], input[id*="numero"], '
                    'input[placeholder*="número"], input[placeholder*="documento"], '
                    'input[type="text"]',
                    datos.credenciales.numero_documento,
                )
                log.info("PASO 3 OK")

                # PASO 4 — Clave teclado virtual
                log.info("PASO 4: Clave teclado virtual")
                await _ingresar_clave_virtual(page, datos.credenciales.clave)
                log.info("PASO 4 OK")

                # PASO 5 — Submit login
                log.info("PASO 5: Submit login")
                await page.click(
                    'button[type="submit"], input[type="submit"], '
                    'button:has-text("Ingresar"), button:has-text("Iniciar"), '
                    'button:has-text("Aceptar")'
                )
                await page.wait_for_load_state("networkidle", timeout=30000)
                log.info("PASO 5 OK — URL: %s", page.url)

                # Verificar login
                error_loc = page.locator('.error-login, .alert-danger, [class*="error"]')
                if await error_loc.count() > 0:
                    msg = await error_loc.first.text_content()
                    log.error("LOGIN FALLIDO: %s", msg)
                    return ResultadoRadicacion(False, None, f"Login fallido: {msg}")
                log.info("Login exitoso")

                # PASO 6 — Navegar a Radicar incapacidades
                log.info("PASO 6: Navegar a Radicar incapacidades")
                await page.hover('nav a:has-text("Empleadores"), a:has-text("Empleadores")')
                await page.wait_for_timeout(400)
                await page.click('a:has-text("Empresas")')
                await page.wait_for_load_state("networkidle")
                log.info("PASO 6a OK — URL: %s", page.url)

                if datos.es_transcripcion:
                    await page.click('a:has-text("Transcribir"), a:has-text("Transcripción")')
                else:
                    await page.click('a:has-text("Radicar incapacidades"), button:has-text("Radicar incapacidades")')
                await page.wait_for_load_state("networkidle")
                log.info("PASO 6b OK — URL: %s", page.url)

                # PASO 7 — Número incapacidad (2 recuadros)
                log.info("PASO 7: Número incapacidad %s | %s", datos.prefijo_incapacidad, datos.numero_incapacidad)
                campos = page.locator('input[type="text"]')
                await campos.nth(0).fill(datos.prefijo_incapacidad)
                await page.wait_for_timeout(200)
                await campos.nth(1).fill(datos.numero_incapacidad)
                log.info("PASO 7 OK")

                # PASO 8 — PDFs si es transcripción
                if datos.es_transcripcion and datos.pdf_incapacidad:
                    log.info("PASO 8: Adjuntando PDFs")
                    await page.set_input_files('input[type="file"]', str(datos.pdf_incapacidad))
                    if datos.pdf_historia_clinica:
                        inputs = page.locator('input[type="file"]')
                        if await inputs.count() > 1:
                            await inputs.nth(1).set_input_files(str(datos.pdf_historia_clinica))
                    log.info("PASO 8 OK")

                # PASO 9 — Radicar
                log.info("PASO 9: Clic Radicar")
                await page.click('button:has-text("Radicar"), input[value="Radicar"]')
                await page.wait_for_timeout(1000)
                log.info("PASO 9 OK")

                # PASO 10 — Confirmar popup
                log.info("PASO 10: Popup confirmación")
                try:
                    await page.wait_for_selector(
                        'button:has-text("Aceptar"), .swal2-confirm, .modal button:has-text("OK")',
                        timeout=5000,
                    )
                    await page.click('button:has-text("Aceptar"), .swal2-confirm, .modal button:has-text("OK")')
                    log.info("PASO 10 OK — popup aceptado")
                except PWTimeout:
                    log.info("PASO 10 — sin popup HTML")

                await page.wait_for_timeout(2000)
                numero_radicado = await _capturar_radicado(page)
                log.info("=== ÉXITO — Radicado: %s ===", numero_radicado)
                return ResultadoRadicacion(True, numero_radicado, "Incapacidad radicada exitosamente.")

            except PWTimeout as e:
                log.error("TIMEOUT: %s", str(e))
                return ResultadoRadicacion(False, None, f"Timeout: {e}")
            except Exception as e:
                log.error("ERROR: %s", str(e))
                return ResultadoRadicacion(False, None, f"Error: {e}")
            finally:
                await context.close()
                await browser.close()
                log.info("Browser cerrado")


_bot_sura = BotSura()


async def radicar_en_sura(datos: DatosIncapacidad, headless: bool = True) -> ResultadoRadicacion:
    return await _bot_sura.radicar(datos, headless=headless)
