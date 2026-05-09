#!/usr/bin/env python3
"""
Test interactivo para el bot de Compensar.

Permite probar el bot localmente CON UN NAVEGADOR VISIBLE,
ideal para debugging de selectores y ver el paso a paso en tiempo real.

Uso:
    python test_compensar_manual.py

El navegador se abrirá SIN headless (verás la pantalla en tiempo real).
Perfecto para ver en vivo cada paso del bot y detectar dónde falla.
"""

import sys
import os
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
    print("🧪 TEST MANUAL - Bot Compensar (NAVEGADOR VISIBLE)")
    print("=" * 80)
    print()
    
    print("Este test abrirá un navegador VISIBLE para que veas el paso a paso.")
    print("Podrás ver exactamente dónde falla el bot.")
    print()
    
    print("TIPOS DE DOCUMENTO ACEPTADOS EN COMPENSAR:")
    print("  • ni  → NIT")
    print("  • cc  → CEDULA")
    print("  • ce  → CEDULA EXTRANJERIA")
    print("  • pa  → PASAPORTE")
    print("  • pe  → PERMISO ESPECIAL PERMANENCIA")
    print()
    
    print("=" * 80)
    print("INGRESA LOS DATOS DE LA EMPRESA (Portal Compensar)")
    print("=" * 80)
    print()
    
    # Datos de Compensar (del portal)
    tipo_doc = input("  Tipo de documento [ni]: ").strip().lower() or "ni"
    numero_doc = input("  Número de documento [860000452]: ").strip() or "860000452"
    clave = input("  Contraseña [Eliot2025.]: ").strip() or "Eliot2025."
    
    print()
    print("=" * 80)
    print("INGRESA LOS DATOS DEL TRABAJADOR")
    print("=" * 80)
    print()
    
    cedula = input("  Cédula del trabajador [12345678]: ").strip() or "12345678"
    prefijo_incap = input("  Prefijo del número de incapacidad [0]: ").strip() or "0"
    numero_incap = input("  Número de incapacidad [67372855]: ").strip() or "67372855"
    
    print()
    print("=" * 80)
    print("¿REQUIERE TRANSCRIPCIÓN? (Si la incapacidad NO es de Compensar)")
    print("=" * 80)
    print()
    
    transcripcion_str = input("  ¿Usar transcripción? (s/n) [n]: ").strip().lower()
    transcripcion = transcripcion_str == 's'
    
    print()
    print("✅ DATOS CONFIGURADOS:")
    print()
    print("  EMPRESA:")
    print(f"    • Tipo documento: {tipo_doc}")
    print(f"    • Número: {numero_doc}")
    print(f"    • Contraseña: {'*' * len(clave)}")
    print()
    print("  TRABAJADOR:")
    print(f"    • Cédula: {cedula}")
    print(f"    • Prefijo incapacidad: {prefijo_incap}")
    print(f"    • Número incapacidad: {numero_incap}")
    print(f"    • Transcripción: {'SÍ' if transcripcion else 'NO'}")
    print()
    
    # Crear datos para el bot
    datos = DatosRadicacion(
        credenciales=CredencialesEmpleador(
            tipo_documento=tipo_doc,
            numero_documento=numero_doc,
            clave=clave,
        ),
        documento_trabajador=cedula,
        prefijo_incapacidad=prefijo_incap,
        numero_incapacidad=numero_incap,
        transcripcion=transcripcion,
    )
    
    print("=" * 80)
    print("🚀 INICIANDO BOT COMPENSAR")
    print("=" * 80)
    print()
    print("El navegador se abrirá AHORA en modo VISIBLE.")
    print("Verás cada paso del bot en tiempo real.")
    print()
    print("✨ PASOS QUE VERÁS:")
    print("  1. Login en Compensar")
    print("  2. Navegar a 'Transacciones en Línea'")
    print("  3. Click en 'Salud'")
    print("  4. Buscar 'Incapacidades'")
    print("  5. Click en 'Radicar'")
    print("  6. Saltar paso si existe")
    print("  7. Seleccionar Incapacidad")
    print("  8. Buscar incapacidad por número")
    print("  9. Cargar incapacidad")
    if transcripcion:
        print(" 10. Adjuntar documento PDF")
        print(" 11. Radicar")
    else:
        print(" 10. Radicar")
    print()
    print("-" * 80)
    
    # Activar modo visible para debugging
    os.environ["PLAYWRIGHT_HEADLESS"] = "0"
    
    print()
    
    try:
        resultado = radicar_en_compensar(datos)
        
        print()
        print("-" * 80)
        print()
        print("✅ BOT COMPLETÓ LA EJECUCIÓN")
        print()
        print(f"  📊 Exitoso: {'SÍ ✓' if resultado.exitoso else 'NO ✗'}")
        print(f"  📝 Número radicado: {resultado.numero_radicado or '(no obtenido)'}")
        print(f"  💬 Mensaje: {resultado.mensaje}")
        print(f"  📸 Evidencia (screenshots): {resultado.pdf_path}")
        print()
        
        if resultado.exitoso:
            print("=" * 80)
            print("🎉 ¡ÉXITO! LA INCAPACIDAD FUE RADICADA EXITOSAMENTE")
            print("=" * 80)
            print()
            print(f"  ✓ Número de radicación: {resultado.numero_radicado}")
            print(f"  ✓ Verifica en el portal Compensar")
            print(f"  ✓ Screenshots guardados en: {resultado.pdf_path}")
            print()
        else:
            print("=" * 80)
            print("⚠️  EL BOT COMPLETÓ PERO NO FUE EXITOSO")
            print("=" * 80)
            print()
            print(f"  Mensaje de error: {resultado.mensaje}")
            print(f"  Mira los screenshots para ver dónde falló: {resultado.pdf_path}")
            print()
            print("POSIBLES CAUSAS:")
            print("  ❌ Selectores incorrectos (elemento no encontrado)")
            print("  ❌ Datos inválidos para el portal")
            print("  ❌ Portal requiere validaciones extras (2FA, CAPTCHA)")
            print("  ❌ Error al extraer el número radicado")
            print("  ❌ Datos de credenciales incorrectos")
            print()
            
    except Exception as e:
        print()
        print("-" * 80)
        print()
        print("=" * 80)
        print("❌ ERROR DURANTE LA EJECUCIÓN DEL BOT")
        print("=" * 80)
        print()
        print(f"  Tipo de error: {type(e).__name__}")
        print(f"  Mensaje: {str(e)}")
        print()
        
        import traceback
        print("TRACEBACK COMPLETO:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)
        print()
        
        print("PRÓXIMOS PASOS PARA DEBUGGING:")
        print("  1. Identifica el selector que falló en el error")
        print("  2. Abre compensar.py y revisa ese selector")
        print("  3. Compara con el código del Playwright codegen original")
        print("  4. Actualiza el selector si es necesario")
        print("  5. Ejecuta este test nuevamente")
        print()
        print("💡 TIP: Ejecuta en navegador visible (+SLOW) para ver dónde falla")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test interactivo del bot Compensar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EJEMPLOS:
  python test_compensar_manual.py                    # Modo interactivo
  python test_compensar_manual.py --mode manual      # Modo manual (por defecto)
        """
    )
    parser.add_argument(
        "--mode",
        choices=["manual"],
        default="manual",
        help="Modo de test (manual con navegador visible)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "manual":
        test_compensar_manual()
