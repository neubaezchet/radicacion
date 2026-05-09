# 🎬 Guía: Grabación del Bot de Compensar

## Propósito

Capturar el flujo de radicación de incapacidades en el portal de Compensar usando Playwright, generando código automático que se pueda reutilizar en la automatización del bot.

## URL del Portal

```
https://seguridad.compensar.com/sign-in?serviceProviderName=WSFEDSALUD-SP&response_type=code%20token&response_mode=form_post&_csrf=e42792d3-0389-46ad-ab2b-47b8602bcdeb&protocol=OIDC
```

## Procedimiento: 2 Métodos

### Método 1: Usando Playwright Codegen (RECOMENDADO)

Genera código Python automáticamente mientras interactúas con el navegador.

```bash
# Desde radicacion/apps/api/bots/
python record_compensar_codegen.py
```

**Qué sucede:**
1. Se abre un navegador con el Inspector de Playwright visible
2. El Inspector graba CADA acción que hagas (clicks, writes, waits)
3. A la derecha verás el código Python generado en tiempo real
4. Cada paso que hagas genera automáticamente código

**Pasos para Grabar:**

1. **Login** (cuando se abra el navegador):
   - Ingresa el **Usuario** (NIT de la empresa o documento)
   - Ingresa la **Contraseña**
   - Haz clic en **"Ingresar"** o **"Sign In"**
   - Espera a que cargue el portal

2. **Navega a Radicación**:
   - Busca y haz clic en la opción de "Radicación"
   - O la opción de "Incapacidades"
   - O "Registrar incapacidad"
   - Espera a que cargue el formulario

3. **Llena el Formulario**:
   - **Cédula del Trabajador**: Ingresa la cédula
   - **Fecha de Inicio**: Ingresa la fecha (formato DD/MM/YYYY o DD MM YYYY)
   - **Número de Incapacidad**: Ingresa el número

4. **Envía el Formulario**:
   - Busca el botón **"Enviar"**, **"Radicar"** o **"Submit"**
   - Haz clic

5. **Nota el Resultado**:
   - Busca en la página el **número de radicado** o **confirmación**
   - Toma nota de dónde aparece (elemento HTML)

6. **Cierra el Navegador**:
   - El código se guardará automáticamente

### Método 2: Grabación Manual Paso a Paso

```bash
python record_compensar.py
```

**Menos automático, pero útil si Codegen tiene problemas.**

## Después de Grabar

### 1. Ubicación del Código Generado

```
radicacion/apps/api/bots/compensar_recorded.py
```

### 2. Análisis del Código Generado

```python
# El archivo contendrá algo como:
async def test_compensar(page):
    await page.goto("https://...")
    await page.fill("input[name='usuario']", "12345678")
    await page.fill("input[name='clave']", "miPassword")
    await page.click("button:has-text('Ingresar')")
    await page.wait_for_navigation()
    # ... más código
```

### 3. Extrae los Selectores Importantes

De tu código grabado, EXTRAE los selectores clave:

| Elemento | Selector | Ejemplo |
|----------|----------|---------|
| Input Usuario | `input[name='usuario']` o `input[id='user']` | - |
| Input Contraseña | `input[name='clave']` o `input[type='password']` | - |
| Botón Login | `button:has-text('Ingresar')` | - |
| Link Radicación | `a:has-text('Radicación')` | - |
| Input Cédula | `input[name='cedula']` | - |
| Input Fecha | `input[name='fecha']` | - |
| Input Incapacidad | `input[name='incapacidad']` | - |
| Botón Enviar | `button:has-text('Enviar')` | - |
| Número Radicado | `text=Radicado:` o `span.radicado` | - |

### 4. Documenta en compensar.py

Abre [compensar.py](compensar.py) y actualiza los selectores en la función `radicar_en_compensar()`:

