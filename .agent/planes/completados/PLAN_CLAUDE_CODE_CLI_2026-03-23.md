# Plan: Super Agente Claude Code

**Creado**: 2026-03-23
**Actualizado**: 2026-03-24
**Módulo**: ia_service + telegram_bot + ia-admin
**Estado**: ✅ Completado (archivado 2026-03-31)

---

## Visión

Claude Code corre en paralelo al `ia_service` existente como un **Super Agente** dentro del mismo bot de Telegram. No es un proveedor LLM más — es un agente autónomo con acceso total al sistema (BD, archivos, logs, terminal). El usuario lo selecciona como modo de agente y habla con él igual que habla con Claude Code en sesión interactiva, pero desde Telegram.

---

## Arquitectura

```
Bot Telegram
├── Modo normal → ia_service Flask (gemini, groq, etc.) — sin cambios
└── Modo Super Agente → claude -p directo (bypass ia_service)
                         ├── Lee BD: effi_data, ia_service_os
                         ├── Lee archivos y logs del repo
                         ├── Ejecuta SQL y comandos
                         └── Gestiona su propio contexto de conversación
```

---

## Acceso y permisos

| Acción | Nivel requerido |
|---|---|
| Usar el Super Agente (consultas) | Nivel 5+ (Jen, Santi) |
| Aprobar cambios de código o estructurales | Solo nivel 7 (Santi) |
| Correcciones automáticas en BD | Claude solo, sin aprobación |

---

## Contexto de conversación

El bot pasa a Claude los **últimos 10 mensajes** de la sesión activa (preguntas y respuestas). Si Claude necesita historial anterior, lo busca él mismo en la BD:

```sql
SELECT mensajes FROM superagente_sesiones WHERE sesion_id = {id}
```

Claude decide cuánto contexto usar — no hay lógica de compresión en el bot.

---

## Formato de respuesta

En el prompt se le instruye a Claude:

- **Respuesta con datos tabulares** → devolver JSON:
```json
{
  "tipo": "tabla",
  "texto": "El canal mayorista lideró con $3.2M en marzo.",
  "titulo": "Ventas por canal — Marzo 2026",
  "columnas": ["Canal", "Total", "Facturas"],
  "filas": [["Mayorista", "$3.2M", 37], ["Minorista", "$1.1M", 22]]
}
```
- **Respuesta de texto** → texto plano directamente

El bot detecta si la respuesta es JSON o texto y usa el renderer de `tabla.py` existente para las tablas.

---

## Flujo de aprobación — cambios de código

Cuando Claude detecta que necesita modificar código o estructura:

```
1. Le dice al usuario actual:
   "Necesito un cambio de [código/estructura]. Voy a pedir autorización a Santiago."

2. Envía mensaje privado a Santi (nivel 7) con:
   - Qué necesita cambiar y en qué archivo
   - Causa raíz identificada
   - El cambio propuesto exacto
   - Botones: [✅ Aprobar] [❌ Rechazar]

3a. Santi aprueba → Claude aplica el cambio → notifica al usuario original que se resolvió
3b. Santi rechaza → Claude documenta en logs/cambios_pendientes.md → continúa sin tocar código
```

---

## Correcciones automáticas en BD

Claude puede modificar sin aprobación: `ia_logica_negocio`, `ia_ejemplos_sql`, `ia_tipos_consulta`.

Cada cambio registra en `ia_cambios_autonomos`:
```
tabla | campo | valor_anterior | valor_nuevo | razon | timestamp | sesion_id
```

Siempre notifica a Telegram al aplicar un cambio.

---

## Reglas anti-parche (en prompt_sistema — siempre aplican)

- Nunca workarounds ni parches superficiales
- Sin try/catch vacíos o genéricos
- Sin hardcodear valores para "resolver" bugs
- Si no se identifica causa raíz → solo documentar, nunca "arreglar" el síntoma
- Respetar arquitectura existente
- Seguir `.agent/skills/desarrollo_python.md`

---

## Tablas nuevas en `ia_service_os`

### `superagente_sesiones`
```sql
CREATE TABLE superagente_sesiones (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  empresa     VARCHAR(50)   NOT NULL DEFAULT 'ori_sil_2',
  usuario_id  VARCHAR(100)  NOT NULL,
  canal       VARCHAR(50)   DEFAULT 'telegram',
  mensajes    JSON          NOT NULL DEFAULT '[]',
  created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_empresa_usuario (empresa, usuario_id)
);
```

### `superagente_config`
```sql
CREATE TABLE superagente_config (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  empresa         VARCHAR(50)   NOT NULL,
  prompt_sistema  TEXT          NOT NULL,
  activo          TINYINT(1)    DEFAULT 1,
  usuario_ult_mod VARCHAR(150),
  updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_empresa (empresa)
);
```

### `ia_cambios_autonomos`
```sql
CREATE TABLE ia_cambios_autonomos (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  empresa         VARCHAR(50)   NOT NULL,
  sesion_id       INT,
  tabla_afectada  VARCHAR(100)  NOT NULL,
  campo           VARCHAR(100),
  valor_anterior  TEXT,
  valor_nuevo     TEXT,
  razon           TEXT          NOT NULL,
  created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  KEY idx_empresa (empresa)
);
```

---

## Sección en el admin (ia.oscomunidad.com)

Dos pantallas — nada más:

**Prompt del sistema**
- Textarea con el prompt actual
- Botón Guardar
- Fecha de última modificación

**Historial de conversaciones**
- Tabla: fecha | usuario | primera pregunta de la sesión
- Click en fila → ver conversación completa de esa sesión

---

## Tareas

### A — BD y datos
- [x] Crear tabla `sa_sesiones` en ia_service_os — 2026-03-24
- [x] Crear tabla `sa_config` en ia_service_os con prompt inicial — 2026-03-24
- [x] Crear tabla `sa_cambios` en ia_service_os — 2026-03-24

### B — Prompt del sistema
- [x] Prompt inicial cargado en sa_config (empresa=ori_sil_2, 2180 chars) — 2026-03-24

### C — Bot Telegram
- [x] `🦾 Super Agente (Claude Code)` en selector de agentes nivel 5+ — 2026-03-24
- [x] `superagente.py`: obtener_sesion, consultar, guardar_intercambio, formatear_historial — 2026-03-24
- [x] `handlers_sa.py`: manejar_superagente, handle_sa_callback — 2026-03-24
- [x] bot.py: routing agente='superagente' → bypass ia_service → claude -p — 2026-03-24
- [x] Tablas reutilizan tabla.py existente (res_fake con columnas/filas del JSON) — 2026-03-24
- [x] Notificación a nivel 7 con botones ✅/❌ + callback handler — 2026-03-24

### D — Admin ia.oscomunidad.com
- [x] SuperAgentePage.vue — tabs Prompt + Historial con drill-down — 2026-03-24
- [x] server.js: 4 endpoints /api/ia/superagente/{config, sesiones, sesiones/:id} — 2026-03-24
- [x] routes.js: ruta /superagente — 2026-03-24

### E — Verificación
- [ ] Probar consulta simple de datos desde Telegram
- [ ] Verificar renderizado de tablas
- [ ] Probar flujo de aprobación de cambio de código
- [ ] Verificar que correcciones en BD quedan en sa_cambios

---

## Qué NO se hace

- No integrar Claude Code dentro de `ia_service` como proveedor
- No ramas de git para cambios de BD (son reversibles con DELETE/UPDATE)
- No limitar acceso de Jen para consultas — igual que Santi
- El admin del super agente NO tiene más pantallas que las 2 definidas
