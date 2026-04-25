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
    DatosRadicacion,
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
    TIPOS_DOCUMENTO_LABELS,
    radicar_en_sura,
)
from config import Settings, get_settings
from jobs import radicaciones

app = FastAPI(
    title="Radicación EPS",
    version="2.1.0",
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
        "version": "2.1.0",
        "docs": "/docs",
        "tipos_documento": TIPOS_DOCUMENTO_LABELS,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tipos-documento")
async def tipos_documento() -> dict[str, Any]:
    """
    Lista los tipos de documento válidos para el portal SURA.
    Devuelve tanto el value del DOM (para enviar al bot) como el label legible.
    """
    return {"tipos_documento": TIPOS_DOCUMENTO_LABELS}


# ── Radicación SURA ───────────────────────────────────────────────────────

@app.post("/api/radicar/sura")
async def radicar_sura_endpoint(
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_service_key)],
    # — Credenciales empleador —
    tipo_documento_empleador: str = Form(
        ...,
        description="Value del select del portal: 'C'=CEDULA, 'A'=NIT, etc. Ver /tipos-documento"
    ),
    numero_documento_empleador: str = Form(...),
    clave_empleador: str = Form(..., description="PIN numérico del portal"),
    # — Trabajador —
    cedula_trabajador: str = Form(...),
    fecha_inicio_incapacidad: Optional[str] = Form(
        None,
        description="Formato: 'DD MM YYYY', ej: '18 04 2026'"
    ),
    # — Incapacidad —
    prefijo_incapacidad: str = Form("0", description="Primer recuadro del número (ej: 0)"),
    numero_incapacidad: str = Form(..., description="Segundo recuadro — dígitos principales"),
    # — Flujo —
    transcripcion: bool = Form(False, description="True si la incapacidad es externa (requiere PDF)"),
    # — Documentos opcionales —
    pdf_incapacidad: Optional[UploadFile] = File(None),
    soportes_adicionales: Optional[list[UploadFile]] = File(None),
) -> dict[str, Any]:

    if tipo_documento_empleador not in TIPOS_DOCUMENTO_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"tipo_documento_empleador '{tipo_documento_empleador}' no válido. "
                f"Valores aceptados: {TIPOS_DOCUMENTO_VALIDOS}. "
                f"Ver /tipos-documento para la lista completa con labels."
            ),
        )

    if transcripcion and not pdf_incapacidad:
        raise HTTPException(
            status_code=422,
            detail="Para transcripciones se requiere adjuntar pdf_incapacidad.",
        )

    job_id = str(uuid.uuid4())

    # Guardar archivos subidos en /tmp/uploads
    pdf_path: Optional[str] = None
    if pdf_incapacidad and pdf_incapacidad.filename:
        p = UPLOADS_DIR / f"{job_id}_incap.pdf"
        p.write_bytes(await pdf_incapacidad.read())
        pdf_path = str(p)

    soportes_paths: list[str] = []
    if soportes_adicionales:
        for i, soporte in enumerate(soportes_adicionales):
            if soporte and soporte.filename:
                sp = UPLOADS_DIR / f"{job_id}_soporte_{i}.pdf"
                sp.write_bytes(await soporte.read())
                soportes_paths.append(str(sp))

    datos = DatosRadicacion(
        credenciales=CredencialesEmpleador(
            tipo_documento=tipo_documento_empleador,
            numero_documento=numero_documento_empleador,
            clave=clave_empleador,
        ),
        documento_trabajador=cedula_trabajador,
        fecha_inicio_incapacidad=fecha_inicio_incapacidad,
        prefijo_incapacidad=prefijo_incapacidad,
        numero_incapacidad=numero_incapacidad,
        transcripcion=transcripcion,
        pdf_incapacidad=pdf_path,
        soportes_adicionales=soportes_paths if soportes_paths else None,
    )

    radicaciones[job_id] = {
        "job_id": job_id,
        "eps": "sura",
        "status": "procesando",
        "cedula_trabajador": cedula_trabajador,
        "numero_incapacidad": f"{prefijo_incapacidad}-{numero_incapacidad}",
        "transcripcion": transcripcion,
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

async def _ejecutar_radicacion(job_id: str, datos: DatosRadicacion) -> None:
    try:
        resultado: ResultadoRadicacion = await radicar_en_sura(datos)
        radicaciones[job_id] = {
            **radicaciones[job_id],
            "status": "exitoso" if resultado.exitoso else "fallido",
            "numero_radicado": resultado.numero_radicado,
            "mensaje": resultado.mensaje,
            "pdf_path": resultado.pdf_path,
        }
    except Exception as e:
        radicaciones[job_id] = {
            **radicaciones[job_id],
            "status": "error",
            "mensaje": str(e),
        }
    finally:
        # Limpiar archivos temporales subidos
        if datos.pdf_incapacidad:
            try:
                Path(datos.pdf_incapacidad).unlink(missing_ok=True)
            except Exception:
                pass
        if datos.soportes_adicionales:
            for sp in datos.soportes_adicionales:
                try:
                    Path(sp).unlink(missing_ok=True)
                except Exception:
                    pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
