"""
Bot SURA — flujo completo mapeado desde imágenes del portal.

Flujo:
  1. Abrir login.sura.com (formulario directo de empleadores)
  2. Seleccionar tipo de identificación (select nativo)
  3. Ingresar número de identificación (input de texto)
  4. Ingresar clave en teclado virtual (botones con * visual, números en DOM)
  5. Clic en checkmark verde para confirmar clave y hacer login
  6. Navegar directo a URL de radicación
  7. Ingresar número incapacidad (2 campos)
  8. Clic "Radicar" (botón superior derecho)
  9. Aceptar popup de confirmación
 10. Capturar número radicado
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
SURA_RADICAR_URL = (
    "https://epsapps.suramericana.com/Semp/faces/pos"
    "/radicarIncapacidad/parametros.jspx"
)


# ── Teclado virtual ───────────────────────────────────────────────────────

async def _ingresar_clave_virtual(page, clave: str) -> None:
    """
    El teclado virtual de SURA muestra botones con '*' visualmente,
    pero los números reales están en atributos del DOM (data-value, value, etc.)
    o como texto real que CSS oculta con font-family password.

    Estrategia:
    1. Intentar encontrar botones por data-value / data-num / value
    2. Si no, leer texto real via JS (puede diferir del visual)
    3. Clic en checkmark verde al final
    """
    log.info("Ingresando clave virtual (%d dígitos)", len(clave))

    # Esperar que el teclado esté visible
    await page.wait_for_selector(
        'button, td, div[class*="key"], span[class*="key"]',
        timeout=10000,
    )
    await page.wait_for_timeout(500)

    # Intentar mapear el teclado — obtener todos los botones candidatos con su valor real
    teclado_js = await page.evaluate("""
        () => {
            const resultados = [];
            // Buscar todos los elementos que podrían ser teclas
            const candidatos = document.querySelectorAll(
                'button, td[onclick], td[data-value], span[data-value], ' +
                'div[data-value], input[type=button], a[data-value]'
            );
            candidatos.forEach((el, idx) => {
                const texto = el.textContent.trim();
                const dataVal = el.getAttribute('data-value') ||
                                el.getAttribute('data-num') ||
                                el.getAttribute('data-key') ||
                                el.getAttribute('value') ||
                                el.getAttribute('data-digit');
                const onclick = el.getAttribute('onclick') || '';
                // Solo guardar si parece una tecla numérica
                const esNumero = /^[0-9]$/.test(dataVal) ||
                                 /^[0-9]$/.test(texto) ||
                                 /[0-9]/.test(onclick.slice(0, 30));
                if (esNumero || (texto === '*' && idx < 20)) {
                    resultados.push({
                        idx,
                        texto,
                        dataVal,
                        onclick: onclick.slice(0, 60),
                        tag: el.tagName,
                        clase: el.className,
                    });
                }
            });
            return resultados;
        }
    """)
    log.info("Teclas encontradas en DOM: %s", teclado_js)

    # Construir mapa digito → elemento
    mapa = {}
    for item in teclado_js:
        # Priorizar data-value
        val = item.get('dataVal') or item.get('texto')
        if val and re.match(r'^[0-9]$', str(val).strip()):
            mapa[val.strip()] = item['idx']

    log.info("Mapa de dígitos: %s", mapa)

    # Si no encontramos mapa por data-value, los botones son posicionales
    # El teclado tiene 10 dígitos (0-9) en 3x3+1 grid, en orden aleatorio
    # Necesitamos saber qué número hay en cada posición
    if not mapa:
        log.warning("No se encontró data-value en teclado. Intentando leer texto real via JS.")
        textos_reales = await page.evaluate("""
            () => {
                const botones = [];
                document.querySelectorAll('button, td[onclick]').forEach((el, i) => {
                    if (i < 20) {
                        botones.push({
                            idx: i,
                            textContent: el.textContent,
                            innerText: el.innerText,
                            value: el.value,
                            dataset: JSON.stringify(el.dataset),
                        });
                    }
                });
                return botones;
            }
        """)
        log.info("Textos reales de botones: %s", textos_reales)

    async def _click_digito(digito: str) -> bool:
        # Método 1: buscar por data-value exacto
        for attr in ['data-value', 'data-num', 'data-key', 'data-digit']:
            try:
                loc = page.locator(f'[{attr}="{digito}"]').first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    await page.wait_for_timeout(300)
                    log.info("Dígito '%s' via %s", digito, attr)
                    return True
            except Exception:
                continue

        # Método 2: buscar botón cuyo textContent real sea el dígito
        # (aunque visualmente muestre *)
        try:
            resultado = await page.evaluate(f"""
                () => {{
                    const els = document.querySelectorAll('button, td[onclick], td');
                    for (let el of els) {{
                        const txt = el.textContent.trim();
                        const dv = el.getAttribute('data-value') || '';
                        if (txt === '{digito}' || dv === '{digito}') {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if resultado:
                await page.wait_for_timeout(300)
                log.info("Dígito '%s' via JS click directo", digito)
                return True
        except Exception as e:
            log.warning("JS click falló para '%s': %s", digito, e)

        # Método 3: usar el índice del mapa si lo tenemos
        if digito in mapa:
            try:
                idx = mapa[digito]
                await page.evaluate(f"""
                    () => {{
                        const els = document.querySelectorAll(
                            'button, td[onclick], td[data-value]'
                        );
                        if (els[{idx}]) els[{idx}].click();
                    }}
                """)
                await page.wait_for_timeout(300)
                log.info("Dígito '%s' via índice %d", digito, idx)
                return True
            except Exception as e:
                log.warning("Click por índice falló: %s", e)

        return False

    for i, digito in enumerate(clave):
        ok = await _click_digito(digito)
        if not ok:
            # Capturar estado del DOM para diagnóstico
            try:
                html = await page.locator('body').inner_html()
                log.error("DOM al fallar dígito '%s':\n%s", digito, html[:4000])
            except Exception:
                pass
            raise Exception(
                f"No se pudo ingresar dígito '{digito}' (pos {i+1}). "
                "Ver DOM en logs de Railway."
            )

    # Clic en el botón verde de confirmación (checkmark)
    log.info("Haciendo clic en confirmación (checkmark verde)")
    confirmado = False
    for sel in [
        'button.confirm, button[class*="confirm"]',
        'button[style*="green"], td[style*="green"]',
        'button:has-text("✓"), button:has-text("✔")',
        # Último botón del teclado suele ser el checkmark
        'table.teclado tr:last-child td:last-child',
        '#btnAceptarClave, #btnConfirmar, #btnOk',
    ]:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click()
                log.info("Checkmark verde clickeado con: %s", sel)
                confirmado = True
                break
        except Exception:
            continue

    if not confirmado:
        # Intentar via JS: buscar el último botón del teclado
        await page.evaluate("""
            () => {
                const btns = document.querySelectorAll('button, td[onclick]');
                // El checkmark suele ser el último botón del teclado
                const ultimo = btns[btns.length - 1];
                if (ultimo) ultimo.click();
            }
        """)
        log.warning("Checkmark clickeado via JS fallback (último botón)")

    await page.wait_for_timeout(500)


# ── Helpers ───────────────────────────────────────────────────────────────

async def _cerrar_modal(page) -> None:
    for sel in ['button:has-text("Aceptar")', 'button:has-text("Cerrar")',
                'button:has-text("OK")', '.modal-close', '#btnCerrar']:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(300)
                break
        except Exception:
            pass


async def _capturar_radicado(page) -> str | None:
    try:
        contenido = await page.locator(
            ".mensaje-exito, .alert-success, .resultado, "
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
        r"[Nn]o[\.:]?\s*[Rr]adicaci[oó]n[:\s]+(\w[\w\-]+)",
        r"[Cc][oó]digo[:\s]+(\d{5,})",
    ]:
        m = re.search(patron, contenido)
        if m:
            log.info("Radicado extraído: %s", m.group(1))
            return m.group(1).strip()
    return "RADICADO_OK"


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
        log.info("Empleador tipo=%s num=%s | CC trabajador=%s | Incap=%s-%s",
                 datos.credenciales.tipo_documento, datos.credenciales.numero_documento,
                 datos.cedula_trabajador, datos.prefijo_incapacidad, datos.numero_incapacidad)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox", "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
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
            )
            await context.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )
            page = await context.new_page()
            page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

            try:
                # ── PASO 1: Abrir formulario de login ─────────────────────
                log.info("PASO 1: Abriendo login SURA")
                await page.goto(SURA_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                # Esperar a que cargue completamente (puede haber redirects)
                await page.wait_for_timeout(2000)
                log.info("PASO 1 OK — URL: %s | Title: %s", page.url, await page.title())
                await _cerrar_modal(page)

                # ── PASO 2: Tipo de identificación (select nativo) ────────
                log.info("PASO 2: Seleccionando tipo de identificación: %s",
                         datos.credenciales.tipo_documento)
                await page.wait_for_selector('select', timeout=15000)
                await page.locator('select').first.select_option(
                    label=datos.credenciales.tipo_documento
                )
                log.info("PASO 2 OK")

                # ── PASO 3: Número de identificación ─────────────────────
                log.info("PASO 3: Número de identificación")
                await page.locator('input[type="text"], input[type="number"]').first.fill(
                    datos.credenciales.numero_documento
                )
                log.info("PASO 3 OK")

                # ── PASO 4: Clave en teclado virtual ─────────────────────
                log.info("PASO 4: Clave teclado virtual")
                # Hacer clic en el campo de contraseña para activar el teclado
                await page.locator(
                    'input[type="password"], input[placeholder*="ontraseña"], '
                    'input[id*="pass"], input[id*="clave"]'
                ).first.click()
                await page.wait_for_timeout(800)
                await _ingresar_clave_virtual(page, datos.credenciales.clave)
                log.info("PASO 4 OK")

                # ── PASO 5: Esperar redirección tras login ────────────────
                log.info("PASO 5: Esperando login...")
                await page.wait_for_load_state("networkidle", timeout=30000)
                log.info("PASO 5 OK — URL: %s", page.url)

                # Verificar si login falló
                if "login" in page.url.lower() or "error" in page.url.lower():
                    try:
                        msg = await page.locator(
                            '.error, .alert, [class*="error"], [class*="mensaje"]'
                        ).first.text_content()
                    except Exception:
                        msg = "Credenciales incorrectas o portal no accesible"
                    log.error("Login fallido: %s", msg)
                    return ResultadoRadicacion(False, None, f"Login fallido: {msg}")

                log.info("Login exitoso")

                # ── PASO 6: Navegar directo a Radicar Incapacidades ───────
                log.info("PASO 6: Navegando a radicar incapacidades")
                await page.goto(SURA_RADICAR_URL, wait_until="networkidle", timeout=30000)
                log.info("PASO 6 OK — URL: %s", page.url)

                # ── PASO 7: Ingresar número de incapacidad (2 campos) ─────
                log.info("PASO 7: Número incapacidad [%s] [%s]",
                         datos.prefijo_incapacidad, datos.numero_incapacidad)
                await page.wait_for_selector('input[type="text"]', timeout=15000)
                campos = page.locator('input[type="text"]')
                await campos.nth(0).fill(datos.prefijo_incapacidad)
                await page.wait_for_timeout(300)
                await campos.nth(1).fill(datos.numero_incapacidad)
                log.info("PASO 7 OK")

                # ── PASO 8: Adjuntar PDFs si es transcripción ─────────────
                if datos.es_transcripcion and datos.pdf_incapacidad:
                    log.info("PASO 8: Adjuntando PDFs")
                    await page.set_input_files(
                        'input[type="file"]', str(datos.pdf_incapacidad)
                    )
                    if datos.pdf_historia_clinica:
                        inputs = page.locator('input[type="file"]')
                        if await inputs.count() > 1:
                            await inputs.nth(1).set_input_files(
                                str(datos.pdf_historia_clinica)
                            )
                    log.info("PASO 8 OK")

                # ── PASO 9: Clic "Radicar" (botón superior derecho) ───────
                log.info("PASO 9: Clic Radicar")
                await page.click(
                    'button:has-text("Radicar"), '
                    'input[value="Radicar"], '
                    'a:has-text("Radicar")'
                )
                await page.wait_for_timeout(1500)
                log.info("PASO 9 OK")

                # ── PASO 10: Confirmar popup ──────────────────────────────
                log.info("PASO 10: Confirmando popup")
                try:
                    await page.wait_for_selector(
                        'button:has-text("Aceptar"), .swal2-confirm, '
                        'button:has-text("OK"), button:has-text("Sí")',
                        timeout=6000,
                    )
                    await page.click(
                        'button:has-text("Aceptar"), .swal2-confirm, '
                        'button:has-text("OK"), button:has-text("Sí")'
                    )
                    log.info("PASO 10 OK — popup aceptado")
                except PWTimeout:
                    log.info("PASO 10 — sin popup HTML (dialog nativo manejado)")

                # ── PASO 11: Capturar número radicado ─────────────────────
                await page.wait_for_timeout(2000)
                numero_radicado = await _capturar_radicado(page)
                log.info("=== ÉXITO — Radicado: %s ===", numero_radicado)
                return ResultadoRadicacion(
                    True, numero_radicado, "Incapacidad radicada exitosamente en SURA."
                )

            except PWTimeout as e:
                log.error("TIMEOUT: %s", str(e))
                return ResultadoRadicacion(False, None, f"Timeout: {e}")
            except Exception as e:
                log.error("ERROR en paso: %s", str(e))
                return ResultadoRadicacion(False, None, f"Error: {e}")
            finally:
                await context.close()
                await browser.close()
                log.info("Browser cerrado")


_bot_sura = BotSura()


async def radicar_en_sura(datos: DatosIncapacidad, headless: bool = True) -> ResultadoRadicacion:
    return await _bot_sura.radicar(datos, headless=headless)
