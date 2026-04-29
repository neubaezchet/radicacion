"""
Bot SURA — construido desde el codegen real.
Radica incapacidades en el portal EPS SURA.
"""

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

log = logging.getLogger(__name__)

SURA_URL = (
    "https://login.sura.com/sso/servicelogin.aspx"
    "?continueTo=https%3A%2F%2Fepsapps.suramericana.com%2FSemp%2F"
    "&service=epssura"
)

PDF_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp/radicaciones"))

# Mapa dígito → código ASCII del botón PIN de SURA
# 0=48, 1=49, 2=50 ... 9=57
ASCII_PIN = {str(d): str(48 + d) for d in range(10)}


def _debug_teclado_virtual(page):
    """Captura información del teclado virtual para debugging."""
    try:
        debug_dir = Path(tempfile.gettempdir()) / "sura_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Capturar HTML del teclado
        html_path = debug_dir / f"teclado_virtual_{timestamp}.html"
        botones = page.locator("button").all()
        html_content = "<h1>Botones del Teclado Virtual</h1>\n<table border='1'><tr><th>Index</th><th>Texto</th><th>Atributos</th></tr>\n"
        
        for i, btn in enumerate(botones):
            try:
                texto = btn.text_content().strip()
                html_attr = page.evaluate("el => el.outerHTML", btn.element_handle())
                html_content += f"<tr><td>{i}</td><td>{texto}</td><td><pre>{html_attr}</pre></td></tr>\n"
            except:
                pass
        
        html_content += "</table>"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        log.info("[SURA DEBUG] Estructura del teclado guardada en: %s", html_path)
        
        # También guardar screenshot
        screen_path = debug_dir / f"teclado_virtual_{timestamp}.png"
        page.screenshot(path=str(screen_path), full_page=False)
        log.info("[SURA DEBUG] Screenshot guardado en: %s", screen_path)
        
    except Exception as e:
        log.warning("[SURA DEBUG] No se pudo capturar info del teclado: %s", str(e))


def _digitar_pin(page, pin: str) -> None:
    """
    Digita el PIN con simulación estricta de ratón humano para evitar 
    los bloqueos de isTrusted y velocidad del portal SURA.
    
    Estrategia:
    - Usa bounding_box() para obtener coordenadas exactas del botón
    - page.mouse.move() con steps=5 para viaje gradual del ratón
    - page.mouse.down() + wait + page.mouse.up() para clic lento (200ms)
    - Pausas realistas entre dígitos (800ms)
    """
    log.info("[SURA] Abriendo teclado virtual (simulación humana de ratón)")
    
    # 1. Clic en el campo para abrir el teclado
    page.locator("#suraPassword").click(delay=150)
    page.wait_for_timeout(500)
    
    # 2. Esperamos a que la caja del teclado termine de hacer su animación
    page.locator(".ui-keyboard-keyset").wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    log.info("[SURA] Teclado virtual detectado y listo")

    # 3. Digitar cada número con movimientos humanos
    for i, digito in enumerate(pin):
        log.info("[SURA] PIN %d/%d digito=%s", i + 1, len(pin), digito)
        
        try:
            # Encontramos el botón usando el atributo data-value
            boton = page.locator(f'button.ui-keyboard-button[data-value="{digito}"]')
            boton.wait_for(state="visible", timeout=5000)
            
            # Obtener las coordenadas EXACTAS del botón en la pantalla
            caja = boton.bounding_box()
            if caja:
                # Calcular el centro exacto del botón
                centro_x = caja["x"] + (caja["width"] / 2)
                centro_y = caja["y"] + (caja["height"] / 2)
                
                # MOVER el ratón hacia el botón poco a poco (steps=5)
                # Esto dispara eventos mouseover legítimamente
                page.mouse.move(centro_x, centro_y, steps=5)
                page.wait_for_timeout(300)  # Pausa mientras se pone el asterisco
                
                # CLIC LENTO: Bajar botón, esperar, soltar botón
                # Esto hace que isTrusted=true y la velocidad sea humana
                page.mouse.down()
                page.wait_for_timeout(200)  # Mantener el clic apretado 200ms
                page.mouse.up()
                
                log.info("[SURA] ✓ Dígito %s digitado (clic lento con mouse.down/up)", digito)
            else:
                # Fallback por si la caja no se detecta
                log.warning("[SURA] No se pudo obtener bounding_box, usando click() simple")
                boton.hover()
                page.wait_for_timeout(300)
                boton.click(delay=200)
                log.info("[SURA] ✓ Dígito %s digitado (fallback)", digito)
            
            # Pausa larga entre números (como alguien buscando la tecla)
            page.wait_for_timeout(800)
            
        except Exception as e:
            log.error("[SURA] Error digitando dígito %s: %s", digito, str(e))
            _debug_teclado_virtual(page)
            raise

    # 4. Botón de Aceptar (✔) - con mismo tratamiento humanizado
    log.info("[SURA] Confirmando PIN con botón Aceptar...")
    
    try:
        boton_aceptar = page.locator("button.ui-keyboard-accept")
        boton_aceptar.wait_for(state="visible", timeout=5000)
        
        caja_acc = boton_aceptar.bounding_box()
        if caja_acc:
            centro_x = caja_acc["x"] + (caja_acc["width"] / 2)
            centro_y = caja_acc["y"] + (caja_acc["height"] / 2)
            page.mouse.move(centro_x, centro_y, steps=5)
            page.wait_for_timeout(300)
            page.mouse.down()
            page.wait_for_timeout(200)
            page.mouse.up()
            log.info("[SURA] ✓ PIN confirmado (mouse.down/up)")
        else:
            boton_aceptar.click(delay=200)
            log.info("[SURA] ✓ PIN confirmado (fallback click)")
            
    except Exception as e:
        log.warning("[SURA] Error con accept, intentando actionkey[enter]...")
        try:
            page.locator(".ui-keyboard-actionkey[name='enter']").click()
            log.info("[SURA] ✓ PIN confirmado (actionkey[enter])")
        except Exception as fallback_error:
            log.error("[SURA] Error confirmando PIN: %s", str(fallback_error))
            raise
    
    page.wait_for_timeout(600)
    log.info("[SURA] Teclado virtual completado exitosamente")


