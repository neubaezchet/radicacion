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
import httpx
import uvicorn

from bots import (
    CredencialesEmpleador,
    DatosRadicacion,
    ResultadoRadicacion,
    TIPOS_DOCUMENTO_VALIDOS,
    TIPOS_DOCUMENTO_LABELS,
    radicar_en_sura,
    radicar_en_compensar,
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


@app.get("/api/config/empresa/{nombre_empresa}")
async def obtener_config_empresa(nombre_empresa: str) -> dict[str, Any]:
    """
    🔐 Obtiene la configuración de bots para una empresa desde el backend principal.
    
    IMPORTANTE: Este endpoint es consultado por el frontend/backend principal para:
    1. Obtener qué bot usar para una empresa
    2. Obtener las credenciales dinámicas del bot
    
    Flujo:
    - Portal admin configura bots por empresa en backend principal
    - Cuando se va a radicar, se consulta este endpoint
    - Backend principal responde con credenciales actualizadas
    
    Ventaja: Cambios en credenciales en admin se reflejan inmediatamente
    en radicación sin redeploying de esta API.
    """
    import httpx
    
    try:
        # Obtener URL del backend principal desde variables de entorno
        backend_principal = os.environ.get(
            "BACKEND_PRINCIPAL_URL",
            "https://web-production-95ed.up.railway.app"
        )
        
        # Consultar el backend principal por credenciales del bot
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{backend_principal}/admin/empresas/{nombre_empresa}/bots",
                headers={"Authorization": f"Bearer {os.environ.get('ADMIN_JWT_SECRET', '')}"}
            )
            resp.raise_for_status()
            
            data = resp.json()
            if not data.get("ok"):
                raise HTTPException(
                    status_code=404,
                    detail=f"Empresa '{nombre_empresa}' no encontrada o sin bots configurados"
                )
            
            bots = data.get("bots", [])
            bots_activos = [b for b in bots if b.get("estado") == "activo"]
            
            if not bots_activos:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay bots activos para '{nombre_empresa}'"
                )
            
            # Retornar la configuración
            return {
                "ok": True,
                "empresa": nombre_empresa,
                "bots_disponibles": len(bots),
                "bots_activos": len(bots_activos),
                "bots": [{
                    "bot_nombre": b.get("bot_nombre"),
                    "estado": b.get("estado"),
                    "tipo_medio": b.get("bot_tipo_medio"),
                } for b in bots_activos],
                "mensaje": "✅ Configuración obtenida dinámicamente del backend principal"
            }
    
    except httpx.HTTPError as e:
        # Si no se puede conectar al backend, devolver error claro
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar con backend principal para obtener config: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obtienen config: {str(e)}"
        )


@app.get("/api/credenciales/empresa/{nombre_empresa}/bot/{bot_nombre}")
async def obtener_credenciales_bot(nombre_empresa: str, bot_nombre: str) -> dict[str, Any]:
    """
    🔐 Obtiene las credenciales de un bot específico para una empresa.
    
    Esta es la consulta que hace el bot cuando necesita radicar:
    1. Bot SURA necesita credenciales → consulta este endpoint
    2. Recibe credenciales actualizadas en vivo
    3. Usa esas credenciales para radicar
    
    Si cambias credenciales en el admin, el bot automáticamente usa las nuevas.
    """
    import httpx
    
    try:
        backend_principal = os.environ.get(
            "BACKEND_PRINCIPAL_URL",
            "https://web-production-95ed.up.railway.app"
        )
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{backend_principal}/admin/empresas/{nombre_empresa}/bots/{bot_nombre}/credenciales",
                headers={"Authorization": f"Bearer {os.environ.get('ADMIN_JWT_SECRET', '')}"}
            )
            resp.raise_for_status()
            
            data = resp.json()
            if not data.get("ok"):
                raise HTTPException(status_code=404, detail="Bot o credenciales no encontrados")
            
            return {
                "ok": True,
                "empresa": nombre_empresa,
                "bot": bot_nombre,
                "credenciales": data.get("credenciales", {}),
                "vigentes_desde": data.get("vigentes_desde"),
                "mensaje": "✅ Credenciales obtenidas en vivo del backend"
            }
    
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error conectando con backend: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


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


