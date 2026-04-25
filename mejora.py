"""
Bot SURA — implementación Playwright completa con logging detallado.
Cada paso imprime en los logs de Railway para identificar errores exactos.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from bots.base import (
    BotRadicacionEPS,
    DatosIncapacidad,
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
)
from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SURA] %(message)s")
log = logging.getLogger("sura")

SURA_PORTAL_URL = "https://www.epssuraycompanias.com.co/eps/empleador"


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
                log.info("Modal inicial cerrado con selector: %s", selector)
                break
        except Exception:
            pass


async def _seleccionar_tipo_documento(page, tipo: str) -> None:
    if tipo not in TIPOS_DOCUMENTO_VALIDOS:
        raise ValueError(f"Tipo de documento '{tipo}' no válido.")
    log.info("Seleccionando tipo de documento: %s", tipo)
    select_loc = page.locator("select").first
    try:
        if await select_loc.is_visible():
            await select_loc.select_option(label=tipo)
            log.info("Tipo de documento seleccionado via <select> nativo")
            return
    except Exception:
        pass
    await page.locator(".dropdown, .select-custom, [class*='tipo']").first.click()
    await page.wait_for_timeout(300)
    await page.locator(f"li:has-text('{tipo}'), option:has-text('{tipo}')").first.click()
    log.info("Tipo de documento seleccionado via dropdown personalizado")


async def _ingresar_clave_virtual(page, clave: str) -> None:
    log.info("Ingresando clave en teclado virtual (%d dígitos)", len(clave))
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
        for base_sel in KEY_SELECTORS:
            try:
                loc = page.locator(f"{base_sel}:has-text('{digito}')").first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    await page.wait_for_timeout(200)
                    log.info("Dígito '%s' clickeado con: %s", digito, base_sel)
                    return True
            except Exception:
                continue
        try:
            loc = page.get_by_text(digito, exact=True).first
            if await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(200)
                log.info("Dígito '%s' clickeado via get_by_text", digito)
                return True
        except Exception:
            pass
        return False

    for i, digito in enumerate(clave):
        success = await _click_digito(digito)
        if not success:
            try:
                html = await page.locator("body").inner_html()
                log.error("HTML del body al fallar teclado (primeros 3000 chars):\n%s", html[:3000])
            except Exception:
                pass
            raise Exception(
                f"No se encontró la tecla '{digito}' (posición {i+1}) en el teclado virtual. "
                "Revisa los logs de Railway para ver el HTML y ajusta KEY_SELECTORS."
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
    log.info("Texto de confirmación: %s", contenido[:300])
    patrones = [
        r"[Nn]úmero\s+[Rr]adicado[:\s]+(\w[\w\-]+)",
        r"[Rr]adicado[:\s#]+(\w[\w\-]+)",
        r"[Nn]o[\.:]?\s+[Rr]adicaci[oó]n[:\s]+(\w[\w\-]+)",
        r"[Cc][oó]digo[:\s]+(\d{5,})",
    ]
    for patron in patrones:
        m = re.search(patron, contenido)
        if m:
            log.info("Número radicado: %s", m.group(1))
            return m.group(1).strip()
    return "RADICADO_CAPTURADO"


class BotSura(BotRadicacionEPS):
    eps_id = "sura"

    async def radicar(self, datos: DatosIncapacidad, *, headless: bool = True) -> ResultadoRadicacion:
        settings = get_settings()

        if settings.mock_radicacion:
            log.info("Modo MOCK activo — resultado simulado")
            await asyncio.sleep(0.5)
            return ResultadoRadicacion(True, "MOCK-0001", "Radicación simulada (MOCK_RADICACION=true).")

        from playwright.async_api import async_playwright, TimeoutError as PWTimeout

        log.info("=== INICIANDO RADICACIÓN REAL SURA ===")
        log.info("Empleador tipo=%s num=%s", datos.credenciales.tipo_documento, datos.credenciales.numero_documento)
        log.info("Trabajador=%s | Incapacidad=%s-%s | Transcripcion=%s",
                 datos.cedula_trabajador, datos.prefijo_incapacidad, datos.numero_incapacidad, datos.es_transcripcion)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                locale="es-CO",
                timezone_id="America/Bogota",
            )
            page = await context.new_page()
            page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

            try:
                log.info("PASO 1: Abriendo portal")
                await page.goto(SURA_PORTAL_URL, wait_until="networkidle", timeout=30000)
                log.info("PASO 1 OK — URL: %s", page.url)
                await _cerrar_modal_inicial(page)

                log.info("PASO 2: Clic en Empleadores")
                await page.click('a:has-text("Empleadores"), a:has-text("Empleador"), button:has-text("Empleador")')
                await page.wait_for_load_state("networkidle")
                log.info("PASO 2 OK — URL: %s", page.url)

                log.info("PASO 3: Tipo de documento")
                await _seleccionar_tipo_documento(page, datos.credenciales.tipo_documento)
                log.info("PASO 3 OK")

                log.info("PASO 4: Número de documento")
                await page.fill(
                    'input[name*="numero"], input[id*="numero"], input[placeholder*="número"], input[placeholder*="documento"]',
                    datos.credenciales.numero_documento,
                )
                log.info("PASO 4 OK")

                log.info("PASO 5: Clave teclado virtual")
                await _ingresar_clave_virtual(page, datos.credenciales.clave)
                log.info("PASO 5 OK")

                log.info("PASO 6: Submit login")
                await page.click('button[type="submit"], input[type="submit"], button:has-text("Ingresar"), button:has-text("Iniciar")')
                await page.wait_for_load_state("networkidle")
                log.info("PASO 6 OK — URL: %s", page.url)

                error_loc = page.locator('.error-login, .alert-danger, [class*="error"]:has-text("contraseña")')
                if await error_loc.count() > 0:
                    msg = await error_loc.first.text_content()
                    log.error("PASO 6 FALLO LOGIN: %s", msg)
                    return ResultadoRadicacion(False, None, f"Login fallido: {msg}")

                log.info("PASO 7: Menú Empleadores > Empresas")
                await page.hover('nav a:has-text("Empleadores"), .menu a:has-text("Empleadores"), a:has-text("Empleadores")')
                await page.wait_for_timeout(400)
                await page.click('a:has-text("Empresas")')
                await page.wait_for_load_state("networkidle")
                log.info("PASO 7 OK — URL: %s", page.url)

                log.info("PASO 8: Radicar incapacidades")
                if datos.es_transcripcion:
                    await page.click('a:has-text("Transcribir"), a:has-text("Transcripción"), button:has-text("Transcribir incapacidad")')
                else:
                    await page.click('a:has-text("Radicar incapacidades"), button:has-text("Radicar incapacidades")')
                await page.wait_for_load_state("networkidle")
                log.info("PASO 8 OK — URL: %s", page.url)

                log.info("PASO 9: Número incapacidad %s | %s", datos.prefijo_incapacidad, datos.numero_incapacidad)
                campos = page.locator('input[type="text"]')
                await campos.nth(0).fill(datos.prefijo_incapacidad)
                await page.wait_for_timeout(200)
                await campos.nth(1).fill(datos.numero_incapacidad)
                log.info("PASO 9 OK")

                if datos.es_transcripcion and datos.pdf_incapacidad:
                    log.info("PASO 10: Adjuntando PDFs")
                    await page.set_input_files('input[type="file"]', str(datos.pdf_incapacidad))
                    if datos.pdf_historia_clinica:
                        file_inputs = page.locator('input[type="file"]')
                        if await file_inputs.count() > 1:
                            await file_inputs.nth(1).set_input_files(str(datos.pdf_historia_clinica))
                    log.info("PASO 10 OK")

                log.info("PASO 11: Clic Radicar")
                await page.click('button:has-text("Radicar"), input[value="Radicar"], a:has-text("Radicar")')
                await page.wait_for_timeout(1000)
                log.info("PASO 11 OK")

                log.info("PASO 12: Popup confirmación")
                try:
                    await page.wait_for_selector(
                        'button:has-text("Aceptar"), .swal2-confirm, .modal button:has-text("OK")',
                        timeout=5000,
                    )
                    await page.click('button:has-text("Aceptar"), .swal2-confirm, .modal button:has-text("OK")')
                    log.info("PASO 12 OK — popup HTML aceptado")
                except PWTimeout:
                    log.info("PASO 12 — sin popup HTML (dialog nativo ya manejado)")

                await page.wait_for_timeout(2000)
                log.info("PASO 13: Capturando radicado")
                numero_radicado = await _capturar_radicado(page)
                log.info("=== ÉXITO — Radicado: %s ===", numero_radicado)

                return ResultadoRadicacion(True, numero_radicado, "Incapacidad radicada exitosamente en SURA.")

            except PWTimeout as e:
                log.error("TIMEOUT: %s", str(e))
                return ResultadoRadicacion(False, None, f"Timeout en portal SURA: {e}")
            except Exception as e:
                log.error("ERROR: %s", str(e))
                return ResultadoRadicacion(False, None, f"Error en bot SURA: {e}")
            finally:
                await context.close()
                await browser.close()
                log.info("Browser cerrado")


_bot_sura = BotSura()


async def radicar_en_sura(datos: DatosIncapacidad, headless: bool = True) -> ResultadoRadicacion:
    return await _bot_sura.radicar(datos, headless=headless)
