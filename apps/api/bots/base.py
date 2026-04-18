"""Contrato común para bots de radicación por EPS."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DatosIncapacidad:
    nit_empleador: str
    clave_empleador: str
    cedula_trabajador: str
    numero_incapacidad: str
    fecha_inicio: str
    fecha_fin: str
    dias_incapacidad: int
    pdf_incapacidad: Path
    pdf_historia_clinica: Optional[Path]


@dataclass
class ResultadoRadicacion:
    exitoso: bool
    numero_radicado: Optional[str]
    mensaje: str


class BotRadicacionEPS(ABC):
    eps_id: str

    @abstractmethod
    async def radicar(self, datos: DatosIncapacidad, *, headless: bool = True) -> ResultadoRadicacion:
        ...
