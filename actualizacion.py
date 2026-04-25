"""
Bot Playwright para radicación de incapacidades en EPS SURA.
Selectores extraídos del DOM real del portal (login.sura.com).

FORMULARIO DE LOGIN (tab "Asesor / Empleador" = #tabInternet):
  - Select tipo doc : select#ctl00_ContentMain_suraType  (name="ctl00$ContentMain$suraType")
  - Input número    : input#suraName                     (name="suraName", maxlength=19)
  - Input clave     : input#suraPassword                 (name="suraPassword", maxlength=4)
      → activa teclado virtual jQuery al recibir foco
  - Botón login     : input#session-internet

TECLADO VIRTUAL (div.ui-keyboard):
  - Cada tecla      : button.ui-keyboard-button[data-value="X"]   (X = dígito 0-9)
  - Borrar          : button.ui-keyboard-button[name="bksp"]
  - Aceptar/Enter   : button.ui-keyboard-button[name="accept"]

VALORES del select (del DOM real):
  C  → CEDULA
  E  → CEDULA EXTRANJERIA
  D  → DIPLOMÁTICO
  X  → DOC.IDENT. DE EXTRANJEROS
  F  → IDENT. FISCAL PARA EXT.
  A  → NIT
  CA → NIT PERSONAS NATURALES
  N  → NUIP
  P  → PASAPORTE
  R  → REGISTRO CIVIL
  T  → TARJ.IDENTIDAD
  TC → CERTIFICADO NACIDO VIVO
  TP → PASAPORTE (segunda opción)
  TE → PERMISO ESPECIAL PERMANENCIA
  TS → SALVOCONDUCTO DE PERMANENCIA
  TF → PERMISO ESPECIAL FORMACN PEPFF
  TT → PERMISO POR PROTECCION TEMPORL
"""

import asyncio
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from base import DatosRadicacion, ResultadoRadicacion

log = logging.getLogger(__name__)

SURA_PORTAL_URL = (
    "https://login.sura.com/sso/servicelogin.aspx"
    "?continueTo=https%3A%2F%2Fepsapps.suramericana.com%2FSemp%2F"
    "&service=epssura"
)

PORTAL_RADICACION_URL = (
    "https://epsapps.suramericana.com/Semp/faces/pos/radicarIncapacidad/parametros.jspx"
)

# Mapa label → value del select (del DOM real)
TIPO_DOC_MAP = {
    "CEDULA":                       "C",
    "CEDULA EXTRANJERIA":           "E",
    "DIPLOMATICO":                  "D",
    "DOC.IDENT. DE EXTRANJEROS":    "X",
    "IDENT. FISCAL PARA EXT.":      "F",
    "NIT":                          "A",
    "NIT PERSONAS NATURALES":       "CA",
    "NUIP":                         "N",
    "PASAPORTE":                    "P",
    "REGISTRO CIVIL":               "R",
    "TARJ.IDENTIDAD":               "T",
    "CERTIFICADO NACIDO VIVO":      "TC",
    "PERMISO ESPECIAL PERMANENCIA": "TE",
    "SALVOCONDUCTO DE PERMANENCIA": "TS",
    "PERMISO ESPECIAL FORMACN PEPFF": "TF",
    "PERMISO POR PROTECCION TEMPORL": "TT",
}

MOCK_RADICACION = os.getenv("MOCK_RADICACION", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _esperar_cloudflare(page) -> None:
    """Espera a que Cloudflare libere la página (hasta 25 s)."""
    log.info("[SURA] Esperando posible challenge Cloudflare...")
    for i in range(25):
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=2000)
            titulo = await page.title()
            url = page.url
            log.info("[SURA]   [CF %d] title='%s' url=%s", i, titulo, url[:80])
            palabras_bloqueo = ("verificando", "checking", "just a moment", "please wait")
            if not any(p in titulo.lower() for p in palabras_bloqueo):
                log.info("[SURA] Cloudflare superado o no presente")
                return
        except Exception as ex:
            log.info("[SURA]   Navegación en progreso (%d): %s", i, str(ex)[:80])
        await page.wait_for_timeout(1000)
    log.warning("[SURA] Timeout Cloudflare — continuando de todas formas")


