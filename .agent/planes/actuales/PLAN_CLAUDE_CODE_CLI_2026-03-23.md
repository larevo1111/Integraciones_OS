# Plan: Super Agente Claude Code

**Creado**: 2026-03-23
**Actualizado**: 2026-03-24
**Módulo**: ia_service + telegram_bot + ia-admin
**Estado**: Diseño completo — listo para implementar

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
- [ ] Crear tabla `superagente_sesiones` en ia_service_os
- [ ] Crear tabla `superagente_config` en ia_service_os con prompt inicial
- [ ] Crear tabla `ia_cambios_autonomos` en ia_service_os

### B — Prompt del sistema
- [ ] Escribir `prompt_sistema` inicial en `superagente_config` con:
  identidad, accesos disponibles, reglas anti-parche, flujo de aprobación, formato de respuesta

### C — Bot Telegram
- [ ] Agregar "Super Agente" como opción en el selector de agentes (niveles 5+)
- [ ] Función `_manejar_superagente()` en bot.py:
  - Lee `superagente_config` para el prompt del sistema
  - Lee últimos 10 mensajes de `superagente_sesiones`
  - Construye prompt y llama `claude -p`
  - Detecta si respuesta es JSON (tabla) o texto plano
  - Guarda pregunta + respuesta en `superagente_sesiones`
- [ ] Reutilizar `tabla.py` para renderizar tablas del super agente
- [ ] Implementar notificación a Santi (nivel 7) cuando Claude pide aprobación de código
  - Mensaje privado con descripción del cambio + botones [✅ Aprobar] [❌ Rechazar]
  - Callback handler para procesar la respuesta de Santi

### D — Admin ia.oscomunidad.com
- [ ] Ruta `/superagente/prompt` — editor del prompt del sistema
- [ ] Ruta `/superagente/historial` — listado de sesiones con drill-down

### E — Verificación
- [ ] Probar consulta simple de datos con Jen (nivel 5)
- [ ] Verificar que la tabla se renderiza correctamente
- [ ] Probar flujo de aprobación: Claude detecta cambio de código → mensaje a Santi → aprobación
- [ ] Verificar que correcciones automáticas en BD quedan registradas en ia_cambios_autonomos

---

## Qué NO se hace

- No integrar Claude Code dentro de `ia_service` como proveedor
- No ramas de git para cambios de BD (son reversibles con DELETE/UPDATE)
- No limitar acceso de Jen para consultas — igual que Santi
- El admin del super agente NO tiene más pantallas que las 2 definidas
