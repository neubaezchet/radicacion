# Servicio de radicación (monorepo)

Repositorio **independiente** centrado en radicación por bots (Playwright) y un panel web. El backend principal solo consume esta API por HTTP.

Pasos de despliegue Railway + Vercel: [docs/DEPLOY.md](docs/DEPLOY.md).

## Por qué Vercel + Railway

- **Vercel** encaja con el **panel estático** (`apps/web`, Vite). CDN, HTTPS y despliegues simples.
- **Railway** (u otro contenedor con Docker) encaja con la **API + Playwright** (`apps/api`): procesos largos, Chromium y sistema de archivos como en tu referente.

No conviene ejecutar el bot Playwright dentro de **Vercel Functions** (límites de tiempo, entorno y coste). La combinación habitual es: **UI en Vercel, API en Railway** (puede ser otro proyecto Railway en la misma cuenta, misma red lógica, distinta URL).

## Estructura

```
radicacion/
├── README.md
├── docs/
│   └── INTEGRATION.md      # Contrato para tu backend principal
├── apps/
│   ├── api/                # FastAPI + bots → Railway (Dockerfile)
│   │   ├── Dockerfile
│   │   ├── railway.toml
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── jobs.py
│   │   └── bots/
│   │       ├── base.py     # Contrato para nuevas EPS
│   │       └── sura.py     # Implementación SURA (pega aquí tu Playwright)
│   └── web/                # Panel → Vercel (Vite)
│       ├── vercel.json
│       ├── vite.config.js
│       └── src/main.js
```

## Desarrollo local

**API** (desde `apps/api`):

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set MOCK_RADICACION=true
set CORS_ORIGINS=http://localhost:5173
python main.py
```

**Web** (desde `apps/web`, en otra terminal):

```bash
cd apps/web
npm install
npm run dev
```

`vite.config.js` hace proxy de `/health` y `/api` al `localhost:8000`, así no hace falta `VITE_RADICACION_API_URL` en local.

## Vercel (panel)

Guía detallada: [docs/DEPLOY.md](docs/DEPLOY.md).

Resumen:

1. Nuevo proyecto en Vercel → importar **el mismo repo**.
2. **Opción A (recomendada):** deja el proyecto en la **raíz del repo**; Vercel usa el `vercel.json` de la raíz para construir `apps/web`.
3. **Opción B:** **Root Directory** = `apps/web` (usa el `vercel.json` de esa carpeta).
4. Variable **obligatoria** en Vercel: `VITE_RADICACION_API_URL` = URL pública de Railway (sin `/` final). Aplica a Production y Preview.
5. En Railway, actualiza `CORS_ORIGINS` con la URL **https** de tu proyecto Vercel (ver [docs/DEPLOY.md](docs/DEPLOY.md)).

## Railway (API)

1. Nuevo proyecto → **Deploy from GitHub** (o CLI).
2. **Root Directory:** `apps/api`.
3. Dejar que use el **Dockerfile** (Playwright + Chromium).
4. Variables recomendadas:

| Variable | Descripción |
|----------|-------------|
| `CORS_ORIGINS` | Orígenes permitidos, p. ej. `https://tu-app.vercel.app` (coma si son varios). |
| `MOCK_RADICACION` | `true` solo para pruebas sin portal real. |
| `RADICACION_API_KEY` | Opcional. Si la defines, `POST /api/radicar/sura` y `GET /api/radicaciones` exigen header `X-Radicacion-Key`. `GET /api/estado/{job_id}` sigue público para poder hacer polling desde el panel sin exponer la clave en el navegador. Si necesitas la clave también en el navegador, mejor **no** uses esta variable y restringe por CORS + tu propio BFF. |

## Endpoints (igual que el referente)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/radicar/sura` | Inicia radicación (multipart) |
| GET | `/api/estado/{job_id}` | Estado del job |
| GET | `/api/radicaciones` | Lista (protegida si hay API key) |

## Añadir otra EPS

1. Crear `apps/api/bots/nueva_eps.py` implementando `BotRadicacionEPS` en `base.py`.
2. Registrar rutas en `main.py` siguiendo el patrón de SURA.
3. Extender el panel en `apps/web` si hace falta selector adicional.

## Próximo paso obligatorio en producción

Copia tu implementación real de Playwright desde el antiguo `bot_sura.py` al método `BotSura.radicar` en `apps/api/bots/sura.py` y desactiva `MOCK_RADICACION`.
