#!/usr/bin/env python3
"""
Script para pruebas locales del bot SURA con grabación de video.
Captura video y screenshots detallados.
"""

import logging
import sys
import tempfile
from pathlib import Path

# Configurar logging detallado
log_file = Path(tempfile.gettempdir()) / "test_sura_recording.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file)),
    ],
)

log = logging.getLogger(__name__)

# Importar el bot directamente
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api" / "bots"))

from sura import radicar_sura

# ─────────────────────────────────────────────────────────────
# DATOS DE PRUEBA — REEMPLAZA CON TUS VALORES REALES
# ─────────────────────────────────────────────────────────────

CREDENCIALES_EMPLEADOR = {
    "tipo_documento": "C",              # "C" = Cédula, "A" = NIT
    "numero_documento": "51899483",     # ← REEMPLAZA CON TU NÚM
    "clave": "2025",                   # ← REEMPLAZA CON TU PIN (números)
}

DATOS_INCAPACIDAD = {
    "numero_incapacidad": "43445280",      # ← REEMPLAZA CON NÚM REAL
    "prefijo_incapacidad": "0",
    "documento_trabajador": "79718363",
    "fecha_inicio": "24_04_2026",
}

# ─────────────────────────────────────────────────────────────


def main():
    """Ejecuta la prueba del bot con grabación de pantalla."""
    
    log.info("=" * 80)
    log.info("PRUEBA LOCAL BOT SURA CON GRABACIÓN")
    log.info("=" * 80)
    log.info(f"Logs guardados en: {log_file}")
    
    # Parámetros de la prueba
    params = {
        "tipo_documento": CREDENCIALES_EMPLEADOR["tipo_documento"],
        "numero_documento": CREDENCIALES_EMPLEADOR["numero_documento"],
        "clave": CREDENCIALES_EMPLEADOR["clave"],
        "numero_incapacidad": DATOS_INCAPACIDAD["numero_incapacidad"],
        "prefijo_incapacidad": DATOS_INCAPACIDAD["prefijo_incapacidad"],
        "documento_trabajador": DATOS_INCAPACIDAD["documento_trabajador"],
        "fecha_inicio": DATOS_INCAPACIDAD["fecha_inicio"],
        "headless": False,  # ← CON VENTANA VISIBLE para ver qué ocurre
    }
    
    log.info("Parámetros de la prueba:")
    for key, value in params.items():
        if key == "clave":
            log.info(f"  {key}: {'*' * len(value)}")
        else:
            log.info(f"  {key}: {value}")
    
    log.info("\nIniciando bot SURA...")
    
    try:
        resultado = radicar_sura(**params)
        
        log.info("\n" + "=" * 80)
        log.info("RESULTADO DE LA PRUEBA")
        log.info("=" * 80)
        log.info(f"Exitoso      : {resultado['exitoso']}")
        log.info(f"Radicado     : {resultado['numero_radicado']}")
        log.info(f"Mensaje      : {resultado['mensaje']}")
        log.info(f"PDF          : {resultado['pdf_path']}")
        
        print("\n" + "=" * 80)
        print("RESULTADO DE LA PRUEBA")
        print("=" * 80)
        print(f"✓ Exitoso      : {resultado['exitoso']}")
        print(f"  Radicado     : {resultado['numero_radicado']}")
        print(f"  Mensaje      : {resultado['mensaje']}")
        print(f"  PDF          : {resultado['pdf_path']}")
        print("=" * 80)
        
        if resultado['exitoso']:
            return 0
        else:
            return 1
            
    except Exception as ex:
        log.error(f"ERROR CRÍTICO: {ex}", exc_info=True)
        print(f"\n❌ ERROR: {ex}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
