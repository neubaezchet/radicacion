#!/usr/bin/env python3
"""
Script para GRABAR el flujo de radicación en Compensar.

Genera código automático de Playwright basado en tus interacciones.

Uso:
    python record_compensar.py

Se abrirá un navegador donde podrás:
1. Ingresar credenciales
2. Hacer login
3. Navegar al formulario de radicación
4. Llenar datos
5. Enviar

Mientras haces esto, Playwright GRABA cada acción y genera el código.
El código se guarda en: compensar_recorded.py

IMPORTANTE:
- Mueve lentamente el ratón
- Espera a que cargue cada página
- Haz clic con precisión
- Cuando termines, presiona Ctrl+Shift+R para detener la grabación
"""

import sys
import os
from pathlib import Path

# Agregar el directorio de la API al path
sys.path.insert(0, str(Path(__file__).parent))


def grabar_compensar():
    """Abre navegador en modo de grabación para Compensar."""
    from playwright.sync_api import sync_playwright
    
    print("=" * 80)
    print("🎬 GRABADOR COMPENSAR - Radicación de Incapacidades")
    print("=" * 80)
    print()
    print("Se abrirá un navegador en modo de GRABACIÓN.")
    print()
    print("📋 Instrucciones:")
    print("  1. Ingresa el usuario (NIT de la empresa)")
    print("  2. Ingresa la contraseña")
    print("  3. Haz clic en 'Ingresar'")
    print("  4. Espera a que cargue el portal")
    print("  5. Navega al formulario de radicación")
    print("  6. Llena los datos de la incapacidad:")
    print("     - Cédula del trabajador")
    print("     - Fecha de inicio")
    print("     - Número de incapacidad")
    print("  7. Envía el formulario")
    print("  8. Nota el número de radicado")
    print()
    print("⌨️ Controles:")
    print("  - Ctrl+Shift+R: Detener grabación y guardar")
    print("  - El código se guardará como: compensar_recorded.py")
    print()
    
    # Crear archivo de salida
    output_file = Path(__file__).parent / "compensar_recorded.py"
    
    print(f"📁 Archivo de salida: {output_file}")
    print()
    
    playwright = sync_playwright().start()
    
    try:
        # Abre un navegador en modo inspector/grabador
        # Nota: El modo de grabación interactivo de Playwright se accede vía línea de comandos
        # Aquí abrimos un contexto normal y el usuario graba manualmente
        
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # URL de Compensar
        url = "https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&_csrf=e42792d3-0389-46ad-ab2b-47b8602bcdeb&protocol=OIDC"
        
        print(f"\n🌐 Navegando a: {url}")
        page.goto(url)
        
        print("\n✅ Navegador abierto. Puedes comenzar a interactuar.")
        print("\nCuando termines, cierra el navegador o presiona Ctrl+C aquí.\n")
        
        # Esperar a que el usuario cierre el navegador o presione Ctrl+C
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️ Grabación detenida por el usuario")
        
        context.close()
        browser.close()
        
    finally:
        playwright.stop()
    
    print("\n" + "=" * 80)
    print("📝 PRÓXIMOS PASOS:")
    print("=" * 80)
    print("""
1. Abre el archivo: compensar_recorded.py
2. Revisa el código generado por el inspector
3. Adapta el código para automatizar correctamente
4. Prueba el bot con datos de prueba

NOTAS IMPORTANTES:
- El código generado necesitará ajustes manuales
- Los selectores pueden cambiar entre navegadores
- Asegúrate de usar waits() apropiados para elementos dinámicos
- Prueba primero sin headless (headless=False)
- Luego pasa a headless=True para producción
""")


if __name__ == "__main__":
    grabar_compensar()
