from .base import (
    CredencialesEmpleador,
    DatosRadicacion,
    DatosIncapacidad,      # alias de DatosRadicacion
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
    TIPOS_DOCUMENTO_LABELS,
)
from .sura import radicar_sura
from .compensar import radicar_en_compensar

__all__ = [
    "CredencialesEmpleador",
    "DatosRadicacion",
    "DatosIncapacidad",
    "ResultadoRadicacion",
    "TIPOS_DOCUMENTO_VALIDOS",
    "TIPOS_DOCUMENTO_LABELS",
    "radicar_sura",
    "radicar_en_compensar",
]
