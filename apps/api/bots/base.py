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
    documento_trabajador: Optional[str] = None
    fecha_inicio_incapacidad: Optional[str] = None  # Formato: "DD MM YYYY" ej: "18 04 2026"

    # Número de incapacidad (dos campos como en el portal)
    prefijo_incapacidad: Optional[str] = "0"     # Campo izquierdo, normalmente "0"
    numero_incapacidad: str                      # Campo derecho, ej: "43445280"

    # Flujo
    transcripcion: bool = False                  # False=digitalizada, True=transcripción

    # Archivos para transcripción
    pdf_incapacidad: Optional[str] = None
    soportes_adicionales: Optional[list[str]] = None


class ResultadoRadicacion(BaseModel):
    """Resultado devuelto por el bot al endpoint de la API."""
    exitoso: bool
    numero_radicado: Optional[str] = None
    mensaje: str
    pdf_path: Optional[str] = None


# Alias para compatibilidad con el __init__.py del proyecto
DatosIncapacidad = DatosRadicacion

# Tipos de documento válidos en el portal SURA
TIPOS_DOCUMENTO_VALIDOS = [
    "C",   # CEDULA
    "E",   # CEDULA EXTRANJERIA
    "D",   # DIPLOMATICO
    "X",   # DOC.IDENT. DE EXTRANJEROS
    "F",   # IDENT. FISCAL PARA EXT.
    "A",   # NIT
    "N",   # NIT PERSONAS NATURALES
    "U",   # NUIP
    "P",   # PASAPORTE
    "R",   # REGISTRO CIVIL
    "T",   # TARJ.IDENTIDAD
    "B",   # CERTIFICADO NACIDO VIVO
    "O",   # PASAPORTE ONU
    "Q",   # PERMISO ESPECIAL PERMANENCIA
    "S",   # SALVOCONDUCTO DE PERMANENCIA
    "G",   # PERMISO ESPECIAL FORMACN PEPFF
    "M",   # PERMISO POR PROTECCION TEMPORL
]

TIPOS_DOCUMENTO_LABELS = {
    "C": "CEDULA",
    "E": "CEDULA EXTRANJERIA",
    "D": "DIPLOMATICO",
    "X": "DOC.IDENT. DE EXTRANJEROS",
    "F": "IDENT. FISCAL PARA EXT.",
    "A": "NIT",
    "N": "NIT PERSONAS NATURALES",
    "U": "NUIP",
    "P": "PASAPORTE",
    "R": "REGISTRO CIVIL",
    "T": "TARJ.IDENTIDAD",
    "B": "CERTIFICADO NACIDO VIVO",
    "O": "PASAPORTE ONU",
    "Q": "PERMISO ESPECIAL PERMANENCIA",
    "S": "SALVOCONDUCTO DE PERMANENCIA",
    "G": "PERMISO ESPECIAL FORMACN PEPFF",
    "M": "PERMISO POR PROTECCION TEMPORL",
}
