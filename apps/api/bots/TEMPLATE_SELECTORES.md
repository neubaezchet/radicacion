# 📋 Template: Selectores Documentados - Compensar

**Llenar después de ejecutar la grabación:**

```bash
python record_compensar_codegen.py
```

## Login - Portal de Seguridad

| Elemento | Selector HTML | Atributos | Tipo |
|----------|----------------|-----------|------|
| Input Usuario (NIT) | | `name`, `id`, `class` | `<input>` |
| Input Contraseña | | `name`, `id`, `class` | `<input>` |
| Botón Ingresar | | `text`, `id`, `class` | `<button>` |
| Formulario Login | | `id`, `class`, `form` | `<form>` |

**Ejemplo completado:**

```
Input Usuario: input[name='userName']
Input Contraseña: input[name='password']
Botón Ingresar: button:has-text('Ingresar')
```

## Radicación - Formulario

| Elemento | Selector HTML | Atributos | Nota |
|----------|----------------|-----------|------|
| Link/Botón Radicación | | `text`, `href`, `class` | Después del login |
| Input Cédula Trabajador | | `name`, `id`, `placeholder` | DD formato |
| Input Fecha Inicio | | `name`, `id`, `placeholder` | DD/MM/YYYY o similar |
| Input Número Incapacidad | | `name`, `id`, `placeholder` | Digits only |
| Input Primer Número (Prefijo) | | `name`, `id` | Si existe (ej: 0) |
| Botón Enviar/Radicar | | `text`, `id`, `class` | Importante |
| Elemento Confirmación | | `id`, `class`, `text` | Dónde sale el radicado |

**Ejemplo completado:**

```
Link Radicación: a[href*='incapacidades']
Input Cédula: input#cedula_trabajador
Input Fecha: input[name='fecha_inicio']
Input Incapacidad: input#numero_incapacidad
Botón Enviar: button.btn-primary:has-text('Radicar')
```

## Respuesta / Confirmación

| Elemento | Selector HTML | Patrón de Búsqueda | Captura |
|----------|----------------|-------------------|---------|
| Número Radicado | | `text=Radicado:`, `data-id`, clase especial | CRÍTICO |
| Mensaje Éxito | | `text=Se radicó`, `alert-success`, SVG | Validación |
| PDF/Descarga | | `href=*.pdf`, `download` | Para comprobante |
| Referencia Tramite | | `text=Referencia:`, `data-ref` | Alternativo a radicado |

**Ejemplo completado:**

```
Número Radicado: span.radicado_number o text=/Radicado: (\d+)/
Mensaje Éxito: div.alert-success
Referencia: strong#referencia
```

## Errores Comunes

| Escenario | Selector | Acción |
|-----------|----------|--------|
| Campo requerido no lleno | `div.error` o `span.invalid` | Reintentarwarning |
| Login incorrecto | `div[role='alert']` | Retornar error |
| Timeout en radicación | `body:visible-timeout` | Aumentar espera |
| CAPTCHA presente | `iframe[src*='captcha']` | Saltar por ahora |

## Pasos clave del flujo

### 1. Navigate & Wait
```python
page.goto("https://seguridad.compensar.com/sign-in...")
page.wait_for_selector("[SELECTOR_LOGIN_FORM]", timeout=10000)
```

### 2. Fill & Submit Login
```python
page.fill("[SELECTOR_INPUT_USUARIO]", numero_documento)
page.fill("[SELECTOR_INPUT_CLAVE]", clave)
page.click("[SELECTOR_BOTON_LOGIN]")
page.wait_for_navigation()
```

### 3. Navigate to Radicación
```python
page.click("[SELECTOR_LINK_RADICACION]")
page.wait_for_selector("[SELECTOR_FORM_RADICACION]", timeout=10000)
```

### 4. Fill Form
```python
page.fill("[SELECTOR_CEDULA]", documento_trabajador)
page.fill("[SELECTOR_FECHA]", fecha_inicio_incapacidad)
page.fill("[SELECTOR_INCAPACIDAD]", numero_incapacidad)
```

### 5. Submit & Extract Result
```python
page.click("[SELECTOR_BOTON_ENVIAR]")
page.wait_for_selector("[SELECTOR_CONFIRMACION]", timeout=15000)

numero_radicado = page.text_content("[SELECTOR_NUMERO_RADICADO]")
```

## Notas de Grabación

- **Navegador**: ¿Chrome, Firefox, Edge?
- **Portal funciona en headless?**: Sí / No / Parcial
- **Validaciones**: ¿2FA?, ¿CAPTCHA?, ¿Campos opcionales?
- **Formatos esperados**: DD/MM/YYYY o DD MM YYYY?
- **Timeouts observados**: ~[segundos]
- **Cambios entre navegadores**: Sí / No

---

## 📝 Instrucciones de Uso

1. **Ejecuta la grabación**: `python record_compensar_codegen.py`
2. **Rellena esta tabla con los selectores**
3. **Copia los selectores a `compensar.py`**
4. **Prueba localmente**
5. **Ajusta timeouts/validaciones**

---

**Archivo**: `radicacion/apps/api/bots/compensar_selectores.md`

Actualizar después de: `record_compensar_codegen.py`
