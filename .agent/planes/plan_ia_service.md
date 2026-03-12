# Plan: Servicio Central de IA — `ia_service_os`

**Ubicación del código:** `scripts/ia_service/`
**BD:** `ia_service_os` en MariaDB local
**API Flask:** puerto 5100 (systemd `ia-service.service`)
**Propósito:** función `consultar()` estándar usable desde cualquier proyecto vía HTTP POST

---

## Estado del plan

| # | Tarea | Estado |
|---|---|---|
| 1 | Crear plan detallado | ✅ |
| 2 | Actualizar CONTEXTO_ACTIVO.md | ✅ |
| 3 | Crear BD `ia_service_os` + 4 tablas + datos iniciales | ✅ |
| 4 | Crear estructura de archivos `scripts/ia_service/` | ✅ |
| 5 | Implementar proveedores: `openai_compat.py` + `google.py` | ✅ |
| 6 | Implementar `contexto.py` + `ejecutor_sql.py` + `formateador.py` | ✅ |
| 7 | Implementar `servicio.py` (orquestador + enrutador interno) | ✅ |
| 8 | Implementar `app.py` (Flask API puerto 5100) | ✅ |
| 9 | Configurar systemd `ia-service.service` | ✅ |
| 10 | Agregar API keys al .env (Gemini ✅, Groq pendiente, DeepSeek pendiente) | ✅ |
| 11 | Prueba end-to-end con Gemini (Groq/DeepSeek sin key aún) | ✅ |
| 12 | Commit + documentación final | ✅ |

## Notas de implementación

- **Gemini 2.5 Flash** es un modelo "thinking" — usa hasta 15 tokens internos antes de responder. Para el enrutador se usan 200 max_tokens mínimo para que siempre responda.
- **Fallback de agente**: si el agente preferido del tipo no tiene API key, el servicio busca automáticamente el primero activo con key configurada.
- **Fallback de enrutamiento**: si Groq no tiene key, usa Gemini. Si ninguno tiene key, retorna `analisis_datos`.
- **API key activa**: guardada SOLO en BD `ia_service_os.ia_agentes` y en `scripts/.env` (en .gitignore). NUNCA en archivos del repo.
- **Puerto 5100**: systemd `ia-service.service` — activo y habilitado en boot.

## Pendiente (para completar con keys de Groq/DeepSeek/Claude)

```bash
# 1. Ir a console.groq.com → API Keys → crear key
# 2. Ir a platform.deepseek.com → API Keys → crear key
# 3. Agregar al .env:
GROQ_API_KEY=gsk_xxx
DEEPSEEK_API_KEY=sk-xxx
# 4. Actualizar en BD:
mysql -u osadmin -pEpist2487. ia_service_os -e "
UPDATE ia_agentes SET api_key='gsk_xxx' WHERE slug='groq-llama';
UPDATE ia_agentes SET api_key='sk-xxx' WHERE slug IN ('deepseek-chat','deepseek-reasoner');
"
# 5. sudo systemctl restart ia-service
```

---

## Diseño definitivo

### 4 Tablas en `ia_service_os`

#### `ia_agentes` — catálogo de modelos con credenciales

```sql
id, slug, nombre, proveedor,
api_formato ENUM('openai','anthropic','google'),
endpoint_url, api_key, modelo_id,
tipo ENUM('free','premium'),
capacidades JSON,       -- ["texto","sql","vision","imagen"]
max_tokens_entrada INT,
max_tokens_salida INT,
costo_input DECIMAL(10,4) NULL,   -- USD por millón tokens
costo_output DECIMAL(10,4) NULL,
rate_limit_rpm INT NULL,
rate_limit_rpd INT NULL,
activo BOOL DEFAULT 1,
orden INT,              -- prioridad para fallback
notas TEXT NULL
```

**Agentes iniciales:**

| slug | modelo | tipo | RPM/RPD |
|---|---|---|---|
| `gemini-flash` | gemini-2.5-flash | free | 10/250 |
| `gemini-flash-lite` | gemini-2.0-flash-lite | free | 15/1500 |
| `deepseek-chat` | deepseek-chat | free* | — |
| `deepseek-reasoner` | deepseek-reasoner | premium | — |
| `groq-llama` | llama-3.3-70b-versatile | free | 30/14400 |
| `claude-sonnet` | claude-sonnet-4-6 | premium | — |

#### `ia_tipos_consulta` — tipos con reglas y pasos predefinidos

```sql
id, slug, nombre, descripcion,
pasos JSON,             -- ["generar_sql","ejecutar","redactar"]
system_prompt TEXT,     -- reglas específicas del tipo
formato_salida VARCHAR(50),  -- texto|tabla|texto_tabla|imagen|documento|json
requiere_estructura BOOL,    -- ¿necesita DDL de BD?
requiere_ejecucion BOOL,     -- ¿hay que ejecutar algo?
agente_preferido VARCHAR(50) NULL,
temperatura DECIMAL(3,2),
activo BOOL DEFAULT 1
```

**Tipos iniciales:**

| slug | pasos | formato | agente_preferido |
|---|---|---|---|
| `analisis_datos` | generar_sql → ejecutar → redactar | texto_tabla | claude-sonnet |
| `redaccion` | redactar | texto | gemini-flash |
| `clasificacion` | analizar → clasificar | json | groq-llama |
| `resumen` | resumir | texto | gemini-flash |
| `enrutamiento` | clasificar_intent | json | groq-llama |
| `generacion_documento` | generar_sql → ejecutar → generar_doc | documento | claude-sonnet |

#### `ia_conversaciones` — contexto vivo por usuario/canal

