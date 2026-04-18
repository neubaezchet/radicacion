"""
Bot SURA — implementación real con Playwright vive aquí.

En el referente original el archivo se llamaba `bot_sura.py`. Copia tu lógica
de automatización a la clase `BotSura` manteniendo las firmas de
`DatosIncapacidad` y `ResultadoRadicacion`.
"""

from __future__ import annotations

import asyncio

from bots.base import BotRadicacionEPS, DatosIncapacidad, ResultadoRadicacion
from config import get_settings


class BotSura(BotRadicacionEPS):
    eps_id = "sura"

    async def radicar(self, datos: DatosIncapacidad, *, headless: bool = True) -> ResultadoRadicacion:
        settings = get_settings()
        if settings.mock_radicacion:
            await asyncio.sleep(0.5)
            return ResultadoRadicacion(
                True,
                "MOCK-0001",
                "Radicación simulada (MOCK_RADICACION=true). Sustituye por Playwright en producción.",
            )

        # TODO: importar playwright y automatizar el portal SURA usando `datos`.
        _ = headless
        return ResultadoRadicacion(
            False,
            None,
            "Bot SURA pendiente: pega aquí la implementación desde tu proyecto (Playwright).",
        )


_bot_sura = BotSura()


async def radicar_en_sura(datos: DatosIncapacidad, headless: bool = True) -> ResultadoRadicacion:
    return await _bot_sura.radicar(datos, headless=headless)
