"""
Bot SURA — selectores 100% confirmados por grabación real con playwright codegen.

LOGIN (tab empleadores #tabInternet):
  #ctl00_ContentMain_suraType     → select tipo documento
  #suraName                       → número identificación empleador
  #suraPassword                   → PIN (activa teclado virtual jQuery)
  button[name="NN"]               → dígito PIN (NN = código ASCII: 0=48..9=57)
  button name="✔"                 → aceptar PIN
  button "Iniciar sesión"         → submit

POST-LOGIN:
  link "Empleadores"              → menú principal
  #SempTranEmpresa                → selector de empresa
  link "Radicar Incapacidades"    → módulo de radicación

FORMULARIO (iframe[name="index1"] > #contenido):
  #radicarIncapacidad:tipoIncapacidad    → prefijo de la incapacidad (ej: "0")
  #radicarIncapacidad:numeroIncapacidad  → número de incapacidad (ej: "43445280")
  link "Radicar"                         → confirmar radicación

PDF de confirmación:
  Se guarda como screenshot PDF con nombre: {cedula_trabajador} {DD MM YYYY}.pdf
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from base import DatosRadicacion, ResultadoRadicacion

log = logging.getLogger(__name__)

SURA_URL = (
    "https://login.sura.com/sso/servicelogin.aspx"
    "?continueTo=https%3A%2F%2Fepsapps.suramericana.com%2FSemp%2F"
    "&service=epssura"
)

MOCK_RADICACION = os.getenv("MOCK_RADICACION", "false").lower() == "true"

# Directorio donde se guardan los PDFs de confirmación
PDF_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp/radicaciones"))

# Mapa ASCII para el teclado virtual: dígito → name del button
ASCII_DIGITO = {str(d): str(48 + d) for d in range(10)}
# "0"→"48", "1"→"49", ..., "9"→"57"


# ─────────────────────────────────────────────────────────────
# Teclado virtual
# ─────────────────────────────────────────────────────────────

def _digitar_pin(page, pin: str) -> None:
    """
    Abre el teclado virtual haciendo clic en #suraPassword,
    pulsa cada dígito por button[name="ASCII"] y acepta con ✔.
    """
    log.info("[SURA] Abriendo teclado virtual")
    page.locator("#suraPassword").click()
    page.wait_for_timeout(800)

    # Borrar valor previo por si acaso
    try:
        page.locator('button[name="bksp"]').dblclick(timeout=2000)
        page.wait_for_timeout(200)
    except Exception:
        pass

    for i, digito in enumerate(pin):
        page.locator(f'button[name="{ASCII_DIGITO[digito]}"]').click()
        log.info("[SURA]   PIN %d/%d", i + 1, len(pin))
        page.wait_for_timeout(150)

    page.get_by_role("button", name="✔").click()
    log.info("[SURA] PIN aceptado")
    page.wait_for_timeout(400)


# ─────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────

def _login(page, datos: DatosRadicacion) -> None:
    cred = datos.credenciales

    log.info("[SURA] PASO 2: tipo_doc=%s", cred.tipo_documento)
    page.locator("#ctl00_ContentMain_suraType").select_option(cred.tipo_documento)

    log.info("[SURA] PASO 3: numero=%s", cred.numero_documento)
    page.locator("#suraName").click()
    page.locator("#suraName").fill(cred.numero_documento)

    log.info("[SURA] PASO 4: PIN")
    _digitar_pin(page, cred.clave)

    log.info("[SURA] PASO 5: Iniciar sesión")
    page.get_by_role("button", name="Iniciar sesión").click()
    page.wait_for_load_state("networkidle", timeout=20000)
    log.info("[SURA] Login OK — %s", page.url[:80])


# ─────────────────────────────────────────────────────────────
# Navegación post-login
# ─────────────────────────────────────────────────────────────

def _navegar_radicacion(page) -> None:
    log.info("[SURA] PASO 6: Empleadores")
    page.get_by_role("link", name="Empleadores").click()
    page.wait_for_load_state("networkidle", timeout=15000)

    log.info("[SURA] PASO 7: Empresa")
    page.locator("#SempTranEmpresa").click()
    page.wait_for_load_state("networkidle", timeout=10000)

    log.info("[SURA] PASO 8: Radicar Incapacidades")
    page.get_by_role("link", name="Radicar Incapacidades").click()
    page.wait_for_load_state("networkidle", timeout=15000)
    log.info("[SURA] Formulario cargado")


# ─────────────────────────────────────────────────────────────
# Frame helper
# ─────────────────────────────────────────────────────────────

def _frame(page):
    """
    Retorna el frame_locator del formulario de radicación.
    Estructura confirmada: iframe[name="index1"] → #contenido
    """
    return (
        page.frame_locator('iframe[name="index1"]')
            .frame_locator("#contenido")
    )


# ─────────────────────────────────────────────────────────────
# Radicación — flujo digitalizada (confirmado por grabación)
# ─────────────────────────────────────────────────────────────

def _radicar_digitalizada(page, datos: DatosRadicacion) -> str:
    """
    Flujo incapacidad digitalizada por SURA.
    IDs confirmados del DOM real:
      #radicarIncapacidad:tipoIncapacidad   → prefijo ("0")
      #radicarIncapacidad:numeroIncapacidad → número
      link "Radicar"                        → confirmar
    """
    log.info("[SURA] FLUJO: Digitalizada")
    f = _frame(page)

    # Prefijo de incapacidad
    prefijo = datos.prefijo_incapacidad or "0"
    log.info("[SURA] Prefijo: %s", prefijo)
    campo_prefijo = f.locator('[id="radicarIncapacidad:tipoIncapacidad"]')
    campo_prefijo.click()
    campo_prefijo.fill(prefijo)

    # Número de incapacidad
    log.info("[SURA] Número: %s", datos.numero_incapacidad)
    campo_num = f.locator('[id="radicarIncapacidad:numeroIncapacidad"]')
    campo_num.dblclick()
    campo_num.fill(datos.numero_incapacidad)

    # Clic fuera para disparar validación del portal
    f.locator("html").click()
    page.wait_for_timeout(1000)

    # Radicar
    log.info("[SURA] Clic en Radicar")
    f.get_by_role("link", name="Radicar").click()
    page.wait_for_load_state("networkidle", timeout=20000)

    return _extraer_radicado(page, f)


# ─────────────────────────────────────────────────────────────
# Radicación — flujo transcripción (pendiente grabación)
# ─────────────────────────────────────────────────────────────

def _radicar_transcripcion(page, datos: DatosRadicacion) -> str:
    """
    Flujo transcripción — incapacidad NO emitida por SURA.
    TODO: grabar este flujo con codegen para confirmar IDs exactos.
    """
    log.info("[SURA] FLUJO: Transcripción")
    f = _frame(page)

    campo_num = f.locator('[id="radicarIncapacidad:numeroIncapacidad"]')
    campo_num.dblclick()
    campo_num.fill(datos.numero_incapacidad)

    if datos.pdf_incapacidad:
        f.locator('input[type="file"]').nth(0).set_input_files(datos.pdf_incapacidad)
        page.wait_for_timeout(1000)

    if datos.soportes_adicionales:
        for i, soporte in enumerate(datos.soportes_adicionales):
            try:
                f.locator('input[type="file"]').nth(i + 1).set_input_files(soporte)
                page.wait_for_timeout(500)
            except Exception:
                log.warning("[SURA] Soporte %d no adjuntado", i + 1)

    f.locator("html").click()
    page.wait_for_timeout(800)

    f.get_by_role("link", name="Radicar").click()
    page.wait_for_load_state("networkidle", timeout=30000)

    return _extraer_radicado(page, f)


# ─────────────────────────────────────────────────────────────
# Extracción del número radicado
# ─────────────────────────────────────────────────────────────

def _extraer_radicado(page, frame) -> str:
    log.info("[SURA] Buscando número de radicado...")
    for fuente in [frame, page]:
        try:
            texto = fuente.locator("body").inner_text(timeout=5000)
            match = re.search(r"[Rr]adicado[:\s#Nº]*(\d+)", texto)
            if match:
                radicado = match.group(1)
                log.info("[SURA] Radicado: %s", radicado)
                return radicado
        except Exception:
            continue
    log.warning("[SURA] Radicado no encontrado — revisar pantalla")
    return "RADICADO_PENDIENTE_REVISION"


# ─────────────────────────────────────────────────────────────
# Guardar PDF de confirmación
# ─────────────────────────────────────────────────────────────

def _guardar_pdf(page, datos: DatosRadicacion) -> str | None:
    """
    Guarda screenshot de la pantalla de confirmación como PDF.
    Nombre: {cedula_trabajador} {DD MM YYYY}.pdf
    Ej: 1085043374 18 04 2026.pdf
    """
    try:
        PDF_DIR.mkdir(parents=True, exist_ok=True)

        # Fecha inicial de incapacidad o fecha actual como fallback
        fecha = datos.fecha_inicio_incapacidad or datetime.now().strftime("%d %m %Y")
        cedula = datos.documento_trabajador or "sin_cedula"
        nombre = f"{cedula} {fecha}.pdf"
        ruta = PDF_DIR / nombre

        page.pdf(path=str(ruta))
        log.info("[SURA] PDF guardado: %s", ruta)
        return str(ruta)

    except Exception as ex:
        log.warning("[SURA] No se pudo guardar PDF: %s", ex)
        # Fallback: screenshot PNG
        try:
            ruta_png = PDF_DIR / f"{datos.documento_trabajador or 'error'}.png"
            page.screenshot(path=str(ruta_png), full_page=True)
            log.info("[SURA] Screenshot PNG guardado: %s", ruta_png)
            return str(ruta_png)
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────
# Punto de entrada principal
# ─────────────────────────────────────────────────────────────

def radicar_sura(datos: DatosRadicacion) -> ResultadoRadicacion:
    if MOCK_RADICACION:
        log.info("[SURA] MODO MOCK")
        return ResultadoRadicacion(
            exitoso=True,
            numero_radicado="MOCK-20260425-001",
            mensaje="Radicación simulada (MOCK_RADICACION=true)",
            pdf_path=None,
        )

    log.info("[SURA] === RADICACIÓN REAL ===")
    log.info("[SURA] Empleador: tipo=%s num=%s",
             datos.credenciales.tipo_documento, datos.credenciales.numero_documento)
    log.info("[SURA] Trabajador=%s | Incap=%s-%s | Transcripcion=%s",
             datos.documento_trabajador, datos.prefijo_incapacidad,
             datos.numero_incapacidad, datos.transcripcion)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1280,900",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-CO",
            timezone_id="America/Bogota",
        )
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
        )
        page = context.new_page()

        try:
            # PASO 1 — Portal
            log.info("[SURA] PASO 1: Abriendo portal")
            page.goto(SURA_URL, wait_until="domcontentloaded", timeout=30000)
            log.info("[SURA] PASO 1 OK — %s", page.title())

            # Login
            _login(page, datos)

            # Navegación
            _navegar_radicacion(page)

            # Radicación según flujo
            if datos.transcripcion:
                numero_radicado = _radicar_transcripcion(page, datos)
            else:
                numero_radicado = _radicar_digitalizada(page, datos)

            # Guardar PDF de confirmación
            pdf_path = _guardar_pdf(page, datos)

            log.info("[SURA] COMPLETADO — Radicado: %s | PDF: %s",
                     numero_radicado, pdf_path)

            return ResultadoRadicacion(
                exitoso=True,
                numero_radicado=numero_radicado,
                mensaje="Radicación exitosa",
                pdf_path=pdf_path,
            )

        except Exception as ex:
            log.error("[SURA] ERROR: %s", str(ex))
            try:
                page.screenshot(path="/tmp/sura_error.png", full_page=True)
                log.info("[SURA] Screenshot error en /tmp/sura_error.png")
            except Exception:
                pass
            return ResultadoRadicacion(
                exitoso=False,
                numero_radicado=None,
                mensaje=f"Error: {str(ex)}",
                pdf_path=None,
            )

        finally:
            context.close()
            browser.close()
            log.info("[SURA] Browser cerrado")
