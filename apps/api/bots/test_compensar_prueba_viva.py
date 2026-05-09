#!/usr/bin/env python3
"""
Prueba EN VIVO del bot Compensar — Radica una incapacidad viendo paso a paso.

Con esta prueba ves exactamente qué está haciendo el bot en cada momento:
- Abre navegador visible
- Muestra cada acción (login, búsqueda, radicación)
- Si falla, ves exactamente dónde
- Descarga automáticamente el PDF de confirmación

Uso:
    python test_compensar_prueba_viva.py

Datos de prueba hardcodeados:
    - NIT Empleador: 860000452
    - Contraseña: Eliot2025.
    - Tipo doc trabajador: CEDULA
    - N° cédula: 52788795
    - Número incapacidad: 67323946
    - Archivo: CamScanner 13-04-2026 12.24.pdf
"""

import os
import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime

# Agregar ruta del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configurar variable de entorno para que el navegador sea VISIBLE
os.environ["PLAYWRIGHT_HEADLESS"] = "false"


def test_compensar():
    """Ejecuta prueba en vivo del bot Compensar."""
    
    print("\n" + "="*70)
    print("🤖 PRUEBA EN VIVO - BOT COMPENSAR".center(70))
    print("="*70)
    
    # Datos de prueba
    nit_empleador = "860000452"
    clave_empleador = "Eliot2025."
    cedula_trabajador = "52788795"
    numero_incapacidad = "67323946"
    
    print("\n📋 Datos de prueba:")
    print(f"  • NIT Empleador: {nit_empleador}")
    print(f"  • Clave: {'*' * len(clave_empleador)}")
    print(f"  • Cédula Trabajador: {cedula_trabajador}")
    print(f"  • N° Incapacidad: {numero_incapacidad}")
    
    # Buscar archivo a adjuntar
    archivo_pdf = None
    posibles_rutas = [
        Path.home() / "Downloads" / "CamScanner 13-04-2026 12.24.pdf",
        Path(__file__).parent / "CamScanner 13-04-2026 12.24.pdf",
        Path("/tmp/CamScanner 13-04-2026 12.24.pdf"),
    ]
    
    for ruta in posibles_rutas:
        if ruta.exists():
            archivo_pdf = str(ruta)
            print(f"  • Archivo PDF: {ruta.name}")
            break
    
    if not archivo_pdf:
        print(f"  ⚠️ Archivo PDF NO encontrado. Se saltará la adjunción.")
        print(f"     Buscó en:")
        for r in posibles_rutas:
            print(f"       - {r}")
    
    # Crear directorio para descargas
    download_dir = Path(tempfile.gettempdir()) / "compensar_descargas"
    download_dir.mkdir(parents=True, exist_ok=True)
    print(f"  • Descargas → {download_dir}")
    
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        print("\n" + "-"*70)
        print("Iniciando Playwright...")
        playwright = sync_playwright().start()
        
        print("Lanzando navegador (visible)...")
        browser = playwright.chromium.launch(
            headless=False,  # ← IMPORTANTE: VISIBLE
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
            ]
        )
        
        # Contexto con descarga automática
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True,  # ← Permitir descargas
        )
        
        page = context.new_page()
        page.set_default_timeout(40000)
        
        login_url = "https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&protocol=OIDC"
        
        print("\n" + "-"*70)
        print("PASO 1: Navegando a login...")
        page.goto(login_url, wait_until="networkidle")
        print("  ✓ Página de login cargada")
        time.sleep(2)
        
        # Manejar diálogo de bot detection (Compensar)
        print("\n  🤖 Verificando si hay diálogo de bot detection...")
        try:
            # Buscar botón exacto "Entiendo" (nuevo HTML) o "Entendido" (antiguo)
            btn_entiendo = page.locator('button[type="submit"]:has-text("Entiendo"), button:has-text("Entendido")').first
            if btn_entiendo.is_visible(timeout=5000):
                print("  • ⚠️ Encontrado diálogo de bot detection")
                print("  • Clickeando 'Entiendo'...")
                btn_entiendo.click()
                time.sleep(1)
                page.wait_for_load_state("networkidle", timeout=10000)
                print("  ✓ Diálogo cerrado")
        except:
            print("  ℹ️ No hay diálogo de bot detection")
        
        # Cerrar anuncios si existen
        try:
            print("  • Buscando anuncios para cerrar...")
            close_btn = page.locator("button[aria-label='Close'], button[aria-label='close'], .close-btn, [class*='close']").first
            if close_btn.is_visible(timeout=3000):
                print("  • ⚠️ Anuncio encontrado - clickeando X...")
                close_btn.click()
                time.sleep(0.5)
                print("  ✓ Anuncio cerrado")
        except:
            print("  ℹ️ No hay anuncios")
        
        # Cerrar anuncio/popup si existe
        print("  • Verificando si hay anuncios para cerrar...")
        try:
            # Buscar botón X o close
            close_btn = page.locator("button[aria-label='Close'], button[aria-label='close'], .close-btn, [class*='close']").first
            if close_btn.is_visible(timeout=3000):
                print("  • Encontrado anuncio/popup")
                print("  • Clickeando X para cerrar...")
                close_btn.click()
                time.sleep(1)
        except:
            pass
        
        time.sleep(1)
        
        # Screenshot
        page.screenshot(path=str(download_dir / "01_login.png"))
        print("  → Screenshot guardado: 01_login.png")
        
        print("\n" + "-"*70)
        print("PASO 2: Ingresando credenciales...")
        
        # Tipo de documento
        print("  • Seleccionando tipo documento (NIT)...")
        page.get_by_label("Tipo de documento *").select_option("ni")
        time.sleep(0.5)
        
        # NIT
        print(f"  • Ingresando NIT: {nit_empleador}")
        page.get_by_role("textbox", name="Número de documento *").fill(nit_empleador)
        time.sleep(0.5)
        
        # Contraseña
        print(f"  • Ingresando contraseña...")
        page.get_by_role("textbox", name="Contraseña *").fill(clave_empleador)
        time.sleep(0.5)
        
        # Screenshot
        page.screenshot(path=str(download_dir / "02_credenciales_ingresadas.png"))
        print("  → Screenshot guardado: 02_credenciales_ingresadas.png")
        
        print("\n" + "-"*70)
        print("PASO 3: Haciendo click en 'Ingresar'...")
        page.get_by_role("button", name="Ingresar").click()
        page.wait_for_load_state("networkidle", timeout=40000)
        print("  ✓ Login completado")
        time.sleep(2)
        
        # Screenshot
        page.screenshot(path=str(download_dir / "03_login_exitoso.png"))
        print("  → Screenshot guardado: 03_login_exitoso.png")
        
        print("\n" + "-"*70)
        print("PASO 4: Navegando a 'Transacciones en Línea'...")
        page.get_by_role("button", name="Transacciones en Línea").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ En Transacciones en Línea")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "04_transacciones.png"))
        print("  → Screenshot guardado: 04_transacciones.png")
        
        print("\n" + "-"*70)
        print("PASO 5: Navegando a 'Salud'...")
        page.get_by_role("link", name="Salud", exact=True).click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ En módulo Salud")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "05_salud.png"))
        print("  → Screenshot guardado: 05_salud.png")
        
        print("\n" + "-"*70)
        print("PASO 6: Navegando a 'Incapacidades'...")
        page.get_by_text("IncapacidadesRegistra y haz").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ En Incapacidades")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "06_incapacidades.png"))
        print("  → Screenshot guardado: 06_incapacidades.png")
        
        print("\n" + "-"*70)
        print("PASO 7: Haciendo click en 'Radicar'...")
        page.get_by_text("Radicar").nth(5).click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ En formulario Radicar")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "07_radicar_form.png"))
        print("  → Screenshot guardado: 07_radicar_form.png")
        
        print("\n" + "-"*70)
        print("PASO 8: Saltando primer paso (Omitir)...")
        page.get_by_role("button", name="Omitir").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ Primer paso omitido")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "08_omitir.png"))
        print("  → Screenshot guardado: 08_omitir.png")
        
        print("\n" + "-"*70)
        print("PASO 9: Seleccionando incapacidad (CardDot)...")
        page.locator(".IncapacidadesCardDot").first.click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ Incapacidad seleccionada")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "09_carddot.png"))
        print("  → Screenshot guardado: 09_carddot.png")
        
        print("\n" + "-"*70)
        print(f"PASO 10: Ingresando número de incapacidad: {numero_incapacidad}")
        page.get_by_role("textbox", name="Número de incapacidad *").fill(numero_incapacidad)
        time.sleep(0.5)
        
        print("  • Haciendo click en 'Buscar Incapacidad'...")
        page.get_by_role("button", name="Buscar Incapacidad").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ Incapacidad encontrada")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "10_buscar_incapacidad.png"))
        print("  → Screenshot guardado: 10_buscar_incapacidad.png")
        
        print("\n" + "-"*70)
        print("PASO 11: Haciendo click en 'Cargar Incapacidad'...")
        page.get_by_role("button", name="Cargar Incapacidad").click()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("  ✓ Incapacidad cargada")
        time.sleep(1)
        
        page.screenshot(path=str(download_dir / "11_cargar_incapacidad.png"))
        print("  → Screenshot guardado: 11_cargar_incapacidad.png")
        
        # Adjuntar documento si existe
        if archivo_pdf:
            print("\n" + "-"*70)
            print("PASO 12: Adjuntando documento...")
            print(f"  • Archivo: {Path(archivo_pdf).name}")
            
            print("  • Haciendo click en 'Adjuntar documentos'...")
            page.get_by_role("button", name="Adjuntar documentos").click()
            time.sleep(1)
            
            print("  • Haciendo click en 'Adjuntar Archivo'...")
            page.get_by_text("Adjuntar Archivo").click()
            time.sleep(1)
            
            print("  • Seleccionando archivo...")
            page.get_by_role("dialog").nth(1).set_input_files(archivo_pdf)
            time.sleep(1)
            
            page.screenshot(path=str(download_dir / "12_archivo_adjunto.png"))
            print("  → Screenshot guardado: 12_archivo_adjunto.png")
            
            print("  • Haciendo click en 'Cargar Documentos'...")
            page.get_by_role("button", name="Cargar Documentos").click()
            page.wait_for_load_state("networkidle", timeout=30000)
            print("  ✓ Documento cargado")
            time.sleep(1)
        
        print("\n" + "-"*70)
        print("PASO 13: Radicando incapacidad (CLICK FINAL)...")
        page.get_by_role("button", name="Radicar").click()
        page.wait_for_load_state("networkidle", timeout=40000)
        print("  ✓ Radicación enviada")
        time.sleep(2)
        
        page.screenshot(path=str(download_dir / "13_radicado.png"))
        print("  → Screenshot guardado: 13_radicado.png")
        
        print("\n" + "-"*70)
        print("PASO 14: Descargando confirmación (PDF)...")
        
        # Esperar a que se abra popup o descargar
        try:
            with page.expect_popup(timeout=10000) as popup_info:
                page.get_by_role("button", name="Descargar confirmación").click()
            
            popup = popup_info.value
            print("  ✓ Popup abierto")
            time.sleep(2)
            
            # Descargar PDF desde el popup
            try:
                with popup.expect_download() as download_info:
                    # Si el popup es un PDF directamente
                    popup.goto("about:blank")  # Esto fuerza descarga
                
                download = download_info.value
                ruta_descarga = download_dir / f"confirmacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                download.save_as(ruta_descarga)
                print(f"  ✓ PDF descargado: {ruta_descarga.name}")
                
            except Exception as e:
                print(f"  ⚠️ No se pudo descargar desde popup: {e}")
                
                # Intentar descargar directamente de la página actual
                try:
                    with page.context.expect_event("page") as page_info:
                        page.get_by_role("button", name="Descargar confirmación").click()
                    
                    nueva_pagina = page_info.value
                    time.sleep(2)
                    nueva_pagina.close()
                except:
                    pass
        
        except Exception as e:
            print(f"  ⚠️ Error al descargar confirmación: {e}")
        
        page.screenshot(path=str(download_dir / "14_final.png"))
        print("  → Screenshot guardado: 14_final.png")
        
        print("\n" + "="*70)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE".center(70))
        print("="*70)
        
        print(f"\n📁 Archivos guardados en: {download_dir}")
        print(f"   Total screenshots: {len(list(download_dir.glob('*.png')))}")
        print(f"   Total PDFs: {len(list(download_dir.glob('*.pdf')))}")
        
    except PlaywrightTimeoutError as e:
        print(f"\n❌ ERROR DE TIMEOUT: {e}")
        print("   El portal tardó demasiado o no respondió")
        if page:
            page.screenshot(path=str(download_dir / "ERROR_timeout.png"))
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        if page:
            page.screenshot(path=str(download_dir / f"ERROR_{type(e).__name__}.png"))
        
    finally:
        print("\n" + "-"*70)
        print("Limpiando recursos...")
        if page:
            page.close()
        if context:
            context.close()
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        
        print("✓ Recursos liberados")
        print("✓ Script finalizado")


if __name__ == "__main__":
    test_compensar()
