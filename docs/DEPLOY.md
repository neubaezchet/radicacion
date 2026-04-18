# Despliegue: Railway (API) + Vercel (panel)

## 1. Railway (ya hecho)

- **Root Directory:** `apps/api`
- URL pública anotada, por ejemplo: `https://xxxx.up.railway.app`

## 2. Vercel (panel)

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → importa el mismo repo de GitHub.
2. **Root Directory:** deja la raíz del repo (`.`) vacía o en **Root Directory** pon `.` / no cambies nada si Vercel detecta el `vercel.json` de la raíz.  
   Si prefieres solo la carpeta web: **Root Directory** = `apps/web` (entonces usa el `vercel.json` dentro de `apps/web` y no necesitas el de la raíz; con ambos no hay conflicto si eliges una u otra forma).
3. **Environment Variables** (pestaña al importar o *Settings → Environment Variables*):

| Nombre | Valor | Entorno |
|--------|--------|---------|
| `VITE_RADICACION_API_URL` | `https://TU-SERVICIO.up.railway.app` | Production, Preview, Development |

Sin barra final. Guarda y **Redeploy** si el primer build fue antes de añadir la variable (Vite “hornea” la URL en build).

4. **Deploy**. Al terminar, copia la URL del panel, por ejemplo `https://radicacion-xxx.vercel.app`.

## 3. Volver a Railway (CORS)

En el servicio de la API → **Variables**:

| Nombre | Valor |
|--------|--------|
| `CORS_ORIGINS` | `https://radicacion-xxx.vercel.app` |

Si usas varios orígenes (preview de Vercel, local): sepáralos por coma, sin espacios:

`https://radicacion-xxx.vercel.app,http://localhost:5173`

Guarda; Railway redeploya la API.

## 4. Comprobar

- Navegador: tu URL de Vercel → el indicador **api · online** debe ponerse verde.
- `https://TU-API.up.railway.app/health` → `{"status":"ok"}`

## 5. Producción del bot

- `MOCK_RADICACION` = `false` o elimínala.
- Implementación Playwright en `apps/api/bots/sura.py`.
