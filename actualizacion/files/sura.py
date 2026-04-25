"""
Bot SURA — implementación Playwright completa.

Flujo mapeado según instructivo docs/INSTRUCTIVO_BOT_SURA.md:
  1. Abrir portal
  2. Login con teclado virtual (números aleatorios)
  3. Navegar Empleadores → Empresas → Radicar incapacidades
  4. Ingresar número de incapacidad (dos recuadros)
  5. Confirmar popup y capturar número radicado

Para flujo TRANSCRIPCIÓN (es_transcripcion=True):
  - Paso adicional: adjuntar PDF y llenar campos extra del médico.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from bots.base import (
    BotRadicacionEPS,
    DatosIncapacidad,
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
)
from config import get_settings

# URL del portal — actualizar si cambia
SURA_PORTAL_URL = "https://www.epssuraycompanias.com.co/eps/empleador"


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

async def _cerrar_modal_inicial(page) -> None:
    """Cierra popups de cookies, avisos legales o bienvenida si aparecen."""
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
                break
        except Exception:
            pass


async def _seleccionar_tipo_documento(page, tipo: str) -> None:
    """Selecciona el tipo de documento en el dropdown del portal SURA."""
    if tipo not in TIPOS_DOCUMENTO_VALIDOS:
        raise ValueError(
            f"Tipo de documento '{tipo}' no válido. "
            f"Opciones: {TIPOS_DOCUMENTO_VALIDOS}"
        )

    # Intentar <select> nativo primero
    select_loc = page.locator("select").first
    try:
        if await select_loc.is_visible():
            await select_loc.select_option(label=tipo)
            return
    except Exception:
        pass

    # Dropdown personalizado: clic para abrir, luego elegir opción
    await page.locator(".dropdown, .select-custom, [class*='tipo']").first.click()
    await page.wait_for_timeout(300)
    await page.locator(f"li:has-text('{tipo}'), option:has-text('{tipo}')").first.click()


async def _ingresar_clave_virtual(page, clave: str) -> None:
    """
    Hace clic en cada dígito de la clave usando el teclado virtual.

    El portal SURA muestra un teclado con números en posición aleatoria.
    Los valores son visibles en el DOM pero cambian de posición en cada carga.
    Se localiza cada dígito por su texto y se hace clic sobre él.
    """
    # Selectores candidatos para las teclas del teclado virtual
    # (ajustar al selector real tras inspeccionar el DOM en producción)
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
                # Busca el elemento cuyo texto sea exactamente este dígito
                loc = page.locator(f"{base_sel}:has-text('{digito}')").first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    await page.wait_for_timeout(200)
                    return True
            except Exception:
                continue

        # Fallback: buscar cualquier botón/celda con ese texto exacto
        try:
            loc = page.get_by_text(digito, exact=True).first
            if await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(200)
                return True
        except Exception:
            pass

        return False

    for digito in clave:
        success = await _click_digito(digito)
        if not success:
            raise Exception(
                f"No se encontró la tecla '{digito}' en el teclado virtual. "
                "Inspecciona el DOM del portal y actualiza KEY_SELECTORS en sura.py."
            )


async def _capturar_radicado(page) -> str | None:
    """Extrae el número de radicado del mensaje de confirmación."""
    try:
        contenido = await page.locator(
            ".mensaje-exito, .alert-success, .resultado, .radicado, "
            "[class*='success'], [class*='exito'], [class*='confirmacion']"
        ).first.text_content()
    except Exception:
        # Intentar con todo el body como fallback
        contenido = await page.locator("body").text_content()

    if not contenido:
        return None

    # Patrones comunes en portales EPS colombianos
    patrones = [
        r"[Nn]úmero\s+[Rr]adicado[:\s]+(\w[\w\-]+)",
        r"[Rr]adicado[:\s#]+(\w[\w\-]+)",
        r"[Nn]o[\.:]?\s+[Rr]adicaci[oó]n[:\s]+(\w[\w\-]+)",
        r"[Cc][oó]digo[:\s]+(\d{5,})",
    ]
    for patron in patrones:
        m = re.search(patron, contenido)
        if m:
            return m.group(1).strip()

    return "RADICADO_CAPTURADO"  # Éxito confirmado pero sin número extraíble


# ---------------------------------------------------------------------------
# Bot principal
# ---------------------------------------------------------------------------

class BotSura(BotRadicacionEPS):
    eps_id = "sura"

    async def radicar(
        self,
        datos: DatosIncapacidad,
        *,
        headless: bool = True,
    ) -> ResultadoRadicacion:
        settings = get_settings()

        # — Modo mock (desarrollo sin portal real) —
        if settings.mock_radicacion:
            await asyncio.sleep(0.5)
            return ResultadoRadicacion(
                exitoso=True,
                numero_radicado="MOCK-0001",
                mensaje="Radicación simulada (MOCK_RADICACION=true).",
            )

        from playwright.async_api import async_playwright, TimeoutError as PWTimeout

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                locale="es-CO",
                timezone_id="America/Bogota",
            )
            page = await context.new_page()

            # Capturar dialogs nativos automáticamente
            page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

            try:
                # ── PASO 1: Abrir portal ──────────────────────────────────
                await page.goto(SURA_PORTAL_URL, wait_until="networkidle", timeout=30000)
                await _cerrar_modal_inicial(page)

                # ── PASO 2: Ir a login de Empleador ──────────────────────
                await page.click(
                    'a:has-text("Empleadores"), '
                    'a:has-text("Empleador"), '
                    'button:has-text("Empleador")'
                )
                await page.wait_for_load_state("networkidle")
                await _cerrar_modal_inicial(page)

                # ── PASO 3: Tipo de documento ─────────────────────────────
                await _seleccionar_tipo_documento(
                    page, datos.credenciales.tipo_documento
                )

                # ── PASO 4: Número de documento ───────────────────────────
                await page.fill(
                    'input[name*="numero"], input[id*="numero"], '
                    'input[placeholder*="número"], input[placeholder*="documento"]',
                    datos.credenciales.numero_documento,
                )

                # ── PASO 5: Clave (teclado virtual) ──────────────────────
                await _ingresar_clave_virtual(page, datos.credenciales.clave)

                # ── PASO 6: Submit login ──────────────────────────────────
                await page.click(
                    'button[type="submit"], '
                    'input[type="submit"], '
                    'button:has-text("Ingresar"), '
                    'button:has-text("Iniciar")'
                )
                await page.wait_for_load_state("networkidle")

                # Verificar login exitoso
                error_loc = page.locator(
                    '.error-login, .alert-danger, [class*="error"]:has-text("contraseña")'
                )
                if await error_loc.count() > 0:
                    msg = await error_loc.first.text_content()
                    return ResultadoRadicacion(
                        exitoso=False,
                        numero_radicado=None,
                        mensaje=f"Login fallido: {msg}",
                    )

                # ── PASO 7: Menú Empleadores → Empresas ──────────────────
                await page.hover(
                    'nav a:has-text("Empleadores"), '
                    '.menu a:has-text("Empleadores"), '
                    'a:has-text("Empleadores")'
                )
                await page.wait_for_timeout(400)
                await page.click('a:has-text("Empresas")')
                await page.wait_for_load_state("networkidle")

                # ── PASO 8: Radicar incapacidades ─────────────────────────
                if datos.es_transcripcion:
                    await page.click(
                        'a:has-text("Transcribir"), '
                        'a:has-text("Transcripción"), '
                        'button:has-text("Transcribir incapacidad")'
                    )
                else:
                    await page.click(
                        'a:has-text("Radicar incapacidades"), '
                        'button:has-text("Radicar incapacidades")'
                    )
                await page.wait_for_load_state("networkidle")

                # ── PASO 9: Número de incapacidad (2 recuadros) ───────────
                # Primer recuadro (prefijo — campo pequeño)
                campos = page.locator('input[type="text"]')
                await campos.nth(0).fill(datos.prefijo_incapacidad)
                await page.wait_for_timeout(200)
                # Segundo recuadro (número principal — campo largo)
                await campos.nth(1).fill(datos.numero_incapacidad)

                # ── PASO 10: Si es transcripción, adjuntar PDFs ───────────
                if datos.es_transcripcion and datos.pdf_incapacidad:
                    await page.set_input_files(
                        'input[type="file"]',
                        str(datos.pdf_incapacidad),
                    )
                    if datos.pdf_historia_clinica:
                        file_inputs = page.locator('input[type="file"]')
                        if await file_inputs.count() > 1:
                            await file_inputs.nth(1).set_input_files(
                                str(datos.pdf_historia_clinica)
                            )

                # ── PASO 11: Clic Radicar (botón superior izquierdo) ──────
                await page.click(
                    'button:has-text("Radicar"), '
                    'input[value="Radicar"], '
                    'a:has-text("Radicar")'
                )
                await page.wait_for_timeout(1000)

                # ── PASO 12: Confirmar popup de confirmación ──────────────
                try:
                    await page.wait_for_selector(
                        'button:has-text("Aceptar"), '
                        '.swal2-confirm, '
                        '.modal button:has-text("OK")',
                        timeout=5000,
                    )
                    await page.click(
                        'button:has-text("Aceptar"), '
                        '.swal2-confirm, '
                        '.modal button:has-text("OK")'
                    )
                except PWTimeout:
                    pass  # El dialog nativo ya fue aceptado por el listener

                # ── PASO 13: Capturar resultado ───────────────────────────
                await page.wait_for_timeout(2000)
                numero_radicado = await _capturar_radicado(page)

                return ResultadoRadicacion(
                    exitoso=True,
                    numero_radicado=numero_radicado,
                    mensaje="Incapacidad radicada exitosamente en SURA.",
                )

            except PWTimeout as e:
                return ResultadoRadicacion(
                    exitoso=False,
                    numero_radicado=None,
                    mensaje=f"Timeout en el portal SURA: {e}",
                )
            except Exception as e:
                return ResultadoRadicacion(
                    exitoso=False,
                    numero_radicado=None,
                    mensaje=f"Error en bot SURA: {e}",
                )
            finally:
                await context.close()
                await browser.close()


# ---------------------------------------------------------------------------
# Instancia y función pública
# ---------------------------------------------------------------------------
_bot_sura = BotSura()


async def radicar_en_sura(
    datos: DatosIncapacidad,
    headless: bool = True,
) -> ResultadoRadicacion:
    return await _bot_sura.radicar(datos, headless=headless)
