from bots.base import (
    CredencialesEmpleador,
    DatosRadicacion,
    DatosIncapacidad,      # alias de DatosRadicacion
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
    TIPOS_DOCUMENTO_LABELS,
)
from bots.sura import radicar_en_sura, radicar_sura

__all__ = [
    "CredencialesEmpleador",
    "DatosRadicacion",
    "DatosIncapacidad",
    "ResultadoRadicacion",
    "TIPOS_DOCUMENTO_VALIDOS",
    "TIPOS_DOCUMENTO_LABELS",
    "radicar_en_sura",
    "radicar_sura",
]
