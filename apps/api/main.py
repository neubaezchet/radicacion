"""
API de radicación (FastAPI) — despliegue recomendado: Railway + Docker (Playwright).
El panel web vive en `apps/web` (Vercel).
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from bots import DatosIncapacidad, ResultadoRadicacion, radicar_en_sura
from config import Settings, get_settings
from jobs import radicaciones

app = FastAPI(title="Radicación EPS", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

UPLOADS_DIR = Path("/tmp/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def parse_cors(settings: Settings) -> list[str]:
    raw = settings.cors_origins.strip()
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors(_settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_service_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_radicacion_key: Annotated[str | None, Header(alias="X-Radicacion-Key")] = None,
) -> None:
    if settings.radicacion_api_key and x_radicacion_key != settings.radicacion_api_key:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "radicacion-api", "docs": "/docs"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/radicar/sura")
async def radicar_sura(
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_service_key)],
    nit_empleador: str = Form(...),
    clave_empleador: str = Form(...),
    cedula_trabajador: str = Form(...),
    numero_incapacidad: str = Form(...),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    dias_incapacidad: int = Form(...),
    pdf_incapacidad: UploadFile = File(...),
    pdf_historia_clinica: Optional[UploadFile] = File(None),
) -> dict[str, Any]:
    job_id = str(uuid.uuid4())

    pdf_path = UPLOADS_DIR / f"{job_id}_incap.pdf"
    pdf_path.write_bytes(await pdf_incapacidad.read())

    historia_path = None
    if pdf_historia_clinica and pdf_historia_clinica.filename:
        historia_path = UPLOADS_DIR / f"{job_id}_historia.pdf"
        historia_path.write_bytes(await pdf_historia_clinica.read())

    datos = DatosIncapacidad(
        nit_empleador=nit_empleador,
        clave_empleador=clave_empleador,
        cedula_trabajador=cedula_trabajador,
        numero_incapacidad=numero_incapacidad,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        dias_incapacidad=dias_incapacidad,
        pdf_incapacidad=pdf_path,
        pdf_historia_clinica=historia_path,
    )

    radicaciones[job_id] = {"status": "procesando", "eps": "sura"}
    background_tasks.add_task(_ejecutar_radicacion, job_id, datos)

    return {"job_id": job_id, "status": "procesando"}


@app.get("/api/estado/{job_id}")
async def estado_radicacion(job_id: str) -> dict[str, Any]:
    if job_id not in radicaciones:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return radicaciones[job_id]


@app.get("/api/radicaciones")
async def listar_radicaciones(_: Annotated[None, Depends(require_service_key)]) -> list[dict[str, Any]]:
    return list(radicaciones.values())


async def _ejecutar_radicacion(job_id: str, datos: DatosIncapacidad) -> None:
    try:
        resultado: ResultadoRadicacion = await radicar_en_sura(datos, headless=True)
        radicaciones[job_id] = {
            "job_id": job_id,
            "eps": "sura",
            "cedula": datos.cedula_trabajador,
            "numero_incapacidad": datos.numero_incapacidad,
            "status": "exitoso" if resultado.exitoso else "fallido",
            "numero_radicado": resultado.numero_radicado,
            "mensaje": resultado.mensaje,
        }
    except Exception as e:  # noqa: BLE001 — queremos persistir el error en el job
        radicaciones[job_id] = {
            "job_id": job_id,
            "eps": "sura",
            "status": "error",
            "mensaje": str(e),
        }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
