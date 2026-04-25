# Instructivo Técnico — Bot Radicación SURA (Playwright)

> **Propósito:** Especificación paso a paso de cada acción que el bot debe ejecutar en el portal EPS SURA para radicar incapacidades. Sirve como guía para implementar o depurar `apps/api/bots/sura.py`.

---

## 1. Datos de entrada requeridos

El backend principal envía estos campos en cada request:

| Campo | Tipo | Descripción |
|---|---|---|
| `tipo_documento_empleador` | `str` | Valor exacto del dropdown (ver sección 3.3) |
| `numero_documento_empleador` | `str` | NIT, cédula u otro número según tipo |
| `clave_empleador` | `str` | Clave del portal (se ingresa en teclado virtual) |
| `prefijo_incapacidad` | `str` | Primer recuadro del número (ej: `"0"`) |
| `numero_incapacidad` | `str` | Segundo recuadro (ej: `"22393939"`) |
| `cedula_trabajador` | `str` | Solo para flujo TRANSCRIPCIÓN |
| `tipo_documento_trabajador` | `str` | Solo para flujo TRANSCRIPCIÓN |
| `pdf_incapacidad` | `Path` | PDF adjunto (solo TRANSCRIPCIÓN) |
| `pdf_historia_clinica` | `Path \| None` | Opcional (solo TRANSCRIPCIÓN) |

> **Importante:** El servicio NUNCA almacena credenciales. Se reciben por request, se usan en la sesión del bot y se descartan.

---

## 2. URL del portal

```
https://www.epssuraycompanias.com.co/eps/empleador
```

> Si la URL cambia, actualizar `SURA_PORTAL_URL` en `config.py`.

---

## 3. Flujo completo paso a paso

### PASO 1 — Abrir el portal

```python
await page.goto(SURA_PORTAL_URL, wait_until="networkidle")
```

- Esperar que cargue completamente.
- Si aparece un modal de cookies o aviso legal → cerrarlo haciendo clic en el botón de aceptar/cerrar.

---

### PASO 2 — Seleccionar rol "Empleador"

El portal tiene una barra de navegación superior. Buscar el enlace o botón que diga **"Empleadores"** o **"Empleador"** y hacer clic.

```python
await page.click('a:has-text("Empleadores"), button:has-text("Empleador")')
await page.wait_for_load_state("networkidle")
```

---

### PASO 3 — Formulario de login

El formulario de inicio de sesión tiene tres elementos:

#### 3.1 Tipo de documento (dropdown)

Selector probable: `select[name*="tipo"], select[id*="tipo"], .select-tipo-doc`

```python
await page.select_option(
    'select[name*="tipoDoc"], select[id*="tipoDoc"]',
    label=datos.tipo_documento_empleador  # ej: "NIT", "CEDULA"
)
```

Si es un dropdown personalizado (no `<select>` nativo):

```python
await page.click('.dropdown-tipo-doc')  # abrir
await page.click(f'li:has-text("{datos.tipo_documento_empleador}")')  # elegir
```

**Valores exactos del dropdown** (copiar tal como aparece en el portal):

```
CEDULA
CEDULA EXTRANJERIA
DIPLOMATICO
DOC.IDENT. DE EXTRANJEROS
IDENT. FISCAL PARA EXT.
NIT
NIT PERSONAS NATURALES
NUIP
PASAPORTE
REGISTRO CIVIL
TARJ.IDENTIDAD
CERTIFICADO NACIDO VIVO
PASAPORTE ONU
PERMISO ESPECIAL PERMANENCIA
SALVOCONDUCTO DE PERMANENCIA
PERMISO ESPECIAL FORMACN PEPFF
PERMISO POR PROTECCION TEMPORL
```

#### 3.2 Número de documento

```python
await page.fill('input[name*="numero"], input[id*="numero"]', datos.numero_documento_empleador)
```

#### 3.3 Clave — Teclado virtual (crítico)

> ⚠️ El portal presenta un **teclado virtual con números en posición aleatoria**. Los dígitos cambian de posición en cada carga. NO se puede usar `fill()`. Se deben localizar los botones por su texto y hacer clic sobre cada dígito de la clave.

**Estrategia:**

```python
async def ingresar_clave_virtual(page, clave: str):
    """
    Hace clic en cada dígito de `clave` usando el teclado virtual del portal.
    Los botones tienen el número como texto visible.
    """
    for digito in clave:
        # Buscar el botón cuyo texto sea exactamente este dígito
        btn = page.locator(
            f'button:has-text("{digito}"), '
            f'td:has-text("{digito}"), '
            f'span.key:has-text("{digito}"), '
            f'div.tecla:has-text("{digito}")'
        ).first
        await btn.click()
        await page.wait_for_timeout(150)  # pausa entre dígitos
```

> **Nota de inspección:** Antes de implementar en producción, inspeccionar el DOM del teclado virtual para identificar el selector exacto de cada tecla. El patrón más común en portales bancarios colombianos es `<td>` o `<button>` dentro de una tabla `.teclado` o `#virtualKeyboard`.

---

### PASO 4 — Iniciar sesión

