# Guía de Debugging - Bot SURA con Teclado Virtual Aleatorio

## 🔧 Cambios Realizados

### 1. **Detección Dinámica del Teclado Virtual** ✓
El bot ahora busca los botones por **contenido de texto** en lugar de selectores fijos:
```python
# Antes (❌ no funcionaba con teclado aleatorio):
page.locator(f'button[name="{ASCII_PIN[digito]}"]').click()

# Ahora (✓ busca dinámicamente):
botones = page.locator(f'button:has-text("{digito}")').all()
for btn in botones:
    if btn.text_content().strip() == digito:
        btn.click()
```

### 2. **Múltiples Selectores de Respaldo** ✓
Si el primer selector no encuentra el botón, intenta otros:
1. `:has-text("{digito}")` — CSS selector
2. `button[value="{digito}"]` — Atributo value
3. `button[data-value="{digito}"]` — Atributo data-value
4. `//button[contains(text(), "{digito}")]` — XPath

### 3. **Diagnóstico Automático en Caso de Error** ✓
Si falla, captura:
- 📸 **Screenshot** del teclado virtual
- 📄 **HTML completo** con atributos de cada botón
- 📹 **Video** de toda la sesión

---

## 🚀 Cómo Usar

### Ejecución Básica (Con Debugging)
```powershell
cd c:\Users\david.baeza\Documents\radicacion
python test_sura_mejorado.py
```

**Esto:**
- ✓ Abre el navegador (NO headless) para que veas lo que ocurre
- ✓ Captura video de la sesión completa
- ✓ Si falla, guarda screenshots y HTML del error
- ✓ Muestra exactamente en qué paso falló

### Archivos de Salida

| Directorio | Contenido | Ubicación |
|-----------|-----------|-----------|
| **sura_videos/** | Videos de la sesión (`.webm`) | `C:\Users\DAVID~1.BAE\AppData\Local\Temp\sura_videos\` |
| **sura_errors/** | Screenshots de errores (`.png`) | `C:\Users\DAVID~1.BAE\AppData\Local\Temp\sura_errors\` |
| **sura_debug/** | HTML del teclado (`.html`) | `C:\Users\DAVID~1.BAE\AppData\Local\Temp\sura_debug\` |
| **test_sura_mejorado.log** | Logs detallados (`.log`) | `C:\Users\DAVID~1.BAE\AppData\Local\Temp\test_sura_mejorado.log` |

---

## 📋 Cómo Interpretar los Errores

### Error: "No se encontró botón para dígito X"
**Significa:** El teclado virtual tiene una estructura diferente a la esperada.

**Solución:**
1. Abre el archivo HTML en `sura_debug/teclado_virtual_*.html`
2. Busca cómo está estructurado cada botón
3. Verifica si tiene: `value=`, `data-value=`, o solo `text`
4. Avísame la estructura exacta

### Ejemplo de HTML esperado:
```html
<!-- Formato 1: Con value -->
<button value="5">5</button>

<!-- Formato 2: Con data-value -->
<button data-value="5">5</button>

<!-- Formato 3: Solo texto -->
<button>5</button>

<!-- Formato 4: Con clases y atributos -->
<button class="numpad-btn" data-num="5">5</button>
```

---

## 🎥 Interpretando Videos/Screenshots

### Qué Buscar:
1. **¿Aparecen asteriscos?** → El PIN se está digitando correctamente
2. **¿El botón responde?** → Pero puede estar en lugar inesperado
3. **¿Dónde se detiene?** → Ese es el paso donde falla

### Pasos del Bot:
```
PASO 1: Abrir portal SURA ✓
PASO 2: Seleccionar tipo documento (C/A) ✓
PASO 3: Digitar número del empleador ✓
PASO 4: Digitar PIN con teclado virtual ← Falla aquí
PASO 5: Iniciar sesión
PASO 6: Navegar a Empleadores
...
```

---

## 🔄 Próximas Pruebas

### Si Falla en PASO 4:
```bash
# 1. Ejecuta la prueba
python test_sura_mejorado.py

# 2. Si falla, comparte conmigo:
#    - El archivo teclado_virtual_*.html
#    - El screenshot teclado_virtual_*.png
#    - El log test_sura_mejorado.log

# 3. Yo analizaré la estructura y ajustaré los selectores
```

### Si Pasa PASO 4 pero Falla Después:
Significa que el teclado virtual está OK, pero hay otro problema:
- Credenciales inválidas
- Cambios en la estructura HTML del portal SURA
- Cambios en los nombres de botones/formularios

---

## ✅ Cuando Funcione Correctamente

Deberías ver en el log:
```
✓ Botón encontrado para dígito 2
✓ Botón encontrado para dígito 0
✓ Botón encontrado para dígito 2
✓ Botón encontrado para dígito 5
Confirmando PIN con botón ✔
✓ Botón encontrado para dígito...
[PASO 5 OK] Portal cargado
[PASO 6 OK] Navegando...
[PASO 9 OK] Formulario completado
[PASO 10 OK] Radicación exitosa
```

---

## 📞 Información para Reportar Errores

Cuando reportes un error, incluye:

1. **Tipo de error:**
   - Falla en PASO 4 (PIN)
   - Falla en PASO 5 (Login)
   - Falla en PASO 9 (Formulario)

2. **Archivos de debugging:**
   - teclado_virtual_*.html (si es PASO 4)
   - error_*.png (screenshot)
   - test_sura_mejorado.log (log completo)

3. **Tu información:**
   - ¿Las credenciales funcionan manualmente en SURA?
   - ¿Hay cambios recientes en SURA?
   - ¿La contraseña tiene caracteres especiales?

---

## 🛠️ Cambios en Código

Archivo: `apps/api/bots/sura.py`

**Función nueva:**
```python
def _debug_teclado_virtual(page):
    """Captura HTML y screenshots del teclado virtual para debugging."""
```

**Sección mejorada (PASO 4):**
```python
# Digitar PIN usando teclado virtual aleatorio
# Busca dinámicamente cada botón por contenido
# Si falla, captura debug automáticamente
```

---

**¡Listo!** Ahora ejecuta la prueba y comparte los resultados. 🚀
