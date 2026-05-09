# 🎬 Compensar Bot: Guía de Implementación Completa

## 📊 Flujo Visual del Proceso

```
FASE 1: GRABACIÓN
═══════════════════════════════════════════════════════════════
   ↓
   Ejecutas: python record_compensar_codegen.py
   ↓
   ┌─────────────────────────────────────────────────────────┐
   │ Se abre: Navegador + Inspector de Playwright           │
   │                                                          │
   │ Inspector GRABA automáticamente cada acción:           │
   │  - Clicks                                               │
   │  - Inputs (text)                                        │
   │  - Navigation                                           │
   │  - Waits                                                │
   └─────────────────────────────────────────────────────────┘
   ↓
   1️⃣ Login en Compensar (manual)
   2️⃣ Navega a Radicación (manual)
   3️⃣ Llena formulario (manual)
   4️⃣ Envía (manual)
   ↓
   Se genera: compensar_recorded.py (código automático)
   ↓


FASE 2: DOCUMENTACIÓN
═══════════════════════════════════════════════════════════════
   ↓
   Abres: compensar_recorded.py
   ↓
   Extraes los selectores clave usando TEMPLATE_SELECTORES.md:
   
   ✅ input[name='usuario']         ← Input NIT
   ✅ input[name='clave']            ← Input Contraseña
   ✅ button:has-text('Ingresar')    ← Botón Login
   ✅ a:has-text('Radicación')       ← Link Radicación
   ✅ input[name='cedula']           ← Input Cédula
   ✅ input[name='fecha']            ← Input Fecha
   ✅ input[name='incapacidad']      ← Input Incapacidad
   ✅ button:has-text('Enviar')      ← Botón Enviar
   ✅ span.radicado_number           ← Número Radicado
   ↓
   Documentas en: compensar_selectores.md
   ↓


FASE 3: ACTUALIZACIÓN DEL BOT
═══════════════════════════════════════════════════════════════
   ↓
   Actualizas: radicacion/apps/api/bots/compensar.py
   
   Reemplazas selectores hardcodeados con los reales:
   
   ANTES:
   page.fill("input[placeholder*='usuario']", numero_documento)
   
   DESPUÉS:
   page.fill("input[name='usuario']", numero_documento)
   ↓
   Pruebas: python test_compensar_manual.py
   ↓
   El bot abre el navegador en modo VISIBLE y:
   - Hace login
   - Navega a radicación
   - Llena el formulario
   - Envía
   - Extrae número radicado
   ↓
   ¿Funciona? → Sí ✅ → Ve a Fase 4
             → No ❌ → Revisa selectores, ajusta, reintenta
   ↓


FASE 4: INTEGRACIÓN EN API
═══════════════════════════════════════════════════════════════
   ↓
   Ya está lista:
   - POST /api/radicar/compensar (endpoint)
   - radicar_en_compensar (función)
   - Admin portal (UI para configurar bots)
   ↓
   Admin configura bot para empresa:
   POST /admin/empresas/COMPENSAR_TEST/bots
   {
     "bot_nombre": "compensar",
     "bot_tipo_medio": "portal",
     "estado": "activo",
     "credenciales": {
       "numero_documento": "860007234",
       "clave": "****"
     }
   }
   ↓
   Radicación consulta credenciales en vivo:
   GET /api/credenciales/empresa/COMPENSAR_TEST/bot/compensar
   ↓
   Bot recibe credenciales y radica
   ↓
   Se guarda resultado en BD:
   {
     "job_id": "uuid...",
     "eps": "compensar",
     "status": "exitoso",
     "numero_radicado": "12345678",
     "mensaje": "Incapacidad radicada exitosamente"
   }
   ↓
```

## 📁 Archivos Creados/Modificados

### Nuevos Archivos:

```
radicacion/apps/api/bots/
├── record_compensar.py              ← Grabador interactivo básico
├── record_compensar_codegen.py      ← Grabador con Playwright codegen ⭐ USAR ESTE
├── test_compensar_manual.py         ← Testing interactivo para debugging
├── compensar_recorded.py            ← SE GENERA después de grabar
├── compensar_selectores.md          ← SE LLENA después de grabar
├── GRABAR_COMPENSAR.md              ← Guía paso a paso
├── TEMPLATE_SELECTORES.md           ← Template para documentar
└── compensar.py                     ← Bot (ya existe, se actualiza)

Documentos:
├── INTEGRACION_BOTS_ADMIN_RADICACION.md ← Actualizado con Compensar
└── (root) COMPENSAR_FLUJO_VISUAL.md     ← Este archivo
```

