#!/usr/bin/env python3
"""
Script de prueba MEJORADO con diagnóstico detallado.
Captura screenshots, videos y HTML para debugging.
"""

import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Configurar logging detallado con colores y timestamps
log_file = Path(tempfile.gettempdir()) / "test_sura_mejorado.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file)),
    ],
)

log = logging.getLogger(__name__)

log.info("=" * 80)
log.info("TEST SURA — Versión Mejorada con Debugging")
log.info("=" * 80)
log.info("Logs guardados en: %s", log_file)

# ─────────────────────────────────────────────────────────────
# CONFIGURAR TUS DATOS DE PRUEBA
# ─────────────────────────────────────────────────────────────

CREDENCIALES_EMPLEADOR = {
    "tipo_documento": "C",              # "C" = Cédula, "A" = NIT
    "numero_documento": "51899483",     # ← REEMPLAZA CON TU NÚM
    "clave": "2025",                   # ← REEMPLAZA CON TU PIN
}

DATOS_INCAPACIDAD = {
    "numero_incapacidad": "43445280",      # ← REEMPLAZA CON NÚM REAL
    "prefijo_incapacidad": "0",
    "documento_trabajador": "79718363",
    "fecha_inicio_incapacidad": "24 04 2026",
}

# ─────────────────────────────────────────────────────────────


def main():
    """Ejecuta prueba con todos los diagnósticos."""

    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from apps.api.bots.sura import radicar_sura

        log.info("✓ Importación correcta de radicar_sura")

        # Preparar datos
        log.info("─" * 80)
        log.info("DATOS DE ENTRADA:")
        log.info("  Tipo Documento: %s", CREDENCIALES_EMPLEADOR["tipo_documento"])
        log.info("  Número: %s", CREDENCIALES_EMPLEADOR["numero_documento"])
        log.info("  PIN: ***")
        log.info("  Número Incapacidad: %s", DATOS_INCAPACIDAD["numero_incapacidad"])
        log.info("─" * 80)

        # Ejecutar bot con ventana visible (no headless para ver qué pasa)
        log.info("Iniciando bot SURA...")
        resultado = radicar_sura(
            tipo_documento=CREDENCIALES_EMPLEADOR["tipo_documento"],
            numero_documento=CREDENCIALES_EMPLEADOR["numero_documento"],
            clave=CREDENCIALES_EMPLEADOR["clave"],
            numero_incapacidad=DATOS_INCAPACIDAD["numero_incapacidad"],
            prefijo_incapacidad=DATOS_INCAPACIDAD["prefijo_incapacidad"],
            documento_trabajador=DATOS_INCAPACIDAD["documento_trabajador"],
            fecha_inicio=DATOS_INCAPACIDAD["fecha_inicio_incapacidad"],
            headless=False,  # ← Mostrar ventana del navegador para ver qué pasa
        )

        # Mostrar resultado
        log.info("=" * 80)
        log.info("✓ RESULTADO EXITOSO")
        log.info("=" * 80)
        log.info("Radicado: %s", resultado.get("numero_radicado"))
        log.info("Mensaje: %s", resultado.get("mensaje"))
        log.info("PDF: %s", resultado.get("pdf_path"))

        return 0

    except Exception as e:
        log.error("=" * 80)
        log.error("✗ ERROR DETECTADO")
        log.error("=" * 80)
        log.error("Tipo de error: %s", type(e).__name__)
        log.error("Mensaje: %s", str(e))
        log.error("─" * 80)

        # Indicar dónde buscar los archivos de debugging
        debug_dir = Path(tempfile.gettempdir()) / "sura_debug"
        error_dir = Path(tempfile.gettempdir()) / "sura_errors"
        video_dir = Path(tempfile.gettempdir()) / "sura_videos"

        if debug_dir.exists():
            log.error("📁 ARCHIVOS DE DEBUG (Teclado Virtual):")
            for f in debug_dir.glob("*"):
                log.error("   → %s", f)

        if error_dir.exists():
            log.error("📁 SCREENSHOTS DE ERROR:")
            for f in error_dir.glob("*"):
                log.error("   → %s", f)

        if video_dir.exists():
            log.error("📁 VIDEOS GRABADOS:")
            for f in video_dir.glob("*"):
                log.error("   → %s", f)

        log.error("=" * 80)
        log.error("Para ver más detalles, abre los archivos listados arriba")
        log.error("=" * 80)

        return 1


if __name__ == "__main__":
    sys.exit(main())
