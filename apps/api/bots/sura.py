"""
Bot SURA — 100% basado en grabación real de playwright codegen.
Adaptado del flujo capturado: grabacion_sura.py
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from bots.base import DatosRadicacion, ResultadoRadicacion

log = logging.getLogger(__name__)

SURA_URL = (
    "https://login.sura.com/sso/servicelogin.aspx"
    "?continueTo=https%3A%2F%2Fepsapps.suramericana.com%2FSemp%2F"
    "&service=epssura"
)

MOCK_RADICACION = os.getenv("MOCK_RADICACION", "false").lower() == "true"
PDF_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp/radicaciones"))

# Mapa ASCII: dígito → código button
ASCII_PIN = {str(d): str(48 + d) for d in range(10)}


def radicar_sura(datos: DatosRadicacion) -> ResultadoRadicacion:
    if MOCK_RADICACION:
        log.info("[SURA] MODO MOCK")
        return ResultadoRadicacion(
            exitoso=True,
            numero_radicado="MOCK-20260425-001",
            mensaje="Radicación simulada",
            pdf_path=None,
        )

    log.info("[SURA] === INICIO ===")
    cred = datos.credenciales

    try:
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

            # PASO 1: Login page
            log.info("[SURA] PASO 1: Abriendo login")
            page.goto(SURA_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)

            # PASO 2: Tipo documento
            log.info("[SURA] PASO 2: Tipo documento = %s", cred.tipo_documento)
            page.locator("#ctl00_ContentMain_suraType").select_option(cred.tipo_documento)
            page.wait_for_timeout(500)

            # PASO 3: Número documento
            log.info("[SURA] PASO 3: Número = %s", cred.numero_documento)
            page.locator("#suraName").click()
            page.locator("#suraName").fill(cred.numero_documento)
            page.wait_for_timeout(500)

            # PASO 4: Teclado virtual + PIN
            log.info("[SURA] PASO 4: Digitando PIN")
            page.locator("#suraPassword").click()
            page.wait_for_timeout(800)

            for digito in cred.clave:
                page.locator(f'button[name="{ASCII_PIN[digito]}"]').click()
                page.wait_for_timeout(100)

            # Aceptar PIN: div().nth(3) según grabación
            page.locator("div").nth(3).click()
            page.wait_for_timeout(400)

            # PASO 5: Submit login
            log.info("[SURA] PASO 5: Iniciar sesión")
            page.get_by_role("button", name="Iniciar sesión").click()
            page.wait_for_load_state("networkidle", timeout=20000)

            # PASO 6: Empleadores
            log.info("[SURA] PASO 6: Link Empleadores")
            page.get_by_role("link", name="Empleadores").click()
            page.wait_for_load_state("networkidle", timeout=15000)

            # PASO 7: Seleccionar empresa
            log.info("[SURA] PASO 7: Seleccionar empresa")
            page.locator("#SempTranEmpresa").click()
            page.wait_for_load_state("networkidle", timeout=10000)

            # PASO 8: Radicar Incapacidades
            log.info("[SURA] PASO 8: Radicar Incapacidades")
            page.get_by_role("link", name="Radicar Incapacidades").click()
            page.wait_for_load_state("networkidle", timeout=15000)

            # PASO 9-11: Formulario radicación
            log.info("[SURA] PASO 9-11: Llenando formulario")
            frame = page.frame_locator('iframe[name="index1"]').frame_locator("#contenido")

            prefijo = datos.prefijo_incapacidad or "0"
            frame.locator('[id="radicarIncapacidad:tipoIncapacidad"]').click()
            frame.locator('[id="radicarIncapacidad:tipoIncapacidad"]').fill(prefijo)
            page.wait_for_timeout(300)

            frame.locator('[id="radicarIncapacidad:numeroIncapacidad"]').click()
            frame.locator('[id="radicarIncapacidad:numeroIncapacidad"]').fill(datos.numero_incapacidad)
            page.wait_for_timeout(300)

            frame.locator("html").click()
            page.wait_for_timeout(500)

            frame.get_by_role("link", name="Radicar").click()
            page.wait_for_load_state("networkidle", timeout=20000)

            # PASO 12: Extraer radicado
            log.info("[SURA] PASO 12: Extrayendo número radicado")
            radicado = _extraer_radicado(page, frame)

            # PASO 13: Guardar PDF
            pdf_path = _guardar_pdf(page, datos)

            log.info("[SURA] === OK === Radicado: %s", radicado)
            return ResultadoRadicacion(
                exitoso=True,
                numero_radicado=radicado,
                mensaje="Radicación exitosa",
                pdf_path=pdf_path,
            )

        finally:
            context.close()
            browser.close()

    except Exception as ex:
        log.error("[SURA] ERROR: %s", str(ex))
        return ResultadoRadicacion(
            exitoso=False,
            numero_radicado=None,
            mensaje=f"Error: {str(ex)[:300]}",
            pdf_path=None,
        )


def _extraer_radicado(page, frame) -> str:
    """Busca el número radicado en la respuesta."""
    for fuente in [frame, page]:
        try:
            texto = fuente.locator("body").inner_text(timeout=5000)
            match = re.search(r"[Rr]adicado[:\s#Nº]*(\d+)", texto)
            if match:
                radicado = match.group(1)
                log.info("[SURA] Radicado encontrado: %s", radicado)
                return radicado
        except Exception:
            continue
    log.warning("[SURA] Radicado no encontrado")
    return "RADICADO_NO_ENCONTRADO"


def _guardar_pdf(page, datos: DatosRadicacion) -> str | None:
    """Guarda screenshot como PDF."""
    try:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datos.fecha_inicio_incapacidad or datetime.now().strftime("%d %m %Y")
        cedula = datos.documento_trabajador or "sin_cedula"
        nombre = f"{cedula} {fecha}.pdf"
        ruta = PDF_DIR / nombre
        page.pdf(path=str(ruta))
        log.info("[SURA] PDF guardado: %s", ruta)
        return str(ruta)
    except Exception:
        return None


async def radicar_en_sura(datos, headless: bool = True) -> ResultadoRadicacion:
    """Wrapper async para FastAPI."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, radicar_sura, datos)