```sql
id INT PK AUTO,
usuario_id VARCHAR(100),
canal VARCHAR(50),           -- telegram, erp, api, script
nombre_usuario VARCHAR(200) NULL,
agente_activo VARCHAR(50) NULL,   -- modelo preferido del usuario
resumen TEXT NULL,           -- resumen vivo (máx 1000 palabras, actualizado cada turno)
metadata JSON NULL,          -- {chat_id, session_erp, etc.}
created_at TIMESTAMP,
updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
INDEX idx_usuario_canal (usuario_id, canal)
```

**Clave:** el servicio busca por `(usuario_id, canal)` si no viene `conversacion_id`, o por `id` si viene explícito. Siempre devuelve el `conversacion_id` usado para que el caller lo reuse.

#### `ia_logs` — auditoría completa

```sql
id INT PK AUTO,
conversacion_id INT NULL,
agente_slug VARCHAR(50),
tipo_consulta VARCHAR(50),
canal VARCHAR(50),
pregunta TEXT,
sql_generado TEXT NULL,
datos_crudos JSON NULL,
respuesta TEXT,
formato VARCHAR(30),
tokens_in INT NULL,
tokens_out INT NULL,
costo_usd DECIMAL(10,6) NULL,
latencia_ms INT NULL,
pasos_ejecutados JSON NULL,
error TEXT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

---

### Estructura de archivos

```
scripts/ia_service/
  __init__.py            # exporta consultar()
  servicio.py            # orquestador principal
  proveedores/
    __init__.py
    openai_compat.py     # Groq + DeepSeek (formato OpenAI)
    google.py            # Gemini (API nativa Google)
    anthropic_prov.py    # Claude (Anthropic API)
  contexto.py            # lee/escribe ia_conversaciones + manejo del resumen
  ejecutor_sql.py        # ejecuta SQL seguro contra Hostinger
  formateador.py         # parsea respuesta IA y extrae formato + resumen
  esquema.py             # genera DDL de tablas relevantes (cacheado)
  config.py              # lee .env, conexión BD local
app.py                   # Flask: POST /ia/consultar, GET /ia/agentes
```

---

### Función principal `consultar()`

```python
resultado = consultar(
    pregunta        = "¿Cuánto vendimos ayer?",
    tipo            = None,          # None = enrutar automáticamente
    agente          = None,          # None = usar agente_preferido del tipo
    usuario_id      = "santi",
    canal           = "telegram",
    conversacion_id = None,          # None = buscar por (usuario_id, canal)
    contexto_extra  = ""             # contexto libre adicional
)

# Respuesta estándar:
{
    "ok":              True,
    "conversacion_id": 42,
    "respuesta":       "Ayer se vendieron $4.2M...",
    "formato":         "texto_tabla",
    "tabla":           {"columnas": [...], "filas": [...]},  # si aplica
    "sql":             "SELECT ...",                          # si aplica
    "agente":          "gemini-flash",
    "tokens":          {"in": 800, "out": 350},
    "costo_usd":       0.0,
    "pasos":           ["generar_sql", "ejecutar", "redactar"],
    "log_id":          1234
}
```

### Flujo interno de `consultar()`

```
1. Si tipo=None → _enrutar(pregunta) → llamada Groq (~100ms) → devuelve slug
2. Leer ia_tipos_consulta[tipo] → saber pasos, system_prompt, temperatura, agente
3. Si agente=None → usar tipo.agente_preferido
4. Leer ia_conversaciones[usuario_id+canal o conversacion_id] → resumen_anterior
5. Si tipo.requiere_estructura → inyectar DDL de tablas relevantes
6. Ejecutar pasos en orden:
   - generar_sql   → llamar IA con system_prompt + DDL + pregunta → extraer SQL
   - ejecutar      → ejecutar SQL en Hostinger → datos_crudos
   - redactar      → llamar IA con datos + pregunta → respuesta humana + [RESUMEN]...
   - resumir       → llamar IA → texto directo + [RESUMEN]...
   - clasificar    → llamar IA → JSON con clasificación + [RESUMEN]...
7. Parsear [RESUMEN_CONTEXTO]...[/RESUMEN_CONTEXTO] de la respuesta → guardar
8. Guardar ia_logs
9. Actualizar ia_conversaciones.resumen + updated_at
10. Devolver resultado estándar
```

### Prompt de resumen (al final de cada turno)

```
Al final de tu respuesta, incluye un resumen actualizado de esta conversación
entre las etiquetas [RESUMEN_CONTEXTO] y [/RESUMEN_CONTEXTO].
El resumen debe ser DETALLADO, máximo 1000 palabras. Incluye siempre:
- Nombres de personas, productos, clientes mencionados
- Datos numéricos relevantes (ventas, fechas, cantidades)
- Decisiones tomadas o acuerdos logrados
- Preguntas ya respondidas (para no repetir)
- Contexto del negocio que emerge de la conversación
```

---

### systemd service

```ini
[Unit]
Description=IA Service OS — API central de IA
After=network.target mariadb.service

[Service]
Type=simple
User=osserver
WorkingDirectory=/home/osserver/Proyectos_Antigravity/Integraciones_OS
EnvironmentFile=/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/.env
ExecStart=/usr/bin/python3 scripts/ia_service/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

### Agentes en orden de implementación

1. ✅ **Gemini Flash** — API key ya existe en bot_telegram/.env
2. 🔲 **Groq Llama** — necesita API key (groq.com — completamente gratis)
3. 🔲 **DeepSeek Chat** — necesita API key (platform.deepseek.com — casi gratis)
4. 🔲 **DeepSeek Reasoner** — misma key que DeepSeek Chat, modelo distinto
5. 🔲 **Claude Sonnet** — API key de Anthropic