```python
def radicar_en_compensar(datos: 'DatosRadicacion') -> 'ResultadoRadicacion':
    # 1. Actualiza estos selectores con los que grabaste:
    
    page.fill("input[name='usuario']", datos.credenciales.numero_documento)
    page.fill("input[name='clave']", datos.credenciales.clave)
    
    # 2. Espera a que cargue después del login
    page.wait_for_selector("text=Radicación")
    
    # 3. Llena el formulario de radicación
    page.fill("input[name='cedula']", datos.documento_trabajador)
    
    # ... etc
```

### 5. Prueba el Bot

```bash
# Dentro del entorno de radicacion

# Prueba local:
python -c "
from apps.api.bots import radicar_en_compensar, DatosRadicacion, CredencialesEmpleador

datos = DatosRadicacion(
    credenciales=CredencialesEmpleador(
        tipo_documento='A',
        numero_documento='860007234',  # Tu NIT de prueba
        clave='tu_clave_aqui',
    ),
    documento_trabajador='12345678',
    fecha_inicio_incapacidad='18 04 2026',
    prefijo_incapacidad='0',
    numero_incapacidad='12345',
)

resultado = radicar_en_compensar(datos)
print(f'Exitoso: {resultado.exitoso}')
print(f'Radicado: {resultado.numero_radicado}')
print(f'Screenshots: {resultado.pdf_path}')
"
```

## Problemas Comunes

### "El navegador se abre pero no pasa nada"
- Espera 3-5 segundos: el portal puede cargar lentamente
- Verifica que tienes conexión a internet
- Prueba sin headless (el navegador debe ser visible)

### "No encuentra el elemento"
- El selector podría haber cambiado
- Prueba alternativas:
  - `input[name='usuario']`
  - `input[id='usuario']`
  - `input[placeholder*='Usuario']`
  - `.form-control.usuario`

### "Timeout: el elemento nunca apareció"
- Aumenta el timeout: `page.set_default_timeout(60000)` (60 segundos)
- Verifica que hiciste clic en el botón correcto
- Busca un campo de validación o error que bloqueó el flujo

### "Falla el login"
- Verifica credenciales: ¿son correctas?
- ¿El portal requiere 2FA? Descártenlo por ahora
- ¿Hay un CAPTCHA? Los bots no pueden resolver CAPTCHAs
- Prueba manualmente primero en el navegador

## Estructura del Flujo Esperado

```
┌─────────────────────────────────────┐
│ Inicio: Login en Compensar          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Fill Usuario + Contraseña           │
│ Click "Ingresar"                    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Esperar a que cargue el portal      │
│ (wait for navigation)               │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Buscar link/botón "Radicación"      │
│ Click para ir al formulario         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Llenar Formulario:                  │
│ - Cédula trabajador                 │
│ - Fecha inicio                      │
│ - Número incapacidad                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Click "Enviar" / "Radicar"          │
│ Esperar respuesta del servidor      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Extraer Número de Radicado          │
│ Capturar pantalla como comprobante  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Retornar ResultadoRadicacion        │
│ (exitoso=True, numero_radicado)     │
└─────────────────────────────────────┘
```

## Archivo de Salida

**Ubicación:** `radicacion/apps/api/bots/compensar_recorded.py`

**Contendrá:** El código Python que Playwright genere

**Uso:** Copia los fragmentos útiles a `compensar.py` y adapta según necesites

## Próximo Paso

Después de grabar y documentar los selectores:

1. ✅ Ejecuta la grabación
2. ✅ Documenta los selectores clave en una tabla
3. ✅ Actualiza compensar.py con los selectores reales
4. ✅ Prueba el bot localmente
5. ✅ Ajusta timeouts y waits según sea necesario
6. ✅ Integra con la API (endpoint POST /api/radicar/compensar)

---

**¡Listo! Ahora puedes comenzar a grabar. Ejecuta:**

```bash
cd radicacion/apps/api/bots
python record_compensar_codegen.py
```
