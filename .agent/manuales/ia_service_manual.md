# Manual del Servicio Central de IA — ia_service_os

**Versión**: 2.9 — 2026-03-20
**Scope**: Servicio de IA centralizado de Origen Silvestre. Corre en el servidor OS (puerto 5100) y sirve a TODOS los proyectos: bot de Telegram, apps, integraciones, ERP.
**Admin panel**: app separada `ia.oscomunidad.com` — ✅ Activa (puerto 9200, `os-ia-admin.service`). Vue+Quasar con **15 páginas en 6 grupos semánticos**: Dashboard, Playground, Lógica de negocio, Documentos RAG, Ejemplos SQL, Agentes, Roles de agentes, Tipos de consulta, Esquemas BD, Conexiones BD, Usuarios, Conversaciones, Bot Telegram, Configuración, Logs. Auth Google OAuth + JWT 2 pasos.

> **REGLA DE SEGURIDAD ABSOLUTA**: Las API keys van SOLO en la BD (`ia_agentes.api_key`) y en `scripts/.env`. NUNCA en archivos .md, código commiteado, comentarios ni mensajes de commit.

---

## Índice

1. [Filosofía del sistema — por qué importa](#filosofia)
2. [Arquitectura completa](#arquitectura)
3. [Base de datos — tablas completas](#bd)
4. [System prompt — 8 capas](#system-prompt)
5. [Tipos de consulta](#tipos)
6. [Agentes disponibles](#agentes)
7. [Arquitectura de dos capas — mecánica vs analítica](#dos-capas)
8. [Temas — routing por área de negocio](#temas)
9. [Sistema RAG — documentos de negocio](#rag)
10. [Embeddings — búsqueda semántica de ejemplos SQL](#embeddings)
11. [Retry inteligente — resultado vacío](#retry)
12. [Enrutador y requiere_sql](#enrutador)
13. [Catálogo de tablas](#catalogo)
14. [Conversaciones — contexto vivo](#conversaciones)
15. [Bot de Telegram](#telegram)
16. [Sistema de usuarios, niveles y configuración](#usuarios)
17. [Multi-empresa](#multiempresa)
17bis. [Protocolo de aprendizaje — ia_logica_negocio](#aprendizaje)
18. [Cómo agregar / configurar un agente](#agregar-agente)
19. [Monitoreo del consumo](#monitoreo)
20. [Operación diaria — comandos útiles](#operacion)
21. [Troubleshooting](#troubleshooting)
22. [Referencia: modelos y costos](#referencia)
23. [Roles de agentes — configuración en ia_config](#roles-agentes)
24. [Gestor admin — páginas y funciones](#gestor-admin)

---

## 1. Filosofía del sistema — por qué importa {#filosofia}

### El principio fundamental: enseñar a razonar, no a memorizar

**El objetivo de este sistema es construir una IA que encuentre las respuestas de forma autónoma.**

Esto significa que NO hay que llenar el sistema de reglas específicas para cada pregunta posible. Si la IA falla en una pregunta concreta y la respuesta correcta se le inyecta directamente en el prompt, la próxima vez la responderá bien — pero eso no es aprendizaje: es memorización. Y el próximo usuario que haga la misma pregunta de otra forma, volverá a fallar.

**La diferencia clave:**

| Enfoque incorrecto | Enfoque correcto |
|---|---|
| "Cuando pregunten por ventas del lunes, usar esta fórmula exacta" | Dar al modelo el contexto y las herramientas para razonar la fórmula él solo |
| Agregar una regla por cada caso edge que falla | Mejorar el contexto general para que el modelo razone mejor en todos los casos |
| Inyectar el resultado correcto de una consulta fallida | Revisar si el sistema prompt tiene la información necesaria para que el modelo llegue solo a ese resultado |
| System prompt de 10,000 palabras con casos específicos | System prompt claro, bien estructurado, con principios generales y ejemplos representativos |

### ¿Cuándo sí agregar reglas específicas?

Solo cuando representan un patrón que el modelo NO puede inferir por sí solo con el contexto disponible:
- Gotchas técnicos de la BD (ej: "id_cliente en facturas tiene prefijo 'CC '")
- Semántica de campos que no es obvia (ej: "precio_neto_total INCLUYE IVA — para sin IVA usa precio_bruto_total - descuento_total")
- Comportamientos contraintuitivos del negocio (ej: vigencia='Vigente' para consignación activa)

Esas cosas el modelo no puede deducirlas. Pero "cómo calcular ventas del lunes" sí puede razonarlo desde los patrones de fecha que ya tiene en el prompt.

### Implicación para el refinamiento del sistema

Cuando la IA falla en una consulta:
1. **Primero diagnosticar**: ¿Le falta contexto general? ¿O es un caso edge muy específico?
2. **Si le falta contexto general** → mejorar el system prompt con el principio, no el caso
3. **Si es un gotcha técnico** → sí agregar la regla, es legítimo
4. **Si es un error de razonamiento puro** → agregar un ejemplo representativo a `ia_ejemplos_sql` (no hardcodear la respuesta, sino demostrar el patrón)

---

## 2. Arquitectura completa {#arquitectura}

```
POST /ia/consultar (Flask :5100)
        ↓
  consultar() — servicio.py
        ↓
  CAPA 0: fecha + contexto dinámico
        ↓
  _enrutar() → Groq Llama (~100–300ms, gratis)
    devuelve: tipo, tema, requiere_sql
        ↓
  ┌─────────────────────────────────────────────────────────┐
  │ FLUJO SQL — tipo=analisis_datos && requiere_sql=True     │
  │                                                          │
  │  agente_sql (Gemini Flash, gratis)                       │
  │    → genera SQL con schema DDL (~27K tokens) + ejemplos  │
  │    → verificación 1: ejecuta SQL en Hostinger            │
  │    → si falla: agente corrige → verificación 2           │
  │    → si vacío: agente corrige → verificación 2 y 3       │
  │                                                          │
  │  agente analítico (elección usuario)                     │
  │    → redacta respuesta con los datos                     │
  │                                                          │
  │  TOTAL: ~20–23s con gemini-pro | ~8–12s con flash-lite   │
  └─────────────────────────────────────────────────────────┘
        ↓
  ┌────────────────────────────────────────────────────────┐
  │ FLUJO SIN SQL — requiere_sql=False o tipo=conversacion  │
  │                                                         │
  │  agente analítico (elección usuario)                    │
  │    → redacta con RAG + contexto conversacional          │
  │                                                         │
  │  TOTAL: ~2.5s con gemini-flash-lite | ~20s con pro      │
  └────────────────────────────────────────────────────────┘
        ↓
  contexto.py → guarda resumen vivo (ia_conversaciones)
        ↓
  ia_logs → auditoría completa
  ia_consumo_diario → agregado diario
        ↓
  retorna: {ok, respuesta, tabla, sql, agente, tokens, costo, conversacion_id}
```

**BD local**: `ia_service_os` — 17 tablas + 1 vista (ver sección 3)
**Puerto**: 5100 (systemd `ia-service.service`)
**Código**: `scripts/ia_service/`

**Módulos Python del servicio:**

| Archivo | Propósito |
|---|---|
| `app.py` | Flask API — define endpoints, middleware auth JWT, CORS |
| `servicio.py` | Orquestador principal — función `consultar()` con todos los pasos |
| `contexto.py` | Manejo de conversaciones y resumen vivo por usuario+canal |
| `ejecutor_sql.py` | Ejecución segura de SQL SELECT en Hostinger via SSH tunnel |
| `esquema.py` | DDL de tablas analíticas desde Hostinger (caché 1h) |
| `formateador.py` | Parseo de SQL de respuestas LLM + formato de filas a tabla |
| `rag.py` | Fragmentación de documentos + búsqueda FULLTEXT por empresa+tema |
| `embeddings.py` | Google text-embedding-004 + cosine similarity para ejemplos SQL |
| `conector.py` | Multi-BD: ejecuta queries en ia_conexiones_bd configuradas |
| `config.py` | Carga ia_config desde BD — parámetros globales |
| `extractor.py` | Extrae texto de PDF/DOCX/PPTX para cargar documentos RAG |
| `actualizar_system_prompt.py` | Regenera XML del system prompt de analisis_datos (ejecutar manualmente) |
| `proveedores/google.py` | Llamadas a API Google: Gemini, Gemma, imagen |
| `proveedores/openai_compat.py` | Llamadas a Groq y DeepSeek (API compatible OpenAI) |
| `proveedores/anthropic_prov.py` | Llamadas a Anthropic Claude |

**Bot de Telegram:** `scripts/telegram_bot/` — `bot.py`, `api_ia.py`, `db.py`, `tabla.py`, `teclado.py`

---

## 3. Base de datos — tablas completas {#bd}

BD: `ia_service_os` en MariaDB local (servidor OS, acceso solo local).

```bash
# Conectar
mysql -u osadmin -pEpist2487. ia_service_os 2>/dev/null

# Ver todas las tablas
mysql -u osadmin -pEpist2487. ia_service_os -e "SHOW TABLES;" 2>/dev/null
```

**Tablas actuales (17 tablas + 1 vista):**

| Tabla | Propósito |
|---|---|
| `ia_agentes` | Modelos IA configurados con API key y capacidades |
| `ia_tipos_consulta` | Flujos por tipo (SQL, RAG, imagen, etc.) + system prompts |
| `ia_temas` | Áreas de negocio por empresa (7 temas para ori_sil_2) — routing por tema |
| `ia_conversaciones` | Contexto vivo por usuario+canal (resumen + mensajes recientes) |
| `ia_logs` | Auditoría completa: SQL, tokens, costo, latencia, error |
| `ia_consumo_diario` | Agregado diario por agente |
| `ia_ejemplos_sql` | Pares pregunta→SQL aprendidos (few-shot learning) |
| `ia_rag_documentos` | Documentos de negocio para RAG |
| `ia_rag_fragmentos` | Chunks ~500 palabras con FULLTEXT index |
| `ia_usuarios` | Usuarios del servicio con nivel de acceso (1–7) |
| `ia_empresas` | Empresas registradas (multi-tenant) — PK: uid |
| `ia_usuarios_empresas` | Relación usuario↔empresa con rol (admin/viewer) |
| `ia_config` | Parámetros globales del sistema (circuit breaker, rate limits, costo max) |
| `ia_conexiones_bd` | Conexiones a BDs externas por empresa (para conector.py) |
| `ia_esquemas` | DDL de tablas por tema+conexión (para inyectar en system prompt) |
| `ia_logica_negocio` | Fragmentos de lógica de negocio aprendidos (RAG contextual) |
| `bot_sesiones` | Sesiones del bot de Telegram (agente preferido, nivel, autorizado) |
| `bot_tablas_temp` | Tablas de datos temporales para la mini app web del bot |
| `v_consumo_hoy` | Vista — consumo del día actual aggregado (atajos de monitoreo) |

### ia_agentes

Modelos de IA configurados. Cada fila es un agente con su provider, modelo y key.

```sql
SELECT slug, nombre, modelo_id, proveedor, activo,
       LENGTH(api_key) > 0 AS tiene_key, rate_limit_rpd, orden, nivel_minimo
FROM ia_agentes ORDER BY orden;
```

| Columna | Descripción |
|---|---|
| `slug` | Identificador único: `gemini-pro`, `groq-llama`, `deepseek-chat`, etc. |
| `nombre` | Nombre display al usuario |
| `modelo_id` | ID exacto del modelo en la API del proveedor |
| `proveedor` | `"google"`, `"openai"` (Groq/DeepSeek), `"anthropic"` |
| `api_key` | KEY del proveedor — SOLO aquí (no en código) |
| `activo` | 1 = disponible, 0 = desactivado |
| `rate_limit_rpd` | Límite diario de requests del proveedor |
| `orden` | Para fallback — si el preferido falla, se usa el siguiente en orden |
| `nivel_minimo` | Nivel de acceso mínimo de usuario (1–7) para usar este agente |

### ia_tipos_consulta

Define los flujos y system prompts por tipo de consulta.

```sql
SELECT slug, descripcion, pasos, agente_preferido, agente_sql, tema
FROM ia_tipos_consulta;
```

| Columna | Descripción |
|---|---|
| `slug` | `analisis_datos`, `redaccion`, `enrutamiento`, `conversacion`, `clasificacion`, `generacion_imagen` |
| `pasos` | JSON array — pasos del flujo: `["enrutar","generar_sql","ejecutar","redactar"]` |
| `agente_preferido` | Slug del agente para redactar respuesta |
| `agente_fallback` | Slug del agente de respaldo si el preferido falla o alcanza su límite |
| `agente_sql` | Slug del agente para generar SQL (capa mecánica, distinto al analítico) |
| `requiere_sql` | TINYINT 0|1 — si el tipo genera SQL antes de responder |
| `system_prompt` | TEXT — prompt completo con XML estructurado |
| `tema` | Campo libre para clasificar temas RAG |

### ia_conversaciones

Contexto vivo de cada conversación. Una fila por usuario+canal.

```sql
SELECT usuario_id, canal, empresa, LENGTH(resumen) AS chars_resumen,
       mensajes_count, updated_at
FROM ia_conversaciones ORDER BY updated_at DESC LIMIT 20;
```

| Columna | Descripción |
|---|---|
| `usuario_id` | ID del usuario (Telegram ID, nombre, etc.) |
| `canal` | `telegram`, `api`, `web`, etc. |
| `empresa` | Código empresa: `ori_sil_2` |
| `resumen` | TEXT — resumen comprimido del historial (máx 1,000 palabras) |
| `mensajes_recientes` | JSON — últimos 10 mensajes `[{role, content}]` |
| `mensajes_count` | Total de mensajes en la conversación |

### ia_logs

Auditoría completa — una fila por llamada a la IA.

```sql
SELECT created_at, agente_slug, tipo_consulta, ok, tokens_in, tokens_out,
       costo_usd, latencia_ms, error
FROM ia_logs ORDER BY created_at DESC LIMIT 20;
```

### ia_consumo_diario

Agregado diario por agente. Se actualiza automáticamente con cada llamada.

```sql
SELECT fecha, agente_slug, llamadas, tokens_total, costo_usd, errores
FROM ia_consumo_diario ORDER BY fecha DESC, llamadas DESC LIMIT 30;
```

### ia_rag_documentos

Documentos de negocio cargados para RAG (búsqueda por contexto).

```sql
SELECT id, nombre, tema, empresa, activo, LENGTH(contenido_completo) AS chars,
       created_at
FROM ia_rag_documentos ORDER BY tema, nombre;
```

| Columna | Descripción |
|---|---|
| `nombre` | Nombre descriptivo del documento |
| `tema` | `estrategia`, `comercial`, `marketing`, `administracion` |
| `empresa` | Código empresa (`ori_sil_2`) |
| `contenido_completo` | Texto completo extraído del documento original |
| `activo` | 1 = incluido en búsquedas RAG |

### ia_rag_fragmentos

Fragmentos individuales de cada documento (para búsqueda FULLTEXT).

```sql
SELECT d.nombre AS documento, f.tema, f.posicion,
       LEFT(f.contenido, 100) AS preview, LENGTH(f.contenido) AS chars
FROM ia_rag_fragmentos f
JOIN ia_rag_documentos d ON d.id = f.documento_id
ORDER BY f.tema, f.posicion;
```

| Columna | Descripción |
|---|---|
| `documento_id` | FK a ia_rag_documentos |
| `tema` | Hereda del documento |
| `posicion` | Orden del fragmento dentro del documento |
| `contenido` | ~500 palabras de texto |
| (índice FULLTEXT sobre `contenido`) | Para búsqueda |

### ia_ejemplos_sql

Ejemplos pregunta→SQL guardados por el sistema (few-shot learning).

```sql
SELECT empresa, pregunta, LEFT(sql_generado, 80) AS sql_preview,
       embedding IS NOT NULL AS tiene_embedding, calidad, creado_en
FROM ia_ejemplos_sql ORDER BY creado_en DESC LIMIT 20;
```

| Columna | Descripción |
|---|---|
| `empresa` | Código empresa |
| `pregunta` | Pregunta en lenguaje natural |
| `sql_generado` | SQL que resolvió la pregunta |
| `resultado_muestra` | JSON muestra del resultado |
| `embedding` | LONGTEXT — vector 768 dims (JSON) para búsqueda semántica |
| `calidad` | `buena`, `mala` — para filtrar ejemplos de baja calidad |

### ia_temas

Áreas de negocio por empresa. Define el `agente_preferido` para cada tema (sobreescribe el default del tipo).

```sql
SELECT slug, nombre, agente_preferido, activo FROM ia_temas ORDER BY id;
```

| Columna | Descripción |
|---|---|
| `slug` | Identificador: `comercial`, `finanzas`, `produccion`, `administracion`, `marketing`, `estrategia`, `general` |
| `agente_preferido` | Slug del agente para respuestas en este tema |
| `schema_tablas` | JSON — lista de tablas relevantes para el tema |
| `system_prompt` | Prompt específico del tema (override al del tipo) |

**Estado actual (2026-03-15):**

| Tema | agente_preferido | Latencia esperada |
|---|---|---|
| finanzas | gemini-pro | ~20s |
| comercial | gemini-pro | ~20s |
| estrategia | gemini-pro | ~20s |
| produccion | gemini-flash-lite | ~2.5s |
| administracion | gemini-flash-lite | ~2.5s |
| marketing | gemini-flash-lite | ~2.5s |
| general | gemini-flash-lite | ~2.5s |

### ia_usuarios

Usuarios del servicio con nivel de acceso.

```sql
SELECT usuario_id, nombre, nivel, canal, empresa, activo FROM ia_usuarios;
```

### ia_config

Parámetros globales del sistema. Se leen en cada arranque del servicio.

```sql
SELECT clave, valor, descripcion FROM ia_config ORDER BY clave;
```

**Configuración actual (2026-03-15):**

| clave | valor | Descripción |
|---|---|---|
| `rate_usuario_rps` | 1 | Max solicitudes/segundo por usuario |
| `rate_usuario_rpm` | 15 | Max solicitudes/minuto por usuario |
| `rate_usuario_rp10s` | 3 | Max solicitudes en 10 segundos por usuario |
| `limite_costo_dia_usd` | 5.00 | Gasto máximo diario USD (0 = sin límite) |
| `circuit_breaker_errores` | 5 | Errores en ventana para suspender agente |
| `circuit_breaker_ventana_min` | 10 | Ventana de tiempo del circuit breaker |
| `acceso_dashboard` | 1 | Nivel mínimo para ver Dashboard |
| `acceso_playground` | 1 | Nivel mínimo para usar Playground |
| `acceso_logs` | 3 | Nivel mínimo para ver Logs |
| `acceso_contextos` | 5 | Nivel mínimo para ver Contextos RAG |
| `acceso_agentes` | 7 | Nivel mínimo para ver Agentes |
| `acceso_tipos` | 7 | Nivel mínimo para ver Tipos de consulta |
| `acceso_usuarios` | 7 | Nivel mínimo para ver Usuarios |
| `acceso_config` | 7 | Nivel mínimo para ver Configuración |
| `acceso_conexiones` | 7 | Nivel mínimo para ver Conexiones BD |

### ia_empresas / ia_usuarios_empresas

Multi-tenant. Ver sección [17. Multi-empresa](#multiempresa).

### ia_conexiones_bd / ia_esquemas

Conexiones a BDs externas por empresa (gestionado desde ia-admin → Conexiones BD, nivel 7 mínimo). `ia_esquemas` almacena DDL personalizado por tema+conexión.

### bot_sesiones / bot_tablas_temp

Para el bot de Telegram. `bot_sesiones` guarda el agente preferido por `telegram_user_id`. `bot_tablas_temp` almacena datasets temporales para la mini app web (tablas con muchas filas).

---

## 4. System prompt — 8 capas {#system-prompt}

El system prompt que recibe el LLM se construye en 8 capas dinámicas (en este orden):

```
CAPA 0 — Fecha y hora actual (siempre)
  "Fecha y hora actuales: 2026-03-20 15:30 (Viernes, 20 de marzo de 2026)"

CAPA 1 — Lógica de negocio (ia_logica_negocio)
  Fragmentos siempre_presente=1 se inyectan siempre
  Fragmentos por keyword se filtran según palabras en la pregunta
  "<logica_negocio>...</logica_negocio>"

CAPA 2 — System prompt base del tipo (desde ia_tipos_consulta)
  Para analisis_datos: XML completo con rol, precisión, catálogo tablas,
  diccionario campos, reglas SQL, ejemplos Q→SQL

CAPA 3 — RAG (solo si hay fragmentos relevantes)
  Fragmentos de documentos de negocio que coinciden con el tema de la pregunta
  "<documentos_negocio>...</documentos_negocio>"

CAPA 4 — DDL del esquema (solo para analisis_datos)
  CREATE TABLE de las tablas de Hostinger — para que el modelo vea estructura real
  "<esquema_base_datos>...</esquema_base_datos>"

CAPA 5 — Resumen de conversación (si hay contexto previo)
  El resumen comprimido del historial (máx 600 palabras)
  "<contexto_conversacion>...</contexto_conversacion>"

CAPA 6 — Mensajes recientes (últimos 5 mensajes)
  Los mensajes literales más recientes con sus preguntas y respuestas exactas

CAPA 7 — Caché SQL (si hay resultado previo en sesión)
  Resultado de la última consulta SQL — evita re-ejecutar la misma pregunta
  "<cache_sql>pregunta, columnas, n_filas, muestra_datos</cache_sql>"

CAPA 8 — Ejemplos SQL (few-shot por embeddings)
  Pares pregunta→SQL similares de ia_ejemplos_sql (cosine similarity con text-embedding-004)
  "<ejemplos_similares>...</ejemplos_similares>"
```

**Todas las capas se pueden gestionar desde ia.oscomunidad.com:**
- Capas 1: Lógica de negocio → página `/logica-negocio`
- Capa 2: System prompt base → página `/tipos` (editor)
- Capa 3: RAG → página `/contextos`
- Capa 4: DDL → página `/esquemas`
- Capas 5–7: Conversaciones → página `/conversaciones`
- Capa 8: Ejemplos SQL → página `/ejemplos-sql`

**¿Por qué XML en CAPA 1?** Anthropic documenta que el modelo parsea las secciones con más precisión cuando están delimitadas con tags XML nombrados (+30% en tareas analíticas complejas).

**Tags XML del system prompt de analisis_datos:**
- `<rol>` — quién es Lara, cómo piensa, cómo habla
- `<precision>` — cómo construir la respuesta con los datos entregados
- `<tablas_disponibles>` — catálogo de tablas con descripciones de negocio
- `<diccionario_campos>` — campos de las tablas principales con semántica
- `<reglas_sql>` — patrones de fecha, tipos de datos, gotchas técnicos
- `<ejemplos>` — 10 pares pregunta/SQL como few-shot examples

---

## 5. Tipos de consulta {#tipos}

Cada consulta se clasifica en un tipo por el enrutador. El tipo define:
- Qué pasos se ejecutan
- Qué agente genera el SQL (capa mecánica)
- Qué agente redacta la respuesta (capa analítica)

| slug | Descripción | Pasos | agente_sql | agente_preferido | agente_fallback |
|---|---|---|---|---|---|
| `analisis_datos` | Preguntas sobre datos históricos de ventas, compras, inventario, etc. | enrutar → generar_sql → ejecutar → redactar | gemini-flash | **cerebras-llama** | gemini-flash-lite |
| `conversacion` | Preguntas de estrategia, planes, metas — respuesta con RAG o contexto | enrutar → redactar | — | **cerebras-llama** | gemini-flash-lite |
| `enrutamiento` | Solo para el enrutador (no tiene steps de respuesta) | — | — | groq-llama | cerebras-llama |
| `redaccion` | Redactar texto, email, documento | redactar | — | **cerebras-llama** | gemini-flash-lite |
| `clasificacion` | Clasificar o etiquetar información | clasificar | — | groq-llama | — |
| `generacion_imagen` | Crear imagen con IA | generar_imagen | — | gemini-image | — |
| `resumen` | Resumir un texto o conjunto de datos | resumir | — | **cerebras-llama** | gemini-flash-lite |
| `generacion_documento` | Generar documentos completos (informes, reportes) | generar_doc | — | **cerebras-llama** | gemini-flash-lite |
| `aprendizaje` | Explicaciones, tutoriales, respuestas educativas | enrutar → redactar | — | **cerebras-llama** | gemini-flash-lite |
| `busqueda_web` | Consultas que requieren información externa o actualizada | enrutar → redactar | — | **cerebras-llama** | gemini-flash-lite |

> **Cambio 2026-03-20**: cerebras-llama reemplaza a gemini-flash como agente analítico principal en todos los tipos de respuesta. gemini-flash-lite reemplaza a deepseek como fallback universal. Ver benchmark: `.agent/docs/COMPARACION_AGENTES_IA.md`

### Cómo actualizar el system prompt de un tipo

```bash
# Editar el script y ejecutarlo
python3 scripts/ia_service/actualizar_system_prompt.py
# Esto actualiza ia_tipos_consulta.system_prompt para slug='analisis_datos'
```

Para otros tipos, actualizar directamente en BD:
```sql
UPDATE ia_tipos_consulta
SET system_prompt = '...'
WHERE slug = 'conversacion';
```

---

## 6. Agentes disponibles {#agentes}

### Estado actual (2026-03-17)

```bash
mariadb -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT slug, nombre, modelo_id, activo, LENGTH(api_key)>0 AS tiene_key,
          rate_limit_rpd, nivel_minimo, orden
   FROM ia_agentes ORDER BY orden;" 2>/dev/null
```

| slug | modelo_id | tiene_key | RPD | nivel_min | Rol principal | Capacidades |
|---|---|---|---|---|---|---|
| `cerebras-llama` | `llama3.1-8b` | ✅ | 1M TPD | 1 | **Default analítico** — 2,200 t/s, 100% éxito respuesta | sql, codigo, documentos |
| `gemini-flash` | `gemini-2.5-flash` | ✅ | 10,000 | 1 | **Generador SQL principal** — 93% éxito, 13s | vision, sql, codigo, documentos |
| `gemini-flash-lite` | `gemini-2.5-flash-lite` | ✅ | 150,000 | 1 | **Fallback analítico** — alto volumen, router fallback 2 | vision, enrutamiento |
| `gpt-oss-120b` | `openai/gpt-oss-120b` | ✅ (key Groq) | 1,000 | 1 | Analítico alternativo — 500 t/s, 100% éxito | sql, codigo, razonamiento |
| `groq-llama` | `llama-3.3-70b-versatile` | ✅ | 14,400 | 1 | **Enrutador principal** — 300ms, gratis (NUNCA agente final) | enrutamiento |
| `deepseek-chat` | `deepseek-chat` | ✅ | — | 1 | Analítico secundario (disponible en bot) | sql, codigo, razonamiento |
| `gemini-image` | `gemini-2.5-flash-image` | ✅ | 70 | 1 | Generación de imágenes | imagen_generacion |
| `gemma-router` | `gemma-3-27b-it` | ❌ (inactivo) | 14,400 | 1 | Router fallback (inactivo) | enrutamiento |
| `gemini-pro` | `gemini-2.5-pro` | ✅ | 1,000 | **6** | SQL complejo + premium (nivel 6+) | vision, sql, codigo, razonamiento |
| `deepseek-reasoner` | `deepseek-reasoner` | ✅ | — | 7 | Razonamiento complejo (solo admin) | razonamiento |
| `claude-sonnet` | `claude-sonnet-4-6` | ✅ | — | **6** | Documentos premium (nivel 6+) | vision, sql, codigo, documentos |

> **Cambio 2026-03-20**: cerebras-llama promovido a Default analítico (100% éxito en 22 pruebas). gemini-flash pasa a Generador SQL principal. gemini-flash-lite = fallback universal.

**Restricción de nivel en bot Telegram:**
- **Nivel 1–5**: cerebras-llama ★, gemini-flash, gpt-oss-120b, deepseek-chat
- **Nivel 6–7**: + gemini-pro, claude-sonnet

**Fallback del router** (hardcodeado en `_enrutar()`):
`groq-llama → cerebras-llama → gemini-flash-lite → gemini-flash`

Las capacidades están en `ia_agentes.capacidades` (JSON). El servicio las consulta dinámicamente para elegir el agente correcto según la tarea — no hay hardcoding de slugs para capacidades específicas.

### Cómo obtener cada API key

**Google Gemini** (ya activo):
1. `aistudio.google.com/apikey` → Create API Key
2. Vincular billing en `console.cloud.google.com/billing`
3. Key empieza con `AIzaSy...`

> ⚠️ **Control de costos Gemini — IMPORTANTE**
> El "Límite de inversión mensual" de AI Studio está marcado como **Experimental** y NO es un freno real de facturación.
> Solo intenta bloquear nuevas llamadas pero permite excedentes y no cancela cargos ya generados.
> **El control real de gasto** se configura en Google Cloud Console → Facturación → **Presupuestos y alertas**:
> ahí se puede definir un tope que desactiva la facturación del proyecto al alcanzarlo.
> Costo esperado en uso normal (producción, sin QA intensivo): **< COP 10,000/mes**.

**Groq** (gratis, sin tarjeta):
1. `console.groq.com` → API Keys → Create API Key
2. Key empieza con `gsk_...`

**DeepSeek** (requiere $5 de recarga):
1. `platform.deepseek.com` → API Keys → Create Key
2. Key empieza con `sk-...`

**Anthropic Claude** (requiere $5 de recarga):
1. `console.anthropic.com` → API Keys → Create Key
2. Key empieza con `sk-ant-...`

### Formato de payload por proveedor

**Google (Gemini)**:
```json
{
  "contents": [{"role": "user", "parts": [{"text": "Hola"}]}],
  "systemInstruction": {"parts": [{"text": "Eres Lara..."}]},
  "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}
}
```
Diferencia OpenAI: role `"assistant"` → `"model"`, system va en `systemInstruction`.

**OpenAI-compat (Groq / DeepSeek)**:
```json
{
  "model": "llama-3.1-8b-instant",
  "messages": [
    {"role": "system", "content": "Eres un enrutador..."},
    {"role": "user", "content": "¿Cuánto vendimos?"}
  ],
  "temperature": 0.1
}
```

**Anthropic**:
```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 4096,
  "system": "Eres Lara...",
  "messages": [{"role": "user", "content": "¿Cuánto vendimos?"}]
}
```
Header requerido: `anthropic-version: 2023-06-01`

---

## 7. Arquitectura de dos capas — mecánica vs analítica {#dos-capas}

### Concepto

Los agentes se dividen en dos roles con propósitos distintos:

**CAPA MECÁNICA** (siempre automática, usuario no la ve ni configura):
- Enrutador: clasifica la pregunta → Groq Llama (gratis, ~100ms)
- Generación SQL: produce el SELECT → Gemini Flash (gratis, ~300ms)
- Retry SQL: si SQL falla, corrige → Gemini Flash (gratis)
- Retry vacío: si resultado = 0 filas, pide fecha máxima y reformula → Gemini Flash

**CAPA ANALÍTICA** (el agente que el usuario elige / que define el tema):
- Interpreta los datos y redacta la respuesta final
- El agente usado depende de la cadena de prioridad: `param_agente → conv.agente_activo → tema.agente_preferido → tipo.agente_preferido → gemini-flash-lite`
- Para temas finanzas/comercial/estrategia → `gemini-pro` (por tema)
- Para temas general/marketing/administracion/produccion → `gemini-flash-lite` (por tema)
- Usuario puede forzar un agente específico desde el bot con `/agente`

### Configuración en BD

```sql
-- Ver configuración actual
SELECT slug, agente_preferido, agente_sql
FROM ia_tipos_consulta WHERE slug = 'analisis_datos';

-- agente_sql = capa mecánica (genera SQL)
-- agente_preferido = capa analítica (redacta respuesta) — PUEDE ser sobreescrito por ia_temas

-- Ver agente por tema
SELECT slug, agente_preferido FROM ia_temas ORDER BY id;
```

### Latencias reales medidas (2026-03-15)

```
FLUJO SIN SQL:
  enrutar       → Groq Llama       ~100–300ms  (gratis)
  redactar      → gemini-flash-lite   ~2–3s    (gratis)
  redactar      → gemini-pro          ~20–26s  (latencia base del modelo)
  redactar      → deepseek-chat       ~18s

FLUJO CON SQL:
  enrutar       → Groq Llama       ~100–300ms
  generar_sql   → gemini-flash      ~3–5s      (con 27K tokens DDL)
  ejecutar BD   → Hostinger SSH     ~200ms
  redactar      → gemini-pro        ~15s
  Total con pro: ~20–23s  |  Total con flash-lite: ~8–12s (estimado)
```

**⚠️ Nota crítica**: gemini-pro tiene ~20s de latencia independientemente del tamaño del prompt. 228 tokens y 27,625 tokens tardan lo mismo (~20s). Es la latencia base del modelo, no del volumen.

### Cambiar el agente SQL (capa mecánica)

```sql
UPDATE ia_tipos_consulta
SET agente_sql = 'gemini-flash'
WHERE slug = 'analisis_datos';
-- Reiniciar servicio después
```

---

## 8. Temas — routing por área de negocio {#temas}

### Qué son los temas

Los temas definen el **área de negocio** de la pregunta. El enrutador (Groq) detecta el tema automáticamente. El tema tiene dos efectos:

1. **Selecciona el agente analítico** (`agente_preferido` del tema sobreescribe al del tipo)
2. **Filtra el RAG** (solo se buscan fragmentos del mismo tema)

### 7 temas actuales para ori_sil_2

```sql
SELECT slug, nombre, agente_preferido FROM ia_temas ORDER BY id;
```

| Tema | Agente preferido | Cuándo se activa |
|---|---|---|
| `comercial` | gemini-pro | Ventas, clientes, canales, facturas, remisiones, cotizaciones, consignación, devoluciones |
| `finanzas` | gemini-pro | Compras, costos, utilidades, márgenes, flujo de caja, cartera, cuentas por cobrar/pagar |
| `produccion` | gemini-flash-lite | Producción, materiales, costos de producción, artículos producidos |
| `administracion` | gemini-flash-lite | Gastos, RRHH, operaciones internas |
| `marketing` | gemini-flash-lite | Campañas, análisis de mercado, tipoDeMarketing, contactos CRM |
| `estrategia` | gemini-pro | Metas, planes, KPIs estratégicos |
| `general` | gemini-flash-lite | Preguntas generales, sin tema específico |

### schema_tablas por tema — tablas que recibe el agente SQL (DDL)

El campo `schema_tablas` en `ia_temas` controla qué tablas se le pasan al agente SQL (DDL de Hostinger). Es crítico que esté correcto — si falta una tabla, el modelo no puede consultarla.

**Estado actual (2026-03-15) — actualizado y corregido:**

| Tema | Tablas (schema_tablas) |
|---|---|
| `comercial` | resumen_ventas_facturas_*, resumen_ventas_remisiones_*, zeffi_facturas_venta_*, zeffi_remisiones_venta_*, zeffi_ordenes_venta_*, zeffi_cotizaciones_ventas_*, zeffi_notas_credito_venta_*, zeffi_devoluciones_venta_*, zeffi_clientes, zeffi_inventario, catalogo_articulos, crm_contactos |
| `finanzas` | zeffi_facturas_venta_*, zeffi_facturas_compra_*, zeffi_ordenes_compra_*, zeffi_remisiones_compra_*, zeffi_proveedores, zeffi_cuentas_por_cobrar, zeffi_cuentas_por_pagar, zeffi_comprobantes_ingreso_*, zeffi_notas_credito_venta_*, resumen_ventas_facturas_mes |
| `produccion` | zeffi_produccion_encabezados, zeffi_articulos_producidos, zeffi_materiales, zeffi_costos_produccion, zeffi_otros_costos, zeffi_inventario, catalogo_articulos |
| `estrategia` | resumen_ventas_facturas_mes, resumen_ventas_remisiones_mes |
| `general` | resumen_ventas_facturas_mes, resumen_ventas_remisiones_mes, zeffi_facturas_venta_encabezados, zeffi_clientes, zeffi_inventario, crm_contactos |
| `marketing` | crm_contactos, zeffi_clientes |
| `administracion` | [] (sin tablas — usa RAG) |

**⚠️ Error histórico corregido (2026-03-15):** `produccion` tenía `zeffi_articulos` (tabla inexistente) en lugar de las tablas de producción reales. Esto causaba que el DDL inyectado estuviera vacío y el modelo no pudiera generar SQL de producción.

**Cómo actualizar schema_tablas:**
```python
import pymysql, json
conn = pymysql.connect(host='localhost', user='osadmin', password='Epist2487.', db='ia_service_os')
cur = conn.cursor()
tablas = ["tabla1", "tabla2", "tabla3"]
cur.execute("UPDATE ia_temas SET schema_tablas=%s WHERE slug='produccion'", [json.dumps(tablas)])
conn.commit()
conn.close()
# Reiniciar el servicio para que el caché de DDL (1h) se invalide
# sudo systemctl restart ia-service.service
```

### Cadena de prioridad del agente

```
1. agente especificado en la llamada (param)
2. agente_activo de la conversación (usuario eligió con /agente)
3. ia_temas.agente_preferido (si el tema tiene uno)
4. ia_tipos_consulta.agente_preferido (fallback del tipo)
5. 'gemini-flash-lite' (hardcoded fallback)
```

### Gestión de temas desde ia-admin

Los temas se gestionan en `ia.oscomunidad.com` → Contextos → Temas (nivel mínimo 5). Desde ahí se puede:
- Cargar documentos RAG por tema
- Editar el system prompt específico del tema
- Vincular una conexión BD y schema de tablas para el tema

---

## 9. Sistema RAG — documentos de negocio {#rag}

### Qué es el RAG aquí

RAG (Retrieval-Augmented Generation) permite que la IA responda preguntas de estrategia, comercial y administración usando documentos internos de la empresa, no solo datos de la BD.

Cuando el enrutador clasifica la pregunta como `conversacion` (no SQL), el sistema busca fragmentos relevantes en `ia_rag_fragmentos` y los inyecta en la CAPA 2 del system prompt.

### Documentos cargados (estado 2026-03-14)

| Tema | Documento | Fragmentos |
|---|---|---|
| `estrategia` | Plan Estratégico Comercial 12 Meses | 5 |
| `comercial` | Presentación y Plan de Acople de Ventas | 23 |
| `marketing` | Guión de Ventas Presentación OS | 7 |
| `administracion` | Informe Sesión Estratégica Stack Tecnológico | 3 |

### Cómo cargar un documento nuevo

1. Extraer el texto del PDF/DOCX (pdfminer, python-docx, etc.)
2. Dividir en fragmentos de ~500 palabras con solapamiento
3. Insertar en `ia_rag_documentos` + `ia_rag_fragmentos`

```python
# Estructura mínima
doc = {
    'nombre': 'Plan de Marketing Q2 2026',
    'tema': 'marketing',          # estrategia | comercial | marketing | administracion
    'empresa': 'ori_sil_2',
    'contenido_completo': texto_completo,
    'activo': 1
}
# INSERT en ia_rag_documentos, luego fragmentar y INSERT en ia_rag_fragmentos
```

### Cómo funciona la búsqueda RAG

```python
# En servicio.py — función _buscar_rag()
# Busca por FULLTEXT MATCH en ia_rag_fragmentos
# Filtra por empresa y, si el enrutador detectó tema, también por tema
# Devuelve top 3 fragmentos más relevantes
SELECT f.contenido, d.nombre, f.tema
FROM ia_rag_fragmentos f
JOIN ia_rag_documentos d ON d.id = f.documento_id
WHERE d.empresa = %s AND d.activo = 1
  AND MATCH(f.contenido) AGAINST (%s IN BOOLEAN MODE)
ORDER BY relevance DESC LIMIT 3
```

### El enrutador detecta el tema

El enrutador (Groq Llama) devuelve también un campo `tema` en el JSON:
```json
{"tipo": "conversacion", "tema": "estrategia", "requiere_sql": false}
```
Este tema se usa para filtrar el RAG por categoría de documento.

---

## 10. Embeddings — búsqueda semántica de ejemplos SQL {#embeddings}

### El problema que resuelve

La tabla `ia_ejemplos_sql` guarda pares pregunta→SQL aprendidos. Antes se buscaban por LIKE (palabras clave). Si el usuario decía "¿qué producto arrasa?" no encontraba el ejemplo de "top productos del mes" aunque son la misma consulta.

Con embeddings, se calcula la distancia semántica entre preguntas en un espacio vectorial de 768 dimensiones — preguntas similares quedan cerca aunque usen palabras distintas.

### Implementación

**Modelo**: Google `text-embedding-004` (768 dims, gratis, ilimitado).
**Código**: `scripts/ia_service/embeddings.py`

```python
# Funciones principales
generar_embedding(texto)           # Llama API Google, devuelve lista 768 floats
guardar_embedding(ejemplo_id, txt) # Genera y guarda en ia_ejemplos_sql.embedding
buscar_ejemplos_semanticos(empresa, pregunta, n=3)  # Cosine similarity
migrar_embeddings_faltantes(empresa)  # Retroalimentar ejemplos sin embedding
```

### Flujo de uso

**Al guardar un ejemplo nuevo** (cuando el modelo genera un buen SQL):
```python
# En _guardar_ejemplo_sql() — el embedding se genera en background thread
threading.Thread(target=guardar_embedding, args=(id_ejemplo, pregunta)).start()
```

**Al buscar ejemplos para el prompt**:
```python
# _obtener_ejemplos_dinamicos() — primero prueba semántico, fallback a LIKE
ejemplos = buscar_ejemplos_semanticos(empresa, pregunta, n=3)
if not ejemplos:
    ejemplos = buscar_por_keywords(empresa, pregunta)  # LIKE fallback
```

### Columna en BD

```sql
ALTER TABLE ia_ejemplos_sql ADD COLUMN embedding LONGTEXT NULL;
-- El embedding se guarda como JSON: "[0.123, -0.456, ...]"
-- Con 500 ejemplos máximo en memoria — suficiente para nuestro volumen
```

---

## 11. Retry inteligente — resultado vacío y columnas reales {#retry}

### Retry por resultado vacío

Antes, si el SQL ejecutaba sin error pero devolvía 0 filas, la IA respondía "no hay datos". Muchas veces era un filtro de fecha demasiado estricto o un estado mal escrito, no que los datos no existan.

```
SQL ejecuta → 0 filas
  → _obtener_fecha_maxima(sql) detecta las tablas usadas
  → Consulta MAX(fecha_de_creacion) de esas tablas en Hostinger
  → Reenvía al LLM: "El SQL devolvió 0 filas.
     El dato más reciente en la tabla es [fecha].
     Verifica si el filtro es correcto."
  → Máximo 2 reintentos (total: 1 original + 2 correcciones)
  → Si sigue vacío al 3er intento: "No encontré datos para ese criterio"
```

Casos resueltos: fechas futuras por error del modelo, filtros de estado mal escritos, lunes sin ventas.

### Retry por columnas SQL inválidas — con columnas reales (2026-03-18)

**El problema anterior**: cuando el modelo generaba SQL con un nombre de columna incorrecto (ej. `d.descripcion_articulo` que no existe), el retry le enviaba el error y le pedía "revisa los nombres de columna en el esquema". El modelo frecuentemente repetía el mismo error porque tenía que adivinar.

**Solución**: `_obtener_columnas_reales(sql)` usa **sqlglot** para extraer las tablas del SQL fallido, luego hace **DESCRIBE** en Hostinger para obtener las columnas reales, e inyecta esa información concreta en el prompt de retry.

```python
# servicio.py — en el paso 'ejecutar', si SQL falla:
columnas_reales = _obtener_columnas_reales(sql_generado)
# devuelve: "Columnas REALES de las tablas usadas:
#   zeffi_facturas_venta_detalles: _pk, sucursal, cantidad, precio_unitario, ...
#   zeffi_facturas_venta_encabezados: _pk, numero_factura, id_cliente, ..."
prompt_retry = (
    f"El SQL falló: {error_sql}\n\n"
    f"{columnas_reales}"
    "Genera un SQL corregido usando SOLO las columnas listadas."
)
```

El modelo tiene información concreta en el 2° intento y lo corrige correctamente.

**Impacto en velocidad**: el retry de error (`_obtener_columnas_reales`) solo ocurre cuando el SQL falla. Agrega 1 query DESCRIBE local (~5ms) + 1 LLM call adicional. En consultas normales sin error: sin cambio.

---

## 12. Enrutador y requiere_sql {#enrutador}

### Qué hace el enrutador

El enrutador es la PRIMERA llamada en cada consulta. Usa Groq Llama (gratis) para clasificar la pregunta en ~100–300ms, antes de hacer ninguna otra llamada.

El enrutador devuelve un JSON:
```json
{
  "tipo": "analisis_datos",
  "tema": null,
  "requiere_sql": true
}
```

### El campo requiere_sql

Este campo es la optimización más importante del enrutador:

- `requiere_sql: true` → flujo SQL completo (hasta 4 llamadas LLM)
- `requiere_sql: false` → usa caché SQL real si existe, o responde con RAG/contexto

**PRINCIPIO FUNDAMENTAL del router (2026-03-18 — reescrito):**

> ¿La respuesta REQUIERE consultar registros de la BD para ser correcta?
> - **SÍ** → `analisis_datos` con `requiere_sql: true`
> - **NO** → `conversacion` (responde con conocimiento general del negocio o contexto previo)

El router NO usa listas de palabras clave para clasificar. Razona por principio. Si hay cualquier filtro nuevo (fecha, producto, cliente distinto) → `requiere_sql: true`. Solo cuando la respuesta es un seguimiento directo de datos YA mostrados ("¿y el margen de eso?", "¿cuál es el mayor?") → puede ser `requiere_sql: false`.

**Caché SQL para seguimientos (ver Sección 14):** cuando `requiere_sql: false`, el sistema inyecta en el router el resumen del último resultado SQL (columnas, número de filas, muestra de 3 filas). El router puede razonar si la pregunta puede responderse con esos datos o necesita una consulta nueva.

**Ejemplos de requiere_sql: false (solo si hay caché disponible):**
- "¿Y cuál fue el segundo?" (después de haber pedido el top)
- "¿Cuál tiene el mayor margen?" (referencia a datos ya mostrados)

**Ejemplos de requiere_sql: true:**
- "¿Cuánto vendimos ayer?" (necesita datos reales de la BD)
- "Top 5 productos del mes" (necesita consultar facturas)
- "Dame las ventas de frutos secos" (aunque se habló de ventas antes — filtro nuevo)

### Flujo completo con tiempos medidos

**CON SQL** (`requiere_sql: true`) — medición real 2026-03-15:

```
enrutar     Groq Llama        ~100–300ms   clasifica tipo/tema/requiere_sql
generar_sql Gemini Flash       ~3–5s       genera SQL con 27K tokens (DDL completo)
ejecutar    BD Hostinger       ~200ms      [verificación 1] corre SELECT
             ↳ si error SQL   +3–5s       agente corrige → [verificación 2]
             ↳ si vacío       +3–5s c/u   agente reformula → [verificación 2 y 3]
redactar    agente analítico   ~15–20s     interpreta datos y redacta

TOTAL (sin reintentos, gemini-pro):  ~20–23s
TOTAL (sin reintentos, flash-lite):  ~8–12s  (estimado)
```

**SIN SQL** (`requiere_sql: false`) — medición real 2026-03-15:

```
enrutar     Groq Llama        ~100–300ms   clasifica tipo/tema
redactar    agente analítico   varía       responde con RAG + contexto

TOTAL con gemini-flash-lite:  ~2.2–3.1s   (medido: log 232=2.5s, 228=2.2s, 227=3.1s)
TOTAL con gemini-pro:         ~20–26s     (medido: log 234=21s, 231=26s — mismo tiempo que con SQL)
TOTAL con deepseek-chat:      ~18s        (medido: log 229=18s)
```

### Observación crítica de latencia: gemini-pro

**gemini-pro tiene ~20s de latencia base independientemente del tamaño del prompt.**

Medición: 228 tokens entrada → 21s | 27,625 tokens entrada → 20s. El tamaño no es el factor dominante — es la latencia inherente del modelo (tiempo de "pensamiento" + red).

Implicación práctica: para preguntas conversacionales (no-SQL) en temas analíticos como `finanzas`, `comercial` o `estrategia` donde el tema tiene `agente_preferido = gemini-pro`, la latencia es ~20s aunque la pregunta sea simple ("explícame un margen bruto"). El sistema usa gemini-pro porque el tema lo indica, pero no agrega valor analítico sobre flash-lite para preguntas conceptuales.

### El enrutador usa contexto completo de la conversación (2026-03-15)

**Cambio crítico**: el enrutador NO analiza solo la pregunta actual. Recibe el historial completo:

```python
# En servicio.py — _enrutar()
historial_ctx = contexto.obtener_mensajes_recientes_formateados(conv)
contexto_enrutador = (f'Resumen de la conversación:\n{resumen_anterior}\n\n{historial_ctx}'
                      if resumen_anterior else historial_ctx)
tipo_enrutado, tema_enrutado, requiere_sql = _enrutar(pregunta, empresa, contexto_enrutador)
```

Esto permite que:
- "¿Y el mes pasado?" → entiende que habla de ventas (porque el resumen dice que se habló de ventas)
- "¿Cuánto compramos?" → asigna tema `finanzas` aunque el historial sea de ventas
- "Detalla eso por canal" → sabe a qué se refiere "eso" gracias al contexto

### Configuración del enrutador en BD

```sql
-- Ver system prompt del enrutador
SELECT system_prompt FROM ia_tipos_consulta WHERE slug = 'enrutamiento';

-- Ver agente del enrutador
SELECT agente_preferido FROM ia_tipos_consulta WHERE slug = 'enrutamiento';
-- groq-llama (enrutador — NUNCA responde como agente final)
```

**System prompt del enrutador** (2026-03-15) — completamente reescrito para cubrir TODOS los módulos:
- ventas: facturas, remisiones, top productos, canales
- compras: órdenes de compra, facturas de compra, proveedores
- producción: lotes producidos, materiales gastados, tiempo de producción
- inventario: stock, costos actuales, catalogo_articulos
- remisiones: mercancía entregada sin facturar (≠ ventas definitivas)
- cotizaciones / pedidos pendientes
- consignación: órdenes de venta vigentes
- cartera: cuentas por cobrar, cuentas por pagar
- devoluciones/notas crédito
- comparaciones entre períodos
- clientes/productos (análisis de comportamiento)
- estrategia/planes (conversacion, no SQL)

**Regla del enrutador**: "En caso de duda → `analisis_datos`" — mejor hacer un SQL innecesario que ignorar un dato real.

### Regla arquitectural: groq-llama es SOLO enrutador

`groq-llama` clasifica la pregunta. **Nunca** aparece como agente final (`redactar`). El agente final siempre es el agente analítico seleccionado por el usuario (o el preferido del tema/tipo).

Estado en BD (2026-03-15):
- `ia_temas.agente_preferido` para `finanzas`, `comercial`, `estrategia` → `gemini-pro`
- `ia_temas.agente_preferido` para `general`, `marketing`, `administracion`, `produccion` → `gemini-flash-lite`
- `ia_tipos_consulta.agente_preferido` para `conversacion` → `gemini-flash-lite`

### Detección pre-router de búsqueda web (2026-03-18)

Antes de llamar al router, `consultar()` detecta si el usuario pide **explícitamente** buscar en internet. Si lo detecta, fuerza `tipo='busqueda_web'` sin pasar por el router (que a veces lo clasificaba como conversación).

```python
# Frases que activan la detección pre-router:
_intento_internet = [
    'busca en internet', 'buscar en internet', 'consulta en internet',
    'consultes en internet', 'búscalo en internet', 'busca en la web',
    'consulta en la web', 'busca en google', 'googlealo', 'búscalo online', ...
]
```

**Principio**: no es una lista de temas (no "busca TRM", "busca precio bitcoin"). Es detección de INTENCIÓN explícita del usuario de salir a internet. El sistema es autónomo — decide por principio qué buscar.

### Distinción crítica: analisis_datos vs conversacion

El sistema distingue DOS tipos principales:
- `analisis_datos`: el dato proviene de la BD histórica de Effi (ventas, compras, inventario...)
- `conversacion`: el dato proviene de documentos de estrategia/planes/marketing (RAG)

Si el enrutador confunde los dos → o se hace una consulta SQL innecesaria, o se responde con RAG cuando debería consultar la BD. Mantener el system prompt del enrutador claro en esta distinción.

---

## 13. Catálogo de tablas {#catalogo}

### Dónde vive el catálogo

El catálogo de tablas tiene **dos representaciones**:

1. **`.agent/CATALOGO_TABLAS.md`** — fuente de verdad legible por humanos. Describe cada tabla con su propósito de negocio, campos clave y gotchas.

2. **`ia_tipos_consulta.system_prompt` (slug=`analisis_datos`)** — versión XML inyectada al LLM:
   - `<tablas_disponibles>` — catálogo compacto: nombre tabla + descripción de negocio
   - `<diccionario_campos>` — campos clave de las tablas principales con su semántica

El LLM SOLO puede usar lo que está en el system_prompt. Si una tabla no está documentada ahí, el modelo no sabrá qué significa ni cuándo usarla.

### Cómo actualizar el catálogo (flujo periódico)

Cuando se agregan tablas nuevas a Effi o cambian los campos:

1. **Actualizar CATALOGO_TABLAS.md** con la descripción de negocio de la nueva tabla
2. **Actualizar el system_prompt de analisis_datos**:
   ```bash
   # Opción A: via script (si existe actualizar_system_prompt.py)
   python3 scripts/ia_service/actualizar_system_prompt.py

   # Opción B: directo en BD (si el script no cubre el cambio)
   python3 -c "
   import pymysql
   conn = pymysql.connect(host='localhost', user='osadmin', password='Epist2487.', db='ia_service_os')
   cur = conn.cursor()
   cur.execute(\"SELECT system_prompt FROM ia_tipos_consulta WHERE slug='analisis_datos'\")
   prompt = cur.fetchone()[0]
   # Editar prompt (agregar tabla/campo al XML)
   new_prompt = prompt.replace('...', '...')
   cur.execute(\"UPDATE ia_tipos_consulta SET system_prompt=%s WHERE slug='analisis_datos'\", [new_prompt])
   conn.commit()
   conn.close()
   "
   ```
3. **Reiniciar el servicio** para que aplique el nuevo prompt:
   ```bash
   sudo systemctl restart ia-service.service
   ```

### Tablas documentadas en el system_prompt (estado 2026-03-15 — v2.3 — 53 tablas completas)

**`ia_tipos_consulta.system_prompt` tiene `MEDIUMTEXT` (ampliado de TEXT). Tamaño: ~64K chars.**

**VENTAS FACTURADAS (6):** zeffi_facturas_venta_encabezados, zeffi_facturas_venta_detalle, zeffi_notas_credito_venta_encabezados, zeffi_notas_credito_venta_detalle, zeffi_devoluciones_venta_encabezados, zeffi_devoluciones_venta_detalle

**REMISIONES (4):** zeffi_remisiones_venta_encabezados, zeffi_remisiones_venta_detalle, zeffi_cotizaciones_ventas_encabezados, zeffi_cotizaciones_ventas_detalle

**ÓRDENES / CONSIGNACIÓN (2):** zeffi_ordenes_venta_encabezados, zeffi_ordenes_venta_detalle

**RESÚMENES PRECALCULADOS (8):** resumen_ventas_facturas_mes, resumen_ventas_facturas_producto_mes, resumen_ventas_facturas_cliente_mes, resumen_ventas_facturas_canal_mes, resumen_ventas_remisiones_mes, resumen_ventas_remisiones_producto_mes, resumen_ventas_remisiones_cliente_mes, resumen_ventas_remisiones_canal_mes

**COMPRAS (7):** zeffi_facturas_compra_encabezados, zeffi_facturas_compra_detalle, zeffi_ordenes_compra_encabezados, zeffi_ordenes_compra_detalle, zeffi_remisiones_compra_encabezados, zeffi_remisiones_compra_detalle, zeffi_proveedores

**PRODUCCIÓN (6):** zeffi_produccion_encabezados, zeffi_articulos_producidos, zeffi_materiales, zeffi_costos_produccion, zeffi_otros_costos, zeffi_cambios_estado

**FINANCIERO (5):** zeffi_cuentas_por_cobrar, zeffi_cuentas_por_pagar, zeffi_comprobantes_ingreso_encabezados, zeffi_comprobantes_ingreso_detalle, zeffi_tipos_egresos

**CLIENTES Y PRODUCTOS (4):** zeffi_clientes, zeffi_inventario, catalogo_articulos, zeffi_categorias_articulos

**INVENTARIO DETALLADO POR BODEGA (1):** zeffi_guias_transporte

**CRM / MARKETING (1):** crm_contactos

**OPERACIONES DE INVENTARIO (3):** zeffi_ajustes_inventario, zeffi_traslados_inventario, zeffi_trazabilidad

**MAESTROS / CATÁLOGOS (5):** zeffi_empleados, zeffi_tarifas_precios, zeffi_tipos_marketing, zeffi_bodegas, codigos_ciudades_dane

**Total: 52 tablas de negocio + sys_menu (excluida — tabla interna ERP).**

### Tablas más usadas — resumen rápido

| Tabla | Cuándo usarla |
|---|---|
| `resumen_ventas_facturas_mes` | Resumen mensual global — SIEMPRE preferir para análisis por mes |
| `zeffi_facturas_venta_encabezados` | Ventas del día/semana, análisis con filtros específicos |
| `zeffi_facturas_venta_detalle` | Análisis por producto/referencia/categoría |
| `zeffi_remisiones_venta_encabezados` | Mercancía entregada sin facturar |
| `zeffi_ordenes_venta_encabezados` | Consignación activa (vigencia='Vigente') |
| `zeffi_clientes` | Datos de un cliente específico |
| `zeffi_inventario` | Stock disponible, precios, costos actuales |
| `catalogo_articulos` | Grupo de producto de un artículo |
| `zeffi_notas_credito_venta_encabezados` | Devoluciones |

### Gotchas técnicos críticos de las tablas

```
1. Todos los campos numéricos en zeffi_* son TEXT → usar CAST(campo AS DECIMAL(15,2))
2. fecha_de_creacion es TEXT "YYYY-MM-DD HH:MM:SS" → usar DATE() para filtrar
3. id_cliente en facturas tiene prefijo: "CC 74084937" → JOIN usa SUBSTRING_INDEX(id_cliente,' ',-1)
4. precio_neto_total en detalle INCLUYE IVA → para sin IVA: precio_bruto_total - descuento_total
5. zeffi_clientes tiene NITs duplicados → siempre deduplicar con GROUP BY en JOINs
6. Consignación activa: SOLO filtrar por vigencia='Vigente' (no por estado_facturacion)
7. Tablas resumen_ventas_* usan campo mes en formato "YYYY-MM", no fechas completas
```

---

## 14. Conversaciones — contexto vivo {#conversaciones}

### Cómo funciona el contexto

El sistema mantiene el hilo de la conversación en `ia_conversaciones` (una fila por usuario+canal).

```
Mensaje 1: "¿Cuánto vendimos ayer?"
  → respuesta con datos de ayer

Mensaje 2: "¿Y el día anterior?"
  → el sistema sabe que hablas de ventas gracias al contexto
  → genera SQL para anteayer sin necesidad de que el usuario especifique "ventas"
```

### Estructura del contexto

| Campo | Descripción |
|---|---|
| `resumen` | Resumen comprimido de toda la conversación (máx 600 palabras) |
| `mensajes_recientes` | JSON — últimos 10 mensajes literales (pregunta + respuesta) |

El resumen se actualiza automáticamente después de cada respuesta.

### Quién genera el resumen — arquitectura (2026-03-15)

**Cambio crítico**: el resumen ya NO lo genera el agente principal (Gemini Pro, Claude, etc.). Lo genera **Groq Llama** en una llamada separada asíncrona después de entregar la respuesta al usuario.

```
Respuesta entregada → _generar_resumen_groq() [llamada separada, no bloquea]
  → Groq Llama (gratis, rápido) genera resumen ≤600 palabras
  → se guarda en ia_conversaciones.resumen
```

**Por qué importa**: antes, el agente principal recibía `_PROMPT_RESUMEN` — una instrucción de generar hasta 1,000 palabras de resumen DENTRO de su respuesta. Esto causaba:
- DeepSeek: +1,783 tokens de resumen en cada respuesta → latencia de 80+ segundos
- Gemini Pro: +1,000 palabras de overhead por consulta

Ahora el agente principal solo redacta la respuesta al usuario. Groq genera el resumen en background.

**Código relevante en servicio.py:**
```python
def _generar_resumen_groq(resumen_anterior: str, pregunta: str, respuesta: str) -> str | None:
    # Usa groq-llama, gemma-router o gemini-flash-lite (lo que esté disponible)
    # Genera resumen máx 600 palabras con: datos numéricos, períodos, conclusiones
    # Retorna None si ningún agente rápido está disponible
    ...
```

### Caché SQL para seguimientos inteligentes (2026-03-18)

Cada vez que se ejecuta un SQL exitoso, el resultado se guarda en `ia_conversaciones.metadata`:

```python
# contexto.py
guardar_cache_sql(conversacion_id, pregunta, columnas, datos)
# guarda: {pregunta_origen, columnas, datos[:500 filas], n_filas}
```

El router recibe un **resumen del caché** en su contexto (pregunta origen, columnas, n° filas, 3 filas de muestra). Con eso puede decidir inteligentemente si `requiere_sql: false` (seguimiento de los mismos datos) o `requiere_sql: true` (filtro nuevo).

Cuando el router dice `requiere_sql: false`:
- Si hay caché con datos reales → usa esos datos (nunca inventa)
- Si no hay caché → fuerza `requiere_sql: true` (no permite respuesta sin datos)

El caché se limpia automáticamente con `/limpiar`.

```python
# Funciones en contexto.py:
guardar_cache_sql(conversacion_id, pregunta, columnas, datos)
leer_cache_sql(conv)      # retorna dict o None
# El campo ia_conversaciones.metadata (JSON) almacena el caché
```

### Limpiar contexto de un usuario

```bash
# Desde el bot: /limpiar
# O directamente en BD:
mysql --user=osadmin --password='Epist2487.' ia_service_os -e \
  "UPDATE ia_conversaciones SET resumen=NULL, mensajes_recientes='[]', metadata=NULL
   WHERE usuario_id='TELEGRAM_ID' AND canal='telegram';" 2>/dev/null
```

---

## 15. Bot de Telegram {#telegram}

### Dos bots — propósitos distintos

| Bot | Username | Uso | Token en .env |
|---|---|---|---|
| **OS IA Bot** | `@os_integraciones_bot` | Asistente conversacional IA — preguntas, análisis, fotos | `TELEGRAM_BOT_TOKEN` |
| **OS Notificaciones** | `@os_notificaciones_sys_bot` | Alertas automáticas del pipeline (errores, resúmenes) | `TELEGRAM_NOTIF_BOT_TOKEN` |

El orquestador (`orquestador.py`) usa `TELEGRAM_NOTIF_BOT_TOKEN` para notificaciones. El bot de IA usa `TELEGRAM_BOT_TOKEN`.

### Autenticación del bot — por número de teléfono

**Todo mensaje es rechazado si el usuario no está autorizado.**

Flujo de primer acceso:
1. Usuario escribe al bot → bot detecta que no está en `bot_sesiones.autorizado=1`
2. Verifica si su `telegram_id` ya está en `ia_usuarios` (si admin lo añadió manualmente)
3. Si no → muestra botón "Compartir mi número"
4. Usuario comparte → bot verifica contra `ia_usuarios.telefono`
5. Si el número está → acceso concedido, se guarda `telegram_id` + `nivel` en `bot_sesiones`
6. Si no → "Tu número no está registrado, contacta a Santiago"

Usuarios registrados: ver tabla en sección 16.

### Archivos del bot de IA

```
scripts/telegram_bot/
  bot.py      — handlers + _verificar_acceso() + handle_contacto()
  api_ia.py   — cliente del ia_service (POST /ia/consultar)
  db.py       — sesiones + auth (verificar_por_telefono, vincular_telegram_id)
  tabla.py    — procesar tablas de datos para el bot
  teclado.py  — teclados reply e inline (inline_ajustes filtra por nivel)
```

### Mensajes de voz — mismo flujo que texto (2026-03-18)

**El bot acepta mensajes de voz** y los procesa con el mismo flujo que texto, incluyendo SQL, búsqueda web y modo aprendizaje.

Flujo:
```
Usuario envía audio
  → handle_voz() transcribe con Whisper (OpenAI API vía Groq)
  → delega a handle_mensaje(texto_override=texto_transcrito)
  → flujo idéntico a mensaje de texto (enrutar → SQL/web/chat → responder)
```

**Gotcha crítico (python-telegram-bot v20)**: los objetos `Message` son inmutables. Es imposible hacer `update.message.text = texto`. Por eso se usa `texto_override` — un parámetro adicional que `handle_mensaje` recibe y usa en lugar de `update.message.text`. Esta solución garantiza que audio y texto siguen exactamente el mismo código.

```python
# bot.py — handle_voz()
async def handle_voz(update, context):
    texto = transcribir_audio(...)  # Whisper via Groq
    await handle_mensaje(update, context, texto_override=texto)

# bot.py — handle_mensaje()
async def handle_mensaje(update, context, texto_override=None):
    texto = texto_override or update.message.text
    # ...resto del flujo idéntico para texto y audio
```

### Capacidad de visión — fotos y documentos

El bot acepta fotos directamente. Flujo completo:

```
Usuario manda foto (con o sin caption)
        ↓
[Visión — Gemini Flash] extrae texto estructurado de la imagen
        ↓
[Enrutador — Groq] decide si requiere SQL u otra acción
        ↓
[Flujo normal] genera SQL si aplica → ejecuta → redacta respuesta
```

- **Solo foto (sin caption)**: describe lo que vio y pregunta qué quiere hacer
- **Foto + caption**: extrae info y ejecuta la instrucción directamente
- **Imagen en blanco**: avisa sin intentar SQL
- Funciona con: capturas de Effi, remisiones en papel, conteos escritos, facturas, etiquetas

### Comandos del bot

| Comando | Acción |
|---|---|
| `/start` | Bienvenida, registra sesión |
| `/ayuda` | Muestra comandos disponibles |
| `/estado` | Muestra agente activo del usuario |
| `/agente` | Menú para cambiar el agente analítico |
| `/ventas` | Shortcut: "¿Cuánto hemos vendido hoy?" |
| `/mes` | Shortcut: "¿Cuánto llevamos vendido este mes vs el mes anterior?" |
| `/limpiar` | Limpia historial de conversación |

### Variables de entorno necesarias

En `scripts/.env`:
```
TELEGRAM_BOT_TOKEN=...          # Bot de IA conversacional
TELEGRAM_CHAT_ID=...            # Chat ID de Santi
TELEGRAM_NOTIF_BOT_TOKEN=...    # Bot de notificaciones del pipeline
TELEGRAM_NOTIF_CHAT_ID=...      # Chat ID destino de alertas
```

### Tabla con datos grandes → mini app web

Si la respuesta tiene una tabla con muchas filas, el bot muestra un botón inline que lleva a:
```
https://menu.oscomunidad.com/bot/tabla?token=TOKEN_TEMPORAL
```

---

## 16. Sistema de usuarios, niveles y configuración {#usuarios}

### Niveles de acceso (1–7)

El nivel controla qué agentes puede usar el usuario en el bot Telegram y qué ve en ia-admin.

| Nivel | Acceso ia-admin | Agentes en bot Telegram |
|---|---|---|
| 1 | Dashboard, Playground | gemini-flash, gpt-oss-120b, deepseek-chat |
| 3 | + Logs | ídem |
| 5 | + Contextos RAG | ídem (Jen tiene nivel 5) |
| 6 | + Agentes, Tipos | + gemini-pro, claude-sonnet |
| 7 | Todo — Usuarios, Config, Conexiones | Todos incluyendo deepseek-reasoner |

(Umbrales configurables en `ia_config.acceso_*`)

### Tabla ia_usuarios — estructura y usuarios activos

```sql
-- Campos: email, nombre, rol, nivel, activo, telefono, telegram_id
SELECT email, nombre, nivel, telefono, telegram_id, activo FROM ia_usuarios;
```

| email | nombre | nivel | teléfono | rol |
|---|---|---|---|---|
| santiago@origensilvestre.com | Santiago Sierra | 7 | +573214550933 | admin |
| jen@origensilvestre.com | Jen | 5 | +572307085143 | viewer |

**Agregar nuevo usuario:**
```sql
INSERT INTO ia_usuarios (email, nombre, rol, nivel, activo, telefono)
VALUES ('nuevo@email.com', 'Nombre', 'viewer', 3, 1, '+57XXXXXXXXXX');
```
El `telegram_id` se llena automáticamente cuando el usuario hace su primer login en el bot.

**Agregar por telegram_id directamente (sin esperar login):**
```sql
UPDATE ia_usuarios SET telegram_id = 123456789 WHERE telefono = '+57XXXXXXXXXX';
```

### Rate limiting (sliding window in-memory)

Configurado en `ia_config`. Si el usuario supera el límite recibe error con `retry_after`:

```
rate_usuario_rps   = 1   (max 1 request/segundo)
rate_usuario_rpm   = 15  (max 15 requests/minuto)
rate_usuario_rp10s = 3   (max 3 requests en 10 segundos)
```

### Circuit breaker por agente — con fallback automático (2026-03-18)

Si un agente acumula `circuit_breaker_errores` (5) errores en `circuit_breaker_ventana_min` (10 min), se suspende. **El sistema NO bloquea al usuario — busca automáticamente otro agente disponible.**

`verificar_limites()` retorna la capa que bloqueó:
- **Capa 1** (presupuesto global agotado) → bloqueo total, no hay alternativa
- **Capa 2** (RPD del agente superado) → `_resolver_agente_disponible()` busca alternativa
- **Capa 3** (circuit breaker por errores) → `_resolver_agente_disponible()` busca alternativa

`_resolver_agente_disponible(nivel_usr, agente_bloqueado, empresa)`:
- Recorre `ia_agentes` por orden de prioridad (`orden ASC`)
- Respeta el nivel del usuario (no asigna gemini-pro a nivel 1-5)
- Verifica que cada candidato pase sus propios límites antes de asignarlo
- Si TODOS los agentes están suspendidos → error al usuario
- Notifica por Telegram del cambio automático

```python
# Ejemplo: gemini-flash bloqueado (capa 3), usuario nivel 5
# → busca alternativa: gemini-pro (nivel 6 — NO), gpt-oss-120b (nivel 1 — SÍ)
# → usa gpt-oss-120b transparentemente, usuario ni se entera
```

### Límite de costo diario

`limite_costo_dia_usd = 5.00` — si el gasto total del día supera $5 USD en todos los agentes, las consultas se rechazan. Configurar a 0 para desactivar el límite.

### Asignar nivel a un usuario

```sql
-- Cambiar nivel de un usuario existente
UPDATE ia_usuarios SET nivel = 7 WHERE email = 'usuario@origensilvestre.com';
```

### Actualizar parámetros de configuración

```sql
UPDATE ia_config SET valor = '10.00' WHERE clave = 'limite_costo_dia_usd';
```
Los cambios se aplican en la siguiente llamada (no requiere reinicio).

---

## 17. Multi-empresa {#multiempresa}

### Arquitectura multi-tenant

El servicio soporta múltiples empresas desde el mismo servidor. Cada empresa tiene su propio conjunto de:
- Agentes de conversación (contextos separados)
- Temas y documentos RAG
- Conexiones BD
- Configuración de acceso (la `ia_config` es global, pero los permisos por usuario son por empresa)

### Tablas involucradas

```sql
-- Empresas registradas
SELECT uid, nombre, siglas, estado FROM ia_empresas;
-- uid = 'ori_sil_2', nombre = 'Origen Silvestre', siglas = 'OS'

-- Usuarios por empresa
SELECT usuario_id, empresa_uid, rol FROM ia_usuarios_empresas;
-- rol: 'admin' o 'viewer'
```

### Flujo de autenticación (ia-admin)

1. Usuario abre `ia.oscomunidad.com` → redirige a Google OAuth
2. Google devuelve email → el backend verifica en `ia_usuarios_empresas`
3. Si tiene 1 empresa → JWT final directo con `empresa_activa`
4. Si tiene varias → pantalla de selección → JWT final con `empresa_activa`

**`empresa` NUNCA viene del cliente** — siempre inyectada desde JWT en middleware `requireAuth`. Imposible que un usuario acceda a datos de otra empresa.

### Campo empresa en todas las tablas

Todas las tablas de datos tienen campo `empresa` (excepto `ia_agentes` — configuración global compartida). Las queries siempre filtran por empresa.

```python
# En servicio.py — empresa viene del JWT o del param de la llamada
resultado = consultar(pregunta="...", empresa="ori_sil_2", ...)
```

### Empresa activa OS

`uid = 'ori_sil_2'` — Origen Silvestre. Santiago = admin (nivel 7). Jennifer = viewer.

---

## 17bis. Protocolo de aprendizaje — ia_logica_negocio {#aprendizaje}

### Qué es

La IA puede aprender lógica de negocio sobre la marcha. Cuando el agente detecta que explicó algo que vale la pena recordar, genera un bloque especial en su respuesta que el servicio interpreta y guarda automáticamente en `ia_logica_negocio`.

### Tabla ia_logica_negocio

```sql
SELECT id, concepto, keywords, siempre_presente, palabras, activo, creado_por
FROM ia_logica_negocio ORDER BY siempre_presente DESC, activo DESC;
```

| Columna | Descripción |
|---|---|
| `concepto` | Nombre del concepto aprendido (VARCHAR 100) |
| `explicacion` | Texto completo de la lógica (TEXT) |
| `keywords` | Palabras clave que activan este fragmento en el RAG (VARCHAR 500) |
| `siempre_presente` | 1 = se inyecta en TODAS las consultas, 0 = solo si coincide keyword |
| `palabras` | Conteo de palabras de la explicación (actualizado automáticamente) |
| `activo` | 1 = se usa, 0 = desactivado (depurador o manualmente) |
| `creado_por` | `'usuario-aprendizaje'`, `'depurador-auto'`, o email de quien lo creó |
| `empresa` | FK empresa (default `'ori_sil_2'`) |

**Estado actual (2026-03-17):** 1 fragmento activo "Lógica de negocio consolidada" (455 palabras, siempre_presente=1), 9 inactivos depurados.

### Cómo el agente aprende

El agente genera un bloque `[GUARDAR_NEGOCIO]` en su respuesta cuando detecta que explicó algo importante:

```
[GUARDAR_NEGOCIO]
concepto: Nombre del concepto
keywords: palabra1, palabra2, palabra3
explicacion: Explicación detallada de la lógica de negocio...
[/GUARDAR_NEGOCIO]
```

El servicio (`servicio.py._procesar_bloque_aprendizaje()`) detecta este bloque, lo extrae, guarda en `ia_logica_negocio`, y elimina el bloque de la respuesta que ve el usuario.

### Restricción crítica: solo en tipo conversacion (2026-03-18)

`_procesar_bloque_aprendizaje()` **solo se ejecuta cuando `tipo == 'conversacion'`**.

Antes se ejecutaba también en `analisis_datos` y `clasificacion`. Esto causaba que el agente guardara "lógica de negocio" falsa cuando respondía preguntas de datos (ej. guardó como lógica "el bot analiza ventas y genera SQL" — descripción del sistema, no del negocio).

```python
# servicio.py — paso 'redactar'
if tipo == 'conversacion':
    _procesar_bloque_aprendizaje(res['texto'], empresa)
# analisis_datos NUNCA guarda lógica de negocio desde respuestas de datos
```

El modo aprendizaje puro (`tipo == 'aprendizaje'`, paso `conversar`) sí puede guardar — ese es su propósito.

### Depurador automático

Cuando el total de palabras en `ia_logica_negocio` supera ~800, el servicio corre `_depurar_logica_negocio()` que:

1. Llama a un agente (fallback: groq → cerebras → gemini-flash-lite → gemini-flash)
2. Le pide consolidar todos los fragmentos en uno solo (~600 palabras)
3. Marca los fragmentos antiguos como `activo=0`
4. Inserta el consolidado con `creado_por='depurador-auto'`, `siempre_presente=1`
5. **Regla estricta:** nunca modifica cifras, porcentajes, nombres de campos ni tablas

### Admin UI

Los fragmentos se gestionan en ia-admin → **Lógica de negocio** (nivel 7):
- Ver todos los fragmentos con conteo de palabras
- Editar concepto, keywords, explicación
- Toggle siempre_presente / activo
- Crear o eliminar fragmentos manualmente

---

## 18. Cómo agregar / configurar un agente {#agregar-agente}

### Paso 1 — Insertar key en BD

```bash
# Ver estado actual
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT slug, activo, LENGTH(api_key)>0 AS tiene_key FROM ia_agentes;" 2>/dev/null

# Agregar key (ejemplo para Groq)
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='gsk_TU_KEY', activo=1 WHERE slug='groq-llama';" 2>/dev/null
```

### Paso 2 — Backup en .env

```bash
# Agregar a scripts/.env (no commiteado)
echo "GROQ_API_KEY=gsk_..." >> scripts/.env
```

### Paso 3 — Reiniciar servicio

```bash
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2)
sudo systemctl start ia-service.service
```

### Paso 4 — Verificar

```bash
curl -s http://localhost:5100/ia/agentes | python3 -m json.tool
```

### Crear un agente nuevo (no existe en BD)

```sql
INSERT INTO ia_agentes
  (slug, nombre, modelo_id, proveedor, api_key, activo, rate_limit_rpd, orden, nivel_minimo)
VALUES
  ('groq-llama-fast', 'Groq Llama Fast', 'llama-3.1-8b-instant',
   'openai', 'gsk_...', 1, 14400, 10, 1);
```

`proveedor` debe ser: `"google"`, `"openai"` (para Groq/DeepSeek), o `"anthropic"`.
La URL base del endpoint se configura en `proveedores/openai_compat.py` según el slug.

---

## 19. Monitoreo del consumo {#monitoreo}

### Logging completo de TODAS las llamadas a la API (2026-03-18)

**Problema anterior**: solo se logueaban las llamadas principales en `consultar()`. Las llamadas del router, generación de resúmenes y depurador eran invisibles — el costo interno era 4-12x menor que lo que Google realmente cobraba.

**Solución**: función `_log_aux()` loguea cada llamada auxiliar en `ia_logs` con el `tipo_consulta` correspondiente:

| `tipo_consulta` | Función que lo genera | Agente típico |
|---|---|---|
| `analisis_datos` | flujo principal `consultar()` | gemini-flash/pro |
| `conversacion` | flujo principal `consultar()` | gemini-flash-lite |
| `router` | `_enrutar()` — 1 call por consulta | groq-llama |
| `resumen` | `_generar_resumen_groq()` — 1 call por consulta | groq-llama |
| `depurador` | `_depurar_logica_negocio()` — ocasional | groq-llama |

Ahora el costo interno refleja la realidad. Para ver el costo real por tipo:

```sql
-- Consumo real completo (todos los tipos)
SELECT tipo_consulta, agente_slug, COUNT(*) AS llamadas,
       ROUND(SUM(costo_usd),4) AS costo_usd
FROM ia_logs
WHERE DATE(created_at) = CURDATE()
GROUP BY tipo_consulta, agente_slug ORDER BY costo_usd DESC;
```

### Llamada simple (utilitaria)

`POST /ia/simple` — llamada directa a un modelo sin pipeline completo. Para clasificación, extracción, sí/no, etc.

```bash
# Ejemplo: clasificar tarea en categoría
curl -s -X POST http://localhost:5100/ia/simple \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Despachar pedido a Muebles La 33",
    "contexto": "Clasificá esta tarea en una categoría.",
    "modelo": "groq-llama",
    "tipo_respuesta": "enum",
    "opciones": ["Ventas","Cartera","Pagos","Logistica"],
    "fallback": "cerebras-llama"
  }'
# → {"ok": true, "resultado": "Logistica", "latencia_ms": 600}
```

**Parámetros**: `prompt` (obligatorio), `contexto`, `modelo` (default: groq-llama), `tipo_respuesta` (texto|numero|json|enum|booleano), `opciones` (solo enum), `temperatura` (default: 0.2), `max_tokens` (default: 500), `fallback` (default: cerebras-llama).

**Código**: `servicio.py → llamada_simple()` usa `_cargar_agente()` + `_llamar_agente()`. Fallback automático si el principal falla.

### Endpoints del servicio

```bash
# Consumo de hoy
curl -s "http://localhost:5100/ia/consumo" | python3 -m json.tool

# Consumo de la semana
curl -s "http://localhost:5100/ia/consumo?periodo=semana" | python3 -m json.tool

# Histórico últimos 30 días
curl -s "http://localhost:5100/ia/consumo/historico" | python3 -m json.tool

# Solo para gemini-pro
curl -s "http://localhost:5100/ia/consumo?agente=gemini-pro" | python3 -m json.tool
```

### SQL directo

```bash
# Consumo hoy por agente
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT agente_slug, llamadas, tokens_total, ROUND(costo_usd,4) AS costo,
          ROUND(llamadas*100.0/a.rate_limit_rpd,1) AS pct_rpd
   FROM ia_consumo_diario c JOIN ia_agentes a ON a.slug=c.agente_slug
   WHERE fecha=CURDATE() ORDER BY llamadas DESC;" 2>/dev/null

# Errores recientes
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT created_at, agente_slug, tipo_consulta, error
   FROM ia_logs WHERE ok=0 ORDER BY created_at DESC LIMIT 10;" 2>/dev/null
```

### Señales de alarma

- `pct_rpd > 90%` para gemini-pro (1,000 RPD) → cambiar temporalmente a gemini-flash
- Error 429 repetido → RPM o RPD superado → esperar 60s (RPM) o hasta 3 AM Colombia (RPD)
- `ok=0` repetido → problema con la key o el modelo

---

## 20. Operación diaria — comandos útiles {#operacion}

```bash
# Estado del servicio
sudo systemctl status ia-service.service

# Logs en tiempo real
journalctl -u ia-service.service -f

# Reiniciar (kill + start porque restart a veces se cuelga)
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2)
sudo systemctl start ia-service.service

# Health check
curl -s http://localhost:5100/ia/health

# Probar consulta de datos
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"¿Cuánto vendimos este mes?","usuario_id":"santi","canal":"api"}' \
  | python3 -m json.tool

# Probar con agente específico
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"Top 5 productos del mes","agente":"gemini-pro","usuario_id":"santi"}' \
  | python3 -m json.tool

# Ver últimas 10 consultas
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT created_at, tipo_consulta, agente_slug, ok, latencia_ms,
          LEFT(pregunta,50) AS pregunta
   FROM ia_logs ORDER BY created_at DESC LIMIT 10;" 2>/dev/null

# Ver conversaciones activas
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT usuario_id, canal, mensajes_count, updated_at
   FROM ia_conversaciones ORDER BY updated_at DESC LIMIT 10;" 2>/dev/null

# Migrar embeddings faltantes en ia_ejemplos_sql
python3 -c "
import sys; sys.path.insert(0,'scripts')
from ia_service.embeddings import migrar_embeddings_faltantes
migrar_embeddings_faltantes('ori_sil_2')
"
```

---

## 21. Troubleshooting {#troubleshooting}

### Resultado vacío / "no hay datos" incorrecto

1. Revisar si la consulta fue al día/período correcto: `mysql ... "SELECT MAX(fecha_de_creacion) FROM zeffi_facturas_venta_encabezados;" 2>/dev/null`
2. El retry de resultado vacío debería haberlo manejado — revisar `ia_logs` para ver si hubo retry
3. Si el modelo eligió la tabla incorrecta → el catálogo en `<tablas_disponibles>` debería guiarlo

### El enrutador classifica mal (analisis_datos vs conversacion)

Revisar el system prompt del enrutador:
```sql
SELECT system_prompt FROM ia_tipos_consulta WHERE slug='enrutamiento';
```
La distinción clave: `analisis_datos` = datos transaccionales de BD. `conversacion` = estrategia, planes, metas.

### SQL generado con error de sintaxis

El retry automático maneja la mayoría. Si es un patrón recurrente:
1. Agregar el caso como ejemplo en `<ejemplos>` del system prompt
2. Si es un gotcha técnico (campo TEXT, JOINs especiales) → agregar a `<reglas_sql>`
3. NO agregar reglas ultra-específicas que no escalen — ver Sección 1 (Filosofía)

### Servicio no responde / timeout al reiniciar

```bash
# systemctl restart a veces se cuelga — usar kill + start
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2) 2>/dev/null
sleep 1
sudo systemctl start ia-service.service
sleep 2
curl -s http://localhost:5100/ia/health
```

### Key inválida / Error 401

La key fue revocada o expiró. Actualizar en BD:
```sql
UPDATE ia_agentes SET api_key='NUEVA_KEY' WHERE slug='gemini-flash';
```
Luego reiniciar el servicio.

### Rate limit Gemini (RPD agotado a las 3 AM Colombia)

```sql
-- Temporalmente cambiar agente SQL a uno con más RPD
UPDATE ia_tipos_consulta SET agente_sql='gemini-flash-lite' WHERE slug='analisis_datos';
```

---

## 22. Referencia: modelos y costos {#referencia}

### Google Gemini (Nivel de pago 1 — estado OS 2026-03-15)

| Nombre | modelo_id en BD | RPD | Uso en OS |
|---|---|---|---|
| Gemini 2.5 Pro | `gemini-2.5-pro` | 1,000 | SQL complejo, análisis finanzas/comercial |
| Gemini 2.5 Flash | `gemini-2.5-flash` | 10,000 | agente_sql (genera SQL), redacción |
| Gemini 2.5 Flash Lite | `gemini-2.5-flash-lite` | 150,000 | Conversación general, alto volumen |
| Gemma 3 27B | `gemma-3-27b-it` | 14,400 | Enrutador fallback (si groq falla) |
| Gemini 2.5 Flash Image | `gemini-2.5-flash-image` | 70 | Generación de imágenes |
| text-embedding-004 | `text-embedding-004` | Ilimitado | Embeddings semánticos (gratis) |

**Reset cuotas**: 3:00 AM Colombia (medianoche Pacific Time)
**Gemma gotcha**: no soporta `systemInstruction` — el sistema inyecta el prompt en el primer mensaje de usuario automáticamente (`proveedores/google.py`).

### Groq (gratis)

| Modelo | modelo_id en BD | RPD | Uso en OS |
|---|---|---|---|
| Llama 3.3 70B | `llama-3.3-70b-versatile` | 1,000 | **Enrutador principal** (NUNCA agente final) |

### DeepSeek

| Modelo | modelo_id en BD | Input | Output |
|---|---|---|---|
| DeepSeek Chat V3 | `deepseek-chat` | $0.07/M | $1.10/M |
| DeepSeek R1 Reasoner | `deepseek-reasoner` | $0.55/M | $2.19/M (solo nivel 7) |

### Anthropic Claude

| Modelo | modelo_id en BD | Input | Output |
|---|---|---|---|
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | $0.80/M | $4.00/M |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | $3.00/M | $15.00/M |
| Claude Opus 4.6 | `claude-opus-4-6` | $15.00/M | $75.00/M |

### Módulos de código por proveedor

| Proveedor | Módulo | Nota |
|---|---|---|
| Google | `proveedores/google.py` | Gemini + Gemma + imagen (autodetecta por modelo_id) |
| Groq / DeepSeek | `proveedores/openai_compat.py` | API compatible OpenAI |
| Anthropic | `proveedores/anthropic_prov.py` | Header `anthropic-version: 2023-06-01` requerido |

---

## 23. Roles de agentes — configuración en ia_config {#roles-agentes}

Los agentes tienen **roles especializados** dentro del sistema. Desde 2026-03-20 todos los roles configurables se gestionan en `ia_config` (antes eran hardcoded en `servicio.py`).

### Tipos de roles

| Rol | Descripción | Configurable |
|---|---|---|
| **Router** | Clasifica cada consulta (tipo, tema, requiere_sql) | ✅ Sí (4 slots) |
| **Analítico** | Redacta la respuesta final | En `ia_tipos_consulta.agente_preferido` |
| **SQL** | Genera el SQL para analisis_datos | En `ia_tipos_consulta.agente_sql` |
| **Resumen** | Comprime el historial de conversación | ✅ Sí (1 slot) |
| **Depurador** | Consolida la lógica de negocio cuando supera 800 palabras | ✅ Sí (1 slot) |
| **Visión** | Procesa imágenes (selección automática por `capacidad=vision`) | Auto — no configurable |

### Claves en ia_config (2026-03-20)

```sql
SELECT clave, valor FROM ia_config WHERE clave LIKE 'rol_%';
```

| Clave | Valor por defecto | Descripción |
|---|---|---|
| `rol_router_principal` | `groq-llama` | Router 1ª opción |
| `rol_router_suplente_1` | `cerebras-llama` | Router 2ª opción |
| `rol_router_suplente_2` | `gemini-flash-lite` | Router 3ª opción |
| `rol_router_suplente_3` | `gemini-flash` | Router 4ª opción (último fallback) |
| `rol_resumen_agente` | `groq-llama` | Agente que comprime historial |
| `rol_depurador_agente` | `groq-llama` | Agente que consolida lógica de negocio |

### Funciones en servicio.py

```python
def _get_config_simple(clave: str, default: str) -> str:
    """Lee un valor de ia_config sin necesitar conexión externa."""
    try:
        with _db() as conn:
            return _get_config(conn, clave, default)
    except Exception:
        return default

def _slugs_router() -> list[str]:
    """Devuelve la cadena de agentes router en orden, desde ia_config."""
    return [
        _get_config_simple('rol_router_principal',  'groq-llama'),
        _get_config_simple('rol_router_suplente_1', 'cerebras-llama'),
        _get_config_simple('rol_router_suplente_2', 'gemini-flash-lite'),
        _get_config_simple('rol_router_suplente_3', 'gemini-flash'),
    ]
```

### Cambiar un rol (ejemplo: router principal → cerebras)

```sql
UPDATE ia_config SET valor='cerebras-llama' WHERE clave='rol_router_principal';
```
También desde **ia.oscomunidad.com → Roles de agentes**.

### ⚠️ Advertencias de costo por rol

- **Router**: usar SOLO modelos rápidos y gratuitos (groq-llama, cerebras-llama, gemini-flash-lite). Cada consulta hace 1 llamada al router.
- **Resumen/Depurador**: también modelos gratuitos. Se llaman con menor frecuencia.
- **NUNCA usar gemini-pro, claude-sonnet, deepseek-reasoner como router** — son costosos y lentos para una tarea de clasificación simple.

---

## 24. Gestor admin — páginas y funciones {#gestor-admin}

**URL**: ia.oscomunidad.com | **Puerto**: 9200 | **Servicio**: `os-ia-admin.service`

### Sidebar — 6 grupos semánticos

| Grupo | Páginas | Nivel mínimo |
|---|---|---|
| (top) | Dashboard, Playground | 1 |
| Conocimiento | Lógica de negocio, Documentos RAG, Ejemplos SQL | 5+ |
| Comportamiento | Agentes, Roles de agentes, Tipos de consulta | 7 |
| Base de Datos | Esquemas BD, Conexiones BD | 7 |
| Usuarios & Sesiones | Usuarios, Conversaciones, Bot Telegram | 7 |
| Sistema | Configuración, Logs | 3+ |

### Páginas nuevas (2026-03-20)

**Esquemas BD** (`/esquemas`): Ver el DDL que se inyecta en el system prompt por tema. Permite editar qué tablas incluir y agregar notas manuales. Botón "Sincronizar DDL" que llama `POST /api/ia/esquemas/:tema_id/sync`.

**Ejemplos SQL** (`/ejemplos-sql`): Lista 303 pares pregunta→SQL aprendidos. Búsqueda por texto. CRUD completo (crear, editar, eliminar). Columnas: pregunta, tablas_usadas, veces_usado, ultima_vez.

**Conversaciones** (`/conversaciones`): Lista sesiones activas con resumen (tamaño en caracteres), mensajes recientes, y caché SQL. Panel lateral muestra resumen completo, últimos 5 mensajes (user/bot), y datos de la caché SQL. Acciones: limpiar resumen, limpiar caché SQL, eliminar sesión completa.

**Roles de agentes** (`/roles`): 4 secciones:
1. **Enrutamiento** — 4 RolCards configurables (principal + 3 suplentes)
2. **Analítico por tipo** — tabla read-only con agente_preferido + agente_fallback de cada tipo
3. **Auxiliares** — RolCards para resumen y depurador
4. **Visión** — listado de agentes con capacidad=vision (auto-seleccionados)

Advertencia visual si se selecciona agente costoso (gemini-pro, claude-sonnet, deepseek-reasoner, deepseek-chat).

---

*Última actualización: 2026-03-18 — v2.7: caché SQL, router por principios, fallback circuit breaker, retry columnas reales, fix audio bot, logging completo*
