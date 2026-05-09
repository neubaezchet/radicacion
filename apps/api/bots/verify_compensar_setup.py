#!/usr/bin/env python3
"""
✅ Verificador de Integridad: Bot Compensar

Valida que todos los archivos y cambios estén en su lugar.
Ejecuta este script para verificar antes de comenzar a grabar.

Uso:
    python verify_compensar_setup.py
"""

import sys
from pathlib import Path


def verificar_archivo(ruta, descripcion):
    """Verifica que un archivo existe."""
    p = Path(ruta)
    if p.exists():
        tamaño = p.stat().st_size
        print(f"  ✅ {descripcion}")
        print(f"     {ruta} ({tamaño} bytes)")
        return True
    else:
        print(f"  ❌ {descripcion}")
        print(f"     NO ENCONTRADO: {ruta}")
        return False


def verificar_contenido(ruta, buscar_texto, descripcion):
    """Verifica que un archivo contiene cierto texto."""
    try:
        p = Path(ruta)
        if not p.exists():
            print(f"  ❌ {descripcion} (archivo no existe)")
            return False
        
        contenido = p.read_text(encoding='utf-8', errors='ignore')
        if buscar_texto in contenido:
            print(f"  ✅ {descripcion}")
            return True
        else:
            print(f"  ❌ {descripcion} (texto no encontrado)")
            print(f"     Buscaba: '{buscar_texto}'")
            return False
    except Exception as e:
        print(f"  ❌ {descripcion} (error: {e})")
        return False


def main():
    print("=" * 80)
    print("✅ VERIFICADOR DE INTEGRIDAD: Bot Compensar")
    print("=" * 80)
    print()
    
    resultados = []
    
    # 1. Verificar archivos creados
    print("1️⃣ Archivos de Grabación")
    print("-" * 80)
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/record_compensar_codegen.py",
        "Script grabador (codegen)"
    ))
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/record_compensar.py",
        "Script grabador (interactivo)"
    ))
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/test_compensar_manual.py",
        "Script de testing manual"
    ))
    print()
    
    # 2. Verificar documentación
    print("2️⃣ Documentación")
    print("-" * 80)
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/GRABAR_COMPENSAR.md",
        "Guía de grabación"
    ))
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/TEMPLATE_SELECTORES.md",
        "Template de selectores"
    ))
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/COMPENSAR_FLUJO_VISUAL.md",
        "Flujo visual completo"
    ))
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/QUICK_START.md",
        "Quick start (comandos listos)"
    ))
    print()
    
    # 3. Verificar bot
    print("3️⃣ Código del Bot")
    print("-" * 80)
    resultados.append(verificar_archivo(
        "radicacion/apps/api/bots/compensar.py",
        "Bot Compensar (función)"
    ))
    resultados.append(verificar_contenido(
        "radicacion/apps/api/bots/compensar.py",
        "def radicar_en_compensar",
        "Función radicar_en_compensar existe"
    ))
    print()
    
    # 4. Verificar exports
    print("4️⃣ Exports en __init__.py")
    print("-" * 80)
    resultados.append(verificar_contenido(
        "radicacion/apps/api/bots/__init__.py",
        "radicar_en_compensar",
        "radicar_en_compensar importado"
    ))
    resultados.append(verificar_contenido(
        "radicacion/apps/api/bots/__init__.py",
        'from .compensar import radicar_en_compensar',
        "Import de compensar en __init__.py"
    ))
    print()
    
    # 5. Verificar API
    print("5️⃣ Endpoint en main.py")
    print("-" * 80)
    resultados.append(verificar_contenido(
        "radicacion/apps/api/main.py",
        "radicar_en_compensar",
        "radicar_en_compensar importado en main.py"
    ))
    resultados.append(verificar_contenido(
        "radicacion/apps/api/main.py",
        "@app.post(\"/api/radicar/compensar\")",
        "Endpoint POST /api/radicar/compensar existe"
    ))
    resultados.append(verificar_contenido(
        "radicacion/apps/api/main.py",
        "_ejecutar_radicacion_compensar",
        "Worker _ejecutar_radicacion_compensar existe"
    ))
    print()
    
    # 6. Verificar Admin
    print("6️⃣ Admin Portal")
    print("-" * 80)
    resultados.append(verificar_contenido(
        "admin-neurobaeza/src/pages/BotConfiguration.jsx",
        "compensar",
        "compensar incluido en BOTS_CATÁLOGO"
    ))
    resultados.append(verificar_contenido(
        "admin-neurobaeza/src/components/Layout.jsx",
        "/bots",
        "Ruta /bots en navegación"
    ))
    print()
    
    # 7. Verificar Documentación de Integración
    print("7️⃣ Documentación de Integración")
    print("-" * 80)
    resultados.append(verificar_contenido(
        "INTEGRACION_BOTS_ADMIN_RADICACION.md",
        "Bot: COMPENSAR EPS",
        "Sección Compensar en documentación"
    ))
    print()
    
    # Resumen
    print("=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    
    total = len(resultados)
    exitosos = sum(resultados)
    fallidos = total - exitosos
    
    print()
    print(f"   ✅ Verificaciones exitosas: {exitosos}/{total}")
    print(f"   ❌ Verificaciones fallidas: {fallidos}/{total}")
    print()
    
    if fallidos == 0:
        print("🎉 ¡TODO ESTÁ LISTO PARA GRABAR!")
        print()
        print("Próximos pasos:")
        print("  1. cd radicacion/apps/api/bots")
        print("  2. python record_compensar_codegen.py")
        print()
        return 0
    else:
        print("⚠️ Hay verificaciones que fallaron.")
        print()
        print("Revisa los archivos faltantes o los textos no encontrados.")
        print("Si hace poco actualizaste el código, intenta de nuevo.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