```python
await page.click('button[type="submit"], input[type="submit"], button:has-text("Ingresar")')
await page.wait_for_load_state("networkidle")
```

Verificar que el login fue exitoso buscando el menú de empleador:

```python
if not await page.locator('text=Empleadores, text=Empresas').count():
    raise Exception("Login fallido: credenciales incorrectas o portal no disponible")
```

---

### PASO 5 — Navegar a Radicar Incapacidades

```python
# Hover sobre "Empleadores" para desplegar el menú
await page.hover('nav a:has-text("Empleadores"), .menu a:has-text("Empleadores")')
await page.wait_for_timeout(300)

# Clic en "Empresas"
await page.click('a:has-text("Empresas")')
await page.wait_for_load_state("networkidle")

# Clic en "Radicar incapacidades"
await page.click('a:has-text("Radicar incapacidades"), button:has-text("Radicar incapacidades")')
await page.wait_for_load_state("networkidle")
```

---

### PASO 6 — Ingresar número de incapacidad

El campo está dividido en **DOS recuadros**:

| Recuadro | Contenido | Ejemplo |
|---|---|---|
| Primero (pequeño) | Prefijo / primer dígito | `0` |
| Segundo (largo) | Número restante | `22393939` |

```python
inputs = page.locator('input[type="text"]').all()
# o selectores más específicos una vez inspeccionado el DOM:
await page.fill('#prefijo_incapacidad, input:nth-of-type(1)', datos.prefijo_incapacidad)
await page.fill('#numero_incapacidad, input:nth-of-type(2)', datos.numero_incapacidad)
```

---

### PASO 7 — Radicar

```python
await page.click('button:has-text("Radicar"), input[value="Radicar"]')
```

---

### PASO 8 — Confirmar popup

El portal muestra un recuadro de confirmación. Aceptar:

```python
# Esperar el dialog o modal
try:
    # Si es un alert nativo del navegador:
    page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
except:
    pass

# Si es un modal HTML:
await page.wait_for_selector('.modal-confirm, .swal2-confirm, button:has-text("Aceptar")', timeout=5000)
await page.click('.modal-confirm button, .swal2-confirm, button:has-text("Aceptar")')
```

---

### PASO 9 — Capturar número de radicado

```python
await page.wait_for_selector('.mensaje-exito, .radicado, text=radicó correctamente', timeout=10000)

# Extraer el número de radicado del texto de confirmación
mensaje = await page.locator('.mensaje-exito, .alert-success, .resultado').text_content()
# El mensaje suele ser: "Se radicó correctamente. Número radicado: XXXXX"
import re
match = re.search(r'[Nn]úmero\s+[Rr]adicado[:\s]+(\w+)', mensaje)
numero_radicado = match.group(1) if match else "RADICADO_SIN_NUMERO"
```

---

## 4. Flujo TRANSCRIPCIÓN (incapacidad externa)

Cuando la incapacidad NO fue emitida directamente por SURA, el portal tiene un flujo adicional de "Transcribir incapacidad". En este caso:

- Después del Paso 5, buscar la opción **"Transcribir incapacidad"** o **"Radicar transcripción"**.
- El formulario pide datos adicionales: médico tratante, diagnóstico CIE-10, fechas, etc.
- Se deben adjuntar los PDFs.

> **Pendiente:** Compartir capturas del formulario de transcripción para especificar los campos exactos. Esta sección se completará con esa información.

---

## 5. Manejo de errores

| Situación | Acción del bot |
|---|---|
| Login fallido | `ResultadoRadicacion(exitoso=False, mensaje="Credenciales inválidas")` |
| Timeout en portal | Retry 1 vez, luego error |
| Popup de error del portal | Capturar texto del popup y retornarlo en `mensaje` |
| Incapacidad ya radicada | Capturar mensaje y retornar con `exitoso=True` si el portal lo indica así |
| CAPTCHA | Reportar como error — requiere intervención manual |

---

## 6. Configuración recomendada de Playwright

```python
browser = await playwright.chromium.launch(
    headless=headless,
    args=[
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",  # evitar detección de bot
    ]
)
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    viewport={"width": 1280, "height": 720},
    locale="es-CO",
    timezone_id="America/Bogota",
)
page = await context.new_page()
```

---

## 7. Variables de entorno requeridas

```env
SURA_PORTAL_URL=https://www.epssuraycompanias.com.co/eps/empleador
MOCK_RADICACION=false
CORS_ORIGINS=https://tu-panel.vercel.app
RADICACION_API_KEY=clave-secreta-para-backend-principal
```

---

## 8. Arquitectura multi-tenant

El servicio atiende N empresas sin almacenar credenciales:

```
Empresa A (backend) ─── POST /api/radicar/sura  {nit_A, clave_A, ...} ──▶ Bot abre sesión como A
Empresa B (backend) ─── POST /api/radicar/sura  {nit_B, clave_B, ...} ──▶ Bot abre sesión como B
Empresa C (backend) ─── POST /api/radicar/sura  {nit_C, clave_C, ...} ──▶ Bot abre sesión como C
```

Cada job corre en su propio `BrowserContext` aislado. Las credenciales solo viven en memoria durante la ejecución del bot y nunca se persisten.