# ── Radicación COMPENSAR ──────────────────────────────────────────────────

@app.post("/api/radicar/compensar")
async def radicar_compensar_endpoint(
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_service_key)],
    # — Credenciales empleador —
    numero_documento_empleador: str = Form(
        ...,
        description="NIT o documento del empleador para Compensar"
    ),
    clave_empleador: str = Form(..., description="Contraseña del portal Compensar"),
    # — Trabajador —
    cedula_trabajador: str = Form(...),
    fecha_inicio_incapacidad: Optional[str] = Form(
        None,
        description="Formato: 'DD MM YYYY', ej: '18 04 2026'"
    ),
    # — Incapacidad —
    numero_incapacidad: str = Form(..., description="Número de incapacidad"),
    # — Flujo —
    transcripcion: bool = Form(False, description="True si la incapacidad es externa (requiere PDF)"),
    # — Documentos opcionales —
    pdf_incapacidad: Optional[UploadFile] = File(None),
    soportes_adicionales: Optional[list[UploadFile]] = File(None),
) -> dict[str, Any]:
    """
    Radica incapacidad en el portal de COMPENSAR.
    
    Endpoint: POST /api/radicar/compensar
    
    Parámetros (form-data):
    - numero_documento_empleador: NIT o documento
    - clave_empleador: contraseña
    - cedula_trabajador: cédula del trabajador
    - fecha_inicio_incapacidad: DD MM YYYY
    - numero_incapacidad: número de la incapacidad
    - transcripcion: true/false
    - pdf_incapacidad: archivo PDF (si transcripción=true)
    """
    
    if transcripcion and not pdf_incapacidad:
        raise HTTPException(
            status_code=422,
            detail="Para transcripciones se requiere adjuntar pdf_incapacidad.",
        )

    job_id = str(uuid.uuid4())

    # Guardar archivos
    pdf_path: Optional[str] = None
    if pdf_incapacidad and pdf_incapacidad.filename:
        p = UPLOADS_DIR / f"{job_id}_compensar_incap.pdf"
        p.write_bytes(await pdf_incapacidad.read())
        pdf_path = str(p)

    soportes_paths: list[str] = []
    if soportes_adicionales:
        for i, soporte in enumerate(soportes_adicionales):
            if soporte and soporte.filename:
                sp = UPLOADS_DIR / f"{job_id}_compensar_soporte_{i}.pdf"
                sp.write_bytes(await soporte.read())
                soportes_paths.append(str(sp))

    # Crear datos para el bot (Compensar usa un formato simplificado)
    datos = DatosRadicacion(
        credenciales=CredencialesEmpleador(
            tipo_documento="A",  # NIT por defecto para Compensar
            numero_documento=numero_documento_empleador,
            clave=clave_empleador,
        ),
        documento_trabajador=cedula_trabajador,
        fecha_inicio_incapacidad=fecha_inicio_incapacidad,
        prefijo_incapacidad="0",
        numero_incapacidad=numero_incapacidad,
        transcripcion=transcripcion,
        pdf_incapacidad=pdf_path,
        soportes_adicionales=soportes_paths if soportes_paths else None,
    )

    radicaciones[job_id] = {
        "job_id": job_id,
        "eps": "compensar",
        "status": "procesando",
        "cedula_trabajador": cedula_trabajador,
        "numero_incapacidad": numero_incapacidad,
        "transcripcion": transcripcion,
    }
    
    background_tasks.add_task(_ejecutar_radicacion_compensar, job_id, datos)

    return {"job_id": job_id, "status": "procesando", "eps": "compensar"}


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


async def _ejecutar_radicacion_compensar(job_id: str, datos: DatosRadicacion) -> None:
    """Worker para radicar en Compensar (similar a SURA)."""
    try:
        resultado: ResultadoRadicacion = radicar_en_compensar(datos)
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