async def _digitar_clave_teclado_virtual(page, clave: str) -> None:
    """
    Hace clic en cada dígito del teclado virtual jQuery.
    Selector confirmado del DOM: button.ui-keyboard-button[data-value="X"]
    El teclado aparece al hacer foco en input#suraPassword.
    """
    log.info("[SURA] Activando teclado virtual...")

    # Foco en el campo de clave para que aparezca el teclado
    campo = page.locator("input#suraPassword")
    await campo.click()
    await page.wait_for_timeout(800)  # animación del teclado

    # Esperar a que el teclado sea visible
    teclado = page.locator("div.ui-keyboard")
    try:
        await teclado.wait_for(state="visible", timeout=8000)
        log.info("[SURA] Teclado virtual visible")
    except PWTimeout:
        log.error("[SURA] El teclado virtual no apareció")
        raise

    # Pulsar cada dígito
    for i, digito in enumerate(clave):
        selector_tecla = f'button.ui-keyboard-button[data-value="{digito}"]'
        tecla = page.locator(selector_tecla)
        try:
            await tecla.wait_for(state="visible", timeout=4000)
            await tecla.click()
            log.info("[SURA]   Dígito %d/%d ('%s') pulsado", i + 1, len(clave), digito)
            await page.wait_for_timeout(200)
        except PWTimeout:
            log.error("[SURA] No se encontró la tecla '%s' en el teclado virtual", digito)
            # Capturar HTML del teclado para debug
            html_teclado = await page.locator("div.ui-keyboard").inner_html()
            log.error("[SURA] HTML teclado: %s", html_teclado[:1000])
            raise

    # Pulsar el botón Aceptar (✔)
    aceptar = page.locator('button.ui-keyboard-button[name="accept"]')
    await aceptar.wait_for(state="visible", timeout=4000)
    await aceptar.click()
    log.info("[SURA] Clave ingresada — botón Aceptar pulsado")
    await page.wait_for_timeout(500)


async def _login(page, datos: DatosRadicacion) -> None:
    """Completa el formulario de login en el tab de empleadores (#tabInternet)."""

    cred = datos.credenciales

    # PASO 2 — Tipo de documento
    log.info("[SURA] PASO 2: Seleccionando tipo de documento '%s'", cred.tipo_documento)
    select = page.locator("select#ctl00_ContentMain_suraType")
    await select.wait_for(state="visible", timeout=10000)

    # El tipo_documento puede llegar como label ("CEDULA") o como value ("C")
    tipo_val = cred.tipo_documento.upper()
    if tipo_val in TIPO_DOC_MAP.values():
        # Ya es el value del select
        await select.select_option(value=tipo_val)
    elif tipo_val in TIPO_DOC_MAP:
        # Es el label, convertir a value
        await select.select_option(value=TIPO_DOC_MAP[tipo_val])
    else:
        # Intentar por label directo (por si el portal tiene variaciones)
        await select.select_option(label=cred.tipo_documento)
    log.info("[SURA] PASO 2 OK")

    # PASO 3 — Número de identificación
    log.info("[SURA] PASO 3: Ingresando número '%s'", cred.numero_documento)
    numero_input = page.locator("input#suraName")
    await numero_input.wait_for(state="visible", timeout=8000)
    await numero_input.click()
    await numero_input.fill(cred.numero_documento)
    log.info("[SURA] PASO 3 OK")

    # PASO 4 — Clave con teclado virtual
    log.info("[SURA] PASO 4: Ingresando clave con teclado virtual")
    await _digitar_clave_teclado_virtual(page, cred.clave)
    log.info("[SURA] PASO 4 OK")

    # PASO 5 — Click en "Iniciar sesión"
    log.info("[SURA] PASO 5: Haciendo clic en Iniciar sesión")
    btn_login = page.locator("input#session-internet")
    await btn_login.wait_for(state="visible", timeout=5000)
    await btn_login.click()
    log.info("[SURA] PASO 5 OK — esperando navegación post-login")

    # Esperar a que el portal cargue el dashboard
    try:
        await page.wait_for_url("**/Semp/**", timeout=20000)
        log.info("[SURA] Login exitoso — URL: %s", page.url[:80])
    except PWTimeout:
        # Verificar si hay mensaje de error de credenciales
        error_span = page.locator("#errormsgtab2")
        if await error_span.is_visible():
            msg = await error_span.inner_text()
            raise RuntimeError(f"Credenciales incorrectas: {msg}")
        titulo = await page.title()
        url_actual = page.url
        log.warning("[SURA] Timeout post-login. Title='%s' URL=%s", titulo, url_actual[:80])
        raise RuntimeError("Timeout esperando dashboard post-login")


