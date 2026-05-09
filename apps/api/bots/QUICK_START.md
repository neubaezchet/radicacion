# ⚡ Quick Start: Comandos Listos para Copiar

## 🎬 PASO 1: Grabar el Flujo

```bash
# 1. Entra al directorio
cd c:\Users\david.baeza\Documents\radicacion\apps\api\bots

# 2. Ejecuta el grabador
python record_compensar_codegen.py

# 3. En el navegador que se abre:
#    - Login con credenciales
#    - Navega a Radicación
#    - Llena formulario
#    - Envía
#    - Cierra navegador
```

**Resultado:** Se genera `compensar_recorded.py`

---

## 📋 PASO 2: Documentar Selectores

```bash
# 1. Abre el archivo generado
code compensar_recorded.py

# 2. Copia los selectores importantes a este template:
#    ✅ input[name='usuario']
#    ✅ input[name='clave']
#    ✅ button:has-text('Ingresar')
#    ... etc

# 3. Documenta en:
code compensar_selectores.md

# 4. O usa el template:
code TEMPLATE_SELECTORES.md
```

---

## 🔧 PASO 3: Actualizar el Bot

### En compensar.py, reemplaza los selectores:

**Sección 1 - LOGIN:**
```python
# ANTES:
page.fill("input[placeholder*='usuario']", numero_documento)

# DESPUÉS (usa tu selector grabado):
page.fill("input[name='usuario']", numero_documento)
```

**Sección 2 - NAVEGAR A RADICACIÓN:**
```python
# ANTES:
page.click("a:has-text('Radicación')")

# DESPUÉS (usa tu selector):
page.click("a:has-text('Radicación')")  # O el que encontraste
```

**Sección 3 - LLENAR FORMULARIO:**
```python
# Actualiza estos con tus selectores:
page.fill("[TU_SELECTOR_CEDULA]", cedula_trabajador)
page.fill("[TU_SELECTOR_FECHA]", fecha_inicio)
page.fill("[TU_SELECTOR_INCAPACIDAD]", numero_incapacidad)
```

**Sección 4 - ENVIAR Y EXTRAER RADICADO:**
```python
page.click("[TU_SELECTOR_BOTON_ENVIAR]")
page.wait_for_selector("[TU_SELECTOR_CONFIRMACION]")
numero_radicado = page.text_content("[TU_SELECTOR_NUMERO_RADICADO]")
```

---

## 🧪 PASO 4: Probar Localmente

```bash
# Ejecuta el test interactivo
python test_compensar_manual.py

# Te pedirá:
# - NIT [860007234]: (presiona Enter para usar default)
# - Contraseña: (ingresa)
# - Cédula [12345678]: (presiona Enter)
# - Fecha [18 04 2026]: (presiona Enter)
# - Incapacidad [12345]: (presiona Enter)

# El navegador se abrirá en modo VISIBLE
# Verás paso a paso qué hace el bot
```

**¿Funciona?** → Sí ✅ → Ve al siguiente paso

**¿Falla?** → Revisa el error y ajusta selectores

---

## ✅ PASO 5: Integración en API (YA LISTO)

El endpoint ya existe. Solo necesitas que:

### Admin configure el bot en el portal:

```
1. Abre: http://localhost:3000/bots
2. Selecciona empresa
3. Haz clic "Asignar Bot"
4. Selecciona "compensar"
5. Llena credenciales
6. Guarda
```

### O via API directamente:

```bash
# Desde tu terminal, realiza un POST:
curl -X POST "http://localhost:8000/admin/empresas/EMPRESA_TEST/bots" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_nombre": "compensar",
    "bot_tipo_medio": "portal",
    "estado": "activo",
    "credenciales": {
      "numero_documento": "860007234",
      "clave": "tu_clave_aqui"
    }
  }'
```

---

## 🎯 Resumen Rápido

| Paso | Comando | Archivo | Tiempo |
|------|---------|---------|--------|
| 1️⃣ Grabar | `python record_compensar_codegen.py` | compensar_recorded.py | 10 min |
| 2️⃣ Documentar | Copiar selectores | compensar_selectores.md | 5 min |
| 3️⃣ Actualizar | Editar compensar.py | compensar.py | 10 min |
| 4️⃣ Probar | `python test_compensar_manual.py` | (test) | 5 min |
| 5️⃣ Integrar | Admin UI o API | (API ya lista) | 2 min |

**Total estimado: ~30 minutos** ⏱️

---

## 🔗 Archivos Importantes

```
Workspace:
c:\Users\david.baeza\Documents\

Bots:
radicacion\apps\api\bots\
├── record_compensar_codegen.py ← Ejecuta primero
├── test_compensar_manual.py    ← Ejecuta después
├── compensar.py                ← Actualiza luego
├── GRABAR_COMPENSAR.md         ← Lee si tienes dudas
├── TEMPLATE_SELECTORES.md      ← Referencia
└── COMPENSAR_FLUJO_VISUAL.md   ← Diagrama completo

API:
radicacion\apps\api\main.py     ← Ya incluye /api/radicar/compensar

Admin:
admin-neurobaeza\src\            ← Ya incluye Compensar
```

---

## 🆘 Troubleshooting Rápido

### "Record no genera archivo"
→ Verifica que interactuaste con el navegador antes de cerrarlo

### "Test dice 'elemento no encontrado'"
→ El selector está mal. Revisa compensar_recorded.py

### "Login funciona pero falla en radicación"
→ El selector del link/botón de Radicación es incorrecto

### "Extrae un número radicado pero está vacío"
→ El selector del número radicado no apunta al elemento correcto

### "Timeout en cierto paso"
→ Aumenta el timeout en compensar.py: `page.set_default_timeout(60000)`

---

## 📞 Soporte

**Si algo falla:**

1. Lee el error en la consola
2. Compara selectores en compensar_recorded.py vs compensar.py
3. Actualiza y prueba nuevamente
4. Si sigue fallando, ejecuta nuevamente record_compensar_codegen.py

**Si no sabes qué hacer:**

1. Ejecuta: `python test_compensar_manual.py --help`
2. Lee: GRABAR_COMPENSAR.md
3. Consulta: COMPENSAR_FLUJO_VISUAL.md

---

## ✨ ¡Listo!

Ahora solo necesitas:

```bash
cd radicacion\apps\api\bots
python record_compensar_codegen.py
```

**¡Adelante! 🚀**
