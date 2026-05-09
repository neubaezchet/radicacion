"""
Bot Compensar — Radicación de incapacidades en portal corporativo.
Construido con Playwright basado en grabación real del portal.

Portal: https://seguridad.compensar.com/sign-in
       https://corporativo.compensar.com/salud/transacciones/...

Flujo:
1. Login en portal OIDC (NIT + contraseña)
2. Navega a Transacciones en Línea
3. Selecciona Salud
4. Va a Incapacidades
5. Busca incapacidad por número
6. Radica con documento adjunto (si aplica)
7. Extrae número de radicado
"""

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

log = logging.getLogger(__name__)

COMPENSAR_LOGIN_URL = "https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&_csrf=e42792d3-0389-46ad-ab2b-47b8602bcdeb&protocol=OIDC"

# Directorio para guardar evidencia
EVIDENCIA_DIR = Path(tempfile.gettempdir()) / "compensar_evidencia"
EVIDENCIA_DIR.mkdir(parents=True, exist_ok=True)


def radicar_en_compensar(datos: 'DatosRadicacion') -> 'ResultadoRadicacion':
    """
    Radica una incapacidad en el portal de Compensar.
    
    Basado en grabación real con Playwright codegen.
    
    Flujo:
    1. Login → NIT + contraseña
    2. Click "Transacciones en Línea"
    3. Click "Salud"
    4. Click "Incapacidades"
    5. Click "Radicar"
    6. Ingresa número de incapacidad
    7. Busca
    8. Carga
    9. Adjunta documento PDF (si transcripción=True)
    10. Radica
    11. Extrae número de radicado
    
    Args:
        datos: DatosRadicacion con credenciales y datos de la incapacidad
        
    Returns:
        ResultadoRadicacion con resultado de la operación
    """
    from .base import ResultadoRadicacion
    
    playwright = None
    browser = None
    context = None
    page = None
    numero_radicado = None
    
    try:
        log.info("[COMPENSAR] Iniciando radicación para incapacidad: %s", datos.numero_incapacidad)
        
        # Timestamp para evidencia
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Inicializar Playwright
        playwright = sync_playwright().start()
        
        # Configurar browser
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
        browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-default-apps",
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        page = context.new_page()
        page.set_default_timeout(30000)  # 30 segundos
        
        log.info("[COMPENSAR] Navegando a: %s", COMPENSAR_LOGIN_URL)
        page.goto(COMPENSAR_LOGIN_URL, wait_until="networkidle")
        
        # Manejar diálogo de detección de bot
        try:
            log.info("[COMPENSAR] Buscando diálogo de bot detection...")
            
            # Buscamos específicamente el botón con el texto 'Entiendo' (o 'Entendido' por si acaso cambia)
            # También usamos type="submit" para ser más precisos con el HTML del portal
            btn_entiendo = page.locator('button[type="submit"]:has-text("Entiendo"), button:has-text("Entendido")').first
            
            if btn_entiendo.is_visible(timeout=5000):
                log.info("[COMPENSAR] Encontrado diálogo 'Entiendo' - clickeando...")
                btn_entiendo.click()
                
                # Le damos un respiro al navegador para que cierre el modal animado
                page.wait_for_timeout(1000) 
                page.wait_for_load_state("networkidle", timeout=10000)
            else:
                log.info("[COMPENSAR] No fue necesario clickear 'Entiendo', no apareció.")
                
        except Exception as e:
            log.debug("[COMPENSAR] No se encontró diálogo Entiendo: %s", e)
        
        # Cerrar anuncios/popups
        try:
            log.info("[COMPENSAR] Buscando anuncios para cerrar...")
            close_btn = page.locator("button[aria-label='Close'], button[aria-label='close'], .close-btn, [class*='close']").first
            if close_btn.is_visible(timeout=3000):
                log.info("[COMPENSAR] Encontrado anuncio - clickeando X...")
                close_btn.click()
                page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            log.debug("[COMPENSAR] No se encontró anuncio: %s", e)
        
        # Screenshot 1: Login inicial
        ss1 = EVIDENCIA_DIR / f"01_login_{timestamp}.png"
        page.screenshot(path=str(ss1), full_page=True)
        log.info("[COMPENSAR] Screenshot: %s", ss1)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 1: Login
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 1: Login con NIT %s", datos.credenciales.numero_documento)
        
        # Select tipo de documento: "ni" = NIT
        page.get_by_label("Tipo de documento *").select_option("ni")
        log.info("[COMPENSAR] ✓ Tipo documento: NIT")
        
        # Fill número de documento
        page.get_by_role("textbox", name="Número de documento *").fill(datos.credenciales.numero_documento)
        log.info("[COMPENSAR] ✓ Documento ingresado")
        
        # Fill contraseña
        page.get_by_role("textbox", name="Contraseña *").fill(datos.credenciales.clave)
        log.info("[COMPENSAR] ✓ Contraseña ingresada")
        
        # Screenshot 2: Login lleno
        ss2 = EVIDENCIA_DIR / f"02_login_lleno_{timestamp}.png"
        page.screenshot(path=str(ss2))
        
        # Click "Ingresar"
        page.get_by_role("button", name="Ingresar").click()
        log.info("[COMPENSAR] ✓ Click Ingresar")
        
        # Esperar redirección
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)  # Animaciones
        
        # Screenshot 3: Después del login
        ss3 = EVIDENCIA_DIR / f"03_despues_login_{timestamp}.png"
        page.screenshot(path=str(ss3), full_page=True)
        log.info("[COMPENSAR] ✓ Login completado")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 2: Transacciones en Línea
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 2: Navigating to Transacciones")
        
        page.get_by_role("button", name="Transacciones en Línea").click()
        page.wait_for_load_state("networkidle", timeout=20000)
        log.info("[COMPENSAR] ✓ Transacciones en Línea")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 3: Seleccionar Salud
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 3: Selecting Salud")
        
        page.get_by_role("link", name="Salud", exact=True).click()
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1000)
        log.info("[COMPENSAR] ✓ Salud seleccionado")
        
        # Screenshot 4: Portal de salud
        ss4 = EVIDENCIA_DIR / f"04_portal_salud_{timestamp}.png"
        page.screenshot(path=str(ss4), full_page=True)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 4: Incapacidades → Radicar
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 4: Navegar a Incapacidades")
        
        page.get_by_text("IncapacidadesRegistra y haz").click()
        page.wait_for_load_state("networkidle", timeout=20000)
        log.info("[COMPENSAR] ✓ Incapacidades")
        
        # Click Radicar (nth(5) según la grabación)
        page.get_by_text("Radicar").nth(5).click()
        page.wait_for_load_state("networkidle", timeout=20000)
        log.info("[COMPENSAR] ✓ Click Radicar")
        
        # Screenshot 5: Formulario radicación
        ss5 = EVIDENCIA_DIR / f"05_formulario_radicacion_{timestamp}.png"
        page.screenshot(path=str(ss5), full_page=True)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 5: Omitir y seleccionar opción
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 5: Omitir y seleccionar")
        
        try:
            page.get_by_role("button", name="Omitir").click()
            log.info("[COMPENSAR] ✓ Omitir")
        except Exception as e:
            log.warning("[COMPENSAR] Omitir no encontrado: %s", e)
        
        # Click primer elemento IncapacidadesCardDot
        page.locator(".IncapacidadesCardDot").first.click()
        page.wait_for_timeout(1000)
        log.info("[COMPENSAR] ✓ Card seleccionado")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 6: Buscar incapacidad por número
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 6: Ingresando número de incapacidad: %s", datos.numero_incapacidad)
        
        page.get_by_role("textbox", name="Número de incapacidad *").fill(datos.numero_incapacidad)
        log.info("[COMPENSAR] ✓ Número ingresado")
        
        # Click "Buscar Incapacidad"
        page.get_by_role("button", name="Buscar Incapacidad").click()
        page.wait_for_load_state("networkidle", timeout=20000)
        log.info("[COMPENSAR] ✓ Búsqueda completada")
        
        # Screenshot 6: Datos encontrados
        ss6 = EVIDENCIA_DIR / f"06_datos_encontrados_{timestamp}.png"
        page.screenshot(path=str(ss6), full_page=True)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 7: Cargar incapacidad
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 7: Cargar incapacidad")
        
        page.get_by_role("button", name="Cargar Incapacidad").click()
        page.wait_for_load_state("networkidle", timeout=20000)
        log.info("[COMPENSAR] ✓ Incapacidad cargada")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 8: Adjuntar documento (si transcripción)
        # ═══════════════════════════════════════════════════════════════════════
        
        if datos.transcripcion and datos.pdf_incapacidad:
            log.info("[COMPENSAR] Step 8: Adjuntando documento: %s", datos.pdf_incapacidad)
            
            page.get_by_role("button", name="Adjuntar documentos").click()
            page.wait_for_timeout(500)
            
            page.get_by_text("Adjuntar Archivo").click()
            page.wait_for_timeout(500)
            
            # Subir archivo
            dialogs = page.locator("[role='dialog']")
            if dialogs.count() > 0:
                dialogs.nth(0).set_input_files(datos.pdf_incapacidad)
            log.info("[COMPENSAR] ✓ Archivo cargado")
            
            # Click "Cargar Documentos"
            page.get_by_role("button", name="Cargar Documentos").click()
            page.wait_for_load_state("networkidle", timeout=20000)
            log.info("[COMPENSAR] ✓ Documentos cargados")
        else:
            log.info("[COMPENSAR] Step 8: Sin transcripción, saltando adjuntos")
        
        # Screenshot 7: Datos completos
        ss7 = EVIDENCIA_DIR / f"07_datos_completos_{timestamp}.png"
        page.screenshot(path=str(ss7), full_page=True)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 9: Radicar
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 9: Radicar")
        
        page.get_by_role("button", name="Radicar").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)  # Esperar procesamiento
        log.info("[COMPENSAR] ✓ Radicar completado")
        
        # Screenshot 8: Confirmación
        ss8 = EVIDENCIA_DIR / f"08_confirmacion_{timestamp}.png"
        page.screenshot(path=str(ss8), full_page=True)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 10: Extraer número radicado
        # ═══════════════════════════════════════════════════════════════════════
        
        log.info("[COMPENSAR] Step 10: Extrayendo número radicado")
        
        # Buscar patrones comunes para el número radicado
        numero_patterns = [
            "text=/Número de radicado[:\\s]+([0-9]+)/",
            "text=/Radicado[:\\s]+([0-9]+)/",
            "text=/Referencia[:\\s]+([0-9]+)/",
            "[data-test='radicado'], [data-id='numero-radicado']",
            "strong, .radicado-number, .reference-number"
        ]
        
        numero_radicado = None
        for pattern in numero_patterns:
            try:
                elemento = page.locator(pattern).first
                if elemento:
                    contenido = elemento.text_content()
                    # Extraer solo números
                    match = re.search(r'\d+', contenido)
                    if match:
                        numero_radicado = match.group()
                        log.info("[COMPENSAR] ✓ Número radicado encontrado: %s", numero_radicado)
                        break
            except Exception as e:
                log.debug("[COMPENSAR] Patrón %s falló: %s", pattern, e)
                continue
        
        if not numero_radicado:
            log.warning("[COMPENSAR] No se pudo extraer número radicado, buscando en HTML")
            html = page.content()
            # Buscar patrón general de número
            match = re.search(r'(?:radicado|referencia|radicar)[:\s]+(\d{6,})', html, re.IGNORECASE)
            if match:
                numero_radicado = match.group(1)
                log.info("[COMPENSAR] ✓ Número extraído de HTML: %s", numero_radicado)
        
        if not numero_radicado:
            numero_radicado = "PENDIENTE_EXTRACCION"
            log.warning("[COMPENSAR] No se pudo extraer número radicado automáticamente")
        
        # Screenshot 9: Final con número radicado
        ss9 = EVIDENCIA_DIR / f"09_radicado_{numero_radicado}_{timestamp}.png"
        page.screenshot(path=str(ss9), full_page=True)
        
        log.info("[COMPENSAR] ✅ Radicación completada exitosamente")
        
        return ResultadoRadicacion(
            exitoso=True,
            numero_radicado=numero_radicado,
            mensaje=f"Incapacidad {datos.numero_incapacidad} radicada exitosamente. Radicado: {numero_radicado}",
            pdf_path=str(ss9)
        )
    
    except PlaywrightTimeoutError as e:
        log.error("[COMPENSAR] Timeout: %s", str(e))
        return ResultadoRadicacion(
            exitoso=False,
            numero_radicado=numero_radicado or "N/A",
            mensaje=f"Timeout en radicación: {str(e)}",
            pdf_path=None
        )
    
    except Exception as e:
        log.error("[COMPENSAR] Error: %s", str(e), exc_info=True)
        
        # Tomar screenshot de error
        try:
            if page:
                ss_error = EVIDENCIA_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=str(ss_error), full_page=True)
        except Exception:
            pass
        
        return ResultadoRadicacion(
            exitoso=False,
            numero_radicado=numero_radicado or "N/A",
            mensaje=f"Error en radicación: {str(e)}",
            pdf_path=None
        )
    
    finally:
        # Limpieza
        try:
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            log.info("[COMPENSAR] Browser cerrado")
        except Exception as e:
            log.warning("[COMPENSAR] Error al cerrar browser: %s", e)
