"""Contrato común para bots de radicación por EPS."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Tipos de documento válidos en el portal SURA (copiados exactamente)
# ---------------------------------------------------------------------------
TipoDocumento = Literal[
    "CEDULA",
    "CEDULA EXTRANJERIA",
    "DIPLOMATICO",
    "DOC.IDENT. DE EXTRANJEROS",
    "IDENT. FISCAL PARA EXT.",
    "NIT",
    "NIT PERSONAS NATURALES",
    "NUIP",
    "PASAPORTE",
    "REGISTRO CIVIL",
    "TARJ.IDENTIDAD",
    "CERTIFICADO NACIDO VIVO",
    "PASAPORTE ONU",
    "PERMISO ESPECIAL PERMANENCIA",
    "SALVOCONDUCTO DE PERMANENCIA",
    "PERMISO ESPECIAL FORMACN PEPFF",
    "PERMISO POR PROTECCION TEMPORL",
]

TIPOS_DOCUMENTO_VALIDOS: list[str] = list(TipoDocumento.__args__)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Datos de credenciales del empleador (multi-tenant: viene en cada request)
# ---------------------------------------------------------------------------
@dataclass
class CredencialesEmpleador:
    tipo_documento: str
    """Valor exacto del dropdown del portal (ver TIPOS_DOCUMENTO_VALIDOS)."""

    numero_documento: str
    """NIT, cédula u otro número según tipo_documento."""

    clave: str
    """Clave del portal. Se ingresa en el teclado virtual. NUNCA se persiste."""


# ---------------------------------------------------------------------------
# Datos de la incapacidad a radicar
# ---------------------------------------------------------------------------
@dataclass
class DatosIncapacidad:
    # — Credenciales del empleador (multi-tenant) —
    credenciales: CredencialesEmpleador

    # — Trabajador —
    tipo_documento_trabajador: str
    cedula_trabajador: str

    # — Incapacidad —
    prefijo_incapacidad: str
    """Primer recuadro del número de incapacidad (ej: '0')."""

    numero_incapacidad: str
    """Segundo recuadro — dígitos restantes (ej: '22393939')."""

    fecha_inicio: str   # DD/MM/YYYY
    fecha_fin: str      # DD/MM/YYYY
    dias_incapacidad: int

    # — Documentos (requeridos para transcripciones) —
    pdf_incapacidad: Optional[Path] = None
    pdf_historia_clinica: Optional[Path] = None

    # — Flujo —
    es_transcripcion: bool = False
    """True = incapacidad externa que requiere adjuntar PDF y más datos."""

    # — Datos adicionales para transcripción —
    datos_extra: dict = field(default_factory=dict)
    """Campos opcionales: medico, diagnostico_cie10, etc."""


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
@dataclass
class ResultadoRadicacion:
    exitoso: bool
    numero_radicado: Optional[str]
    mensaje: str


# ---------------------------------------------------------------------------
# Contrato base
# ---------------------------------------------------------------------------
class BotRadicacionEPS(ABC):
    eps_id: str

    @abstractmethod
    async def radicar(
        self,
        datos: DatosIncapacidad,
        *,
        headless: bool = True,
    ) -> ResultadoRadicacion:
        ...