def radicar_sura(
    tipo_documento: str,
    numero_documento: str,
    clave: str,
    numero_incapacidad: str,
    prefijo_incapacidad: str = "0",
    documento_trabajador: str = None,
    fecha_inicio: str = None,
    headless: bool = True,
) -> dict:
    """
    Radica una incapacidad en el portal EPS SURA.

    Parámetros:
        tipo_documento      : "C" = Cédula, "A" = NIT
        numero_documento    : número del empleador
        clave               : PIN numérico ej: "22025"
        numero_incapacidad  : número de la incapacidad
        prefijo_incapacidad : prefijo, por defecto "0"
        documento_trabajador: cédula del trabajador (para el PDF)
        fecha_inicio        : fecha inicio incapacidad (para el PDF)
        headless            : True = sin ventana (servidor), False = con ventana (pruebas)

    Retorna dict con:
        exitoso, numero_radicado, mensaje, pdf_path
    """

    log.info("[SURA] === INICIO ===")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1280,900",
            ],
        )
        
        # Grabar video si no es headless (para debugging)
        video_path = None
        if not headless:
            video_dir = Path(tempfile.gettempdir()) / "sura_videos"
            video_dir.mkdir(parents=True, exist_ok=True)
            video_path = str(video_dir / f"sura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm")
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-CO",
            timezone_id="America/Bogota",
            record_video_dir=str(Path(tempfile.gettempdir()) / "sura_videos") if not headless else None,
        )
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
        )
        page = context.new_page()

        try:
            # ── PASO 1: Abrir portal ──────────────────────────────────────
            log.info("[SURA] PASO 1: Abriendo portal")
            page.goto(SURA_URL, wait_until="domcontentloaded", timeout=30000)

            # ── PASO 2: Tipo de documento ─────────────────────────────────
            log.info("[SURA] PASO 2: Tipo documento = %s", tipo_documento)
            page.locator("#ctl00_ContentMain_suraType").select_option(tipo_documento)
            page.wait_for_timeout(500)

            # ── PASO 3: Número de documento ───────────────────────────────
            log.info("[SURA] PASO 3: Número = %s", numero_documento)
            page.locator("#suraName").click()
            page.locator("#suraName").fill(numero_documento)
            page.wait_for_timeout(400)

            # ── PASO 4: PIN ───────────────────────────────────────────────
            log.info("[SURA] PASO 4: Digitando PIN")
            _digitar_pin(page, clave)
            
            # Cerrar teclado virtual presionando Escape
            log.info("[SURA] Cerrando teclado virtual")
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)

            # ── PASO 5: Iniciar sesión ────────────────────────────────────
            log.info("[SURA] PASO 5: Iniciando sesión")
            
            # Click en "Iniciar sesión" via JavaScript
            boton_iniciar = page.get_by_role("button", name="Iniciar sesión")
            boton_iniciar.evaluate("el => el.click()")
            
            # Esperar que el SSO redirija al portal (hasta 60 segundos)
            page.wait_for_url("**/Semp/**", timeout=60000)
            page.get_by_role("link", name="Empleadores").wait_for(
                state="visible", timeout=60000
            )
            log.info("[SURA] PASO 5 OK — portal cargado")

            # ── PASO 6: Hover Empleadores → Empresa ───────────────────────
            log.info("[SURA] PASO 6: Navegando al menú Empresa")
            page.get_by_role("link", name="Empleadores").hover()
            page.wait_for_timeout(800)
            page.get_by_role("link", name="Empresa").click()
            page.wait_for_timeout(500)
            log.info("[SURA] PASO 6 OK")

            # ── PASO 7: Seleccionar empresa ───────────────────────────────
            log.info("[SURA] PASO 7: Seleccionando empresa")
            page.locator("#SempTranEmpresa").wait_for(state="visible", timeout=15000)
            page.locator("#SempTranEmpresa").click()
            page.wait_for_load_state("networkidle", timeout=15000)
            log.info("[SURA] PASO 7 OK")

            # ── PASO 8: Radicar Incapacidades ─────────────────────────────
            log.info("[SURA] PASO 8: Click en Radicar Incapacidades")
            page.get_by_role("link", name="Radicar Incapacidades").wait_for(
                state="visible", timeout=15000
            )
            page.get_by_role("link", name="Radicar Incapacidades").click()
            page.wait_for_load_state("networkidle", timeout=15000)
            log.info("[SURA] PASO 8 OK")

            # ── PASO 9: Formulario en iframe ──────────────────────────────
            log.info("[SURA] PASO 9: Llenando formulario")
            frame = (
                page.frame_locator('iframe[name="index1"]')
                    .frame_locator("#contenido")
            )
            frame.locator("body").wait_for(state="visible", timeout=10000)

            # Prefijo
            frame.locator('[id="radicarIncapacidad:tipoIncapacidad"]').wait_for(
                state="visible", timeout=8000
            )
            frame.locator('[id="radicarIncapacidad:tipoIncapacidad"]').click()
            frame.locator('[id="radicarIncapacidad:tipoIncapacidad"]').fill(
                prefijo_incapacidad
            )
            page.wait_for_timeout(300)

            # Número de incapacidad
            frame.locator('[id="radicarIncapacidad:numeroIncapacidad"]').wait_for(
                state="visible", timeout=8000
            )
            frame.locator('[id="radicarIncapacidad:numeroIncapacidad"]').click()
            frame.locator('[id="radicarIncapacidad:numeroIncapacidad"]').fill(
                numero_incapacidad
            )
            page.wait_for_timeout(300)

            # Click fuera para que el portal valide los campos
            frame.locator("html").click()
            page.wait_for_timeout(600)

            # Botón Radicar
            frame.get_by_role("link", name="Radicar").wait_for(
                state="visible", timeout=8000
            )
            frame.get_by_role("link", name="Radicar").click()
            page.wait_for_load_state("networkidle", timeout=20000)
            log.info("[SURA] PASO 9 OK")

            # ── PASO 10: Extraer número de radicado ───────────────────────
            radicado = _extraer_radicado(page, frame)
            pdf_path = _guardar_pdf(page, documento_trabajador, fecha_inicio)

            log.info("[SURA] === FIN OK === Radicado: %s", radicado)
            return {
                "exitoso": True,
                "numero_radicado": radicado,
                "mensaje": "Radicación exitosa",
                "pdf_path": pdf_path,
            }

        except Exception as ex:
            log.error("[SURA] ERROR: %s", str(ex), exc_info=True)
            
            # Guardar screenshot del error
            try:
                screenshot_dir = Path(tempfile.gettempdir()) / "sura_errors"
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = screenshot_dir / f"error_{timestamp}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                log.info("[SURA] Screenshot de error guardado en: %s", screenshot_path)
            except Exception as screenshot_error:
                log.error("[SURA] Error capturando screenshot: %s", screenshot_error)
            
            return {
                "exitoso": False,
                "numero_radicado": None,
                "mensaje": f"Error: {str(ex)[:300]}",
                "pdf_path": None,
            }

        finally:
            context.close()
            browser.close()


