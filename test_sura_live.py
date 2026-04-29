#!/usr/bin/env python3
"""
Test SURA EN VIVO - Muestra el navegador en tiempo real.
Ejecutar desde PowerShell en la carpeta radicacion.
"""

import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Configurar logging
log_file = Path(tempfile.gettempdir()) / "test_sura_live.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file)),
    ],
)

log = logging.getLogger(__name__)

print("\n" + "="*80)
print("BOT SURA - EJECUCIÓN EN VIVO")
print("="*80)
print(f"📝 Logs guardados en: {log_file}\n")

# Datos de prueba
TIPO_DOC = "C"
NUM_DOC = "51899483"
PIN = "2025"
NUM_INCAPACIDAD = "43445280"

print(f"📋 DATOS DE PRUEBA:")
print(f"   Tipo: {TIPO_DOC}")
print(f"   Documento: {NUM_DOC}")
print(f"   PIN: ***")
print(f"   Incapacidad: {NUM_INCAPACIDAD}")
print(f"\n⏳ Iniciando navegador en 3 segundos...\n")

sys.path.insert(0, str(Path(__file__).parent))

try:
    from apps.api.bots.sura import radicar_sura

    # Ejecutar con ventana visible
    resultado = radicar_sura(
        tipo_documento=TIPO_DOC,
        numero_documento=NUM_DOC,
        clave=PIN,
        numero_incapacidad=NUM_INCAPACIDAD,
        prefijo_incapacidad="0",
        documento_trabajador="79718363",
        fecha_inicio="24 04 2026",
        headless=False,  # ← MOSTRAR NAVEGADOR EN VIVO
    )

    print("\n" + "="*80)
    print("✅ ¡ÉXITO!")
    print("="*80)
    print(f"Radicado: {resultado.get('numero_radicado')}")
    print(f"Mensaje: {resultado.get('mensaje')}")
    print(f"PDF: {resultado.get('pdf_path')}")

except Exception as e:
    print("\n" + "="*80)
    print("❌ ERROR DETECTADO")
    print("="*80)
    print(f"\nTipo: {type(e).__name__}")
    print(f"Error: {str(e)}\n")

    # Mostrar dónde están los archivos de debugging
    debug_dir = Path(tempfile.gettempdir()) / "sura_debug"
    error_dir = Path(tempfile.gettempdir()) / "sura_errors"
    video_dir = Path(tempfile.gettempdir()) / "sura_videos"

    print("-" * 80)
    if debug_dir.exists():
        print("\n📁 ARCHIVOS DE DEBUG DEL TECLADO:")
        for f in sorted(debug_dir.glob("*"))[-3:]:
            print(f"   📄 {f.name}")
            print(f"      {f}")

    if error_dir.exists():
        print("\n📁 SCREENSHOTS DE ERROR:")
        for f in sorted(error_dir.glob("*"))[-3:]:
            print(f"   📸 {f.name}")
            print(f"      {f}")

    if video_dir.exists():
        print("\n📁 VIDEOS GRABADOS:")
        for f in sorted(video_dir.glob("*"))[-3:]:
            print(f"   🎬 {f.name}")
            print(f"      {f}")

    print(f"\n📝 LOGS COMPLETOS:")
    print(f"   {log_file}")
    print("\n" + "="*80)
    sys.exit(1)

print("\n" + "="*80 + "\n")
