# Integración con el backend principal

Este servicio es **autónomo**: el backend principal solo necesita HTTP (multipart o JSON según evolucione la API).

## URL base

- **Producción API (Railway):** `https://<tu-proyecto-api>.up.railway.app`
- **Panel (Vercel):** `https://<tu-proyecto-web>.vercel.app`

Configura CORS en la API con el origen del panel (`CORS_ORIGINS`).

## Flujo recomendado

1. `POST /api/radicar/sura` con `multipart/form-data` (igual que en el README raíz).
2. Respuesta: `{ "job_id": "...", "status": "procesando" }`.
3. Polling: `GET /api/estado/{job_id}` hasta que `status` sea distinto de `procesando`.

## Seguridad

- No persistir claves de portal en logs ni en disco sin cifrar.
- Opcional: `RADICACION_API_KEY` en la API exige header `X-Radicacion-Key` en `POST /api/radicar/sura` y en `GET /api/radicaciones`. El panel en Vercel **no** debe incrustar esa clave (sería pública). Usa la clave solo desde el **backend principal** (llamadas servidor a servidor), o deja la variable sin definir y apóyate en **CORS** y red privada/VPN si aplica.

## Variables que el backend principal debe conocer

| Variable en el backend | Uso |
|------------------------|-----|
| `RADICACION_API_BASE_URL` | Base URL del servicio Railway |
| `RADICACION_API_KEY` | Opcional, si habilitaste autenticación |

## Ejemplo con API key (servidor a servidor)

```bash
curl -sS -X POST "$RADICACION_API_BASE_URL/api/radicar/sura" \
  -H "X-Radicacion-Key: $RADICACION_API_KEY" \
  -F nit_empleador=900123456 \
  -F clave_empleador=*** \
  -F cedula_trabajador=12345678 \
  -F numero_incapacidad=INC-2026-00001 \
  -F fecha_inicio=01/04/2026 \
  -F fecha_fin=05/04/2026 \
  -F dias_incapacidad=5 \
  -F pdf_incapacidad=@incap.pdf
```