def _extraer_radicado(page, frame) -> str:
    """Busca el número de radicado en el texto de la página."""
    for fuente in [frame, page]:
        try:
            texto = fuente.locator("body").inner_text(timeout=5000)
            match = re.search(r"[Rr]adicado[:\s#Nº]*(\d+)", texto)
            if match:
                return match.group(1)
        except Exception:
            continue
    return "RADICADO_NO_ENCONTRADO"


def _guardar_pdf(page, documento_trabajador: str, fecha_inicio: str) -> str | None:
    """Guarda la página actual como PDF."""
    try:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        fecha = fecha_inicio or datetime.now().strftime("%d_%m_%Y")
        cedula = documento_trabajador or "sin_cedula"
        ruta = PDF_DIR / f"{cedula}_{fecha}.pdf"
        page.pdf(path=str(ruta))
        return str(ruta)
    except Exception:
        return None


# ── Punto de entrada para pruebas locales ────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    resultado = radicar_sura(
        tipo_documento="C",           # C = Cédula
        numero_documento="51899483",  # reemplaza con tu número
        clave="22025",                # reemplaza con tu PIN
        numero_incapacidad="12345",   # reemplaza con el número real
        prefijo_incapacidad="0",
        documento_trabajador="987654321",
        fecha_inicio="26_04_2026",
        headless=False,               # False = con ventana para ver qué hace
    )

    print("\n=== RESULTADO ===")
    print(f"Exitoso      : {resultado['exitoso']}")
    print(f"Radicado     : {resultado['numero_radicado']}")
    print(f"Mensaje      : {resultado['mensaje']}")
    print(f"PDF          : {resultado['pdf_path']}")