### Archivos Modificados:

```
radicacion/apps/api/
├── main.py                          ← Nuevo endpoint POST /api/radicar/compensar
│                                       Nueva función worker
│                                       Imports actualizados
└── bots/__init__.py                 ← radicar_en_compensar exportado

admin-neurobaeza/
├── src/pages/BotConfiguration.jsx   ← Ya incluye Compensar en BOTS_CATÁLOGO
├── src/components/Layout.jsx        ← Ya incluye link a /bots
└── src/api.js                       ← Ya incluye métodos para bot CRUD
```

## 🔄 Flujo de Uso (Después de Todo Listo)

### Admin configura bot en el portal:

```
1. Abre admin-neurobaeza
2. Va a "Configuración de Bots"
3. Selecciona una empresa
4. Haz clic en "Asignar Bot"
5. Selecciona "compensar_eps"
6. Ingresa NIT: 860007234
7. Ingresa Contraseña: ****
8. Cambia estado a "activo"
9. Guarda
```

### Sistema radica automáticamente:

```
Backend recibe request → 
  Consulta credenciales del bot activo →
    /radicacion/api/credenciales/empresa/EMPRESA/bot/compensar →
      radicacion API consulta BD del backend →
        Devuelve credenciales en vivo →
          Bot recibe credenciales →
            1. Abre portal Compensar
            2. Hace login con credenciales
            3. Navega a radicación
            4. Llena datos del trabajador
            5. Envía
            6. Extrae número radicado
            7. Retorna resultado exitoso
```

## ✅ Checklist de Implementación

### FASE 1: Grabación ⏳

- [ ] Ejecutar: `python record_compensar_codegen.py`
- [ ] Hacer login en Compensar (manual)
- [ ] Navegar a Radicación (manual)
- [ ] Llenar formulario de prueba (manual)
- [ ] Enviar formulario (manual)
- [ ] Verificar número radicado aparece en portal (manual)
- [ ] Cerrar navegador → Se genera compensar_recorded.py

### FASE 2: Documentación ⏳

- [ ] Abrir: compensar_recorded.py
- [ ] Extraer selectores clave
- [ ] Usar TEMPLATE_SELECTORES.md como referencia
- [ ] Documentar en: compensar_selectores.md

### FASE 3: Actualización del Bot ⏳

- [ ] Actualizar compensar.py con selectores reales
- [ ] Ejecutar: `python test_compensar_manual.py`
- [ ] Ingresar credenciales de prueba
- [ ] Verificar que el bot radica correctamente
- [ ] Ajustar timeouts si es necesario
- [ ] Probar múltiples veces

### FASE 4: Integración ✅

- [x] Endpoint POST /api/radicar/compensar ← LISTO
- [x] Worker _ejecutar_radicacion_compensar ← LISTO
- [x] Imports en main.py ← LISTO
- [x] Admin UI con Compensar ← LISTO
- [x] Radicacion API endpoints ← LISTO

## 🚀 Próximos Pasos

### Inmediatos (próxima sesión):

1. **Ejecutar grabación interactiva**
   ```bash
   cd radicacion/apps/api/bots
   python record_compensar_codegen.py
   ```

2. **Documentar selectores encontrados**
   - Usar TEMPLATE_SELECTORES.md
   - Guardar en compensar_selectores.md

3. **Actualizar compensar.py**
   - Copiar selectores del código grabado
   - Reemplazar en función radicar_en_compensar()

4. **Prueba interactiva**
   ```bash
   python test_compensar_manual.py
   ```

### Posteriores (cuando Compensar esté listo):

- [ ] Crear bot para Famisanar (email)
- [ ] Crear bot para Nueva EPS (portal)
- [ ] Crear bot para ARL SURA (portal)
- [ ] Testing en staging
- [ ] Deployment a producción

## 📞 Ayuda Rápida

### Si record_compensar_codegen.py no funciona:

```bash
# Verifica que Playwright esté instalado
python -m playwright --version

# Si no está:
pip install playwright
python -m playwright install chromium
```

### Si el bot no encuentra selectores:

1. Abre compensar_recorded.py
2. Compara con compensar.py
3. Busca patrones similares
4. Actualiza los selectores

### Si hay timeout en ciertos pasos:

1. Aumenta el timeout: `page.set_default_timeout(60000)`
2. Agrega waits explícitos: `page.wait_for_selector(..., timeout=10000)`
3. Verifica que la navegación es correcta

---

**Estado actual: 🚧 LISTO PARA GRABAR**

**Próximo paso:** Ejecutar `python record_compensar_codegen.py` y documentar selectores.
