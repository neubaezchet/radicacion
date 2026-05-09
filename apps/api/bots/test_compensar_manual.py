#!/usr/bin/env python3
"""
Test interactivo para el bot de Compensar.

Permite probar el bot localmente CON UN NAVEGADOR VISIBLE,
ideal para debugging de selectores.

Uso:
    python test_compensar_manual.py

El navegador se abrirá SIN headless (verás la pantalla en tiempo real).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bots import (
    radicar_en_compensar,
    DatosRadicacion,
    CredencialesEmpleador,
)


def test_compensar_manual():
    """Prueba el bot con un navegador VISIBLE."""
    
    print("=" * 80)
    print("🧪 TEST MANUAL - Bot Compensar")
    print("=" * 80)
    print()
    
    print("Este test abrirá un navegador VISIBLE para que puedas ver qué pasa.")
    print()
    
    print("📋 Datos de prueba que usaremos:")
    print()
    
    # Datos de prueba
    nit = input("  NIT/Documento empleador [860007234]: ").strip() or "860007234"
    clave = input("  Contraseña: ").strip()
    
    if not clave:
        print("❌ Error: La contraseña es requerida")
        return
    
    cedula = input("  Cédula del trabajador [12345678]: ").strip() or "12345678"
    fecha = input("  Fecha inicio (DD MM YYYY) [18 04 2026]: ").strip() or "18 04 2026"
    incapacidad = input("  Número de incapacidad [12345]: ").strip() or "12345"
    
    print()
    print("✅ Datos configurados:")
    print(f"  • NIT: {nit}")
    print(f"  • Cédula: {cedula}")
    print(f"  • Fecha: {fecha}")
    print(f"  • Incapacidad: {incapacidad}")
    print()
    
    # Crear datos para el bot
    datos = DatosRadicacion(
        credenciales=CredencialesEmpleador(
            tipo_documento="A",  # NIT
            numero_documento=nit,
            clave=clave,
        ),
        documento_trabajador=cedula,
        fecha_inicio_incapacidad=fecha,
        prefijo_incapacidad="0",
        numero_incapacidad=incapacidad,
    )
    
    print("🚀 Iniciando bot Compensar...")
    print()
    print("El navegador se abrirá en modo VISIBLE.")
    print("Si hay errores, los verás en la pantalla y en la consola aquí.")
    print()
    print("-" * 80)
    print()
    
    try:
        resultado = radicar_en_compensar(datos)
        
        print()
        print("-" * 80)
        print()
        print("✅ Bot completó la ejecución")
        print()
        print(f"   Exitoso: {resultado.exitoso}")
        print(f"   Número radicado: {resultado.numero_radicado}")
        print(f"   Mensaje: {resultado.mensaje}")
        print(f"   Screenshots: {resultado.pdf_path}")
        print()
        
        if resultado.exitoso:
            print("🎉 ¡ÉXITO! La incapacidad fue radicada.")
            print()
            print("Comprueba:")
            print(f"  - Número radicado en portal: {resultado.numero_radicado}")
            print(f"  - Screenshots en: {resultado.pdf_path}")
        else:
            print("⚠️ El bot completó pero reporta que NO fue exitoso.")
            print()
            print("Revisa:")
            print(f"  - El mensaje: {resultado.mensaje}")
            print(f"  - Los screenshots: {resultado.pdf_path}")
            print()
            print("Posibles causas:")
            print("  1. Selectores incorrectos (elemento no encontrado)")
            print("  2. Datos inválidos para el portal")
            print("  3. Portal requiere validaciones extras (2FA, CAPTCHA)")
            print("  4. Error en extracción del número radicado")
            
    except Exception as e:
        print()
        print("-" * 80)
        print()
        print(f"❌ Error: {type(e).__name__}")
        print(f"   {str(e)}")
        print()
        
        import traceback
        print("Traceback completo:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)
        print()
        
        print("Próximos pasos:")
        print("  1. Verifica el selector que falló en el error anterior")
        print("  2. Abre compensar_recorded.py para ver el código grabado")
        print("  3. Compara selectores en el código grabado vs compensar.py")
        print("  4. Actualiza los selectores en compensar.py")
        print("  5. Ejecuta este test nuevamente")
        print()


def test_compensar_headless():
    """Prueba el bot en modo headless (sin navegador visible)."""
    
    print("=" * 80)
    print("🧪 TEST HEADLESS - Bot Compensar (sin navegador visible)")
    print("=" * 80)
    print()
    
    # Este sería para CI/CD, por ahora no lo implementamos
    print("⏭️ Modo headless no implementado aún.")
    print("Usa test_compensar_manual() para debugging interactivo.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test del bot Compensar"
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "headless"],
        default="manual",
        help="Modo de test: manual (navegador visible) o headless"
    )
    
    args = parser.parse_args()
    
    if args.mode == "manual":
        test_compensar_manual()
    else:
        test_compensar_headless()
