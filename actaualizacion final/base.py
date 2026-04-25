"""
Modelos de datos compartidos entre la API y los bots.
"""
from pydantic import BaseModel
from typing import Optional


class CredencialesEmpleador(BaseModel):
    """
    Credenciales del empleador para el portal de la EPS.
    tipo_documento: value del select del portal (ej: "C" para CEDULA, "A" para NIT)
    """
    tipo_documento: str          # "C", "E", "A", etc. — value del select del DOM
    numero_documento: str        # Número de identificación del empleador
    clave: str                   # PIN de 4 dígitos


class DatosRadicacion(BaseModel):
    """
    Todos los datos necesarios para radicar una incapacidad.
    El backend los envía en cada request; el bot nunca los almacena.
    """
    credenciales: CredencialesEmpleador

    # Datos del trabajador
    documento_trabajador: Optional[str] = None   # Cédula del trabajador (para el PDF)
    fecha_inicio_incapacidad: Optional[str] = None  # Formato: "DD MM YYYY" ej: "18 04 2026"

    # Número de incapacidad (dos campos como en el portal)
    prefijo_incapacidad: Optional[str] = "0"     # Campo izquierdo, normalmente "0"
    numero_incapacidad: str                      # Campo derecho, ej: "43445280"

    # Flujo
    transcripcion: bool = False                  # False=digitalizada, True=transcripción

    # Archivos para transcripción
    pdf_incapacidad: Optional[str] = None        # Ruta local al PDF de la incapacidad
    soportes_adicionales: Optional[list[str]] = None  # Rutas a soportes adicionales


class ResultadoRadicacion(BaseModel):
    """Resultado devuelto por el bot al endpoint de la API."""
    exitoso: bool
    numero_radicado: Optional[str] = None
    mensaje: str
    pdf_path: Optional[str] = None   # Ruta al PDF de confirmación guardado en el servidor
