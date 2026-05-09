#!/usr/bin/env python3
"""
Grabador AVANZADO para Compensar - Usa Playwright codegen.

Este script genera código automáticamente mientras interactúas con el portal.

Uso:
    python record_compensar_codegen.py

Se abrirá el Inspector de Playwright que:
1. Graba TODAS tus acciones (clicks, writes, waits)
2. Genera código Python automáticamente
3. Puedes copiar el código generado

IMPORTANTE:
- La grabación está ACTIVA desde que se abre el navegador
- Cada acción se registra en el Inspector
- En la parte derecha verás el código generado
- Presiona Ctrl+S para guardar o copia manualmente
"""

import subprocess
import sys
from pathlib import Path

def grabar_con_codegen():
    """Usa playwright codegen para grabar el flujo interactivamente."""
    
    print("=" * 80)
    print("🎬 GRABADOR AVANZADO COMPENSAR - Codegen Playwright")
    print("=" * 80)
    print()
    
    url = "https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&_csrf=e42792d3-0389-46ad-ab2b-47b8602bcdeb&protocol=OIDC"
    
    output_file = Path(__file__).parent / "compensar_recorded.py"
    
    print(f"📝 URL: {url}")
    print(f"💾 Código será guardado en: {output_file}")
    print()
    print("Abriendo Playwright Inspector...")
    print()
    print("INSTRUCCIONES:")
    print("  1. Cuando se abra el navegador, verás el Inspector a la derecha")
    print("  2. El Inspector GRABA cada acción que hagas")
    print("  3. Realiza el siguiente flujo:")
    print("     - Login con credenciales")
    print("     - Navegación a radicación")
    print("     - Llenar formulario")
    print("     - Enviar")
    print("  4. En el Inspector, verás el código generado en tiempo real")
    print("  5. Copia el código que necesites")
    print("  6. Cierra el navegador cuando termines")
    print()
    
    # Comando para ejecutar codegen
    cmd = [
        sys.executable,
        "-m",
        "playwright",
        "codegen",
        url,
        "--output",
        str(output_file)
    ]
    
    print(f"▶️ Ejecutando: {' '.join(cmd)}")
    print()
    
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("❌ Error: Playwright no está instalado")
        print("Instala con: pip install playwright")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Grabación detenida")
    
    # Verificar si se generó el archivo
    if output_file.exists():
        print(f"\n✅ Código generado: {output_file}")
        print(f"\nTamaño: {output_file.stat().st_size} bytes")
        
        # Mostrar primeras líneas
        with open(output_file) as f:
            lineas = f.readlines()[:20]
            print("\n📄 Primeras líneas del código generado:")
            print("-" * 80)
            for linea in lineas:
                print(linea.rstrip())
            print("-" * 80)
        
        print("\n✅ Ahora puedes revisar y adaptar el código en compensar_recorded.py")
    else:
        print("\n⚠️ No se generó archivo de salida")
        print("Asegúrate de haber interactuado con el navegador")


if __name__ == "__main__":
    grabar_con_codegen()
