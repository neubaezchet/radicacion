"""
API de radicación (FastAPI) — Railway + Docker (Playwright).
Multi-tenant: las credenciales vienen en cada request, nunca se almacenan.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from bots import (
    CredencialesEmpleador,
    DatosIncapacidad,
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
    radicar_en_sura,
)
from config import Settings, get_settings
from jobs import radicaciones

app = FastAPI(
    title="Radicación EPS",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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


# ── Info ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "radicacion-api",
        "version": "2.0.0",
        "docs": "/docs",
        "tipos_documento": TIPOS_DOCUMENTO_VALIDOS,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tipos-documento")
async def tipos_documento() -> dict[str, list[str]]:
    """Lista los tipos de documento válidos para el portal SURA."""
    return {"tipos_documento": TIPOS_DOCUMENTO_VALIDOS}


# ── Radicación SURA ───────────────────────────────────────────────────────

@app.post("/api/radicar/sura")
async def radicar_sura(
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_service_key)],
    # — Credenciales empleador (multi-tenant) —
    tipo_documento_empleador: str = Form(..., description="Tipo de documento del empleador según portal SURA"),
    numero_documento_empleador: str = Form(..., description="NIT, cédula u otro número"),
    clave_empleador: str = Form(..., description="Clave del portal (teclado virtual)"),
    # — Trabajador —
    tipo_documento_trabajador: str = Form("CEDULA"),
    cedula_trabajador: str = Form(...),
    # — Incapacidad —
    prefijo_incapacidad: str = Form(..., description="Primer recuadro del número (ej: 0)"),
    numero_incapacidad: str = Form(..., description="Segundo recuadro — dígitos restantes"),
    fecha_inicio: str = Form(..., description="DD/MM/YYYY"),
    fecha_fin: str = Form(..., description="DD/MM/YYYY"),
    dias_incapacidad: int = Form(...),
    es_transcripcion: bool = Form(False, description="True si la incapacidad es externa (requiere PDF)"),
    # — Documentos opcionales —
    pdf_incapacidad: Optional[UploadFile] = File(None),
    pdf_historia_clinica: Optional[UploadFile] = File(None),
) -> dict[str, Any]:

    if tipo_documento_empleador not in TIPOS_DOCUMENTO_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"tipo_documento_empleador '{tipo_documento_empleador}' no válido. "
                   f"Opciones: {TIPOS_DOCUMENTO_VALIDOS}",
        )

    if es_transcripcion and not pdf_incapacidad:
        raise HTTPException(
            status_code=422,
            detail="Para transcripciones se requiere pdf_incapacidad.",
        )

    job_id = str(uuid.uuid4())

    pdf_path: Optional[Path] = None
    if pdf_incapacidad and pdf_incapacidad.filename:
        pdf_path = UPLOADS_DIR / f"{job_id}_incap.pdf"
        pdf_path.write_bytes(await pdf_incapacidad.read())

    historia_path: Optional[Path] = None
    if pdf_historia_clinica and pdf_historia_clinica.filename:
        historia_path = UPLOADS_DIR / f"{job_id}_historia.pdf"
        historia_path.write_bytes(await pdf_historia_clinica.read())

    datos = DatosIncapacidad(
        credenciales=CredencialesEmpleador(
            tipo_documento=tipo_documento_empleador,
            numero_documento=numero_documento_empleador,
            clave=clave_empleador,
        ),
        tipo_documento_trabajador=tipo_documento_trabajador,
        cedula_trabajador=cedula_trabajador,
        prefijo_incapacidad=prefijo_incapacidad,
        numero_incapacidad=numero_incapacidad,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        dias_incapacidad=dias_incapacidad,
        es_transcripcion=es_transcripcion,
        pdf_incapacidad=pdf_path,
        pdf_historia_clinica=historia_path,
    )

    radicaciones[job_id] = {
        "job_id": job_id,
        "eps": "sura",
        "status": "procesando",
        "cedula_trabajador": cedula_trabajador,
        "numero_incapacidad": f"{prefijo_incapacidad}-{numero_incapacidad}",
        "es_transcripcion": es_transcripcion,
    }
    background_tasks.add_task(_ejecutar_radicacion, job_id, datos)

    return {"job_id": job_id, "status": "procesando"}


@app.get("/api/estado/{job_id}")
async def estado_radicacion(job_id: str) -> dict[str, Any]:
    if job_id not in radicaciones:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return radicaciones[job_id]


@app.get("/api/radicaciones")
async def listar_radicaciones(
    _: Annotated[None, Depends(require_service_key)],
) -> list[dict[str, Any]]:
    return list(radicaciones.values())


# ── Worker ────────────────────────────────────────────────────────────────

async def _ejecutar_radicacion(job_id: str, datos: DatosIncapacidad) -> None:
    try:
        resultado: ResultadoRadicacion = await radicar_en_sura(datos, headless=True)
        radicaciones[job_id] = {
            **radicaciones[job_id],
            "status": "exitoso" if resultado.exitoso else "fallido",
            "numero_radicado": resultado.numero_radicado,
            "mensaje": resultado.mensaje,
        }
    except Exception as e:
        radicaciones[job_id] = {
            **radicaciones[job_id],
            "status": "error",
            "mensaje": str(e),
        }
    finally:
        # Limpiar archivos temporales
        for attr in ("pdf_incapacidad", "pdf_historia_clinica"):
            p: Path | None = getattr(datos, attr, None)
            if p and p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