async def _navegar_a_radicacion(page) -> None:
    """Navega directamente a la URL de radicación de incapacidades."""
    log.info("[SURA] PASO 6: Navegando a módulo de radicación")
    await page.goto(PORTAL_RADICACION_URL, wait_until="networkidle", timeout=30000)
    url_actual = page.url
    log.info("[SURA] PASO 6 OK — URL radicación: %s", url_actual[:100])


async def _radicar_incapacidad_digitalizada(page, datos: DatosRadicacion) -> str:
    """
    Flujo 1: Incapacidad digitalizada (emitida directamente por SURA).
    Solo se ingresa el número; SURA autocompleta el resto.
    Retorna el número de radicado.
    """
    log.info("[SURA] FLUJO: Incapacidad digitalizada")

    # Campo prefijo de incapacidad
    if datos.prefijo_incapacidad:
        log.info("[SURA] Ingresando prefijo '%s'", datos.prefijo_incapacidad)
        prefijo_input = page.locator(
            'input[id*="prefijo"], input[name*="prefijo"], '
            'input[placeholder*="prefijo"]'
        ).first
        await prefijo_input.wait_for(state="visible", timeout=8000)
        await prefijo_input.fill(datos.prefijo_incapacidad)

    # Número de incapacidad
    log.info("[SURA] Ingresando número de incapacidad '%s'", datos.numero_incapacidad)
    num_input = page.locator(
        'input[id*="numero"][id*="incapacidad"], '
        'input[name*="numero"][name*="incapacidad"], '
        'input[id*="numInc"], input[name*="numInc"]'
    ).first
    await num_input.wait_for(state="visible", timeout=8000)
    await num_input.fill(datos.numero_incapacidad)

    # Botón buscar / consultar
    btn_consultar = page.locator(
        'input[value*="Consultar"], button:has-text("Consultar"), '
        'input[value*="Buscar"], button:has-text("Buscar")'
    ).first
    await btn_consultar.wait_for(state="visible", timeout=8000)
    await btn_consultar.click()
    await page.wait_for_load_state("networkidle", timeout=15000)

    # Botón radicar / confirmar
    btn_radicar = page.locator(
        'input[value*="Radicar"], button:has-text("Radicar"), '
        'input[value*="Confirmar"], button:has-text("Confirmar")'
    ).first
    await btn_radicar.wait_for(state="visible", timeout=10000)
    await btn_radicar.click()
    await page.wait_for_load_state("networkidle", timeout=20000)

    return await _extraer_numero_radicado(page)


async def _radicar_transcripcion(page, datos: DatosRadicacion) -> str:
    """
    Flujo 2: Transcripción de incapacidad (no emitida por SURA).
    Requiere adjuntar PDF y completar datos adicionales.
    Retorna el número de radicado.
    """
    log.info("[SURA] FLUJO: Transcripción de incapacidad")

    # Número de incapacidad (campo libre)
    num_input = page.locator(
        'input[id*="numero"], input[name*="numero"]'
    ).first
    await num_input.wait_for(state="visible", timeout=8000)
    await num_input.fill(datos.numero_incapacidad)

    # Documento de identidad del trabajador
    if datos.documento_trabajador:
        log.info("[SURA] Ingresando doc trabajador '%s'", datos.documento_trabajador)
        doc_input = page.locator(
            'input[id*="trabajador"], input[name*="trabajador"], '
            'input[id*="afiliado"], input[name*="afiliado"]'
        ).first
        try:
            await doc_input.wait_for(state="visible", timeout=5000)
            await doc_input.fill(datos.documento_trabajador)
        except PWTimeout:
            log.warning("[SURA] Campo documento trabajador no encontrado, continuando")

    # Adjuntar PDF de la incapacidad
    if datos.pdf_incapacidad:
        log.info("[SURA] Adjuntando PDF de incapacidad")
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(timeout=8000)
        await file_input.set_input_files(datos.pdf_incapacidad)
        log.info("[SURA] PDF adjuntado")

    # Adjuntar soportes adicionales
    if datos.soportes_adicionales:
        for i, soporte in enumerate(datos.soportes_adicionales):
            log.info("[SURA] Adjuntando soporte adicional %d", i + 1)
            file_inputs = page.locator('input[type="file"]')
            count = await file_inputs.count()
            if count > i + 1:
                await file_inputs.nth(i + 1).set_input_files(soporte)

    # Botón radicar
    btn_radicar = page.locator(
        'input[value*="Radicar"], button:has-text("Radicar"), '
        'input[value*="Guardar"], button:has-text("Guardar")'
    ).first
    await btn_radicar.wait_for(state="visible", timeout=10000)
    await btn_radicar.click()
    await page.wait_for_load_state("networkidle", timeout=30000)

    return await _extraer_numero_radicado(page)


async def _extraer_numero_radicado(page) -> str:
    """Extrae el número de radicado de la pantalla de confirmación."""
    log.info("[SURA] Extrayendo número de radicado...")

    selectores_radicado = [
        '[id*="radicado"]',
        '[id*="Radicado"]',
        '[id*="numero"][id*="rad"]',
        'span:has-text("Radicado")',
        'td:has-text("Radicado") + td',
        '.radicado',
        '#radicado',
    ]

    for sel in selectores_radicado:
        try:
            elem = page.locator(sel).first
            if await elem.is_visible():
                texto = (await elem.inner_text()).strip()
                if texto and any(c.isdigit() for c in texto):
                    log.info("[SURA] Radicado encontrado: '%s'", texto)
                    return texto
        except Exception:
            continue

    # Fallback: capturar screenshot y retornar texto de la página
    log.warning("[SURA] No se encontró número de radicado por selectores")
    try:
        contenido = await page.inner_text("body")
        # Buscar patrón numérico después de "Radicado" o "radicado"
        import re
        match = re.search(r"[Rr]adicado[:\s#]*(\d+)", contenido)
        if match:
            radicado = match.group(1)
            log.info("[SURA] Radicado por regex: '%s'", radicado)
            return radicado
    except Exception:
        pass

    return "RADICADO_PENDIENTE_REVISION"


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

async def radicar_sura(datos: DatosRadicacion) -> ResultadoRadicacion:
    """Punto de entrada del bot SURA."""

    if MOCK_RADICACION:
        log.info("[SURA] === MODO MOCK ===")
        return ResultadoRadicacion(
            exitoso=True,
            numero_radicado="MOCK-20260425-001",
            mensaje="Radicación simulada (MOCK_RADICACION=true)",
        )

    log.info("[SURA] === INICIANDO RADICACIÓN REAL SURA ===")
    log.info(
        "[SURA] Empleador tipo=%s num=%s",
        datos.credenciales.tipo_documento,
        datos.credenciales.numero_documento,
    )
    log.info(
        "[SURA] Trabajador=%s | Incapacidad=%s-%s | Transcripcion=%s",
        datos.documento_trabajador,
        datos.prefijo_incapacidad,
        datos.numero_incapacidad,
        datos.transcripcion,
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1280,900",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-CO",
            timezone_id="America/Bogota",
        )

        # Ocultar webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-CO', 'es'] });
        """)

        page = await context.new_page()

        try:
            # PASO 1 — Abrir portal
            log.info("[SURA] PASO 1: Abriendo portal de login")
            await page.goto(SURA_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            log.info("[SURA] PASO 1 OK — URL: %s", page.url[:80])

            await _esperar_cloudflare(page)

            # Login
            await _login(page, datos)

            # Navegar a radicación
            await _navegar_a_radicacion(page)

            # Ejecutar flujo según tipo
            if datos.transcripcion:
                numero_radicado = await _radicar_transcripcion(page, datos)
            else:
                numero_radicado = await _radicar_incapacidad_digitalizada(page, datos)

            log.info("[SURA] === RADICACIÓN COMPLETADA: %s ===", numero_radicado)
            return ResultadoRadicacion(
                exitoso=True,
                numero_radicado=numero_radicado,
                mensaje="Radicación exitosa",
            )

        except Exception as ex:
            log.error("[SURA] ERROR: %s", str(ex))
            # Capturar screenshot para diagnóstico
            try:
                screenshot_path = f"/tmp/sura_error_{asyncio.get_event_loop().time():.0f}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                log.info("[SURA] Screenshot guardado en %s", screenshot_path)
            except Exception:
                pass
            return ResultadoRadicacion(
                exitoso=False,
                numero_radicado=None,
                mensaje=f"Error en radicación: {str(ex)}",
            )

        finally:
            await browser.close()
            log.info("[SURA] Browser cerrado")
